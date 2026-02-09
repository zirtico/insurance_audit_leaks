"""
LLM Normalization Layer (OCR -> Engine JSON)
============================================
Free baseline implementation using deterministic heuristics with an optional
local LLM (Ollama) for richer mapping.
"""

from dataclasses import asdict
from typing import Any, Dict, List, Optional
import json
import re

from llm_mapping import (
    ClaimPayload,
    MappingDiagnostics,
    NormalizedAuditPayload,
    PolicyInfoPayload,
    ClassCodeExposurePayload,
    LOSS_RUN_REQUIRED_FIELDS,
    LOSS_RUN_OPTIONAL_FIELDS,
    FIELD_SYNONYMS,
    LOSS_RUN_MAPPING_RULES,
    STATUS_INFERENCE_RULES,
    ENTITY_RECONCILIATION_RULES,
    MATH_VALIDATION_RULES,
    PAYROLL_MAPPING_RULES,
)
from llm_provider import BaseLLMProvider, default_provider


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace("\n", " ")


def _parse_money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value)
    raw = raw.replace("$", "").replace(",", "").strip()
    raw = raw.replace("(", "-").replace(")", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _table_dict_to_rows(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not table:
        return []
    # pandas.DataFrame.to_dict() default is dict[column][index] = value
    columns = {col: table[col] for col in table}
    indexes = set()
    for col_values in columns.values():
        indexes.update(col_values.keys())
    rows = []
    for idx in sorted(indexes):
        row = {col: columns[col].get(idx) for col in columns}
        rows.append(row)
    return rows


def _find_column(headers: List[str], target: str) -> Optional[str]:
    target_lower = target.lower()
    for header in headers:
        if target_lower == header:
            return header
    for header in headers:
        if target_lower in header:
            return header
    synonyms = FIELD_SYNONYMS.get(target_lower, [])
    for header in headers:
        for synonym in synonyms:
            if synonym in header:
                return header
    return None


def _infer_status(value: Any) -> str:
    if value is None:
        return "Open"
    text = str(value).strip().lower()
    if text in {"c", "closed"}:
        return "Closed"
    if text in {"o", "open"}:
        return "Open"
    if "deny" in text or "non-comp" in text:
        return "Denied"
    return text.title()


def _infer_injury_code(incurred_indemnity: float, incurred_medical: float) -> str:
    if incurred_indemnity == 0 and incurred_medical > 0:
        return "6"
    return ""


def _validate_incurred(
    paid: float,
    reserves: float,
    incurred: float,
    tolerance: float = 1.0
) -> bool:
    return abs((paid + reserves) - incurred) <= tolerance


def _extract_global_fields(raw_text: str) -> Dict[str, str]:
    if not raw_text:
        return {}
    text = raw_text.replace("\n", " ")
    patterns = {
        "policy_number": r"(?:Policy\s*(?:Number|No\.?)|Pol\.?\s*#)\s*[:#]?\s*([A-Z0-9\-]+)",
        "valuation_date": r"(?:Valuation\s*Date|Valuation)\s*[:#]?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
        "policy_period": r"(?:Policy\s*Period|Policy\s*Term)\s*[:#]?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})\s*(?:to|-)\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
        "policy_deductible": r"(?:Deductible|Policy\s*Deductible)\s*[:#]?\s*\\$?([0-9,]+\\.?[0-9]{0,2})",
    }
    results: Dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        if key == "policy_period":
            results["policy_effective_date"] = match.group(1)
            results["policy_expiration_date"] = match.group(2)
        else:
            results[key] = match.group(1)
    if "policy_deductible" in results:
        results["policy_deductible"] = str(_parse_money(results["policy_deductible"]))
    return results


def normalize_loss_run_tables(
    tables_data: List[Dict[str, Any]],
    diagnostics: MappingDiagnostics,
    global_fields: Optional[Dict[str, str]] = None
) -> List[ClaimPayload]:
    claims: List[ClaimPayload] = []
    global_fields = global_fields or {}
    for table in tables_data:
        rows = _table_dict_to_rows(table)
        if not rows:
            continue
        headers = [_normalize_header(h) for h in rows[0].keys()]
        header_map = {h: original for h, original in zip(headers, rows[0].keys())}

        def col(name: str) -> Optional[str]:
            return _find_column(list(header_map.keys()), name)

        col_claim_number = col("claim_number")
        col_claimant_name = col("claimant_name")
        col_accident_date = col("accident_date")
        col_paid_indemnity = col("paid_indemnity")
        col_paid_medical = col("paid_medical")
        col_reserves_indemnity = col("reserves_indemnity")
        col_reserves_medical = col("reserves_medical")
        col_incurred_indemnity = col("incurred_indemnity")
        col_incurred_medical = col("incurred_medical")
        col_status = col("status")
        col_injury_code = col("injury_code")
        col_closure_date = col("closure_date")

        for row in rows:
            def value(col_key: Optional[str]) -> Any:
                if not col_key:
                    return None
                return row.get(header_map[col_key])

            paid_indemnity = _parse_money(value(col_paid_indemnity))
            paid_medical = _parse_money(value(col_paid_medical))
            reserves_indemnity = _parse_money(value(col_reserves_indemnity))
            reserves_medical = _parse_money(value(col_reserves_medical))

            incurred_indemnity = _parse_money(value(col_incurred_indemnity))
            incurred_medical = _parse_money(value(col_incurred_medical))

            if incurred_indemnity == 0.0:
                incurred_indemnity = paid_indemnity + reserves_indemnity
            if incurred_medical == 0.0:
                incurred_medical = paid_medical + reserves_medical

            injury_code = str(value(col_injury_code) or "").strip()
            if not injury_code:
                injury_code = _infer_injury_code(incurred_indemnity, incurred_medical)

            status = _infer_status(value(col_status))

            if not _validate_incurred(paid_medical, reserves_medical, incurred_medical):
                diagnostics.row_level_flags.append(
                    f"Claim {value(col_claim_number)} medical totals mismatch"
                )
            if not _validate_incurred(paid_indemnity, reserves_indemnity, incurred_indemnity):
                diagnostics.row_level_flags.append(
                    f"Claim {value(col_claim_number)} indemnity totals mismatch"
                )

            claims.append(
                ClaimPayload(
                    claim_number=str(value(col_claim_number) or "").strip(),
                    accident_date=str(value(col_accident_date) or "").strip(),
                    claimant_name=str(value(col_claimant_name) or "").strip(),
                    injury_code=injury_code,
                    incurred_indemnity=incurred_indemnity,
                    incurred_medical=incurred_medical,
                    paid_indemnity=paid_indemnity,
                    paid_medical=paid_medical,
                    reserves_indemnity=reserves_indemnity,
                    reserves_medical=reserves_medical,
                    status=status,
                    closure_date=str(value(col_closure_date) or "").strip() or None,
                    claim_notes=" | ".join(
                        note for note in [
                            global_fields.get("policy_number") and f"Policy {global_fields['policy_number']}",
                            global_fields.get("valuation_date") and f"Valuation {global_fields['valuation_date']}",
                        ]
                        if note
                    ),
                )
            )

    return claims


def normalize_payroll_tables(
    tables_data: List[Dict[str, Any]],
    diagnostics: MappingDiagnostics
) -> List[ClassCodeExposurePayload]:
    exposures: Dict[str, ClassCodeExposurePayload] = {}

    for table in tables_data:
        rows = _table_dict_to_rows(table)
        if not rows:
            continue
        headers = [_normalize_header(h) for h in rows[0].keys()]
        header_map = {h: original for h, original in zip(headers, rows[0].keys())}

        def col(name: str) -> Optional[str]:
            return _find_column(list(header_map.keys()), name)

        col_class_code = col("class_code")
        col_payroll = col("payroll")
        col_overtime = col("overtime_pay")
        col_severance = col("severance")
        col_travel = col("travel")
        col_description = col("description")

        for row in rows:
            def value(col_key: Optional[str]) -> Any:
                if not col_key:
                    return None
                return row.get(header_map[col_key])

            class_code = str(value(col_class_code) or "").strip()
            if not class_code:
                continue

            payroll = _parse_money(value(col_payroll))
            overtime = _parse_money(value(col_overtime))
            severance = _parse_money(value(col_severance))
            travel = _parse_money(value(col_travel))
            description = str(value(col_description) or "").strip()

            if class_code not in exposures:
                exposures[class_code] = ClassCodeExposurePayload(
                    class_code=class_code,
                    description=description or f"Class {class_code}",
                    payroll=0.0,
                    elr=0.0,
                    d_ratio=0.0,
                )

            exposure = exposures[class_code]
            exposure.payroll += payroll
            exposure.overtime_earnings += overtime
            exposure.severance_pay += severance
            exposure.travel_reimbursements += travel

    if not exposures:
        diagnostics.warnings.append("No payroll exposures parsed from OCR tables.")

    return list(exposures.values())


def normalize_payroll_rows(
    tables_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    payroll_rows: List[Dict[str, Any]] = []
    for table in tables_data:
        rows = _table_dict_to_rows(table)
        if not rows:
            continue
        headers = [_normalize_header(h) for h in rows[0].keys()]
        header_map = {h: original for h, original in zip(headers, rows[0].keys())}

        def col(name: str) -> Optional[str]:
            return _find_column(list(header_map.keys()), name)

        col_employee = col("employee_name")
        col_job_title = col("job_title")
        col_class_code = col("class_code")
        col_payroll = col("annual_payroll")

        if not any([col_employee, col_job_title, col_class_code, col_payroll]):
            continue

        for row in rows:
            def value(col_key: Optional[str]) -> Any:
                if not col_key:
                    return None
                return row.get(header_map[col_key])

            payroll_rows.append(
                {
                    "employee_name": str(value(col_employee) or "").strip(),
                    "job_title": str(value(col_job_title) or "").strip(),
                    "class_code": str(value(col_class_code) or "").strip(),
                    "annual_payroll": _parse_money(value(col_payroll)),
                }
            )

    return payroll_rows


def normalize_from_ingest(
    ingest_payload: Dict[str, Any],
    policy: Optional[PolicyInfoPayload] = None,
    exposures: Optional[List[ClassCodeExposurePayload]] = None,
    provider: Optional[BaseLLMProvider] = None,
    fail_closed: bool = True
) -> NormalizedAuditPayload:
    provider = provider or default_provider()
    diagnostics = MappingDiagnostics()

    tables_data = ingest_payload.get("tables_data", [])
    raw_text = ingest_payload.get("raw_text") or ingest_payload.get("markdown_content", "")
    global_fields = _extract_global_fields(raw_text)

    claims = normalize_loss_run_tables(tables_data, diagnostics, global_fields)

    if exposures is None:
        exposures = normalize_payroll_tables(tables_data, diagnostics)

    payroll_rows = normalize_payroll_rows(tables_data)

    llm_prompt = build_llm_prompt(ingest_payload)
    llm_response = provider.generate(llm_prompt)
    diagnostics.llm_used = not llm_response.used_fallback
    diagnostics.llm_model = llm_response.model
    if llm_response.used_fallback:
        diagnostics.warnings.append("LLM fallback used; semantic remap skipped.")
    if not llm_response.used_fallback and llm_response.content.strip():
        try:
            llm_json = json.loads(llm_response.content)
            llm_claims = llm_json.get("claims") or llm_json.get("loss_run_claims")
            if llm_claims:
                claims = [ClaimPayload(**claim) for claim in llm_claims]
            llm_exposures = llm_json.get("exposures") or llm_json.get("payroll_exposures")
            if llm_exposures:
                exposures = [ClassCodeExposurePayload(**exp) for exp in llm_exposures]
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            diagnostics.warnings.append(f"LLM normalization parse error: {exc}")

    if ingest_payload.get("summation_audit"):
        audit = ingest_payload["summation_audit"]
        diagnostics.totals_match = audit.get("status") == "PASS"
        diagnostics.totals_variance = audit.get("variance")

    if not claims:
        diagnostics.parsing_errors.append("No claims parsed from OCR tables.")

    if policy is None:
        policy = PolicyInfoPayload(
            policy_number=global_fields.get("policy_number", ""),
            policy_effective_date=global_fields.get("policy_effective_date", ""),
            policy_expiration_date=global_fields.get("policy_expiration_date", ""),
            anniversary_rating_date=global_fields.get("valuation_date", ""),
            total_manual_premium=0.0,
            total_standard_premium=0.0,
            current_mod=1.0,
            state="GA",
            policy_deductible=float(global_fields.get("policy_deductible", 0.0) or 0.0),
        )

    if exposures is None:
        exposures = []

    if fail_closed and (diagnostics.parsing_errors or diagnostics.row_level_flags):
        diagnostics.parsing_errors.append("Fail-closed: manual review required.")

    return NormalizedAuditPayload(
        policy=policy,
        exposures=exposures,
        claims=claims,
        payroll_rows=payroll_rows,
        diagnostics=diagnostics
    )


def build_review_report(normalized: NormalizedAuditPayload) -> Dict[str, Any]:
    return {
        "status": "manual_review_required",
        "parsing_errors": normalized.diagnostics.parsing_errors,
        "row_level_flags": normalized.diagnostics.row_level_flags,
        "warnings": normalized.diagnostics.warnings,
        "llm_used": normalized.diagnostics.llm_used,
        "llm_model": normalized.diagnostics.llm_model,
        "totals_match": normalized.diagnostics.totals_match,
        "totals_variance": normalized.diagnostics.totals_variance,
        "policy": normalized.policy.__dict__,
        "claim_count": len(normalized.claims),
        "exposure_count": len(normalized.exposures),
    }


def build_llm_prompt(ingest_payload: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are an insurance loss-run parser.",
            "Normalize OCR markdown + tables to ClaimPayload JSON.",
            "Rules:",
            *LOSS_RUN_MAPPING_RULES,
            *STATUS_INFERENCE_RULES,
            *ENTITY_RECONCILIATION_RULES,
            *MATH_VALIDATION_RULES,
            *PAYROLL_MAPPING_RULES,
            "Output JSON only.",
            json.dumps(ingest_payload, indent=2),
        ]
    )

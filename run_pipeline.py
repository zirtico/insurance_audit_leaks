"""
End-to-End Pipeline Runner (PDF -> Audit Letter)
================================================
Free baseline runner that ties ingestion, normalization, engine, and letter output.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any
import json

from ingest_files import DoclingIngestionEngine
from llm_normalizer import normalize_from_ingest, build_review_report
from llm_audit_letters import generate_audit_letter
from llm_misclassification import analyze_misclassifications
from mod_engine import run_full_audit, PolicyInfo, Claim, ClassCodeExposure


def run_pipeline(
    pdf_path: str,
    valuation_date: Optional[date] = None,
    review_report_path: str = "review_report.json",
    output_path: Optional[str] = None
) -> str:
    valuation_date = valuation_date or date.today()

    def log(message: str) -> None:
        print(f"[pipeline] {message}")

    def write_error_report(stage: str, error: str, extra: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "status": "pipeline_error",
            "stage": stage,
            "error": error,
        }
        if extra:
            payload.update(extra)
        with open(review_report_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    log("Starting ingestion")
    ingest_engine = DoclingIngestionEngine()
    ingest_payload = ingest_engine.analyze_document(pdf_path)
    if ingest_payload.get("status") != "SUCCESS":
        error_message = ingest_payload.get("reason") or "Unknown ingestion failure"
        write_error_report("ingestion", error_message)
        raise RuntimeError(f"Ingestion failed: {error_message}")
    log("Ingestion complete")

    log("Starting normalization")
    normalized = normalize_from_ingest(ingest_payload)
    if normalized.diagnostics.parsing_errors or normalized.diagnostics.row_level_flags:
        review_report = build_review_report(normalized)
        with open(review_report_path, "w", encoding="utf-8") as handle:
            json.dump(review_report, handle, indent=2)
        raise RuntimeError(
            "Normalization failed; manual review required: "
            f"errors={normalized.diagnostics.parsing_errors} "
            f"flags={normalized.diagnostics.row_level_flags}"
        )
    log("Normalization complete")

    def parse_date(value: str) -> date:
        if not value:
            return valuation_date
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return valuation_date

    policy = PolicyInfo(
        policy_number=normalized.policy.policy_number,
        policy_effective_date=parse_date(normalized.policy.policy_effective_date),
        policy_expiration_date=parse_date(normalized.policy.policy_expiration_date),
        anniversary_rating_date=parse_date(normalized.policy.anniversary_rating_date),
        total_manual_premium=normalized.policy.total_manual_premium,
        total_standard_premium=normalized.policy.total_standard_premium,
        current_mod=normalized.policy.current_mod,
        state=normalized.policy.state,
        policy_deductible=normalized.policy.policy_deductible,
    )

    exposures = [
        ClassCodeExposure(**exp.__dict__)
        for exp in normalized.exposures
    ]

    claims = [
        Claim(
            claim_number=claim.claim_number,
            accident_date=parse_date(claim.accident_date),
            claimant_name=claim.claimant_name,
            injury_code=claim.injury_code,
            incurred_indemnity=claim.incurred_indemnity,
            incurred_medical=claim.incurred_medical,
            paid_indemnity=claim.paid_indemnity,
            paid_medical=claim.paid_medical,
            reserves_indemnity=claim.reserves_indemnity,
            reserves_medical=claim.reserves_medical,
            status=claim.status,
            claim_notes=claim.claim_notes,
            closure_date=parse_date(claim.closure_date) if claim.closure_date else None,
        )
        for claim in normalized.claims
    ]

    try:
        log("Starting engine calculation")
        audit_report = run_full_audit(
            policy_info=policy,
            raw_exposures=exposures,
            raw_claims=claims,
            valuation_date=valuation_date,
        )
        log("Engine calculation complete")
    except Exception as exc:
        write_error_report("engine", str(exc))
        raise

    try:
        log("Starting misclassification analysis")
        misclassification_flags = analyze_misclassifications(normalized.payroll_rows)
        log("Drafting audit letter")
        letter = generate_audit_letter(
            audit_json=json.loads(audit_report.to_json()),
            misclassification_flags=misclassification_flags
        )
    except Exception as exc:
        write_error_report("letter_generation", str(exc))
        raise
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(letter)
        log(f"Letter written to {output_path}")
    log("Pipeline complete")
    return letter


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <path_to_pdf> [output_path]")
        sys.exit(1)

    pdf = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else None
    letter = run_pipeline(pdf, output_path=output)
    print(letter)

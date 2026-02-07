"""
LLM Mapping Contract (OCR -> Normalized JSON)
=============================================
Purpose:
  Provide a deterministic, explicit mapping contract for the LLM layer.
  The OCR pipeline (ingest_files.py) outputs markdown + tables; the LLM
  should normalize that output into the schemas below before calling
  mod_engine.run_full_audit.

This file is intentionally state-agnostic and can be extended as needed.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any


# ═══════════════════════════════════════════════════════════════════════════
# CORE SCHEMAS (aligned to mod_engine.py)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PolicyInfoPayload:
    policy_number: str
    policy_effective_date: str  # YYYY-MM-DD
    policy_expiration_date: str  # YYYY-MM-DD
    anniversary_rating_date: str  # YYYY-MM-DD
    total_manual_premium: float
    total_standard_premium: float
    current_mod: float
    state: str  # e.g., "GA"


@dataclass
class ClassCodeExposurePayload:
    class_code: str
    description: str
    payroll: float
    elr: float
    d_ratio: float
    overtime_earnings: float = 0.0
    overtime_rate: float = 1.5
    executive_officer_payroll: float = 0.0
    severance_pay: float = 0.0
    travel_reimbursements: float = 0.0
    subcontractor_payroll: float = 0.0


@dataclass
class ClaimPayload:
    claim_number: str
    accident_date: str  # YYYY-MM-DD
    claimant_name: str
    injury_code: str  # "6" for med-only
    incurred_indemnity: float
    incurred_medical: float
    paid_indemnity: float
    paid_medical: float
    reserves_indemnity: float
    reserves_medical: float
    status: str  # Open / Closed / Denied
    last_payment_date: Optional[str] = None
    claim_notes: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# SUPPORTING SCHEMAS (for misclassification & validation)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PayrollRowPayload:
    employee_name: str
    job_title: str
    class_code: Optional[str]
    annual_payroll: float
    job_duties: Optional[str] = None
    employee_id: Optional[str] = None
    officer_indicator: Optional[bool] = None


@dataclass
class MappingDiagnostics:
    parsing_errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    totals_match: Optional[bool] = None
    totals_variance: Optional[float] = None


@dataclass
class NormalizedAuditPayload:
    policy: PolicyInfoPayload
    exposures: List[ClassCodeExposurePayload]
    claims: List[ClaimPayload]
    payroll_rows: List[PayrollRowPayload] = field(default_factory=list)
    diagnostics: MappingDiagnostics = field(default_factory=MappingDiagnostics)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════
# LLM MAPPING GUIDANCE (FIELD SYNONYMS & REQUIRED FIELDS)
# ═══════════════════════════════════════════════════════════════════════════

LOSS_RUN_REQUIRED_FIELDS = {
    "identifiers": ["claim_number", "claimant_name", "accident_date"],
    "financials": [
        "paid_medical",
        "paid_indemnity",
        "reserves_medical",
        "reserves_indemnity",
        "incurred_medical",
        "incurred_indemnity",
    ],
    "status": ["status", "injury_code"],
    "legal_recovery": ["subrogation_amount", "litigated_indicator"],
    "description": ["nature_of_injury", "cause_of_loss", "body_part"],
}

PAYROLL_REQUIRED_FIELDS = {
    "employee_id": ["employee_id", "ssn_last4", "name"],
    "earnings_type": ["regular_pay", "overtime_pay", "double_time"],
    "exclusions": ["severance", "tips", "third_party_sick_pay"],
    "dates": ["pay_period_start", "pay_period_end", "check_date"],
    "classification": ["class_code"],
}

SUI_REQUIRED_FIELDS = {
    "employee_info": ["full_name", "ssn"],
    "job_info": ["occupational_title", "job_description"],
    "quarterly_pay": ["gross_wages"],
    "officer_status": ["officer_indicator"],
}

FIELD_SYNONYMS = {
    "paid_indemnity": ["indem pd", "loss paid", "comp paid", "paid indemnity"],
    "paid_medical": ["medical paid", "med paid", "paid medical"],
    "reserves_indemnity": ["indem res", "indemnity reserve", "case reserve"],
    "reserves_medical": ["medical reserve", "med res", "case reserve medical"],
    "incurred_indemnity": ["incurred indemnity", "indem incurred", "total indemnity"],
    "incurred_medical": ["incurred medical", "med incurred", "total medical"],
    "claim_number": ["claim #", "claim no", "claim id"],
    "accident_date": ["loss date", "injury date", "accident date"],
    "injury_code": ["ij code", "injury code", "inj code"],
    "status": ["claim status", "status"],
    "overtime_pay": ["ot pay", "overtime pay", "time and a half"],
    "double_time": ["double time", "2x", "double-time"],
    "regular_pay": ["regular pay", "base pay", "straight time"],
}


def required_fields_for(document_type: str) -> Dict[str, List[str]]:
    if document_type == "loss_run":
        return LOSS_RUN_REQUIRED_FIELDS
    if document_type == "payroll_journal":
        return PAYROLL_REQUIRED_FIELDS
    if document_type == "sui_report":
        return SUI_REQUIRED_FIELDS
    raise ValueError(f"Unknown document_type: {document_type}")

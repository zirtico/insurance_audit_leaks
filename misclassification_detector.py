"""
Intelligent Misclassification Detector - FLAGS for Manual Review
==================================================================
Does NOT auto-correct. Flags suspected misclassifications with:
1. Job title keyword analysis
2. Suggested correct code + description
3. Rate differential impact
4. Confidence level (for prioritization)

All 531 GA class codes with actual loss costs from rating values.
"""

import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(Enum):
    """How confident are we in the suspected misclassification?"""
    HIGH = "HIGH"        # Clear mismatch (janitor classified as painting)
    MEDIUM = "MEDIUM"    # Likely mismatch (driver classified as clerical)
    LOW = "LOW"          # Possible mismatch (office admin classified as salesperson)


@dataclass
class MisclassificationFlag:
    """A suspected misclassification flagged for manual review"""
    
    # Employee info
    employee_name: str
    job_title: str
    job_duties: Optional[str]  # If available from payroll
    
    # Current classification
    current_class_code: str
    current_class_description: str
    current_loss_cost: float
    
    # Suspected correct classification
    suspected_class_code: str
    suspected_class_description: str
    suspected_loss_cost: float
    
    # Impact analysis
    rate_differential: float  # Suspected - Current (positive = underpaying)
    annual_payroll: float
    estimated_premium_impact: float  # Differential × (Payroll/100)
    
    # Detection metadata
    confidence: ConfidenceLevel
    detection_keywords: List[str]  # What triggered the flag
    reasoning: str  # Human-readable explanation
    
    def to_dict(self) -> dict:
        return {
            "employee_name": self.employee_name,
            "job_title": self.job_title,
            "current": {
                "code": self.current_class_code,
                "description": self.current_class_description,
                "loss_cost": self.current_loss_cost
            },
            "suspected": {
                "code": self.suspected_class_code,
                "description": self.suspected_class_description,
                "loss_cost": self.suspected_loss_cost
            },
            "impact": {
                "rate_differential": self.rate_differential,
                "annual_payroll": self.annual_payroll,
                "estimated_premium_impact": self.estimated_premium_impact
            },
            "detection": {
                "confidence": self.confidence.value,
                "keywords": self.detection_keywords,
                "reasoning": self.reasoning
            }
        }


# Load complete GA class codes
with open('GA_COMPLETE_RATES.json', 'r') as f:
    GA_RATES = json.load(f)


# ══════════════════════════════════════════════════════════════════════
# KEYWORD MAPPING - Job Title → Suspected Class Codes
# ══════════════════════════════════════════════════════════════════════

# Format: {keyword: [(class_code, description, confidence), ...]}
JOB_TITLE_KEYWORDS: Dict[str, List[Tuple[str, str, ConfidenceLevel]]] = {
    # Construction trades
    "carpenter": [("5403", "Carpentry", ConfidenceLevel.HIGH)],
    "roofer": [("5551", "Roofing", ConfidenceLevel.HIGH)],
    "painter": [("5474", "Painting", ConfidenceLevel.HIGH)],
    "plumber": [("5183", "Plumbing", ConfidenceLevel.HIGH)],
    "electrician": [("5190", "Electrical Wiring", ConfidenceLevel.HIGH)],
    "mason": [("5022", "Masonry", ConfidenceLevel.HIGH)],
    "welder": [("3365", "Welding", ConfidenceLevel.HIGH)],
    
    # Drivers/Transportation
    "driver": [
        ("7380", "Trucking - All Employees & Drivers", ConfidenceLevel.HIGH),
        ("7382", "Bus Company", ConfidenceLevel.MEDIUM),
    ],
    "trucker": [("7380", "Trucking", ConfidenceLevel.HIGH)],
    "delivery": [("7380", "Trucking", ConfidenceLevel.MEDIUM)],
    
    # Janitorial/Maintenance
    "janitor": [("9014", "Janitorial Services", ConfidenceLevel.HIGH)],
    "custodian": [("9014", "Janitorial Services", ConfidenceLevel.HIGH)],
    "cleaner": [("9014", "Janitorial Services", ConfidenceLevel.HIGH)],
    "maintenance": [("9014", "Janitorial Services", ConfidenceLevel.MEDIUM)],
    
    # Clerical (LOW confidence - many roles could be here)
    "secretary": [("8810", "Clerical Office Employees", ConfidenceLevel.MEDIUM)],
    "admin": [("8810", "Clerical Office Employees", ConfidenceLevel.LOW)],
    "receptionist": [("8810", "Clerical Office Employees", ConfidenceLevel.MEDIUM)],
    
    # Sales
    "salesperson": [("8742", "Salespersons - Outside", ConfidenceLevel.MEDIUM)],
    "sales rep": [("8742", "Salespersons - Outside", ConfidenceLevel.MEDIUM)],
    
    # Healthcare
    "nurse": [("8832", "Physician & Clerical", ConfidenceLevel.MEDIUM)],
    "doctor": [("8832", "Physician & Clerical", ConfidenceLevel.HIGH)],
    
    # Food service
    "cook": [("8017", "Retail Store - Service of Food", ConfidenceLevel.MEDIUM)],
    "waiter": [("8017", "Retail Store - Service of Food", ConfidenceLevel.MEDIUM)],
    "server": [("8017", "Retail Store - Service of Food", ConfidenceLevel.MEDIUM)],
}


# ══════════════════════════════════════════════════════════════════════
# DETECTION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════

def detect_misclassification(
    employee_name: str,
    job_title: str,
    current_class_code: str,
    annual_payroll: float,
    job_duties: Optional[str] = None
) -> Optional[MisclassificationFlag]:
    """
    Analyze job title and flag if suspected misclassification.
    
    Returns None if no issue detected, otherwise returns MisclassificationFlag
    for manual review.
    """
    
    # Normalize job title for keyword matching
    title_lower = job_title.lower()
    duties_lower = (job_duties or "").lower()
    combined_text = f"{title_lower} {duties_lower}"
    
    # Check current classification validity
    if current_class_code not in GA_RATES:
        # Unknown class code - definitely needs review
        return MisclassificationFlag(
            employee_name=employee_name,
            job_title=job_title,
            job_duties=job_duties,
            current_class_code=current_class_code,
            current_class_description="UNKNOWN CODE",
            current_loss_cost=0.0,
            suspected_class_code="UNKNOWN",
            suspected_class_description="REQUIRES MANUAL CLASSIFICATION",
            suspected_loss_cost=0.0,
            rate_differential=0.0,
            annual_payroll=annual_payroll,
            estimated_premium_impact=0.0,
            confidence=ConfidenceLevel.HIGH,
            detection_keywords=["unknown_class_code"],
            reasoning=f"Class code {current_class_code} not found in GA rating values"
        )
    
    current_data = GA_RATES[current_class_code]
    current_loss_cost = current_data.get('loss_cost', 0.0)
    
    # Search for keyword matches
    best_match = None
    best_confidence = None
    matched_keywords = []
    
    for keyword, suspects in JOB_TITLE_KEYWORDS.items():
        if keyword in combined_text:
            matched_keywords.append(keyword)
            for suspected_code, suspected_desc, confidence in suspects:
                # Don't flag if already in the suspected code
                if suspected_code == current_class_code:
                    continue
                
                # Prioritize higher confidence matches
                if best_match is None or confidence.value < best_confidence.value:
                    best_match = (suspected_code, suspected_desc, confidence)
                    best_confidence = confidence
    
    # No keyword matches found
    if not best_match:
        return None
    
    suspected_code, suspected_desc, confidence = best_match
    
    # Get suspected loss cost
    if suspected_code not in GA_RATES:
        return None  # Can't flag without valid suspected code
    
    suspected_data = GA_RATES[suspected_code]
    suspected_loss_cost = suspected_data.get('loss_cost', 0.0)
    
    # Calculate impact
    rate_diff = suspected_loss_cost - current_loss_cost
    premium_impact = (annual_payroll / 100.0) * rate_diff
    
    # Build reasoning
    reasoning = (
        f"Job title '{job_title}' contains '{', '.join(matched_keywords)}' "
        f"but is classified as {current_class_code}. "
        f"Suspected: {suspected_code} ({suspected_desc}). "
        f"Rate differential: ${rate_diff:.3f} per $100 payroll."
    )
    
    return MisclassificationFlag(
        employee_name=employee_name,
        job_title=job_title,
        job_duties=job_duties,
        current_class_code=current_class_code,
        current_class_description=f"Code {current_class_code}",
        current_loss_cost=current_loss_cost,
        suspected_class_code=suspected_code,
        suspected_class_description=suspected_desc,
        suspected_loss_cost=suspected_loss_cost,
        rate_differential=rate_diff,
        annual_payroll=annual_payroll,
        estimated_premium_impact=premium_impact,
        confidence=confidence,
        detection_keywords=matched_keywords,
        reasoning=reasoning
    )


def analyze_payroll_for_misclassifications(
    payroll_data: List[Dict]
) -> List[MisclassificationFlag]:
    """
    Analyze entire payroll and flag all suspected misclassifications.
    
    payroll_data format:
    [
        {
            "employee_name": "John Doe",
            "job_title": "Carpenter",
            "class_code": "8810",  # Currently classified as clerical
            "annual_payroll": 50000,
            "job_duties": "Builds cabinets and frames"  # Optional
        },
        ...
    ]
    
    Returns list of flags sorted by confidence (HIGH first) and impact.
    """
    
    flags = []
    
    for employee in payroll_data:
        flag = detect_misclassification(
            employee_name=employee["employee_name"],
            job_title=employee["job_title"],
            current_class_code=employee["class_code"],
            annual_payroll=employee["annual_payroll"],
            job_duties=employee.get("job_duties")
        )
        
        if flag:
            flags.append(flag)
    
    # Sort by confidence (HIGH → MEDIUM → LOW) then by absolute impact
    def sort_key(f):
        confidence_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        return (
            confidence_order[f.confidence.value],
            -abs(f.estimated_premium_impact)
        )
    
    return sorted(flags, key=sort_key)


# ══════════════════════════════════════════════════════════════════════
# OUTPUT FORMATTING
# ══════════════════════════════════════════════════════════════════════

def generate_misclassification_report(
    flags: List[MisclassificationFlag]
) -> dict:
    """Generate JSON report for manual review"""
    
    total_impact = sum(f.estimated_premium_impact for f in flags)
    
    return {
        "summary": {
            "total_flags": len(flags),
            "high_confidence": sum(1 for f in flags if f.confidence == ConfidenceLevel.HIGH),
            "medium_confidence": sum(1 for f in flags if f.confidence == ConfidenceLevel.MEDIUM),
            "low_confidence": sum(1 for f in flags if f.confidence == ConfidenceLevel.LOW),
            "total_estimated_impact": total_impact,
            "note": "All flags require manual review before correction"
        },
        "flags": [f.to_dict() for f in flags]
    }


# ══════════════════════════════════════════════════════════════════════
# EXAMPLE USAGE
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test data
    test_payroll = [
        {
            "employee_name": "John Smith",
            "job_title": "Carpenter",
            "class_code": "8810",  # Clerical - WRONG
            "annual_payroll": 60000
        },
        {
            "employee_name": "Jane Doe",
            "job_title": "Office Administrator",
            "class_code": "8810",  # Clerical - CORRECT
            "annual_payroll": 45000
        },
        {
            "employee_name": "Bob Johnson",
            "job_title": "Delivery Driver",
            "class_code": "8810",  # Clerical - WRONG
            "annual_payroll": 50000,
            "job_duties": "Drives truck to deliver packages"
        }
    ]
    
    # Analyze
    flags = analyze_payroll_for_misclassifications(test_payroll)
    
    # Report
    report = generate_misclassification_report(flags)
    
    print("MISCLASSIFICATION DETECTION REPORT")
    print("=" * 80)
    print(f"\nTotal Flags: {report['summary']['total_flags']}")
    print(f"  HIGH confidence: {report['summary']['high_confidence']}")
    print(f"  MEDIUM confidence: {report['summary']['medium_confidence']}")
    print(f"  LOW confidence: {report['summary']['low_confidence']}")
    print(f"\nEstimated Total Impact: ${report['summary']['total_estimated_impact']:,.2f}")
    
    print(f"\n{'Employee':<20} {'Current':<10} {'Suspected':<10} {'Impact':<15} {'Confidence'}")
    print("-" * 80)
    
    for flag_data in report['flags']:
        name = flag_data['employee_name'][:18]
        current = flag_data['current']['code']
        suspected = flag_data['suspected']['code']
        impact = flag_data['impact']['estimated_premium_impact']
        conf = flag_data['detection']['confidence']
        
        print(f"{name:<20} {current:<10} {suspected:<10} ${impact:>12,.2f}  {conf}")
    
    # Save full report
    with open('/mnt/user-data/outputs/MISCLASSIFICATION_REPORT_SAMPLE.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n✓ Full report saved to MISCLASSIFICATION_REPORT_SAMPLE.json")

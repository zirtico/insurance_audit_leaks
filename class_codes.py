"""
Workers Compensation Class Code Lookup Tables
==============================================

Uses Missouri and New York class code guides (free/public) as proxy for NCCI Scopes Manual.
These are ~90% accurate for all NCCI states.

Primary use: Leak #8 detection (Class Code 8810 misclassification)
"""

from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class ClassCodeDefinition:
    """Standard class code information"""
    code: str
    description: str
    jobs_included: str
    hazard_group: str = "Unknown"  # Will be populated from rating values
    
    @property
    def is_clerical(self) -> bool:
        return self.code == "8810"
    
    @property
    def is_construction(self) -> bool:
        construction_ranges = [
            (5000, 6999),  # Construction/Contracting
        ]
        code_num = int(self.code)
        return any(start <= code_num <= end for start, end in construction_ranges)
    
    @property
    def is_manufacturing(self) -> bool:
        mfg_ranges = [
            (2000, 4999),  # Manufacturing
        ]
        code_num = int(self.code)
        return any(start <= code_num <= end for start, end in mfg_ranges)


# ═══════════════════════════════════════════════════════════════════════════
# MISSOURI CLASS CODES (From MO_class_codes.pdf)
# ═══════════════════════════════════════════════════════════════════════════

MO_CLASS_CODES = {
    "5192": ClassCodeDefinition(
        code="5192",
        description="Coin Operated Machines, Repair and Installation",
        jobs_included="Install and Repair Parking Meters and Signs"
    ),
    "5506": ClassCodeDefinition(
        code="5506",
        description="Street, Road Maintenance",
        jobs_included="Street Maintenance and Construction, Street Cleaning"
    ),
    "6045": ClassCodeDefinition(
        code="6045",
        description="Levee Construction",
        jobs_included="Levee Construction"
    ),
    "6217": ClassCodeDefinition(
        code="6217",
        description="Sanitary Land Fill",
        jobs_included="Employees Working at Land or Excavation Fill/Compost Sites"
    ),
    "6306": ClassCodeDefinition(
        code="6306",
        description="Sewer Construction or Maintenance",
        jobs_included="Sewer Construction and Maintenance"
    ),
    "6836": ClassCodeDefinition(
        code="6836",
        description="Marina",
        jobs_included="Marina Employees"
    ),
    "7382": ClassCodeDefinition(
        code="7382",
        description="Bus Company Employees",
        jobs_included="Bus Drivers"
    ),
    "7403": ClassCodeDefinition(
        code="7403",
        description="Aircraft Operation and Employees or Airport Employees",
        jobs_included="All Airport Employees"
    ),
    "7502": ClassCodeDefinition(
        code="7502",
        description="Gas Department Employees",
        jobs_included="Gas Department Employees"
    ),
    "7520": ClassCodeDefinition(
        code="7520",
        description="Waterworks Operation",
        jobs_included="Waterworks"
    ),
    "7539": ClassCodeDefinition(
        code="7539",
        description="Electric Power Company",
        jobs_included="Electrical Production and Distribution"
    ),
    "7580": ClassCodeDefinition(
        code="7580",
        description="Sewage Treatment",
        jobs_included="Sewage Treatment and/or Wastewater Plant Employees"
    ),
    "7600": ClassCodeDefinition(
        code="7600",
        description="Telecommunications",
        jobs_included="Internet/Cable TV Equipment Installation or Maintenance"
    ),
    "7705": ClassCodeDefinition(
        code="7705",
        description="EMS",
        jobs_included="Ambulance Services and Emergency Medical Services"
    ),
    "7710": ClassCodeDefinition(
        code="7710",
        description="Fire Fighters",
        jobs_included="Fire Fighters (Including Volunteer)"
    ),
    "7720": ClassCodeDefinition(
        code="7720",
        description="Police Officers",
        jobs_included="Police Officers (full time and reserve), Corrections Officers, Bailiffs, Crossing Guards, Turn Keys"
    ),
    "8017": ClassCodeDefinition(
        code="8017",
        description="Food Service/Concessions",
        jobs_included="All Employees Involved in Sale of Food/Beverages and Door Attendants"
    ),
    "8264": ClassCodeDefinition(
        code="8264",
        description="Recycling",
        jobs_included="All Employees Involved in Recycling Activities"
    ),
    "8391": ClassCodeDefinition(
        code="8391",
        description="Auto Repair Shop",
        jobs_included="All Auto Repair Employees Including Vehicle Maintenance And Mechanics"
    ),
    "8601": ClassCodeDefinition(
        code="8601",
        description="Engineers",
        jobs_included="Contracted Engineers From Architectural or Engineering Firms"
    ),
    "8742": ClassCodeDefinition(
        code="8742",
        description="Social Services Employees, Salespersons/Collectors",
        jobs_included="Social Services Workers or Salesmen That Travel"
    ),
    "8810": ClassCodeDefinition(
        code="8810",
        description="Clerical",
        jobs_included="All Clerical Employees Including Administration, Secretaries, Clerks, Accountants, Data Processing or Computer Operation, All Library Employees, Dispatchers, Judges, Court Clerks, Mayors, Councils, Trustees, Elected Officials, Cable-Broadcasting, Tourism, Board of Directors, Aldermen, Assessors, Treasurers, Collectors"
    ),
    "8820": ClassCodeDefinition(
        code="8820",
        description="City Attorney & Prosecuting Attorney",
        jobs_included="All Attorneys; including the City Attorney and Prosecuting Attorney if they are Employees"
    ),
    "8824": ClassCodeDefinition(
        code="8824",
        description="Senior Center – Health Care",
        jobs_included="Senior Center Employees providing Health Care"
    ),
    "8825": ClassCodeDefinition(
        code="8825",
        description="Senior Center – Food Service",
        jobs_included="Senior Center Employees providing Food Service"
    ),
    "8826": ClassCodeDefinition(
        code="8826",
        description="Senior Center – All Other",
        jobs_included="All Other Senior Center Employees"
    ),
    "8831": ClassCodeDefinition(
        code="8831",
        description="Animal Control",
        jobs_included="Dog Catchers, Animal Shelter Employees, Rabies Control"
    ),
    "8832": ClassCodeDefinition(
        code="8832",
        description="Physician",
        jobs_included="All Health Department Employees"
    ),
    "8869": ClassCodeDefinition(
        code="8869",
        description="Day Care Facility",
        jobs_included="All Employees Involved in Childcare/Babysitting"
    ),
    "9014": ClassCodeDefinition(
        code="9014",
        description="Janitorial Services",
        jobs_included="All Janitors and Building Maintenance Employees"
    ),
    "9015": ClassCodeDefinition(
        code="9015",
        description="Swimming Pool/Buildings, NOC",
        jobs_included="All Swimming Pool Employees Including Lifeguards"
    ),
    "9060": ClassCodeDefinition(
        code="9060",
        description="Golf Course Employees",
        jobs_included="Golf Course Employees"
    ),
    "9063": ClassCodeDefinition(
        code="9063",
        description="Umpires and Instructors",
        jobs_included="All Umpires and Instructors, Including YMCA Teachers and Instructors, Whether Paid on Fee Basis or Through City Payroll"
    ),
    "9102": ClassCodeDefinition(
        code="9102",
        description="Parks Employees",
        jobs_included="Park Maintenance and Cemetery Mowing"
    ),
    "9220": ClassCodeDefinition(
        code="9220",
        description="Cemetery Operation",
        jobs_included="Grave Digging and Ground Maintenance"
    ),
    "9403": ClassCodeDefinition(
        code="9403",
        description="Garbage or Refuse Collection",
        jobs_included="Garbage Collection"
    ),
    "9410": ClassCodeDefinition(
        code="9410",
        description="Municipal Employees, NOC",
        jobs_included="Building Inspectors, Engineers Or Building Inspectors on City Payroll, Property Appraisers"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# NEW YORK CLASS CODES (From NY_class_codes.pdf - subset)
# ═══════════════════════════════════════════════════════════════════════════

NY_CLASS_CODES = {
    "0005": ClassCodeDefinition(
        code="0005",
        description="Nursery Employees & Drivers",
        jobs_included="Nursery Employees & Drivers"
    ),
    "2003": ClassCodeDefinition(
        code="2003",
        description="Bakery & Route Salespersons, Route Supervisors, Drivers",
        jobs_included="Bakery & Route Salespersons, Route Supervisors, Drivers"
    ),
    "2501": ClassCodeDefinition(
        code="2501",
        description="Clothing Mfg.",
        jobs_included="Clothing Manufacturing"
    ),
    "5022": ClassCodeDefinition(
        code="5022",
        description="Masonry NOC",
        jobs_included="Masonry"
    ),
    "5183": ClassCodeDefinition(
        code="5183",
        description="Plumbing NOC & Drivers",
        jobs_included="Plumbing"
    ),
    "5190": ClassCodeDefinition(
        code="5190",
        description="Electrical Wiring-Within Buildings-& Drivers",
        jobs_included="Electrical Wiring"
    ),
    "5403": ClassCodeDefinition(
        code="5403",
        description="Carpentry NOC",
        jobs_included="Carpentry"
    ),
    "5474": ClassCodeDefinition(
        code="5474",
        description="Painting Or Decorating NOC & Drivers",
        jobs_included="Painting"
    ),
    "5506": ClassCodeDefinition(
        code="5506",
        description="Street Or Road Construction-Paving Or Repaving-& Drivers",
        jobs_included="Road Construction"
    ),
    "5645": ClassCodeDefinition(
        code="5645",
        description="Carpentry-Detached One Or Two-Family Dwellings",
        jobs_included="Residential Carpentry"
    ),
    "8001": ClassCodeDefinition(
        code="8001",
        description="Florist Store & Drivers",
        jobs_included="Florist"
    ),
    "8006": ClassCodeDefinition(
        code="8006",
        description="Grocery Store-Retail-No Fresh Meat",
        jobs_included="Grocery Store"
    ),
    "8008": ClassCodeDefinition(
        code="8008",
        description="Clothing Or Wearing Apparel Store-Retail",
        jobs_included="Clothing Store"
    ),
    "8017": ClassCodeDefinition(
        code="8017",
        description="Retail Store NOC-No Service Of Food",
        jobs_included="General Retail"
    ),
    "8033": ClassCodeDefinition(
        code="8033",
        description="Supermarket-Retail",
        jobs_included="Supermarket"
    ),
    "8044": ClassCodeDefinition(
        code="8044",
        description="Furniture Store-Wholesale Or Retail-& Drivers",
        jobs_included="Furniture Store"
    ),
    "8391": ClassCodeDefinition(
        code="8391",
        description="Automobile Sales Or Service Agency-All Operations-& Drivers",
        jobs_included="Auto Sales/Service"
    ),
    "8601": ClassCodeDefinition(
        code="8601",
        description="Engineer Or Architect - Consulting",
        jobs_included="Engineering/Architecture"
    ),
    "8742": ClassCodeDefinition(
        code="8742",
        description="Salespersons, Collectors Or Messengers-Outside",
        jobs_included="Outside Sales"
    ),
    "8810": ClassCodeDefinition(
        code="8810",
        description="Clerical Office Employees NOC",
        jobs_included="Clerical Office Employees"
    ),
    "8820": ClassCodeDefinition(
        code="8820",
        description="Attorney-All Employees-& Clerical, Messengers, Drivers",
        jobs_included="Attorneys"
    ),
    "8832": ClassCodeDefinition(
        code="8832",
        description="Physician & Clerical",
        jobs_included="Physicians"
    ),
    "8868": ClassCodeDefinition(
        code="8868",
        description="School-Professional Employees & Clerical",
        jobs_included="School Employees"
    ),
    "8869": ClassCodeDefinition(
        code="8869",
        description="Day Care Centers-Children-Professional Employees & Clerical, Salespersons",
        jobs_included="Day Care"
    ),
    "9014": ClassCodeDefinition(
        code="9014",
        description="Exterminator & Drivers",
        jobs_included="Pest Control"
    ),
    "9060": ClassCodeDefinition(
        code="9060",
        description="Club-Country, Golf, Fishing Or Yacht-& Clerical",
        jobs_included="Country Club"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED CLASS CODE LOOKUP
# ═══════════════════════════════════════════════════════════════════════════

# Combine MO and NY codes (NY takes precedence for duplicates)
ALL_CLASS_CODES = {**MO_CLASS_CODES, **NY_CLASS_CODES}


def lookup_class_code(code: str) -> Optional[ClassCodeDefinition]:
    """
    Look up class code definition.
    
    Returns None if code not found (will need manual review)
    """
    return ALL_CLASS_CODES.get(code)


def is_clerical_misclassified(
    employee_title: str,
    assigned_class_code: str
) -> bool:
    """
    Detect if an employee should be 8810 but isn't.
    
    Leak #8: Class Code 8810 misclassification
    """
    
    # Keywords that indicate clerical work
    clerical_keywords = [
        "admin", "secretary", "clerk", "accountant", "bookkeeper",
        "receptionist", "data entry", "office", "dispatcher",
        "manager", "supervisor" (if not field supervisor)
    ]
    
    title_lower = employee_title.lower()
    is_clerical_job = any(kw in title_lower for kw in clerical_keywords)
    
    # If job is clerical but not assigned to 8810, it's a leak
    return is_clerical_job and assigned_class_code != "8810"


def get_typical_rate_differential(
    from_code: str,
    to_code: str = "8810"
) -> float:
    """
    Estimate rate differential for misclassification impact.
    
    This is a rough estimate - actual rates vary by state/year.
    Returns a multiplier (e.g., 5.0 means from_code is 5x more expensive)
    """
    
    # Typical rate ranges (per $100 payroll)
    rate_estimates = {
        "8810": 0.05,   # Clerical (very low)
        "5403": 4.00,   # Carpentry (high)
        "5645": 12.00,  # Residential carpentry (very high)
        "5022": 5.50,   # Masonry (high)
        "5474": 6.00,   # Painting (high)
        "5506": 3.00,   # Road construction (medium-high)
        "8391": 2.00,   # Auto repair (medium)
        "9014": 1.50,   # Janitorial (medium-low)
    }
    
    from_rate = rate_estimates.get(from_code, 2.00)  # Default medium
    to_rate = rate_estimates.get(to_code, 0.05)  # Default to clerical
    
    return from_rate / to_rate


# ═══════════════════════════════════════════════════════════════════════════
# COMMON MISCLASSIFICATION PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

COMMON_MISCLASSIFICATIONS = {
    # Pattern: (Job Title Keywords, Correct Code, Common Incorrect Code)
    "office_to_construction": {
        "keywords": ["admin", "secretary", "office manager", "bookkeeper"],
        "correct_code": "8810",
        "common_incorrect": ["5403", "5645", "5022", "5474"]
    },
    "driver_misclass": {
        "keywords": ["driver", "delivery"],
        "correct_code": "7380",  # Drivers NOC
        "common_incorrect": ["8810"]  # Sometimes misclassified as clerical
    },
    "salesperson_misclass": {
        "keywords": ["sales", "salesperson", "sales rep"],
        "correct_code": "8742",  # Outside sales
        "common_incorrect": ["8810"]
    }
}


def detect_misclassification_pattern(
    employee_title: str,
    assigned_code: str
) -> Optional[Dict]:
    """
    Detect common misclassification patterns.
    
    Returns: {
        "pattern": "office_to_construction",
        "correct_code": "8810",
        "confidence": 0.90
    }
    """
    
    title_lower = employee_title.lower()
    
    for pattern_name, pattern_info in COMMON_MISCLASSIFICATIONS.items():
        if any(kw in title_lower for kw in pattern_info["keywords"]):
            if assigned_code in pattern_info["common_incorrect"]:
                return {
                    "pattern": pattern_name,
                    "correct_code": pattern_info["correct_code"],
                    "confidence": 0.85  # High confidence for known patterns
                }
    
    return None

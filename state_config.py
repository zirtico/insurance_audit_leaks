"""
State-Specific Configuration for Experience Mod Calculations
==============================================================

This file contains all state-specific parameters needed for mod calculations.
Each state has its own configuration class that can be easily swapped.

For NCCI states: Use standard NCCI formulas with state-specific values
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import date


# ═══════════════════════════════════════════════════════════════════════════
# BASE STATE CONFIG (Template for all states)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class StateConfig:
    """Base configuration class - all states must implement these"""
    
    state_code: str
    state_name: str
    
    # Experience Rating Parameters
    split_point: float
    sal_per_claim: float  # State Accident Limitation (single claim cap)
    sal_multiple_claim: float  # Multiple claim cap (usually 2× SAL)
    g_value: float  # G parameter for W/B calculation
    s_value: float  # S = G × 250,000
    
    # ERA (Experience Rating Adjustment)
    is_era_state: bool  # Does 70% med-only discount apply?
    era_discount: float = 0.30  # Med-only ratable portion (30% of total)
    
    # System Type
    is_ncci_state: bool  # NCCI vs independent bureau
    bureau_name: str  # "NCCI", "WCIRB", "NYCIRB", "PCRB", etc.
    
    # Effective Dates
    effective_date: date
    elr_decimals: int = 3  # 2026 standard = 3 decimals
    
    # Minimum Premium Eligibility
    min_expected_losses: float = 5000.0  # Typical NCCI threshold
    
    # Class Code Tables (for leak detection)
    class_codes: Dict[str, 'ClassCodeInfo'] = None  # Will be loaded separately
    
    def calculate_w_and_b(self, expected_losses: float) -> Tuple[float, float]:
        """
        Calculate W (weighting) and B (ballast) using state-specific formula.
        NCCI states use deterministic formula; others may override.
        """
        if self.is_ncci_state:
            return self._calculate_w_b_ncci(expected_losses)
        else:
            raise NotImplementedError(f"W/B calculation not implemented for {self.state_code}")
    
    def _calculate_w_b_ncci(self, E: float) -> Tuple[float, float]:
        """
        NCCI Standard Formulas (2026):
        
        Kp = (E × (E + 0.01028S)) / (0.75E + 0.8153S)  [min: 7,500]
        Ke = (E × (E + 0.0204S)) / (0.1E + 0.5109S)
        B = Kp
        W = (E + Ke) / (E + Kp)
        """
        S = self.s_value
        
        # Calculate Kp (minimum 7,500)
        Kp_numerator = E * (E + 0.01028 * S)
        Kp_denominator = 0.75 * E + 0.8153 * S
        Kp = max(7500.0, Kp_numerator / Kp_denominator)
        
        # Calculate Ke
        Ke_numerator = E * (E + 0.0204 * S)
        Ke_denominator = 0.1 * E + 0.5109 * S
        Ke = Ke_numerator / Ke_denominator
        
        # Derive W and B
        B = Kp
        W = (E + Ke) / (E + Kp)
        
        return (W, B)
    
    def apply_sal_cap(self, claim_total: float) -> float:
        """Apply State Accident Limitation to a single claim"""
        return min(claim_total, self.sal_per_claim)
    
    def apply_multiple_claim_cap(self, claims_same_date: List[float]) -> List[float]:
        """
        Apply multiple claim rule: if one accident injures N people,
        total impact capped at 2× SAL (in most states)
        """
        total = sum(claims_same_date)
        cap = self.sal_multiple_claim
        
        if total <= cap:
            return claims_same_date  # No adjustment needed
        
        # Proportionally reduce each claim
        ratio = cap / total
        return [claim * ratio for claim in claims_same_date]


# ═══════════════════════════════════════════════════════════════════════════
# GEORGIA CONFIGURATION (NCCI State)
# ═══════════════════════════════════════════════════════════════════════════

class GeorgiaConfig(StateConfig):
    """
    Georgia Workers Compensation Experience Rating Configuration
    
    Source: NCCI Advisory Loss Costs and Rating Values Filing
    Effective: March 1, 2026
    """
    
    def __init__(self):
        super().__init__(
            state_code="GA",
            state_name="Georgia",
            
            # From GA Rating Values PDF (Page 29)
            split_point=21_500.00,
            sal_per_claim=176_000.00,
            sal_multiple_claim=352_000.00,  # 2× SAL
            g_value=12.65,
            s_value=3_162_500.00,  # 12.65 × 250,000
            
            # ERA Status
            is_era_state=True,
            era_discount=0.30,
            
            # Bureau Info
            is_ncci_state=True,
            bureau_name="NCCI",
            
            # Effective Date
            effective_date=date(2026, 3, 1),
            elr_decimals=3,
            
            # Eligibility
            min_expected_losses=5_000.00
        )
    
    def get_elr_and_dratio(self, class_code: str) -> Tuple[float, float]:
        """
        Look up ELR and D-Ratio for a class code from rating values.
        
        Returns: (ELR, D-Ratio)
        """
        # TODO: Load from parsed rating values table
        # For now, placeholder that will be replaced with actual table lookup
        
        # Example structure (will be loaded from file):
        # GA_CLASS_CODES = {
        #     "8810": {"elr": 0.050, "d_ratio": 0.40},
        #     "5403": {"elr": 2.157, "d_ratio": 0.32},
        #     ...
        # }
        
        raise NotImplementedError("ELR/D-Ratio table loading not yet implemented")


# ═══════════════════════════════════════════════════════════════════════════
# STATE FACTORY (Loads correct config based on state code)
# ═══════════════════════════════════════════════════════════════════════════

STATE_CONFIGS = {
    "GA": GeorgiaConfig,
}

def get_state_config(state_code: str) -> StateConfig:
    """
    Factory function to get state configuration.
    
    Usage:
        config = get_state_config("GA")
        W, B = config.calculate_w_and_b(50000)
    """
    if state_code not in STATE_CONFIGS:
        raise ValueError(f"State {state_code} not yet implemented. Available: {list(STATE_CONFIGS.keys())}")
    
    return STATE_CONFIGS[state_code]()


# ═══════════════════════════════════════════════════════════════════════════
# CLASS CODE INFORMATION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ClassCodeInfo:
    """Information about a specific class code"""
    code: str
    description: str
    elr: float  # Expected Loss Rate (per $100 payroll)
    d_ratio: float  # Discount Ratio (primary vs total)
    hazard_group: str  # A, B, C, D, E, F, G
    industry_group: str  # Manufacturing, Contracting, etc.
    
    @property
    def is_clerical(self) -> bool:
        """Check if this is clerical code 8810"""
        return self.code == "8810"
    
    @property
    def is_governing(self) -> bool:
        """Check if this is a governing class (typically high-rated construction)"""
        # List of common governing classes
        governing_codes = {"5403", "5437", "5645", "5474", "5506", "5022"}
        return self.code in governing_codes

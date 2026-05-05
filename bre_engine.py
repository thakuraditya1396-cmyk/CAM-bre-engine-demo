"""
bre_engine.py — JSON-driven Business Rules Engine for Credit Underwriting

Architecture:
    Input (answers dict) → CAMCalculator → RuleEngine → Decision + RiskScore
    
The engine is stateless. Pass it a fully-populated answers dict and it
returns a structured BREResult. The config JSON is the single source of truth.
"""

import json
import math
from dataclasses import dataclass, field
from typing import Any


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class CAMReport:
    """Credit Assessment Memo — the structured income statement for underwriting."""
    # Revenue side
    gross_revenue:        float = 0.0   # A: total revenue across all SENP sources
    business_expense:     float = 0.0   # B: raw material + labor + electricity + rent
    net_business_income:  float = 0.0   # C = A - B
    seasonal_adj_income:  float = 0.0   # D = C * seasonal_factor
    cam_income:           float = 0.0   # E = D * haircut (0.85 for SENP)
    family_income:        float = 0.0   # F: working co-applicant income
    total_cam_income:     float = 0.0   # G = E + F

    # Obligation side
    existing_emis:        float = 0.0   # H: sum of all running loan EMIs
    household_expense:    float = 0.0   # I: monthly household outflow
    total_obligations:    float = 0.0   # J = H + I
    proposed_emi:         float = 0.0   # K: new EMI being applied for
    total_outflow:        float = 0.0   # L = J + K

    # Derived metrics
    surplus:              float = 0.0   # M = G - L
    foir:                 float = 0.0   # N = K / G * 100 (Fixed Obligation to Income Ratio)
    adjusted_foir:        float = 0.0   # O = FOIR + dependent penalty + illness penalty

    # Metadata
    dependents:           int   = 0
    seasonal_factor:      float = 1.0
    haircut_applied:      float = 1.0
    source_breakdown:     list  = field(default_factory=list)


@dataclass
class BREResult:
    """Final output of the rule engine."""
    decision:      str   = "Pending"   # Eligible / Refer / Reject
    risk_score:    int   = 50
    risk_band:     str   = ""
    flags:         list  = field(default_factory=list)   # human-readable warnings
    rules_fired:   list  = field(default_factory=list)   # which rule IDs triggered
    cam:           CAMReport = field(default_factory=CAMReport)
    remarks:       str   = ""


# ─────────────────────────────────────────────
# CAM CALCULATOR
# ─────────────────────────────────────────────

class CAMCalculator:
    """
    Computes the Credit Assessment Memo income from raw field data.
    
    Why a separate class? Because income calculation is the most
    complex and lender-specific part. Keeping it isolated lets you
    swap haircuts, seasonal models, or family income rules without
    touching the rule engine.
    """

    def __init__(self, config: dict):
        self.haircuts   = config["cam_haircut"]
        self.dep_penalty = config["dependent_penalty_per_head"]
        self.ill_penalty = config["illness_foir_penalty"]

    def compute(self, answers: dict) -> CAMReport:
        cam = CAMReport()
        occ = answers.get("occupation", "SENP")

        # ── STEP 1: Applicant income by occupation type ──────────────
        if occ == "SENP":
            cam = self._compute_senp(answers, cam)

        elif occ == "Salaried":
            salary        = answers.get("salary", 0)
            cam.gross_revenue      = salary
            cam.net_business_income = salary
            cam.seasonal_adj_income = salary  # salary needs no seasonal adj
            cam.cam_income          = salary * self.haircuts["Salaried"]

        elif occ == "SEP":
            income        = answers.get("income", 0)
            cam.gross_revenue      = income
            cam.net_business_income = income
            cam.seasonal_adj_income = income
            cam.cam_income          = income * self.haircuts["SEP"]

        # ── STEP 2: Family income (working co-applicants at 50%) ─────
        family = answers.get("family", [])
        cam.dependents = sum(1 for m in family if m.get("occupation") == "Dependent")
        cam.family_income = sum(
            m.get("income", 0) * 0.5
            for m in family
            if m.get("occupation") == "Working" and m.get("co_applicant", False)
        )
        cam.total_cam_income = cam.cam_income + cam.family_income

        # ── STEP 3: Obligations ───────────────────────────────────────
        loans = answers.get("loans", [])
        cam.existing_emis    = sum(l.get("emi", 0) for l in loans)
        cam.household_expense = answers.get("hh_exp", 0)
        cam.proposed_emi      = answers.get("emi_pref", 0)
        cam.total_obligations = cam.existing_emis + cam.household_expense
        cam.total_outflow     = cam.total_obligations + cam.proposed_emi

        # ── STEP 4: Derived metrics ───────────────────────────────────
        cam.surplus = cam.total_cam_income - cam.total_outflow

        if cam.total_cam_income > 0:
            cam.foir = (cam.proposed_emi / cam.total_cam_income) * 100
        else:
            cam.foir = 999  # Sentinel: divide-by-zero → always reject

        # Adjusted FOIR adds a small penalty per dependent (they consume
        # future income without contributing) and for chronic illness
        # (potential medical expenses). This is an underwriting convention.
        dep_adj  = cam.dependents * self.dep_penalty
        ill_adj  = self.ill_penalty if answers.get("illness") else 0
        cam.adjusted_foir = cam.foir + dep_adj + ill_adj

        return cam

    def _compute_senp(self, answers: dict, cam: CAMReport) -> CAMReport:
        """
        Multi-source SENP income calculation.
        
        The key insight for SENP underwriting: never just take revenue at
        face value. Apply three layers:
          1. Subtract business expenses to get net income.
          2. Adjust for seasonality — a dairy farmer earns differently in
             summer vs winter. We blend 60% lean-season + 40% peak-season
             to get a conservative annual-average monthly income.
          3. Apply a CAM haircut (typically 0.85) because field-estimated
             income has inherent uncertainty.
        """
        sources    = answers.get("income_sources", [])
        expenses   = answers.get("business_expenses", {})
        breakdown  = []

        gross_total = 0
        for src in sources:
            # Revenue for this source
            rev     = src.get("revenue", 0)
            # Per-source seasonal multipliers (default to 1.0 if not given)
            peak    = src.get("season_peak", 1.0)
            lean    = src.get("season_lean", 1.0)
            # Conservative seasonal blend: weight lean more than peak
            s_factor = (0.6 * lean) + (0.4 * peak)
            adj_rev = rev * s_factor
            gross_total += adj_rev
            breakdown.append({
                "source":           src.get("name", "Unknown"),
                "monthly_revenue":  rev,
                "seasonal_factor":  round(s_factor, 3),
                "adjusted_revenue": round(adj_rev, 2)
            })

        cam.gross_revenue = gross_total
        cam.source_breakdown = breakdown

        # Business expenses are entered at the household level (not per source)
        # because shared costs like electricity or labor are hard to split.
        biz_exp = (
            expenses.get("raw_cost", 0) +
            expenses.get("labor", 0) +
            expenses.get("electricity", 0) +
            expenses.get("biz_rent", 0)
        )
        cam.business_expense    = biz_exp
        cam.net_business_income = max(0, gross_total - biz_exp)  # floor at 0
        cam.seasonal_adj_income = cam.net_business_income        # already seasonally adjusted above
        cam.seasonal_factor     = 1.0  # absorbed into per-source calcs
        cam.haircut_applied     = self.haircuts["SENP"]
        cam.cam_income          = cam.net_business_income * cam.haircut_applied

        return cam


# ─────────────────────────────────────────────
# RULE ENGINE
# ─────────────────────────────────────────────

class RuleEngine:
    """
    Evaluates the sorted rule set against computed metrics.
    
    Rules are priority-ordered. Hard rules (reject) are evaluated first;
    soft rules (risk flags) accumulate a score. This avoids the classic
    BRE pitfall where soft-flag rules override a hard reject.
    """

    def __init__(self, config: dict):
        # Sort rules by priority so hard gates fire before soft flags
        self.rules      = sorted(config["rules"], key=lambda r: r["priority"])
        self.base_score = config["risk_score"]["base"]
        self.bands      = config["risk_score"]["interpretation"]

    def evaluate(self, answers: dict, cam: CAMReport) -> BREResult:
        result     = BREResult(cam=cam)
        risk_score = self.base_score

        # Build a flat context dict so rule conditions are simple to evaluate.
        # In production, replace eval() with a proper expression parser
        # (e.g. simpleeval library) for security.
        ctx = {
            "age":           answers.get("age", 0),
            "occupation":    answers.get("occupation", ""),
            "vintage":       answers.get("vintage", 0),
            "cam_income":    cam.total_cam_income,
            "adjusted_foir": cam.adjusted_foir,
            "foir":          cam.foir,
            "surplus":       cam.surplus,
            "illness":       answers.get("illness", False),
            "informal_loans": answers.get("informal_loans", False),
            "disruption":    answers.get("disruption", False),
            "stability":     answers.get("stability", "Medium"),
            "location_type": answers.get("location_type", "Permanent"),
            "prop_type":     answers.get("prop_type", "None"),
            "alt_income":    answers.get("alt_income", False),
            "amb":           answers.get("amb", 0),
            "emi_pref":      answers.get("emi_pref", 0),
        }

        decision_set = False

        for rule in self.rules:
            try:
                condition_met = eval(rule["condition"], {"__builtins__": {}}, ctx)
            except Exception:
                continue  # Skip malformed rule expressions gracefully

            if not condition_met:
                continue

            result.rules_fired.append(rule["id"])
            action = rule["action"]

            if action == "reject" and not decision_set:
                result.decision = "Reject"
                result.flags.append(f"❌ {rule['name']}: {rule['reason']}")
                decision_set = True  # First reject wins; keep evaluating for risk flags

            elif action == "refer" and not decision_set:
                result.decision = "Refer"
                result.flags.append(f"⚠️ {rule['name']}: {rule['reason']}")
                decision_set = True

            elif action == "eligible" and not decision_set:
                result.decision = "Eligible"
                result.flags.append(f"✅ {rule['name']}: {rule['reason']}")
                decision_set = True

            elif action == "risk_flag":
                penalty = rule.get("risk_penalty", 0)
                risk_score -= penalty
                result.flags.append(f"🚩 {rule['name']}: {rule['reason']} (−{penalty} pts)")

            elif action == "risk_bonus":
                bonus = rule.get("risk_bonus", 0)
                risk_score += bonus
                result.flags.append(f"💚 {rule['name']}: {rule['reason']} (+{bonus} pts)")

        result.risk_score = max(0, min(100, risk_score))  # Clamp 0–100
        result.risk_band  = self._band(result.risk_score)

        if not decision_set:
            result.decision = "Refer"  # Default: if no rule fires, refer for manual review

        return result

    def _band(self, score: int) -> str:
        if score >= 70: return "Low Risk"
        if score >= 50: return "Medium Risk"
        if score >= 30: return "High Risk"
        return "Very High Risk"


# ─────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────

class BRE:
    """
    Top-level orchestrator. This is the only class the UI needs to touch.
    
    Usage:
        bre = BRE("bre_config.json")
        result = bre.run(answers)
    """

    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = json.load(f)
        self.cam_calc = CAMCalculator(self.config)
        self.engine   = RuleEngine(self.config)

    def run(self, answers: dict) -> BREResult:
        cam    = self.cam_calc.compute(answers)
        result = self.engine.evaluate(answers, cam)
        return result

    def cam_summary(self, result: BREResult) -> dict:
        """Returns a printable CAM summary dict for display."""
        c = result.cam
        return {
            "A. Gross Revenue (₹)":           f"{c.gross_revenue:,.0f}",
            "B. Business Expenses (₹)":        f"{c.business_expense:,.0f}",
            "C. Net Business Income (₹)":      f"{c.net_business_income:,.0f}",
            "D. CAM Haircut Applied":           f"{c.haircut_applied * 100:.0f}%",
            "E. CAM Income (₹)":               f"{c.cam_income:,.0f}",
            "F. Family Co-applicant Income (₹)":f"{c.family_income:,.0f}",
            "G. Total CAM Income (₹)":         f"{c.total_cam_income:,.0f}",
            "──────────────────────────────":  "",
            "H. Existing EMIs (₹)":            f"{c.existing_emis:,.0f}",
            "I. Household Expense (₹)":        f"{c.household_expense:,.0f}",
            "J. Proposed EMI (₹)":             f"{c.proposed_emi:,.0f}",
            "K. Total Outflow (₹)":            f"{c.total_outflow:,.0f}",
            "──────────────────────────────":  "",
            "L. Surplus (₹)":                  f"{c.surplus:,.0f}",
            "M. FOIR":                         f"{c.foir:.1f}%",
            "N. Adjusted FOIR":                f"{c.adjusted_foir:.1f}%",
            "O. Dependents":                   str(c.dependents),
        }


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Sample answers — a SENP applicant with two income sources
    sample = {
        "name":       "Ramesh Kumar",
        "age":        38,
        "occupation": "SENP",
        "vintage":    5,
        "income_sources": [
            {"name": "Dairy",    "revenue": 25000, "season_peak": 1.1, "season_lean": 0.85},
            {"name": "Poultry",  "revenue": 15000, "season_peak": 1.2, "season_lean": 0.75},
        ],
        "business_expenses": {
            "raw_cost":    8000,
            "labor":       3000,
            "electricity": 1000,
            "biz_rent":    2000
        },
        "family": [
            {"name": "Sunita",  "occupation": "Working",   "income": 10000, "co_applicant": True},
            {"name": "Child 1", "occupation": "Dependent", "income": 0,     "co_applicant": False},
        ],
        "loans": [
            {"type": "Agri Loan", "emi": 3000}
        ],
        "hh_exp":   8000,
        "emi_pref": 7000,
        "amb":      12000,
        "illness":       False,
        "informal_loans": False,
        "disruption":     False,
        "stability":      "High",
        "location_type":  "Permanent",
        "prop_type":      "Self",
        "alt_income":     True
    }

    bre    = BRE("bre_config.json")
    result = bre.run(sample)

    print(f"\n{'='*50}")
    print(f"  DECISION:   {result.decision}")
    print(f"  RISK SCORE: {result.risk_score}/100 ({result.risk_band})")
    print(f"{'='*50}")
    print("\nCAM Summary:")
    for k, v in bre.cam_summary(result).items():
        print(f"  {k:<38} {v}")
    print("\nFlags / Remarks:")
    for flag in result.flags:
        print(f"  {flag}")
    print(f"\nRules Fired: {', '.join(result.rules_fired)}")

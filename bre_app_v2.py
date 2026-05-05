"""
bre_app_v2.py — Dynamic JSON-driven BRE Streamlit Application

This version renders the questionnaire from bre_config.json rather than
hardcoding steps. The UI is just an interpreter of the config.

Run with:  streamlit run bre_app_v2.py
"""

import json
import streamlit as st
from bre_engine import BRE, BREResult

# ─────────────────────────────────────────────
# CONFIG + ENGINE INIT
# ─────────────────────────────────────────────

st.set_page_config(page_title="Credit BRE", layout="centered", page_icon="🏦")

@st.cache_resource
def load_bre():
    return BRE("bre_config.json")

bre = load_bre()

# ─────────────────────────────────────────────
# SESSION STATE BOOTSTRAP
# ─────────────────────────────────────────────

def reset():
    st.session_state.clear()

if "page" not in st.session_state:
    st.session_state.page         = "kyc"
    st.session_state.answers      = {}
    st.session_state.family       = []
    st.session_state.income_srcs  = []
    st.session_state.loans        = []

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def next_page(name: str):
    st.session_state.page = name
    st.rerun()

def save(key: str, value):
    st.session_state.answers[key] = value

def progress_bar():
    """Shows which module the user is currently in."""
    pages  = ["kyc", "occupation", "family", "business", "income",
              "expense", "liabilities", "loan", "risk", "result"]
    labels = ["KYC", "Occupation", "Family", "Business", "Income",
              "Expenses", "Liabilities", "Loan", "Risk", "Result"]
    idx = pages.index(st.session_state.page) if st.session_state.page in pages else 0
    st.progress((idx) / (len(pages) - 1), text=f"Step {idx+1}/{len(pages)}: {labels[idx]}")

# ─────────────────────────────────────────────
# PAGE: KYC
# ─────────────────────────────────────────────

def page_kyc():
    st.header("👤 Applicant Information")

    a = st.session_state.answers
    name   = st.text_input("Full Name", value=a.get("name", ""))
    age    = st.number_input("Age", min_value=18, max_value=80, value=int(a.get("age", 25)))
    gender = st.radio("Gender", ["Male", "Female", "Other"],
                      index=["Male","Female","Other"].index(a.get("gender","Male")),
                      horizontal=True)
    res    = st.selectbox("Residence Type", ["Owned", "Rented", "Parental"],
                          index=["Owned","Rented","Parental"].index(a.get("res_type","Owned")))

    rent = 0
    if res == "Rented":
        rent = st.number_input("Monthly Rent Paid (₹)", min_value=0, value=int(a.get("rent", 0)))

    if st.button("Next →", use_container_width=True):
        if not name:
            st.error("Please enter the applicant name.")
            return
        save("name", name); save("age", age); save("gender", gender)
        save("res_type", res); save("rent", rent)
        next_page("occupation")


# ─────────────────────────────────────────────
# PAGE: OCCUPATION
# ─────────────────────────────────────────────

def page_occupation():
    st.header("💼 Occupation")

    a   = st.session_state.answers
    occ = st.selectbox("Occupation Type", ["Salaried", "SENP", "SEP"],
                       index=["Salaried","SENP","SEP"].index(a.get("occupation","SENP")))

    if occ == "Salaried":
        company = st.text_input("Company Name", value=a.get("company", ""))
        salary  = st.number_input("Monthly Salary (₹)", min_value=0, value=int(a.get("salary", 0)))

    elif occ == "SEP":
        prof   = st.selectbox("Profession", ["Doctor", "CA", "Lawyer", "Architect", "Other"],
                               index=0)
        income = st.number_input("Monthly Income (₹)", min_value=0, value=int(a.get("income", 0)))

    elif occ == "SENP":
        vintage = st.number_input("Business Vintage (years)", min_value=0, value=int(a.get("vintage", 0)))
        biz_type = st.text_input("Business Type / Name", value=a.get("biz_type", ""))
        loc_type = st.selectbox("Business Location", ["Permanent", "Temporary"],
                                index=["Permanent","Temporary"].index(a.get("location_type","Permanent")))

    if st.button("Next →", use_container_width=True):
        save("occupation", occ)
        if occ == "Salaried":
            save("company", company); save("salary", salary)
        elif occ == "SEP":
            save("profession", prof); save("income", income)
        elif occ == "SENP":
            save("vintage", vintage); save("biz_type", biz_type)
            save("location_type", loc_type)
        next_page("family")


# ─────────────────────────────────────────────
# PAGE: FAMILY
# ─────────────────────────────────────────────

def page_family():
    st.header("👨‍👩‍👧 Family Details")

    col1, col2 = st.columns([3, 1])
    with col1:
        count = st.number_input("Number of Family Members (excluding applicant)",
                                min_value=0, step=1, value=len(st.session_state.family))

    # Dynamic family member form
    family = []
    for i in range(int(count)):
        with st.expander(f"Family Member {i+1}", expanded=True):
            existing = st.session_state.family[i] if i < len(st.session_state.family) else {}
            c1, c2 = st.columns(2)
            name = c1.text_input("Name",       key=f"fn_{i}", value=existing.get("name",""))
            age  = c2.number_input("Age",      key=f"fa_{i}", min_value=0, value=int(existing.get("age", 0)))
            c3, c4, c5 = st.columns(3)
            occ  = c3.selectbox("Status",      key=f"fo_{i}", options=["Working","Dependent"],
                                 index=0 if existing.get("occupation","Working")=="Working" else 1)
            inc  = c4.number_input("Income (₹)", key=f"fi_{i}", min_value=0,
                                    value=int(existing.get("income", 0)),
                                    disabled=(occ == "Dependent"))
            co   = c5.checkbox("Co-applicant?", key=f"fc_{i}",
                                value=existing.get("co_applicant", False),
                                disabled=(occ == "Dependent"))
            family.append({"name": name, "age": age, "occupation": occ,
                            "income": inc if occ == "Working" else 0,
                            "co_applicant": co})

    if st.button("Next →", use_container_width=True):
        st.session_state.family = family
        occ = st.session_state.answers.get("occupation")
        next_page("income" if occ == "SENP" else "expense")


# ─────────────────────────────────────────────
# PAGE: INCOME (SENP multi-source)
# ─────────────────────────────────────────────

def page_income():
    st.header("💰 Income Sources")

    st.info("""
    **How SENP income is calculated:**  
    For each source: Monthly Revenue × Seasonal Factor → Net after expenses → 85% CAM haircut.  
    Seasonal factor = 60% lean-season weight + 40% peak-season weight (conservative blend).
    """)

    options = ["Dairy", "Tea Stall", "Poultry", "Vegetable Farming", "Other"]
    selected = st.multiselect("Select all income sources",
                               options,
                               default=st.session_state.answers.get("selected_sources", []))

    income_srcs = []
    for src in selected:
        st.subheader(f"📦 {src}")
        c1, c2 = st.columns(2)
        rev  = c1.number_input(f"Monthly Revenue (₹)",  key=f"rev_{src}", min_value=0)
        peak = c2.number_input("Peak Season Multiplier", key=f"pk_{src}",
                                min_value=0.5, max_value=3.0, value=1.0, step=0.05,
                                help="e.g. 1.2 means 20% more revenue in peak season")
        lean = c1.number_input("Lean Season Multiplier", key=f"ln_{src}",
                                min_value=0.1, max_value=1.5, value=1.0, step=0.05,
                                help="e.g. 0.8 means 20% less revenue in lean season")

        s_factor = round((0.6 * lean) + (0.4 * peak), 3)
        adj_rev  = round(rev * s_factor, 0)
        c2.metric("Seasonally-Adjusted Revenue", f"₹{adj_rev:,.0f}", delta=f"Factor: {s_factor}")

        income_srcs.append({
            "name":         src,
            "revenue":      rev,
            "season_peak":  peak,
            "season_lean":  lean
        })

    st.session_state.answers["selected_sources"] = selected

    if st.button("Next →", use_container_width=True):
        if not selected:
            st.error("Select at least one income source.")
            return
        st.session_state.income_srcs = income_srcs
        next_page("expense")


# ─────────────────────────────────────────────
# PAGE: EXPENSE
# ─────────────────────────────────────────────

def page_expense():
    st.header("📉 Expenses")

    a   = st.session_state.answers
    occ = a.get("occupation")

    if occ == "SENP":
        st.subheader("Business Expenses (monthly)")
        c1, c2 = st.columns(2)
        raw  = c1.number_input("Raw Material / Milk / Feed (₹)", min_value=0, value=int(a.get("raw_cost",0)))
        lab  = c2.number_input("Labor / Helper Cost (₹)",        min_value=0, value=int(a.get("labor",0)))
        elec = c1.number_input("Electricity (₹)",                min_value=0, value=int(a.get("electricity",0)))
        rent = c2.number_input("Business Rent / Stall Charges (₹)", min_value=0, value=int(a.get("biz_rent",0)))
        total_biz_exp = raw + lab + elec + rent
        st.metric("Total Business Expense", f"₹{total_biz_exp:,.0f}")

    st.subheader("Household Expense")
    hh = st.number_input("Monthly Household Expense (₹)", min_value=0, value=int(a.get("hh_exp", 0)))

    if st.button("Next →", use_container_width=True):
        if occ == "SENP":
            save("business_expenses", {"raw_cost": raw, "labor": lab,
                                        "electricity": elec, "biz_rent": rent})
        save("hh_exp", hh)
        next_page("liabilities")


# ─────────────────────────────────────────────
# PAGE: LIABILITIES
# ─────────────────────────────────────────────

def page_liabilities():
    st.header("🏦 Existing Liabilities")

    count = st.number_input("Number of Existing Loans", min_value=0, step=1,
                             value=len(st.session_state.loans))

    loans = []
    for i in range(int(count)):
        existing = st.session_state.loans[i] if i < len(st.session_state.loans) else {}
        with st.expander(f"Loan {i+1}", expanded=True):
            c1, c2, c3 = st.columns(3)
            ltype = c1.text_input("Loan Type",         key=f"lt_{i}", value=existing.get("type",""))
            outst = c2.number_input("Outstanding (₹)", key=f"lo_{i}", min_value=0,
                                     value=int(existing.get("outstanding", 0)))
            emi   = c3.number_input("EMI (₹/month)",   key=f"le_{i}", min_value=0,
                                     value=int(existing.get("emi", 0)))
            loans.append({"type": ltype, "outstanding": outst, "emi": emi})

    col1, col2 = st.columns(2)
    amb = col1.number_input("Average Monthly Bank Balance (₹)", min_value=0,
                             value=int(st.session_state.answers.get("amb", 0)))
    acct_type = col2.selectbox("Bank Account Type", ["Savings", "Current"])

    if st.button("Next →", use_container_width=True):
        st.session_state.loans = loans
        save("amb", amb)
        save("acct_type", acct_type)
        next_page("loan")


# ─────────────────────────────────────────────
# PAGE: LOAN REQUIREMENT
# ─────────────────────────────────────────────

def page_loan():
    st.header("📋 Loan Requirement")

    a = st.session_state.answers
    c1, c2 = st.columns(2)
    loan_amt = c1.number_input("Loan Amount Required (₹)", min_value=0,
                                value=int(a.get("loan_amt_req", 0)))
    tenure   = c2.number_input("Preferred Tenure (months)", min_value=6, max_value=240,
                                value=int(a.get("tenure_pref", 36)))
    emi_pref = c1.number_input("Comfortable EMI (₹/month)", min_value=0,
                                value=int(a.get("emi_pref", 0)))
    purpose  = c2.text_input("Loan Purpose", value=a.get("loan_purpose", ""))

    # Quick EMI estimator for guidance
    if loan_amt > 0 and tenure > 0:
        rate_monthly = 0.015  # assume ~18% p.a.
        emi_calc = loan_amt * rate_monthly * (1 + rate_monthly)**tenure / ((1 + rate_monthly)**tenure - 1)
        st.info(f"💡 Indicative EMI at ~18% p.a. for {tenure} months: **₹{emi_calc:,.0f}**")

    if st.button("Next →", use_container_width=True):
        save("loan_amt_req", loan_amt)
        save("tenure_pref", tenure)
        save("emi_pref", emi_pref)
        save("loan_purpose", purpose)
        next_page("risk")


# ─────────────────────────────────────────────
# PAGE: RISK INDICATORS
# ─────────────────────────────────────────────

def page_risk():
    st.header("⚠️ Risk Indicators")

    a = st.session_state.answers

    illness     = st.toggle("Any chronic illness in the household?",
                             value=a.get("illness", False))
    informal    = st.toggle("Any informal / moneylender borrowing?",
                             value=a.get("informal_loans", False))
    alt_income  = st.toggle("Is there any alternate income source available?",
                             value=a.get("alt_income", False))
    disruption  = st.toggle("Any business disruption in the last 12 months?",
                             value=a.get("disruption", False))
    stability   = st.select_slider("Business Stability",
                                    options=["Low", "Medium", "High"],
                                    value=a.get("stability", "Medium"))
    prop_type   = st.selectbox("Property Ownership",
                                ["None", "Family", "Self"],
                                index=["None","Family","Self"].index(a.get("prop_type","None")))
    prop_val = 0
    if prop_type == "Self":
        prop_val = st.number_input("Estimated Property Value (₹)", min_value=0,
                                    value=int(a.get("prop_value", 0)))

    if st.button("Calculate →", type="primary", use_container_width=True):
        save("illness", illness)
        save("informal_loans", informal)
        save("alt_income", alt_income)
        save("disruption", disruption)
        save("stability", stability)
        save("prop_type", prop_type)
        save("prop_value", prop_val)
        next_page("result")


# ─────────────────────────────────────────────
# PAGE: RESULT
# ─────────────────────────────────────────────

def page_result():
    st.header("📊 BRE Assessment Report")

    # Assemble the answers dict for the engine
    answers = dict(st.session_state.answers)
    answers["family"]       = st.session_state.family
    answers["income_sources"] = st.session_state.income_srcs
    answers["loans"]        = st.session_state.loans

    result: BREResult = bre.run(answers)
    cam = result.cam

    # ── Decision Banner ──────────────────────────────────────
    decision_map = {
        "Eligible": ("success", "✅ ELIGIBLE"),
        "Refer":    ("warning", "⚠️ REFER TO CREDIT MANAGER"),
        "Reject":   ("error",   "❌ NOT ELIGIBLE"),
    }
    level, label = decision_map.get(result.decision, ("info", result.decision))
    getattr(st, level)(f"**{label}**", icon=None)

    # ── Risk Score ───────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Risk Score",    f"{result.risk_score}/100")
    col2.metric("Risk Band",     result.risk_band)
    col3.metric("Adjusted FOIR", f"{cam.adjusted_foir:.1f}%")

    # ── CAM Income Statement ─────────────────────────────────
    st.subheader("📋 CAM Income Statement")

    occ = answers.get("occupation")
    if occ == "SENP" and cam.source_breakdown:
        st.markdown("**Source-wise Revenue Breakdown:**")
        for src in cam.source_breakdown:
            st.markdown(
                f"- **{src['source']}**: ₹{src['monthly_revenue']:,.0f} → "
                f"Seasonal adj ×{src['seasonal_factor']} → **₹{src['adjusted_revenue']:,.0f}**"
            )
        st.markdown("---")

    cam_rows = bre.cam_summary(result)
    for label_, value in cam_rows.items():
        if label_.startswith("──"):
            st.markdown("---")
        elif value:
            c1, c2 = st.columns([3, 1])
            c1.markdown(label_)
            c2.markdown(f"**{value}**")

    # ── Flags & Rule Explanations ────────────────────────────
    st.subheader("🔍 Rule Decisions & Flags")
    for flag in result.flags:
        st.markdown(f"- {flag}")

    # ── Raw Data Expander ────────────────────────────────────
    with st.expander("🗂️ View Raw Input Data"):
        st.json(answers)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Application", use_container_width=True):
            reset()
            st.rerun()
    with col2:
        # Prepare a plain-text CAM report for download
        report_lines = [
            f"BRE Report — {answers.get('name','Applicant')}",
            f"Decision: {result.decision}",
            f"Risk Score: {result.risk_score}/100 ({result.risk_band})",
            f"FOIR: {cam.foir:.1f}%  |  Adjusted FOIR: {cam.adjusted_foir:.1f}%",
            "---",
        ]
        report_lines += [f"{k}: {v}" for k, v in cam_rows.items()]
        report_lines += ["---", "Flags:"]
        report_lines += result.flags
        st.download_button("⬇️ Download Report",
                            "\n".join(report_lines),
                            file_name=f"BRE_{answers.get('name','report')}.txt",
                            use_container_width=True)


# ─────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────

st.title("🏦 Credit Underwriting BRE")
progress_bar()
st.divider()

page_map = {
    "kyc":         page_kyc,
    "occupation":  page_occupation,
    "family":      page_family,
    "income":      page_income,
    "expense":     page_expense,
    "liabilities": page_liabilities,
    "loan":        page_loan,
    "risk":        page_risk,
    "result":      page_result,
}

# Render the correct page — if occupation is not SENP, skip the income sources page
current = st.session_state.page
if current == "income" and st.session_state.answers.get("occupation") != "SENP":
    next_page("expense")
else:
    page_map.get(current, page_kyc)()

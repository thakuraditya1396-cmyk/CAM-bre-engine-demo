import streamlit as st

st.set_page_config(page_title="BRE Demo", layout="centered")

# -----------------------------
# Initialize session
# -----------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.data = {}
    st.session_state.income_sources = []

st.title("📊 Credit Underwriting BRE Demo")

# -----------------------------
# STEP 1: Basic Info
# -----------------------------
if st.session_state.step == 1:
    st.header("Step 1: Basic Information")

    name = st.text_input("Full Name")
    age = st.number_input("Age", min_value=18, max_value=80)

    if st.button("Next"):
        st.session_state.data["name"] = name
        st.session_state.data["age"] = age
        st.session_state.step = 2

# -----------------------------
# STEP 2: Occupation
# -----------------------------
elif st.session_state.step == 2:
    st.header("Step 2: Occupation Type")

    occupation = st.selectbox("Select Occupation", ["Salaried", "SENP", "SEP"])

    if st.button("Next"):
        st.session_state.data["occupation"] = occupation
        st.session_state.step = 3

# -----------------------------
# STEP 3: Income Handling
# -----------------------------
elif st.session_state.step == 3:

    occupation = st.session_state.data["occupation"]

    if occupation == "Salaried":
        st.header("Salaried Details")

        company = st.text_input("Company Name")
        salary = st.number_input("Monthly Salary")

        if st.button("Next"):
            st.session_state.data["company"] = company
            st.session_state.data["salary"] = salary
            st.session_state.step = 5

    elif occupation == "SENP":
        st.header("SENP - Income Sources")

        options = ["Dairy", "Food Stall", "Poultry", "Other"]
        selected = st.multiselect("Select Income Sources", options)

        if st.button("Next"):
            st.session_state.income_sources = selected
            st.session_state.current_source = 0
            st.session_state.step = 4

    elif occupation == "SEP":
        st.header("Professional Details")

        prof = st.selectbox("Profession", ["Doctor", "Lawyer", "CA", "Other"])
        income = st.number_input("Monthly Income")

        if st.button("Next"):
            st.session_state.data["profession"] = prof
            st.session_state.data["income"] = income
            st.session_state.step = 5

# -----------------------------
# STEP 4: LOOP (SENP Income)
# -----------------------------
elif st.session_state.step == 4:

    sources = st.session_state.income_sources
    index = st.session_state.current_source

    if index < len(sources):
        source = sources[index]

        st.header(f"Income Details - {source}")

        revenue = st.number_input(f"{source} Monthly Revenue")
        expense = st.number_input(f"{source} Monthly Expense")

        if st.button("Save & Next"):
            if "senp_income" not in st.session_state.data:
                st.session_state.data["senp_income"] = []

            st.session_state.data["senp_income"].append({
                "source": source,
                "revenue": revenue,
                "expense": expense
            })

            st.session_state.current_source += 1
            st.experimental_rerun()

    else:
        st.session_state.step = 5

# -----------------------------
# STEP 5: Household Expense
# -----------------------------
elif st.session_state.step == 5:

    st.header("Household Details")

    expense = st.number_input("Monthly Household Expense")

    if st.button("Next"):
        st.session_state.data["household_expense"] = expense
        st.session_state.step = 6

# -----------------------------
# STEP 6: Loan Details
# -----------------------------
elif st.session_state.step == 6:

    st.header("Loan Requirement")

    loan = st.number_input("Loan Amount Required")
    emi = st.number_input("Comfortable EMI")

    if st.button("Calculate"):
        st.session_state.data["loan"] = loan
        st.session_state.data["emi"] = emi
        st.session_state.step = 7

# -----------------------------
# STEP 7: Summary + Decision
# -----------------------------
elif st.session_state.step == 7:

    st.header("📊 Summary & Decision")

    data = st.session_state.data

    total_income = 0

    if data["occupation"] == "Salaried":
        total_income = data.get("salary", 0)

    elif data["occupation"] == "SEP":
        total_income = data.get("income", 0)

    elif data["occupation"] == "SENP":
        for item in data.get("senp_income", []):
            total_income += (item["revenue"] - item["expense"])

    total_expense = data.get("household_expense", 0)
    emi = data.get("emi", 0)

    foir = (emi / total_income) * 100 if total_income > 0 else 0

    st.write("### Applicant Data")
    st.json(data)

    st.write("### Calculations")
    st.write(f"Total Income: ₹{total_income}")
    st.write(f"FOIR: {round(foir,2)}%")

    # BRE Decision Rule
    if foir < 50:
        st.success("✅ Eligible")
    elif foir < 65:
        st.warning("⚠ Refer")
    else:
        st.error("❌ Not Eligible")

    if st.button("Restart"):
        st.session_state.clear()

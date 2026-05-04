import streamlit as st

st.set_page_config(page_title="BRE Demo", layout="centered")

# -----------------------------
# SESSION INIT
# -----------------------------
if "step" not in st.session_state:
    st.session_state.step = 1
    st.session_state.data = {}
    st.session_state.family = []
    st.session_state.income_sources = []

st.title("📊 Credit Underwriting BRE Demo")

# -----------------------------
# STEP 1: BASIC INFO
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
# STEP 2: OCCUPATION
# -----------------------------
elif st.session_state.step == 2:

    st.header("Step 2: Occupation")

    occupation = st.selectbox("Select Occupation", ["Salaried", "SENP", "SEP"])

    if st.button("Next"):
        st.session_state.data["occupation"] = occupation
        st.session_state.step = 3


# -----------------------------
# STEP 3: FAMILY COUNT
# -----------------------------
elif st.session_state.step == 3:

    st.header("Step 3: Family Details")

    num_members = st.number_input("Number of Family Members", min_value=0, step=1)

    if st.button("Next"):
        st.session_state.num_members = num_members
        st.session_state.family_index = 0
        st.session_state.family = []
        st.session_state.step = 4


# -----------------------------
# STEP 4: FAMILY LOOP
# -----------------------------
elif st.session_state.step == 4:

    i = st.session_state.family_index
    total = st.session_state.num_members

    if i < total:

        st.header(f"Family Member {i+1}")

        name = st.text_input("Name", key=f"name_{i}")
        age = st.number_input("Age", key=f"age_{i}")
        occupation = st.selectbox("Occupation", ["Working", "Dependent"], key=f"occ_{i}")
        income = st.number_input("Monthly Income", key=f"inc_{i}")

        if st.button("Save & Next"):

            st.session_state.family.append({
                "name": name,
                "age": age,
                "occupation": occupation,
                "income": income
            })

            st.session_state.family_index += 1
            st.experimental_rerun()

    else:
        st.session_state.step = 5


# -----------------------------
# STEP 5: APPLICANT INCOME
# -----------------------------
elif st.session_state.step == 5:

    occupation = st.session_state.data["occupation"]

    if occupation == "Salaried":

        st.header("Salaried Details")

        company = st.text_input("Company Name")
        salary = st.number_input("Monthly Salary")

        if st.button("Next"):
            st.session_state.data["company"] = company
            st.session_state.data["salary"] = salary
            st.session_state.step = 7


    elif occupation == "SEP":

        st.header("Professional Details")

        prof = st.selectbox("Profession", ["Doctor", "Lawyer", "CA", "Other"])
        income = st.number_input("Monthly Income")

        if st.button("Next"):
            st.session_state.data["profession"] = prof
            st.session_state.data["income"] = income
            st.session_state.step = 7


    elif occupation == "SENP":

        st.header("SENP - Income Sources")

        options = ["Dairy", "Food Stall", "Poultry", "Other"]
        selected = st.multiselect("Select Income Sources", options)

        if st.button("Next"):
            st.session_state.income_sources = selected
            st.session_state.current_source = 0
            st.session_state.data["senp_income"] = []
            st.session_state.step = 6


# -----------------------------
# STEP 6: SENP LOOP
# -----------------------------
elif st.session_state.step == 6:

    sources = st.session_state.income_sources
    index = st.session_state.current_source

    if index < len(sources):

        source = sources[index]

        st.header(f"{source} Details")

        revenue = st.number_input(f"{source} Monthly Revenue")
        expense = st.number_input(f"{source} Monthly Expense")

        if st.button("Save & Next"):

            st.session_state.data["senp_income"].append({
                "source": source,
                "revenue": revenue,
                "expense": expense
            })

            st.session_state.current_source += 1
            st.experimental_rerun()

    else:
        st.session_state.step = 7


# -----------------------------
# STEP 7: HOUSEHOLD EXPENSE
# -----------------------------
elif st.session_state.step == 7:

    st.header("Household Expense")

    expense = st.number_input("Monthly Household Expense")

    if st.button("Next"):
        st.session_state.data["household_expense"] = expense
        st.session_state.step = 8


# -----------------------------
# STEP 8: LOAN DETAILS
# -----------------------------
elif st.session_state.step == 8:

    st.header("Loan Requirement")

    loan = st.number_input("Loan Amount Required")
    emi = st.number_input("Proposed EMI")

    if st.button("Calculate"):
        st.session_state.data["loan"] = loan
        st.session_state.data["emi"] = emi
        st.session_state.step = 9


# -----------------------------
# STEP 9: FINAL CALCULATION
# -----------------------------
elif st.session_state.step == 9:

    st.header("📊 Final Assessment")

    data = st.session_state.data

    total_income = 0

    # Applicant Income
    if data["occupation"] == "Salaried":
        total_income += data.get("salary", 0)

    elif data["occupation"] == "SEP":
        total_income += data.get("income", 0)

    elif data["occupation"] == "SENP":
        for item in data.get("senp_income", []):
            total_income += (item["revenue"] - item["expense"])

    # Family Income + Dependents
    family_income = 0
    dependents = 0

    for member in st.session_state.family:
        if member["occupation"] == "Working":
            family_income += member["income"]
        else:
            dependents += 1

    total_income += family_income

    # Expense + EMI
    household_expense = data.get("household_expense", 0)
    emi = data.get("emi", 0)

    # FOIR
    foir = (emi / total_income) * 100 if total_income > 0 else 0

    # Dependency Adjustment
    adjusted_foir = foir + (dependents * 2)

    # -----------------------------
    # DISPLAY
    # -----------------------------
    st.subheader("Applicant Data")
    st.json(data)

    st.subheader("Family Data")
    st.write(st.session_state.family)

    st.subheader("Financial Summary")
    st.write(f"Total Income: ₹{total_income}")
    st.write(f"Household Expense: ₹{household_expense}")
    st.write(f"FOIR: {round(foir,2)}%")
    st.write(f"Adjusted FOIR: {round(adjusted_foir,2)}%")

    # -----------------------------
    # DECISION ENGINE
    # -----------------------------
    if adjusted_foir < 50:
        st.success("✅ Eligible")

    elif adjusted_foir < 65:
        st.warning("⚠ Refer")

    else:
        st.error("❌ Not Eligible")

    if st.button("Restart"):
        st.session_state.clear()
        st.experimental_rerun()
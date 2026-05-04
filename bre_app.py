import streamlit as st

# ---------------- STATE ----------------
if "responses" not in st.session_state:
    st.session_state.responses = {}

if "current_q" not in st.session_state:
    st.session_state.current_q = "Q1"

# ---------------- QUESTION CONFIG ----------------
questions = {

    "Q1": {
        "text": "Occupation Type",
        "type": "select",
        "options": ["Salaried", "SENP", "SEP"],
        "next": {
            "Salaried": "Q2",
            "SENP": "Q4",
            "SEP": "Q5"
        }
    },

    "Q2": {
        "text": "Company Name",
        "type": "text",
        "next": "Q3"
    },

    "Q3": {
        "text": "Designation",
        "type": "text",
        "next": "Q6"
    },

    "Q4": {
        "text": "Select Income Sources",
        "type": "multi",
        "options": ["Dairy", "Food Stall", "Poultry"],
        "next": "Q6"
    },

    "Q5": {
        "text": "Profession",
        "type": "select",
        "options": ["Doctor", "Lawyer", "CA"],
        "next": "Q6"
    },

    "Q6": {
        "text": "Full Name",
        "type": "text",
        "next": "Q7"
    },

    "Q7": {
        "text": "Age",
        "type": "number",
        "next": "Q8"
    },

    "Q8": {
        "text": "Residence Type",
        "type": "select",
        "options": ["Owned", "Rented", "Parental"],
        "next": {
            "Owned": "END",
            "Rented": "Q9",
            "Parental": "Q10"
        }
    },

    "Q9": {
        "text": "Monthly Rent",
        "type": "number",
        "next": "END"
    },

    "Q10": {
        "text": "Property Owner Name",
        "type": "text",
        "next": "END"
    }
}

# ---------------- RENDER ----------------
q = questions[st.session_state.current_q]

st.title("BRE Demo Engine")

answer = None

if q["type"] == "text":
    answer = st.text_input(q["text"])

elif q["type"] == "number":
    answer = st.number_input(q["text"])

elif q["type"] == "select":
    answer = st.selectbox(q["text"], q["options"])

elif q["type"] == "multi":
    answer = st.multiselect(q["text"], q["options"])

# ---------------- NEXT BUTTON ----------------
if st.button("Next"):

    st.session_state.responses[st.session_state.current_q] = answer

    nxt = q["next"]

    if isinstance(nxt, dict):
        st.session_state.current_q = nxt.get(answer, "END")
    else:
        st.session_state.current_q = nxt

# ---------------- END ----------------
if st.session_state.current_q == "END":
    st.success("Completed")
    st.write(st.session_state.responses)
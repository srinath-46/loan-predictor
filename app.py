import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils import predict_risk, save_to_db, init_db, engine, load_csvs_to_db

st.set_page_config(page_title="Loan Risk Predictor", layout="centered")
st.title("🏦 Loan Default Risk Predictor")

# Step 1: Initialize DB
init_db()

# Step 2: Load CSVs into DB ONCE
if "csv_loaded" not in st.session_state:
    with st.spinner("Loading data from CSVs into database..."):
        load_csvs_to_db()
        st.session_state.csv_loaded = True
        st.success("📦 CSV data loaded into database!")

# ----------------------------
# Section 1: Search Existing Customer
# ----------------------------
st.subheader("📂 Search Existing Customer by ID")

customer_id = st.text_input("Enter Customer ID (e.g., C0456)")

if st.button("🔍 Fetch From Database"):
    try:
        query = """
            SELECT c.age, c.annual_income, cr.credit_score, cr.num_inquiries,
                   cr.open_credit_lines, cr.total_accounts, cr.delinquent_accounts,
                   l.loan_amount, l.loan_term_months
            FROM customers c
            JOIN loans l ON c.customer_id = l.customer_id
            JOIN credits cr ON c.customer_id = cr.customer_id
            WHERE c.customer_id = :cid
            LIMIT 1
        """
        result = pd.read_sql(text(query), engine, params={"cid": customer_id})

        if not result.empty:
            st.success("✅ Customer data loaded")
            st.dataframe(result)

            input_dict = result.iloc[0].to_dict()
            input_dict['debt_to_income'] = input_dict['loan_amount'] / input_dict['annual_income']
            input_df = pd.DataFrame([input_dict])
            score, category = predict_risk(input_df)

            st.success(f"🧠 Risk Score: {score} → Category: **{category}**")
            input_dict.update({"prediction": score, "risk_category": category})
            save_to_db(input_dict)
            st.info("📥 Entry saved to database")
        else:
            st.warning("❌ Customer ID not found")
    except Exception as e:
        st.error(f"Database error: {e}")

# ----------------------------
# Section 2: Manual Entry
# ----------------------------
st.subheader("📝 Or Enter Customer Details Manually")

with st.form("prediction_form"):
    age = st.slider("Age", 18, 70)
    annual_income = st.number_input("Annual Income", step=1000)
    credit_score = st.slider("Credit Score", 300, 850)
    num_inquiries = st.number_input("Number of Inquiries", min_value=0, step=1)
    open_credit_lines = st.number_input("Open Credit Lines", min_value=0, step=1)
    total_accounts = st.number_input("Total Accounts", min_value=1, step=1)
    delinquent_accounts = st.number_input("Delinquent Accounts", min_value=0, step=1)
    loan_amount = st.number_input("Loan Amount", step=1000)
    loan_term_months = st.selectbox("Loan Term (Months)", [12, 24, 36, 60, 120, 180])

    submitted = st.form_submit_button("📊 Predict")

if submitted:
    debt_to_income = loan_amount / annual_income
    input_dict = {
        "age": age,
        "annual_income": annual_income,
        "credit_score": credit_score,
        "num_inquiries": num_inquiries,
        "open_credit_lines": open_credit_lines,
        "total_accounts": total_accounts,
        "delinquent_accounts": delinquent_accounts,
        "loan_amount": loan_amount,
        "loan_term_months": loan_term_months,
        "debt_to_income": debt_to_income
    }
    input_df = pd.DataFrame([input_dict])
    score, category = predict_risk(input_df)

    st.success(f"🧠 Risk Score: {score} → Category: **{category}**")
    input_dict.update({"prediction": score, "risk_category": category})
    save_to_db(input_dict)
    st.info("📥 Entry saved to database")

# ----------------------------
# Section 3: Past Predictions
# ----------------------------
st.subheader("📊 Past Predictions")
try:
    df = pd.read_sql("SELECT * FROM loan_predictions ORDER BY id DESC", engine)
    st.dataframe(df)
except Exception as e:
    st.warning("No data available yet. Once predictions are made, they will appear here.")

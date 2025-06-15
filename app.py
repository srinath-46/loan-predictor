import streamlit as st
import pandas as pd
from sqlalchemy import text
from utils import predict_risk, save_to_db, init_db, engine, load_csvs_to_db

st.set_page_config(page_title="Loan Risk Predictor", layout="centered")
st.title("🏦 Loan Default Risk Predictor")

# Step 1: Initialize database
init_db()

# Step 2: Load CSVs ONCE (first run only)
if "csv_loaded" not in st.session_state:
    with st.spinner("Loading CSVs into database..."):
        load_csvs_to_db()
        st.session_state.csv_loaded = True
        st.success("✅ CSVs loaded into database.")

# ----------------------------
# Section 1: Search by Customer ID
# ----------------------------
st.subheader("📂 Search Existing Customer")

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

            # 🔧 Add required model features
            input_dict['credit_utilization'] = input_dict['open_credit_lines'] / input_dict['total_accounts']
            input_dict['payment_ratio'] = 0.85  # Approximate value
            input_dict['loan_age_months'] = 12  # Estimated default
            input_dict['gender_encoded'] = 0     # Default: 0 (female)
            input_dict['marital_status_encoded'] = 0  # Default: 0 (single)

            # Convert to DataFrame and match feature order
            input_df = pd.DataFrame([input_dict])
            input_df = input_df[[
                'age', 'annual_income', 'credit_score', 'num_inquiries',
                'open_credit_lines', 'total_accounts', 'delinquent_accounts',
                'debt_to_income', 'credit_utilization', 'payment_ratio',
                'loan_age_months', 'gender_encoded', 'marital_status_encoded'
            ]]

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
    gender = st.selectbox("Gender", ["Female", "Male"])
    marital_status = st.selectbox("Marital Status", ["Single", "Married"])

    submitted = st.form_submit_button("📊 Predict")

if submitted:
    debt_to_income = loan_amount / annual_income
    credit_utilization = open_credit_lines / total_accounts
    payment_ratio = 0.85
    loan_age_months = 12
    gender_encoded = 1 if gender == "Male" else 0
    marital_status_encoded = 1 if marital_status == "Married" else 0

    input_dict = {
        "age": age,
        "annual_income": annual_income,
        "credit_score": credit_score,
        "num_inquiries": num_inquiries,
        "open_credit_lines": open_credit_lines,
        "total_accounts": total_accounts,
        "delinquent_accounts": delinquent_accounts,
        "debt_to_income": debt_to_income,
        "credit_utilization": credit_utilization,
        "payment_ratio": payment_ratio,
        "loan_age_months": loan_age_months,
        "gender_encoded": gender_encoded,
        "marital_status_encoded": marital_status_encoded
    }

    input_df = pd.DataFrame([input_dict])
    score, category = predict_risk(input_df)

    st.success(f"🧠 Risk Score: {score} → Category: **{category}**")
    input_dict.update({"prediction": score, "risk_category": category})
    save_to_db(input_dict)
    st.info("📥 Entry saved to database")

# ----------------------------
# Section 3: Show History
# ----------------------------
st.subheader("📊 Past Predictions")

try:
    df = pd.read_sql("SELECT * FROM loan_predictions ORDER BY id DESC", engine)
    st.dataframe(df)
except Exception as e:
    st.warning("No predictions found in the database yet.")

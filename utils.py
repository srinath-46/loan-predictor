import pandas as pd
import joblib
from sqlalchemy import create_engine, text

model = joblib.load("xgb_model.pkl")
engine = create_engine('sqlite:///database.db')

def init_db():
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS loan_predictions"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS loan_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                age INTEGER,
                annual_income REAL,
                credit_score INTEGER,
                num_inquiries INTEGER,
                open_credit_lines INTEGER,
                total_accounts INTEGER,
                delinquent_accounts INTEGER,
                loan_amount REAL,
                loan_term_months INTEGER,
                debt_to_income REAL,
                credit_utilization REAL,
                payment_ratio REAL,
                loan_age_months INTEGER,
                gender_encoded INTEGER,
                marital_status_encoded INTEGER,
                prediction REAL,
                risk_category TEXT
            );
        """))


def predict_risk(input_df):
    pred_prob = model.predict_proba(input_df)[0][1]
    risk_score = round(pred_prob * 100, 2)
    if risk_score >= 70:
        risk = "High"
    elif risk_score >= 40:
        risk = "Medium"
    else:
        risk = "Low"
    return risk_score, risk

def save_to_db(data_dict):
    df = pd.DataFrame([data_dict])
    df.to_sql("loan_predictions", engine, if_exists="append", index=False)

def load_csvs_to_db():
    customer_df = pd.read_csv("customer_profile_large.csv")
    loan_df = pd.read_csv("loan_history_large.csv")
    repayment_df = pd.read_csv("repayment_records_cleaned.csv")
    credit_df = pd.read_csv("credit_score_large.csv")
    econ_df = pd.read_csv("economic_indicators_large.csv")

    customer_df.to_sql("customers", engine, if_exists="replace", index=False)
    loan_df.to_sql("loans", engine, if_exists="replace", index=False)
    repayment_df.to_sql("repayments", engine, if_exists="replace", index=False)
    credit_df.to_sql("credits", engine, if_exists="replace", index=False)
    econ_df.to_sql("economic_indicators", engine, if_exists="replace", index=False)

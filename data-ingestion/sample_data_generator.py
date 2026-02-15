import uuid
import random
import json
import os
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()

# ---------------- CONFIG ----------------

NUM_CUSTOMERS = 200
SUSPICIOUS_RATIO = 0.6

CRIME_TYPES = [
    "layering",
    "structuring",
    "account_takeover",
    "sanctions",
    "elder_exploitation",
    "cyber_fraud",
    "trade_based_ml"
]

MODEL_METADATA = {
    "model_name": "risk_model_v1",
    "model_version": "1.0.0",
    "rule_engine_version": "2.1.3"
}

OUTPUT_FOLDER = "sample-data"

# ---------------- SETUP OUTPUT FOLDER ----------------

def setup_output_folder():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created folder: {OUTPUT_FOLDER}")
    else:
        print(f"Folder already exists: {OUTPUT_FOLDER}")

def write_json(filename, data):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# ---------------- DATA GENERATION ----------------

def generate_customer():
    age = random.randint(25, 85)
    return {
        "customer_id": f"CUST_{uuid.uuid4().hex[:8]}",
        "full_name": fake.name(),
        "age": age,
        "occupation": random.choice([
            "Retail Business Owner",
            "Consultant",
            "Importer/Exporter",
            "IT Professional",
            "Retired"
        ]),
        "synthetic_flag": True
    }

def generate_kyc(customer):
    return {
        "customer_id": customer["customer_id"],
        "expected_monthly_turnover": random.randint(200000, 800000),
        "pep_flag": random.choice([False, False, False, True]),
        "sanctions_flag": False,
        "synthetic_flag": True
    }

def generate_account(customer_id):
    return {
        "account_id": f"ACC_{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id,
        "synthetic_flag": True
    }

def generate_normal_transactions(account_id, turnover):
    txns = []
    for _ in range(30):
        txns.append({
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "account_id": account_id,
            "amount": random.randint(5000, turnover // 5),
            "country": "India",
            "date": fake.date_between(start_date='-60d', end_date='-10d').isoformat(),
            "synthetic_flag": True
        })
    return txns

# ---------------- SUSPICIOUS PATTERN ----------------

def inject_layering(account_id):
    txns = []
    for _ in range(47):
        txns.append({
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "account_id": account_id,
            "amount": random.randint(80000, 150000),
            "country": "India",
            "date": datetime.now().isoformat(),
            "synthetic_flag": True
        })

    txns.append({
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 5000000,
        "country": "UAE",
        "date": datetime.now().isoformat(),
        "synthetic_flag": True
    })

    return txns

# ---------------- FEATURE ENGINEERING ----------------

def compute_features(transactions, customer, kyc):
    inbound_count = len(transactions)
    foreign_txn = sum(1 for t in transactions if t["country"] != "India")
    total_amount = sum(t["amount"] for t in transactions)

    return {
        "inbound_count_7d": inbound_count,
        "foreign_txn_count": foreign_txn,
        "total_amount_7d": total_amount,
        "age": customer["age"],
        "expected_turnover": kyc["expected_monthly_turnover"]
    }

def generate_shap_values(features):
    shap = []

    shap.append({
        "feature": "inbound_count_7d",
        "value": features["inbound_count_7d"],
        "contribution": features["inbound_count_7d"] * 0.5
    })

    shap.append({
        "feature": "foreign_txn_count",
        "value": features["foreign_txn_count"],
        "contribution": features["foreign_txn_count"] * 10
    })

    shap.append({
        "feature": "total_amount_7d",
        "value": features["total_amount_7d"],
        "contribution": features["total_amount_7d"] / 100000
    })

    shap.append({
        "feature": "age",
        "value": features["age"],
        "contribution": -2 if features["age"] < 30 else 1
    })

    shap.append({
        "feature": "expected_turnover",
        "value": features["expected_turnover"],
        "contribution": -5 if features["total_amount_7d"] < features["expected_turnover"] else 5
    })

    return shap

def compute_risk_score(shap_values):
    base_score = 30
    total = sum(item["contribution"] for item in shap_values)
    return min(max(int(base_score + total), 0), 100)

# ---------------- ALERT + CASE ----------------

def generate_alert(customer_id, scenario, features):
    shap_values = generate_shap_values(features)
    risk_score = compute_risk_score(shap_values)

    return {
        "alert_id": f"ALERT_{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id,
        "alert_type": scenario,
        "risk_score": risk_score,
        "model_metadata": MODEL_METADATA,
        "feature_values": features,
        "shap_explanations": shap_values,
        "top_risk_drivers": sorted(
            shap_values,
            key=lambda x: abs(x["contribution"]),
            reverse=True
        )[:3],
        "alert_date": datetime.now().isoformat(),
        "synthetic_flag": True
    }

def generate_case(alert):
    return {
        "case_id": f"CASE_{uuid.uuid4().hex[:8]}",
        "alert_id": alert["alert_id"],
        "assigned_analyst": random.choice(["Analyst_A", "Analyst_B"]),
        "status": "Under Review",
        "synthetic_flag": True
    }

# ---------------- MAIN ----------------

def main():

    setup_output_folder()

    customers, kycs, accounts, transactions, alerts, cases = [], [], [], [], [], []

    for _ in range(NUM_CUSTOMERS):

        customer = generate_customer()
        kyc = generate_kyc(customer)
        account = generate_account(customer["customer_id"])
        normal_txns = generate_normal_transactions(
            account["account_id"],
            kyc["expected_monthly_turnover"]
        )

        customers.append(customer)
        kycs.append(kyc)
        accounts.append(account)
        transactions.extend(normal_txns)

        if random.random() < SUSPICIOUS_RATIO:
            scenario = random.choice(CRIME_TYPES)

            suspicious_txns = inject_layering(account["account_id"])
            transactions.extend(suspicious_txns)

            features = compute_features(suspicious_txns, customer, kyc)
            alert = generate_alert(customer["customer_id"], scenario, features)
            case = generate_case(alert)

            alerts.append(alert)
            cases.append(case)

    write_json("customers.json", customers)
    write_json("kyc.json", kycs)
    write_json("accounts.json", accounts)
    write_json("transactions.json", transactions)
    write_json("alerts.json", alerts)
    write_json("cases.json", cases)

    print(f"\n✅ Synthetic dataset generated successfully inside '{OUTPUT_FOLDER}' folder!")

if __name__ == "__main__":
    main()

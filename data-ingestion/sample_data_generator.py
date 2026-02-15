import uuid
import random
import json
import os
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("en_GB")

# ================= CONFIG =================

NUM_CUSTOMERS = 300
SUSPICIOUS_RATIO = 0.65
OUTPUT_FOLDER = "sample-data"

CRIME_SCENARIOS = {
    "money_laundering": [
        "layering",
        "structuring",
        "mule_account",
        "funnel_account",
        "trade_based_ml",
        "crypto_offramp",
        "cash_intensive_business"
    ],
    "fraud": [
        "account_takeover",
        "loan_stacking",
        "mortgage_fraud",
        "app_scam",
        "cyber_fraud"
    ],
    "sanctions": ["sanctions"],
    "terrorist_financing": ["terrorist_financing"]
}

SCENARIO_WEIGHTS = {
    "money_laundering": 0.45,
    "fraud": 0.30,
    "sanctions": 0.10,
    "terrorist_financing": 0.15
}

MODEL_METADATA = {
    "model_name": "uk_fincrime_risk_model",
    "model_version": "5.0.0",
    "rule_engine_version": "6.0.0",
    "jurisdiction": "UK"
}

# ================= SETUP =================

def setup_output_folder():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

def write_json(filename, data):
    with open(os.path.join(OUTPUT_FOLDER, filename), "w") as f:
        json.dump(data, f, indent=2)

def random_date_within(days):
    start = datetime.now() - timedelta(days=days)
    return (start + timedelta(hours=random.randint(0, days * 24))).isoformat()

# ================= BASE DATA =================

def generate_customer():
    return {
        "customer_id": f"CUST_{uuid.uuid4().hex[:8]}",
        "full_name": fake.name(),
        "age": random.randint(25, 85),
        "residence_country": "UK",
        "occupation": random.choice([
            "Retail Business Owner", "Consultant",
            "Importer/Exporter", "IT Professional", "Retired"
        ]),
        "synthetic_flag": True
    }

def generate_kyc(customer):
    return {
        "customer_id": customer["customer_id"],
        "expected_monthly_turnover": random.randint(20000, 150000),
        "pep_flag": random.choice([False, False, False, True]),
        "sanctions_flag": False,
        "synthetic_flag": True
    }

def generate_account(customer_id):
    return {
        "account_id": f"ACC_{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id,
        "currency": "GBP",
        "synthetic_flag": True
    }

def generate_normal_transactions(account_id, turnover):
    txns = []
    for _ in range(30):
        txns.append({
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "account_id": account_id,
            "amount": random.randint(100, max(1000, turnover // 4)),
            "country": "UK",
            "transaction_type": random.choice(["Credit", "Debit"]),
            "date": random_date_within(60),
            "synthetic_flag": True
        })
    return txns

# ================= INJECTORS =================

def inject_layering(account_id):
    txns = []
    for _ in range(40):
        txns.append({
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "account_id": account_id,
            "amount": random.randint(2000, 8000),
            "country": "UK",
            "transaction_type": "Credit",
            "date": random_date_within(7),
            "synthetic_flag": True
        })
    txns.append({
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 200000,
        "country": "UK",
        "transaction_type": "Debit",
        "date": random_date_within(2),
        "synthetic_flag": True
    })
    return txns

def inject_structuring(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 9900,
        "country": "UK",
        "transaction_type": "Cash Deposit",
        "date": random_date_within(5),
        "synthetic_flag": True
    } for _ in range(20)]

def inject_mule_account(account_id):
    txns = []
    for _ in range(15):
        txns.append({
            "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
            "account_id": account_id,
            "amount": random.randint(2000, 6000),
            "country": "UK",
            "transaction_type": "Credit",
            "date": random_date_within(7),
            "synthetic_flag": True
        })
    txns.append({
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 85000,
        "country": "UK",
        "transaction_type": "Debit",
        "date": random_date_within(2),
        "synthetic_flag": True
    })
    return txns

def inject_funnel_account(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": random.randint(4000, 12000),
        "country": "UK",
        "transaction_type": "Cash Deposit",
        "date": random_date_within(5),
        "synthetic_flag": True
    } for _ in range(25)]

def inject_trade_based_ml(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 300000,
        "country": "UK",
        "transaction_type": "Trade Payment",
        "invoice_value": 80000,
        "date": random_date_within(3),
        "synthetic_flag": True
    }]

def inject_crypto_offramp(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": random.randint(50000, 150000),
        "country": "UK",
        "transaction_type": "Credit",
        "crypto_exchange_flag": True,
        "date": random_date_within(3),
        "synthetic_flag": True
    }]

def inject_cash_intensive_business(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": random.randint(8000, 15000),
        "country": "UK",
        "transaction_type": "Cash Deposit",
        "date": random_date_within(7),
        "synthetic_flag": True
    } for _ in range(30)]

def inject_account_takeover(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 45000,
        "country": "UK",
        "transaction_type": "Debit",
        "new_device_flag": True,
        "date": random_date_within(2),
        "synthetic_flag": True
    }]

def inject_loan_stacking(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": random.randint(20000, 40000),
        "country": "UK",
        "transaction_type": "Loan Credit",
        "date": random_date_within(3),
        "synthetic_flag": True
    } for _ in range(5)]

def inject_mortgage_fraud(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 350000,
        "country": "UK",
        "transaction_type": "Loan Disbursement",
        "income_mismatch_flag": True,
        "date": random_date_within(3),
        "synthetic_flag": True
    }]

def inject_app_scam(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 45000,
        "country": "UK",
        "transaction_type": "Faster Payment",
        "customer_reported_scam_flag": True,
        "date": random_date_within(2),
        "synthetic_flag": True
    }]

def inject_cyber_fraud(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 22000,
        "country": "UK",
        "transaction_type": "Debit",
        "ip_mismatch_flag": True,
        "date": random_date_within(2),
        "synthetic_flag": True
    }]

def inject_sanctions(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": 150000,
        "country": "UK",
        "transaction_type": "Wire",
        "counterparty_high_risk_flag": True,
        "date": random_date_within(3),
        "synthetic_flag": True
    }]

def inject_terrorist_financing(account_id):
    return [{
        "transaction_id": f"TXN_{uuid.uuid4().hex[:8]}",
        "account_id": account_id,
        "amount": random.randint(200, 900),
        "country": "UK",
        "transaction_type": "Debit",
        "date": random_date_within(7),
        "synthetic_flag": True
    } for _ in range(20)]

INJECTOR_MAP = {
    "layering": inject_layering,
    "structuring": inject_structuring,
    "mule_account": inject_mule_account,
    "funnel_account": inject_funnel_account,
    "trade_based_ml": inject_trade_based_ml,
    "crypto_offramp": inject_crypto_offramp,
    "cash_intensive_business": inject_cash_intensive_business,
    "account_takeover": inject_account_takeover,
    "loan_stacking": inject_loan_stacking,
    "mortgage_fraud": inject_mortgage_fraud,
    "app_scam": inject_app_scam,
    "cyber_fraud": inject_cyber_fraud,
    "sanctions": inject_sanctions,
    "terrorist_financing": inject_terrorist_financing
}

# ================= FEATURES =================

def compute_features(all_txns, kyc):
    turnover = max(kyc["expected_monthly_turnover"], 1)

    window_start = datetime.now() - timedelta(days=7)
    recent = [t for t in all_txns if datetime.fromisoformat(t["date"]) >= window_start]

    total_amount = sum(t["amount"] for t in recent)
    credit_count = len([t for t in recent if t["transaction_type"] == "Credit"])
    debit_count = len([t for t in recent if t["transaction_type"] == "Debit"])

    deviation_ratio = total_amount / turnover

    return {
        "credit_count_7d": credit_count,
        "debit_count_7d": debit_count,
        "total_amount_7d": total_amount,
        "deviation_ratio": round(deviation_ratio, 2)
    }

def generate_shap(features, typology):

    shap = []

    if typology in ["layering", "mule_account"]:
        shap.append({
            "feature": "credit_count_7d",
            "value": features["credit_count_7d"],
            "contribution": min(features["credit_count_7d"] * 0.6, 20)
        })

    if typology in ["account_takeover", "terrorist_financing", "cyber_fraud"]:
        shap.append({
            "feature": "debit_count_7d",
            "value": features["debit_count_7d"],
            "contribution": min(features["debit_count_7d"] * 1.0, 25)
        })

    shap.append({
        "feature": "deviation_ratio",
        "value": features["deviation_ratio"],
        "contribution": min(features["deviation_ratio"] * 10, 30)
    })

    return shap

def compute_risk(shap_values):
    return min(30 + int(sum(x["contribution"] for x in shap_values)), 100)

# ================= ALERT =================

def generate_alert(customer_id, category, typology, features):
    shap_vals = generate_shap(features, typology)
    risk = compute_risk(shap_vals)

    return {
        "alert_id": f"ALERT_{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id,
        "crime_category": category,
        "typology_type": typology,
        "risk_score": risk,
        "model_metadata": MODEL_METADATA,
        "feature_values": features,
        "shap_explanations": shap_vals,
        "top_risk_drivers": sorted(shap_vals, key=lambda x: abs(x["contribution"]), reverse=True)[:3],
        "alert_date": datetime.now().isoformat(),
        "synthetic_flag": True
    }

def generate_case(alert):
    return {
        "case_id": f"CASE_{uuid.uuid4().hex[:8]}",
        "alert_id": alert["alert_id"],
        "assigned_analyst": random.choice(["UK_Analyst_A", "UK_Analyst_B"]),
        "status": "Under Review",
        "synthetic_flag": True
    }

# ================= MAIN =================

def main():

    setup_output_folder()

    customers, kycs, accounts, transactions, alerts, cases = [], [], [], [], [], []

    categories = list(CRIME_SCENARIOS.keys())
    weights = [SCENARIO_WEIGHTS[c] for c in categories]

    for _ in range(NUM_CUSTOMERS):

        customer = generate_customer()
        kyc = generate_kyc(customer)
        account = generate_account(customer["customer_id"])

        customers.append(customer)
        kycs.append(kyc)
        accounts.append(account)

        normal_txns = generate_normal_transactions(account["account_id"], kyc["expected_monthly_turnover"])
        transactions.extend(normal_txns)

        if random.random() < SUSPICIOUS_RATIO:

            category = random.choices(categories, weights=weights)[0]
            typology = random.choice(CRIME_SCENARIOS[category])

            suspicious_txns = INJECTOR_MAP[typology](account["account_id"])
            transactions.extend(suspicious_txns)

            all_txns = normal_txns + suspicious_txns
            features = compute_features(all_txns, kyc)

            alert = generate_alert(customer["customer_id"], category, typology, features)
            case = generate_case(alert)

            alerts.append(alert)
            cases.append(case)

    write_json("customers.json", customers)
    write_json("kyc.json", kycs)
    write_json("accounts.json", accounts)
    write_json("transactions.json", transactions)
    write_json("alerts.json", alerts)
    write_json("cases.json", cases)

    print(f"\n✅ Enterprise UK Financial Crime dataset generated in '{OUTPUT_FOLDER}'")

if __name__ == "__main__":
    main()

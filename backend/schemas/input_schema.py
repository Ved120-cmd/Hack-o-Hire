"""
Input Schemas – Pydantic models for the JSON payload ingested at /cases/ingest.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    transaction_id: str
    date: str
    amount: float
    currency: str = "INR"
    type: str  # credit | debit
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_bank: Optional[str] = None
    counterparty_country: Optional[str] = "IN"
    channel: Optional[str] = None
    description: Optional[str] = None


class AccountInput(BaseModel):
    account_id: str
    account_type: str = "savings"
    currency: str = "INR"
    opened_date: Optional[str] = None
    balance: float = 0.0
    transactions: List[TransactionInput] = []


class KYCInput(BaseModel):
    risk_rating: str = "medium"  # low | medium | high
    pep_status: bool = False
    sanctions_match: bool = False
    source_of_funds: Optional[str] = None
    occupation: Optional[str] = None
    annual_income: Optional[float] = None
    verification_date: Optional[str] = None
    id_documents: List[str] = []


class CustomerInput(BaseModel):
    customer_id: str
    name: str
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = "IN"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class AlertInput(BaseModel):
    alert_id: str
    alert_type: str
    severity: str = "medium"
    description: Optional[str] = None
    generated_at: Optional[str] = None


class CaseInput(BaseModel):
    """Top-level JSON input payload."""
    customer: CustomerInput
    kyc: KYCInput
    accounts: List[AccountInput]
    transactions: Optional[List[TransactionInput]] = None  # flat list alternative
    alerts: List[AlertInput] = []

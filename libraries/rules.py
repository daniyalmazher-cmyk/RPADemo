"""Detection rules: regex patterns, scoring weights, classification tiers."""
import re

# Sensitive data patterns
CNIC_PATTERN = re.compile(r"\b\d{5}[-\s]?\d{7}[-\s]?\d{1}\b")
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?:\+?92|0)[\s-]?3\d{2}[\s-]?\d{7}\b")
SALARY_KEYWORDS = re.compile(
    r"\b(salary|payroll|net\s*pay|gross\s*pay|annual\s*income|monthly\s*income|monthly_salary)\b",
    re.IGNORECASE,
)

# Risk score weights: full weight for first hit, half per additional, capped at 100
WEIGHTS = {
    "cnic": 30,
    "iban": 25,
    "credit_card": 35,
    "salary_indicator": 20,
    "email": 5,
    "phone": 5,
}

# Classification tiers
HIGHLY_CONFIDENTIAL = {"cnic", "iban", "credit_card"}
CONFIDENTIAL = {"salary_indicator", "email", "phone"}

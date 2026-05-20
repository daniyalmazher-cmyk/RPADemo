"""Detection rules: regex patterns, scoring weights, classification tiers.

Tuned for Saudi Arabia (KSA): Saudi National ID / Iqama, SA IBAN, +966 mobile.
"""
import re

# Saudi National ID (citizens, leading 1) and Iqama (residents, leading 2):
# both are 10 digits. Weak pattern by itself — a checksum validator could be
# added later to cut false positives.
SAUDI_ID_PATTERN = re.compile(r"\b[12]\d{9}\b")

# Saudi IBAN: "SA" + 2 check digits + 2-digit bank code + 18-digit BBAN
# = 24 chars total, i.e. SA followed by 22 digits.
IBAN_PATTERN = re.compile(r"\bSA\d{22}\b")

CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Saudi mobile: +966 5X XXXXXXXX or 05X XXXXXXXX (always 5 followed by 8 more
# digits). Allow flexible separator placement so common groupings like
# "+966 50 123 4567", "055 598 7654", or "0501234567" all match.
PHONE_PATTERN = re.compile(r"(?:\+?966|0)[\s-]?5(?:[\s-]?\d){8}\b")

SALARY_KEYWORDS = re.compile(
    r"\b(salary|payroll|net\s*pay|gross\s*pay|annual\s*income|monthly\s*income|monthly_salary)\b",
    re.IGNORECASE,
)

# Risk score weights: full weight for first hit, half per additional, capped at 100
WEIGHTS = {
    "saudi_id": 30,
    "iban": 25,
    "credit_card": 35,
    "salary_indicator": 20,
    "email": 5,
    "phone": 5,
}

# Classification tiers
HIGHLY_CONFIDENTIAL = {"saudi_id", "iban", "credit_card"}
CONFIDENTIAL = {"salary_indicator", "email", "phone"}

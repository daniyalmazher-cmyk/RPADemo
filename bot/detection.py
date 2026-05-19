"""Regex-based sensitive data detection."""
import re

# Pakistani CNIC: 5 digits - 7 digits - 1 digit, separators optional
CNIC_PATTERN = re.compile(r"\b\d{5}[-\s]?\d{7}[-\s]?\d{1}\b")

# IBAN: 2 letter country code + 2 check digits + 11-30 alphanumerics
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")

# Credit card: 13-19 digits with optional space/dash separators
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Pakistani mobile: +92 / 0092 / 0 followed by 3XXXXXXXXX
PHONE_PATTERN = re.compile(r"(?:\+?92|0)[\s-]?3\d{2}[\s-]?\d{7}\b")

SALARY_KEYWORDS = re.compile(
    r"\b(salary|payroll|net\s*pay|gross\s*pay|annual\s*income|monthly\s*income|monthly_salary)\b",
    re.IGNORECASE,
)


def _luhn_valid(digits: str) -> bool:
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def detect_sensitive_data(content: str) -> dict[str, list[str]]:
    """Run every pattern over the text. Returns a dict of category -> unique matches."""
    detections: dict[str, list[str]] = {
        "cnic": sorted({m for m in CNIC_PATTERN.findall(content)}),
        "iban": sorted({m for m in IBAN_PATTERN.findall(content)}),
        "credit_card": [],
        "email": sorted({m for m in EMAIL_PATTERN.findall(content)}),
        "phone": sorted({m for m in PHONE_PATTERN.findall(content)}),
        "salary_indicator": [],
    }

    seen_cards: set[str] = set()
    for raw in CREDIT_CARD_PATTERN.findall(content):
        normalized = re.sub(r"[\s-]", "", raw)
        if _luhn_valid(normalized) and normalized not in seen_cards:
            seen_cards.add(normalized)
            detections["credit_card"].append(normalized)

    # Exclude credit-card matches that overlap with IBANs (rare but possible)
    detections["credit_card"] = [
        c for c in detections["credit_card"] if not any(c in iban for iban in detections["iban"])
    ]

    if SALARY_KEYWORDS.search(content):
        detections["salary_indicator"] = ["present"]

    return detections

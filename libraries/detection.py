"""Apply rules + validators to a text blob; return categorized detections."""
import re

from libraries.rules import (
    CREDIT_CARD_PATTERN,
    EMAIL_PATTERN,
    IBAN_PATTERN,
    PHONE_PATTERN,
    SALARY_KEYWORDS,
    SAUDI_ID_PATTERN,
)
from libraries.validators import luhn_valid


def detect(content: str) -> dict[str, list[str]]:
    detections: dict[str, list[str]] = {
        "saudi_id": sorted(set(SAUDI_ID_PATTERN.findall(content))),
        "iban": sorted(set(IBAN_PATTERN.findall(content))),
        "credit_card": [],
        "email": sorted(set(EMAIL_PATTERN.findall(content))),
        "phone": sorted(set(PHONE_PATTERN.findall(content))),
        "salary_indicator": [],
    }

    seen: set[str] = set()
    for raw in CREDIT_CARD_PATTERN.findall(content):
        norm = re.sub(r"[\s-]", "", raw)
        if luhn_valid(norm) and norm not in seen:
            seen.add(norm)
            detections["credit_card"].append(norm)

    # Drop card hits that overlap an IBAN (digits inside an IBAN can luhn-validate).
    # Compare digit-only forms so the SA letters in the IBAN don't break the check.
    iban_digit_blobs = [re.sub(r"\D", "", iban) for iban in detections["iban"]]
    detections["credit_card"] = [
        c for c in detections["credit_card"]
        if not any(c in blob for blob in iban_digit_blobs)
    ]

    if SALARY_KEYWORDS.search(content):
        detections["salary_indicator"] = ["present"]

    return detections

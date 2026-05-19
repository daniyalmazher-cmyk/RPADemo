"""Classification labels and risk scoring."""

# Weight assigned to the first occurrence of each category
WEIGHTS = {
    "cnic": 30,
    "iban": 25,
    "credit_card": 35,
    "salary_indicator": 20,
    "email": 5,
    "phone": 5,
}

HIGHLY_CONFIDENTIAL = {"cnic", "iban", "credit_card"}
CONFIDENTIAL = {"salary_indicator", "email", "phone"}


def classify_file(detections: dict[str, list[str]]) -> str:
    """Map detections to one of: Highly Confidential / Confidential / Public."""
    if any(detections.get(cat) for cat in HIGHLY_CONFIDENTIAL):
        return "Highly Confidential"
    if any(detections.get(cat) for cat in CONFIDENTIAL):
        return "Confidential"
    return "Public"


def compute_risk_score(detections: dict[str, list[str]]) -> int:
    """0-100 score. Full weight for first hit, half weight per additional hit, capped at 100."""
    score = 0
    for category, weight in WEIGHTS.items():
        count = len(detections.get(category, []))
        if count == 0:
            continue
        score += weight + (count - 1) * (weight // 2)
    return min(score, 100)

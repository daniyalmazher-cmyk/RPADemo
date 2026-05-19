"""Map detections to a classification label and a 0-100 risk score."""
from libraries.rules import CONFIDENTIAL, HIGHLY_CONFIDENTIAL, WEIGHTS


def classify_file(detections: dict[str, list[str]]) -> str:
    if any(detections.get(c) for c in HIGHLY_CONFIDENTIAL):
        return "Highly Confidential"
    if any(detections.get(c) for c in CONFIDENTIAL):
        return "Confidential"
    return "Public"


def compute_risk_score(detections: dict[str, list[str]]) -> int:
    score = 0
    for category, weight in WEIGHTS.items():
        count = len(detections.get(category, []))
        if count == 0:
            continue
        score += weight + (count - 1) * (weight // 2)
    return min(score, 100)

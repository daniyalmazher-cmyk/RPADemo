"""Report writers: CSV and JSON outputs that downstream DLP systems can consume."""
import csv
import json
from pathlib import Path

CSV_FIELDS = [
    "file_name",
    "file_path",
    "file_type",
    "classification",
    "risk_score",
    "cnic_count",
    "iban_count",
    "credit_card_count",
    "email_count",
    "phone_count",
    "salary_indicator",
]


def write_csv_report(results: list[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in results:
            d = r["detections"]
            writer.writerow({
                "file_name": r["file_name"],
                "file_path": r["file_path"],
                "file_type": r["file_type"],
                "classification": r["classification"],
                "risk_score": r["risk_score"],
                "cnic_count": len(d["cnic"]),
                "iban_count": len(d["iban"]),
                "credit_card_count": len(d["credit_card"]),
                "email_count": len(d["email"]),
                "phone_count": len(d["phone"]),
                "salary_indicator": "yes" if d["salary_indicator"] else "no",
            })


def write_json_report(results: list[dict], path: Path) -> None:
    payload = {
        "schema_version": "1.0",
        "record_count": len(results),
        "records": results,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)

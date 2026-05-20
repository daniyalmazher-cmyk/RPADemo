"""Generate fake KSA-flavored fintech files for emailing to the bot's Gmail inbox.

Not part of the bot itself — this is a developer/demo utility. Writes a set
of realistic-looking files (CSV, Excel, PDF, TXT) into ./sample_files/ so
they can be attached to a "DLP SCAN" email.

All IDs, IBANs, card numbers, phones and addresses below are synthetic.

Usage:
    python scripts/generate_sample_files.py
"""
import csv
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT_DIR = Path("sample_files")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created = [
        _customers_csv(OUT_DIR / "customers_export.csv"),
        _salary_xlsx(OUT_DIR / "salary_sheet_q1.xlsx"),
        _transactions_csv(OUT_DIR / "card_transactions_apr.csv"),
        _kyc_pdf(OUT_DIR / "kyc_report_mohammed.pdf"),
        _kyc_txt_arabic(OUT_DIR / "kyc_request_arabic.txt"),
        _public_notice(OUT_DIR / "branch_notice.txt"),
    ]
    print(f"Wrote {len(created)} files to {OUT_DIR}/")
    for p in created:
        print(f"  - {p}")


def _write_csv(path: Path, rows: list[dict]) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _write_xlsx(path: Path, rows: list[dict]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(list(rows[0].keys()))
    for r in rows:
        ws.append(list(r.values()))
    wb.save(path)
    return path


def _customers_csv(path: Path) -> Path:
    rows = [
        {"customer_id": "C-1001", "name": "Mohammed Al-Saud",
         "national_id": "1023456789",
         "email": "mohammed.alsaud@example.com", "phone": "+966 50 123 4567",
         "iban": "SA0380000000608010167519",
         "address": "Olaya Street, Riyadh"},
        {"customer_id": "C-1002", "name": "Fatimah Al-Qahtani",
         "national_id": "1098765432",
         "email": "fatimah.q@example.com", "phone": "055 598 7654",
         "iban": "SA4420000001234567891234",
         "address": "Tahlia Street, Jeddah"},
        {"customer_id": "C-1003", "name": "Abdullah Al-Otaibi",
         "national_id": "1056789012",
         "email": "abdullah.o@example.com", "phone": "+966 54 555 1234",
         "iban": "SA2110000056781234567891",
         "address": "King Fahd Road, Dammam"},
        {"customer_id": "C-1004", "name": "Rajeev Kumar",
         "national_id": "2034567890",  # Iqama (resident)
         "email": "rajeev.k@example.com", "phone": "+966 53 222 3344",
         "iban": "SA9180000000123456789012",
         "address": "Corniche Road, Khobar"},
    ]
    return _write_csv(path, rows)


def _salary_xlsx(path: Path) -> Path:
    rows = [
        {"employee_id": "E-501", "name": "Noura Al-Ghamdi", "department": "Risk",
         "monthly_salary": 32000, "annual_income": 384000,
         "bank_iban": "SA8610000000222333444555"},
        {"employee_id": "E-502", "name": "Khalid Al-Dosari", "department": "Engineering",
         "monthly_salary": 45000, "annual_income": 540000,
         "bank_iban": "SA5220000001112223334445"},
        {"employee_id": "E-503", "name": "Sara Al-Harbi", "department": "Compliance",
         "monthly_salary": 38000, "annual_income": 456000,
         "bank_iban": "SA1930000000556677889900"},
    ]
    return _write_xlsx(path, rows)


def _transactions_csv(path: Path) -> Path:
    # Card numbers below are well-known Luhn-valid test PANs (not real).
    rows = [
        {"txn_id": "T-9001", "card_number": "4539578763621486",
         "amount_sar": 1250, "merchant": "Amazon.sa", "date": "2026-04-01"},
        {"txn_id": "T-9002", "card_number": "5500000000000004",
         "amount_sar": 420, "merchant": "Noon", "date": "2026-04-02"},
        {"txn_id": "T-9003", "card_number": "371449635398431",
         "amount_sar": 8900, "merchant": "Saudia Airlines", "date": "2026-04-03"},
        {"txn_id": "T-9004", "card_number": "6011111111111117",
         "amount_sar": 220, "merchant": "HungerStation", "date": "2026-04-04"},
    ]
    return _write_csv(path, rows)


def _kyc_pdf(path: Path) -> Path:
    c = canvas.Canvas(str(path), pagesize=letter)
    _, height = letter
    y = height - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "KYC Verification Report")
    y -= 30
    c.setFont("Helvetica", 11)
    for line in [
        "Applicant: Ahmed Al-Shehri",
        "National ID: 1078901234",
        "Date of Birth: 1988-07-12",
        "Phone: +966 50 765 4321",
        "Email: ahmed.alshehri@example.com",
        "Residential Address: Al Olaya District, Riyadh",
        "Bank IBAN: SA2910000000789012345678",
        "Annual Income: SAR 720,000 (Salary)",
        "Source of Funds: Salary",
        "",
        "Verification Status: APPROVED",
        "Reviewed By: Compliance Officer #142",
    ]:
        c.drawString(50, y, line)
        y -= 18
    c.showPage()
    c.save()
    return path


def _kyc_txt_arabic(path: Path) -> Path:
    # Realistic shape for a Saudi bank intake: Arabic labels with Latin-digit
    # values for IDs / IBAN / phone (how these are usually written even in
    # Arabic-language forms).
    content = (
        "طلب فتح حساب بنكي\n"
        "\n"
        "الاسم: محمد الشهري\n"
        "رقم الهوية الوطنية: 1078901234\n"
        "الجوال: +966 50 111 2233\n"
        "البريد الإلكتروني: m.alshehri@example.com\n"
        "رقم الآيبان: SA0380000000608010167519\n"
        "الراتب الشهري: 25,000 ريال سعودي\n"
        "العنوان: حي العليا، الرياض\n"
        "\n"
        "ملاحظة: المعلومات الواردة في هذا المستند سرية.\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _public_notice(path: Path) -> Path:
    path.write_text(
        "Public Notice\n\n"
        "Branch hours updated. New timings effective May 2026.\n"
        "For more details visit our website.\n",
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    main()

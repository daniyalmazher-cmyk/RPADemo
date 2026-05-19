"""Generate realistic-looking fake fintech files for the demo input folder."""
from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_all_samples(input_dir: Path) -> list[Path]:
    input_dir.mkdir(parents=True, exist_ok=True)
    return [
        _customers_csv(input_dir / "customers_export.csv"),
        _salary_xlsx(input_dir / "salary_sheet_q1.xlsx"),
        _transactions_csv(input_dir / "card_transactions_apr.csv"),
        _kyc_pdf(input_dir / "kyc_report_faraz.pdf"),
        _public_notice(input_dir / "branch_notice.txt"),
    ]


def _customers_csv(path: Path) -> Path:
    rows = [
        {
            "customer_id": "C-1001", "name": "Ayesha Khan",
            "cnic": "35202-1234567-2",
            "email": "ayesha.khan@example.com", "phone": "+92 300 1234567",
            "iban": "PK36SCBL0000001123456702",
            "address": "12 Mall Road, Lahore",
        },
        {
            "customer_id": "C-1002", "name": "Bilal Ahmed",
            "cnic": "42101-7654321-9",
            "email": "bilal.ahmed@example.com", "phone": "0321 9876543",
            "iban": "PK24NBPA1234567890123456",
            "address": "44 Sea View, Karachi",
        },
        {
            "customer_id": "C-1003", "name": "Sara Tariq",
            "cnic": "61101-1111111-3",
            "email": "sara.t@example.com", "phone": "+92 333 4445556",
            "iban": "PK70HABB0000123456789012",
            "address": "9 F-10, Islamabad",
        },
        {
            "customer_id": "C-1004", "name": "Hassan Raza",
            "cnic": "33100-2222222-4",
            "email": "hassan.r@example.com", "phone": "0345 5556667",
            "iban": "PK11MEZN0099887766554433",
            "address": "88 Gulberg, Lahore",
        },
    ]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _salary_xlsx(path: Path) -> Path:
    rows = [
        {"employee_id": "E-501", "name": "Mariam Sheikh", "department": "Risk",
         "monthly_salary": 320000, "annual_income": 3840000,
         "bank_iban": "PK86UBLA0010002000300040"},
        {"employee_id": "E-502", "name": "Omar Farooq", "department": "Engineering",
         "monthly_salary": 450000, "annual_income": 5400000,
         "bank_iban": "PK52ABPA0011223344556677"},
        {"employee_id": "E-503", "name": "Zainab Iqbal", "department": "Compliance",
         "monthly_salary": 380000, "annual_income": 4560000,
         "bank_iban": "PK19BAHL0033445566778899"},
    ]
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def _transactions_csv(path: Path) -> Path:
    # Card numbers below are well-known test PANs (Luhn-valid, not real).
    rows = [
        {"txn_id": "T-9001", "card_number": "4539578763621486",
         "amount_pkr": 12500, "merchant": "Amazon", "date": "2026-04-01"},
        {"txn_id": "T-9002", "card_number": "5500000000000004",
         "amount_pkr": 4200, "merchant": "Daraz", "date": "2026-04-02"},
        {"txn_id": "T-9003", "card_number": "371449635398431",
         "amount_pkr": 89000, "merchant": "Emirates", "date": "2026-04-03"},
        {"txn_id": "T-9004", "card_number": "6011111111111117",
         "amount_pkr": 2200, "merchant": "Foodpanda", "date": "2026-04-04"},
    ]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _kyc_pdf(path: Path) -> Path:
    c = canvas.Canvas(str(path), pagesize=letter)
    _, height = letter
    y = height - 60
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "KYC Verification Report")
    y -= 30
    c.setFont("Helvetica", 11)
    lines = [
        "Applicant: Faraz Malik",
        "CNIC: 36502-7788990-1",
        "Date of Birth: 1988-07-12",
        "Phone: +92 301 7654321",
        "Email: faraz.malik@example.com",
        "Residential Address: 7 Bahria Town, Rawalpindi",
        "Bank IBAN: PK29ALFH0001234567890123",
        "Annual Income: PKR 7,200,000 (Salary)",
        "Source of Funds: Salary",
        "",
        "Verification Status: APPROVED",
        "Reviewed By: Compliance Officer #142",
    ]
    for line in lines:
        c.drawString(50, y, line)
        y -= 18
    c.showPage()
    c.save()
    return path


def _public_notice(path: Path) -> Path:
    path.write_text(
        "Public Notice\n\n"
        "Branch hours updated. New timings effective May 2026.\n"
        "For more details visit our website.\n",
        encoding="utf-8",
    )
    return path

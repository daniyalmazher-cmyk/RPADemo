"""File discovery and content extraction."""
from pathlib import Path

import pandas as pd
import pdfplumber
from RPA.FileSystem import FileSystem

SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls", ".pdf", ".txt")


def discover_files(root: Path) -> list[Path]:
    """Walk the input tree using RPA.FileSystem and return supported files, sorted."""
    fs = FileSystem()
    found: set[Path] = set()
    for ext in SUPPORTED_EXTENSIONS:
        for hit in fs.find_files(f"{root}/**/*{ext}", include_dirs=False):
            p = Path(str(hit))
            if p.is_file():
                found.add(p)
    return sorted(found)


def extract_content(file_path: Path) -> str:
    """Return text from CSV / Excel / PDF / TXT as a single blob."""
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        return df.to_string(index=False)

    if suffix in (".xlsx", ".xls"):
        sheets = pd.read_excel(file_path, sheet_name=None, dtype=str)
        parts = []
        for name, df in sheets.items():
            parts.append(f"# Sheet: {name}")
            parts.append(df.fillna("").astype(str).to_string(index=False))
        return "\n".join(parts)

    if suffix == ".pdf":
        pages = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        return "\n".join(pages)

    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")

    return ""

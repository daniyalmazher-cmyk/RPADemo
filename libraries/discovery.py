"""File discovery and content extraction."""
from pathlib import Path

import pandas as pd
from RPA.FileSystem import FileSystem
from RPA.PDF import PDF

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
        pdf = PDF()
        pages = pdf.get_text_from_pdf(str(file_path))
        if isinstance(pages, dict):
            return "\n".join(str(pages[k] or "") for k in sorted(pages.keys()))
        return str(pages or "")

    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")

    return ""

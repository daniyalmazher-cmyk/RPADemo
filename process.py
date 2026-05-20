"""Process orchestrator.

start() pulls fresh files from Gmail (via libraries.email_source), then runs
the discovery + detection + classification pipeline.
finish() writes reports + audit log, and is invoked from a finally block so
the run leaves behind useful artifacts even when start() fails partway.
"""
import shutil
from pathlib import Path

from robocorp import log

from libraries.audit import AuditLogger
from libraries.classification import classify_file, compute_risk_score
from libraries.detection import detect
from libraries.discovery import discover_files, extract_content
from libraries.email_source import fetch_attachments
from libraries.reporting import write_csv_report, write_json_report


class Process:
    def __init__(self) -> None:
        self.input_dir = Path("input")
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

        self.audit = AuditLogger()
        self.results: list[dict] = []

    # ---------- start ---------------------------------------------------------

    def start(self) -> None:
        """Fetch new email attachments, then detect + classify each file."""
        self.audit.event("start", {"input_dir": str(self.input_dir)})
        self._reset_input_dir()

        try:
            downloaded = fetch_attachments(self.input_dir)
            log.info(f"Downloaded {len(downloaded)} attachment(s) from Gmail")
            self.audit.event("email_fetch_complete", {
                "downloaded_count": len(downloaded),
                "files": [str(f) for f in downloaded],
            })
        except Exception as exc:
            # Don't abort the run — finish() still writes whatever we have.
            # Operators can drop files directly into input/ as a fallback path.
            log.exception(f"Email fetch failed: {exc}")
            self.audit.event("email_fetch_failed", {"error": str(exc)})

        files = discover_files(self.input_dir)
        log.info(f"Discovered {len(files)} files")
        self.audit.event("discovery_complete", {
            "file_count": len(files),
            "files": [str(f) for f in files],
        })

        for f in files:
            self._scan_file(f)

    def _reset_input_dir(self) -> None:
        if self.input_dir.exists():
            shutil.rmtree(self.input_dir)
        self.input_dir.mkdir(parents=True)

    def _scan_file(self, path: Path) -> None:
        log.info(f"Processing {path.name}")
        try:
            content = extract_content(path)
            detections = detect(content)
            classification = classify_file(detections)
            risk_score = compute_risk_score(detections)

            self.results.append({
                "file_path": str(path),
                "file_name": path.name,
                "file_type": path.suffix.lstrip("."),
                "detections": detections,
                "classification": classification,
                "risk_score": risk_score,
            })
            self.audit.event("file_processed", {
                "file": str(path),
                "classification": classification,
                "risk_score": risk_score,
                "detection_counts": {k: len(v) for k, v in detections.items()},
            })
        except Exception as exc:
            log.exception(f"Failed to process {path.name}: {exc}")
            self.audit.event("file_error", {"file": str(path), "error": str(exc)})

    # ---------- finish --------------------------------------------------------

    def finish(self) -> None:
        """Write CSV / JSON / audit reports. Always runs (called from finally)."""
        csv_path = self.output_dir / "report.csv"
        json_path = self.output_dir / "classification_report.json"
        audit_path = self.output_dir / "audit_log.json"

        write_csv_report(self.results, csv_path)
        write_json_report(self.results, json_path)
        self.audit.event("reports_written", {
            "csv": str(csv_path),
            "json": str(json_path),
        })
        self.audit.flush(audit_path)

        log.info(f"Done. Processed {len(self.results)} files.")
        log.info(f"  CSV:   {csv_path}")
        log.info(f"  JSON:  {json_path}")
        log.info(f"  Audit: {audit_path}")

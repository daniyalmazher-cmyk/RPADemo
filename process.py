"""Process orchestrator.

start() does all the discovery + detection + classification work.
finish() writes reports + audit log, and is invoked from a finally block so
the run leaves behind useful artifacts even when start() fails partway.
"""
from pathlib import Path

from robocorp import log

from libraries.audit import AuditLogger
from libraries.classification import classify_file, compute_risk_score
from libraries.detection import detect
from libraries.discovery import discover_files, extract_content
from libraries.reporting import write_csv_report, write_json_report
from libraries.sample_data import generate_all_samples


class Process:
    def __init__(self) -> None:
        self.input_dir = Path("input")
        self.output_dir = Path("output")
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        self.audit = AuditLogger()
        self.results: list[dict] = []

    # ---------- start ---------------------------------------------------------

    def start(self) -> None:
        """Discover files, detect sensitive data, classify, score risk."""
        self.audit.event("start", {"input_dir": str(self.input_dir)})

        if not any(self.input_dir.iterdir()):
            log.info("Input folder empty - bootstrapping sample data")
            generate_all_samples(self.input_dir)
            self.audit.event("sample_data_generated")

        files = discover_files(self.input_dir)
        log.info(f"Discovered {len(files)} files")
        self.audit.event("discovery_complete", {
            "file_count": len(files),
            "files": [str(f) for f in files],
        })

        for f in files:
            self._scan_file(f)

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
        csv_path = self.output_dir / "classification_report.csv"
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

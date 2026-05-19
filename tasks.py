"""Robocorp task entry points for the Sensitive Data Discovery & Classification bot.

Two operating modes:

1. **Folder mode** (`scan_and_classify`) — reads files from ./input/, writes
   reports to ./output/. Useful for local dev and standalone runs.

2. **Work-item mode** (`process_workitems`) — consumes Control Room input work
   items, downloads their attached files, runs the same pipeline, and emits an
   output work item carrying the reports + a summary payload. This is the
   production deployment pattern.

A producer task (`seed_demo_workitem`) and a bootstrap task
(`prepare_sample_data`) are included so the demo is one-click in either mode.
"""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from robocorp import log, workitems
from robocorp.tasks import task

from bot.audit import AuditLogger
from bot.classification import classify_file, compute_risk_score
from bot.detection import detect_sensitive_data
from bot.discovery import discover_files, extract_content
from bot.reporting import write_csv_report, write_json_report
from bot.sample_data import generate_all_samples

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
DEVDATA_BATCH_DIR = Path("devdata/work-items-in/demo-batch")


# ---------- shared scan pipeline ----------------------------------------------

def _scan_files(files: list[Path], audit: AuditLogger) -> list[dict]:
    audit.event("discovery_complete", {
        "file_count": len(files),
        "files": [str(f) for f in files],
    })
    results: list[dict] = []
    for f in files:
        log.info(f"Processing {f.name}")
        try:
            content = extract_content(f)
            detections = detect_sensitive_data(content)
            classification = classify_file(detections)
            risk_score = compute_risk_score(detections)
            results.append({
                "file_path": str(f),
                "file_name": f.name,
                "file_type": f.suffix.lstrip("."),
                "detections": detections,
                "classification": classification,
                "risk_score": risk_score,
            })
            audit.event("file_processed", {
                "file": str(f),
                "classification": classification,
                "risk_score": risk_score,
                "detection_counts": {k: len(v) for k, v in detections.items()},
            })
        except Exception as exc:
            log.exception(f"Failed to process {f.name}: {exc}")
            audit.event("file_error", {"file": str(f), "error": str(exc)})
    return results


def _write_outputs(
    results: list[dict], output_dir: Path, audit: AuditLogger
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "classification_report.csv"
    json_path = output_dir / "classification_report.json"
    audit_path = output_dir / "audit_log.json"
    write_csv_report(results, csv_path)
    write_json_report(results, json_path)
    audit.event("reports_written", {
        "csv": str(csv_path),
        "json": str(json_path),
    })
    audit.flush(audit_path)
    return csv_path, json_path, audit_path


def _summarize(results: list[dict]) -> dict:
    counts = {"Public": 0, "Confidential": 0, "Highly Confidential": 0}
    max_score = 0
    top_files: list[str] = []
    for r in results:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
        if r["risk_score"] > max_score:
            max_score = r["risk_score"]
            top_files = [r["file_name"]]
        elif r["risk_score"] == max_score and max_score > 0:
            top_files.append(r["file_name"])
    return {
        "file_count": len(results),
        "classification_counts": counts,
        "max_risk_score": max_score,
        "highest_risk_files": top_files,
    }


# ---------- task: bootstrap sample data ---------------------------------------

@task
def prepare_sample_data() -> None:
    """Generate demo files under ./input/ and seed a dev work item under ./devdata/."""
    INPUT_DIR.mkdir(exist_ok=True)
    samples = generate_all_samples(INPUT_DIR)
    log.info(f"Generated {len(samples)} sample files in {INPUT_DIR}/")
    for p in samples:
        log.info(f"  - {p.name}")

    # Mirror samples into devdata so the work-item FileAdapter can resolve them
    DEVDATA_BATCH_DIR.mkdir(parents=True, exist_ok=True)
    files_map: dict[str, str] = {}
    for src in samples:
        dst = DEVDATA_BATCH_DIR / src.name
        shutil.copy2(src, dst)
        files_map[src.name] = src.name

    work_items = [{
        "payload": {
            "batch_id": "demo-batch-001",
            "source": "demo-local",
            "requested_by": "compliance@bank.example.com",
            "scan_type": "full",
        },
        "files": files_map,
    }]
    (DEVDATA_BATCH_DIR / "work-items.json").write_text(
        json.dumps(work_items, indent=2), encoding="utf-8"
    )
    log.info(f"Seeded dev work item at {DEVDATA_BATCH_DIR}/work-items.json")


# ---------- task: folder mode -------------------------------------------------

@task
def scan_and_classify() -> None:
    """Scan ./input/, detect sensitive data, classify each file, write DLP-ready reports."""
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    audit = AuditLogger()
    audit.event("scan_started", {"input_dir": str(INPUT_DIR), "mode": "folder"})

    if not any(INPUT_DIR.iterdir()):
        log.info("Input folder empty - generating sample data")
        generate_all_samples(INPUT_DIR)
        audit.event("sample_data_generated", {})

    files = discover_files(INPUT_DIR)
    log.info(f"Discovered {len(files)} files")

    results = _scan_files(files, audit)
    csv_path, json_path, audit_path = _write_outputs(results, OUTPUT_DIR, audit)
    summary = _summarize(results)

    log.info(f"Done. Processed {len(results)} files. Peak risk: {summary['max_risk_score']}")
    log.info(f"  CSV:   {csv_path}")
    log.info(f"  JSON:  {json_path}")
    log.info(f"  Audit: {audit_path}")


# ---------- task: producer (seed an output work item) -------------------------

@task
def seed_demo_workitem() -> None:
    """Producer: create an output work item carrying the sample files.

    In a Control Room process, this output queues as the input for the
    consumer step (`process_workitems`).
    """
    INPUT_DIR.mkdir(exist_ok=True)
    if not any(INPUT_DIR.iterdir()):
        generate_all_samples(INPUT_DIR)

    files = sorted(p for p in INPUT_DIR.iterdir() if p.is_file())
    batch_id = f"demo-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    out = workitems.outputs.create(payload={
        "batch_id": batch_id,
        "source": "demo-seed",
        "requested_by": "demo@local",
        "file_count": len(files),
    })
    for f in files:
        out.add_file(str(f))
    out.save()
    log.info(f"Seeded output work item '{batch_id}' with {len(files)} files")


# ---------- task: consumer (process input work items) -------------------------

@task
def process_workitems() -> None:
    """Consumer: scan files attached to each input work item; emit output work item with reports."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    INPUT_DIR.mkdir(exist_ok=True)

    processed = 0
    for item in workitems.inputs:
        audit = AuditLogger()
        try:
            payload = item.payload or {}
            batch_id = str(payload.get("batch_id") or getattr(item, "id", None) or f"item-{processed}")
            log.info(f"Processing batch '{batch_id}'")
            audit.event("batch_started", {
                "batch_id": batch_id,
                "payload": payload,
                "mode": "workitem",
            })

            # Download attachments into a batch-scoped folder so cwd stays clean
            batch_input = INPUT_DIR / batch_id
            batch_input.mkdir(parents=True, exist_ok=True)
            local_files: list[Path] = []
            for fname in item.files:
                dst = batch_input / fname
                try:
                    item.get_file(fname, str(dst))
                except TypeError:
                    # Older adapters: get_file(name) downloads to cwd; move it.
                    downloaded = Path(str(item.get_file(fname)))
                    if downloaded.resolve() != dst.resolve():
                        shutil.move(str(downloaded), str(dst))
                local_files.append(dst)
            audit.event("files_downloaded", {
                "count": len(local_files),
                "files": [f.name for f in local_files],
            })

            results = _scan_files(local_files, audit)

            batch_output = OUTPUT_DIR / batch_id
            csv_path, json_path, audit_path = _write_outputs(results, batch_output, audit)
            summary = _summarize(results)

            # Emit output work item carrying reports + a summary the next stage can act on
            out = workitems.outputs.create(payload={
                "batch_id": batch_id,
                "input_payload": payload,
                "summary": summary,
                "reports": {
                    "csv": csv_path.name,
                    "json": json_path.name,
                    "audit": audit_path.name,
                },
            })
            out.add_file(str(csv_path))
            out.add_file(str(json_path))
            out.add_file(str(audit_path))
            out.save()

            item.done()
            processed += 1
            log.info(
                f"Batch '{batch_id}' done. "
                f"Files: {summary['file_count']}, peak risk: {summary['max_risk_score']}"
            )
        except Exception as exc:
            log.exception(f"Failed to process work item: {exc}")
            try:
                item.fail(
                    exception_type="APPLICATION",
                    code="PROCESSING_ERROR",
                    message=str(exc),
                )
            except Exception:
                log.exception("Could not mark work item as failed")

    if processed == 0:
        log.warn(
            "No input work items were available. "
            "For local runs, run `prepare_sample_data` first and ensure "
            "RC_WORKITEM_INPUT_PATH points to devdata/work-items-in/demo-batch/work-items.json"
        )
    else:
        log.info(f"Processed {processed} work item(s)")

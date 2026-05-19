# Sensitive Data Discovery & Classification Bot

A Robocorp + RPA Framework bot that scans enterprise files, detects sensitive
financial and personal data, classifies each file by sensitivity, scores risk,
and emits structured reports that downstream DLP / governance systems
(Microsoft Purview, Forcepoint, etc.) can consume.

This repo contains **only the bot** — the Streamlit visualization layer lives
in a separate project and reads the reports written here.

## What it does

```
input/ (CSV, Excel, PDF, TXT)
   │
   ▼
RPA Framework discovery  ──▶  Content extraction (pandas, pdfplumber)
                                       │
                                       ▼
                          Regex-based sensitive data detection
                          (CNIC, IBAN, credit card + Luhn, email,
                           phone, salary indicators)
                                       │
                                       ▼
                  Classification (Public / Confidential / Highly Confidential)
                                       │
                                       ▼
                          Risk score (0–100, weighted)
                                       │
                                       ▼
              output/classification_report.csv
              output/classification_report.json
              output/audit_log.json
```

## Project layout

```
.
├── robot.yaml              # Robocorp tasks + env config
├── conda.yaml              # Python deps for the bot environment
├── tasks.py                # @task entry points
├── bot/
│   ├── discovery.py        # File walking + content extraction
│   ├── detection.py        # Regex patterns + Luhn validation
│   ├── classification.py   # Labels + risk scoring
│   ├── reporting.py        # CSV / JSON report writers
│   ├── audit.py            # Per-run audit logger
│   └── sample_data.py      # Generates fake fintech demo files
├── input/                  # Created at runtime; bot reads from here
└── output/                 # Created at runtime; reports + artifacts
```

## Tasks

The bot exposes four Robocorp tasks (see `robot.yaml`):

| Task                            | Mode       | What it does                                                                    |
|---------------------------------|------------|---------------------------------------------------------------------------------|
| `Prepare Sample Data`           | bootstrap  | Writes demo files into `input/` AND seeds a dev work item under `devdata/`.     |
| `Scan and Classify (folder)`    | folder     | Reads from `input/`, writes reports to `output/`. Simple standalone run.        |
| `Seed Demo Work Item (producer)`| work item  | Producer — creates an output work item carrying the sample files.               |
| `Process Work Items (consumer)` | work item  | Consumer — for each input WI, downloads files, scans, emits an output WI.       |

`Scan and Classify (folder)` auto-generates sample data if `input/` is empty, so
both modes are one-click in Control Room.

## Operating modes

### 1. Folder mode

Drop files into `input/` (or let the bot bootstrap samples). The bot scans the
folder and writes reports to `output/`. Useful for local dev and bots running
against a fileshare.

### 2. Work-item mode (Control Room production pattern)

Files arrive as **attachments on input work items**. The consumer downloads
them, scans them, and emits an **output work item** carrying:
- `classification_report.csv` (file)
- `classification_report.json` (file)
- `audit_log.json` (file)
- `payload`: `{batch_id, summary: {file_count, classification_counts, max_risk_score, highest_risk_files}, reports: {...}}`

Downstream consumers (DLP routing, alerting, governance ingestion) read the
summary payload to make decisions without parsing the reports themselves.

## Run locally (with `rcc`)

```bash
# Bootstrap sample data (writes input/ AND devdata/work-items-in/)
rcc run -t "Prepare Sample Data"

# Folder mode
rcc run -t "Scan and Classify (folder)"

# Work-item mode (rcc auto-loads devdata/env.json)
rcc run -t "Process Work Items (consumer)"
```

Outputs land in `./output/`; output work items land in `./devdata/work-items-out/`.

## Run locally (without rcc, in any Python 3.10+ env)

```bash
pip install robocorp robocorp-tasks robocorp-workitems rpaframework \
            pandas openpyxl pdfplumber reportlab

# Bootstrap
python -m robocorp.tasks run tasks.py -t prepare_sample_data

# Folder mode
python -m robocorp.tasks run tasks.py -t scan_and_classify

# Work-item mode — point the adapter at the seeded dev batch
RC_WORKITEM_INPUT_PATH=devdata/work-items-in/demo-batch/work-items.json \
RC_WORKITEM_OUTPUT_PATH=devdata/work-items-out/work-items.json \
python -m robocorp.tasks run tasks.py -t process_workitems
```

## Deploy to Robocorp Cloud (Control Room)

1. Push this repo to GitHub (or zip it).
2. In Control Room → **Robots** → **New Robot** → link the repo (or upload the zip).
3. Control Room reads `robot.yaml` and registers all four tasks.
4. Pick a deployment pattern:

   **Pattern A — folder mode (simplest demo):**
   - Create a Process running `Scan and Classify (folder)`.
   - The bot auto-bootstraps sample data, so the first run works out of the box.
   - Reports appear as run artifacts.

   **Pattern B — producer/consumer (full Control Room demo):**
   - Create a Process with two steps:
     1. `Seed Demo Work Item (producer)` — creates an input work item with sample files.
     2. `Process Work Items (consumer)` — consumes it, emits an output work item.
   - The output work item is visible in the Work Items view with the reports
     attached and the summary payload, ready for a downstream process.

5. For real input, replace `Seed Demo Work Item` with an actual producer
   (an SFTP poller, a webhook, an inbox watcher, etc.) that creates input
   work items carrying the files to scan.

## Output schema

`classification_report.csv` columns:

```
file_name, file_path, file_type, classification, risk_score,
cnic_count, iban_count, credit_card_count, email_count, phone_count,
salary_indicator
```

`classification_report.json` envelope:

```json
{
  "schema_version": "1.0",
  "record_count": N,
  "records": [
    {
      "file_path": "...",
      "file_name": "...",
      "file_type": "csv|xlsx|pdf|txt",
      "detections": {
        "cnic": [...], "iban": [...], "credit_card": [...],
        "email": [...], "phone": [...], "salary_indicator": [...]
      },
      "classification": "Public|Confidential|Highly Confidential",
      "risk_score": 0-100
    }
  ]
}
```

`audit_log.json` carries a `run_id`, timestamps, and an event stream
(discovery, per-file outcome, errors, report paths).

## Detection rules

| Category        | Pattern / logic                                                          |
|-----------------|--------------------------------------------------------------------------|
| CNIC            | `\d{5}-?\d{7}-?\d{1}` (Pakistani national ID)                            |
| IBAN            | `[A-Z]{2}\d{2}[A-Z0-9]{11,30}`                                           |
| Credit card     | 13–19 digit groups, Luhn-validated                                       |
| Email           | RFC-ish `local@host.tld`                                                 |
| Phone           | Pakistani mobile (`+92 3XX XXXXXXX` / `03XX XXXXXXX`)                    |
| Salary signal   | Keywords: salary, payroll, net/gross pay, annual/monthly income          |

## Classification & risk

- **Highly Confidential** — any CNIC, IBAN, or credit card present.
- **Confidential** — any salary signal, email, or phone (no high-tier hits).
- **Public** — nothing matched.

Risk score: full weight for the first hit in a category, half weight per
additional hit, summed across categories, capped at 100. Weights:
CNIC 30, IBAN 25, credit card 35, salary 20, email/phone 5 each.

"""Fetch DLP-scan attachments from a Gmail inbox via IMAP.

Looks for unread messages whose subject contains "DLP SCAN", downloads each
message's attachments into a per-email folder under `input/`, then marks the
emails as read so they aren't re-processed.

Credentials are read from Robocorp Vault under the secret name
`gmail_credentials` with keys:
    - username : the Gmail address
    - password : a Gmail App Password (NOT the account password)

Set this secret in Control Room → Vault for cloud runs. For local runs, use a
`devdata/vault.json` file plus `RC_VAULT_SECRET_FILE` in env.
"""
from pathlib import Path

from robocorp import log, vault
from RPA.Email.ImapSmtp import ImapSmtp

GMAIL_IMAP_HOST = "imap.gmail.com"
GMAIL_IMAP_PORT = 993

SUBJECT_FILTER = "DLP SCAN"
VAULT_SECRET_NAME = "gmail_credentials"

SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls", ".pdf", ".txt")


def _safe_token(text: str, n: int = 40) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in (text or ""))
    return cleaned[:n] or "msg"


def fetch_attachments(target_dir: Path) -> list[Path]:
    """Connect, find unread DLP-SCAN emails, save supported attachments, mark read.

    Returns the list of saved file paths (filtered to supported extensions).
    Raises if vault credentials are missing or IMAP login fails — callers
    should decide whether to abort the run or continue with existing files.
    """
    creds = vault.get_secret(VAULT_SECRET_NAME)
    username = creds["username"]
    password = creds["password"]

    mail = ImapSmtp(imap_server=GMAIL_IMAP_HOST, imap_port=GMAIL_IMAP_PORT)
    mail.authorize_imap(account=username, password=password)
    log.info(f"Authorized to Gmail IMAP as {username}")

    try:
        messages = mail.list_messages(
            criterion=f'UNSEEN SUBJECT "{SUBJECT_FILTER}"',
            source_folder="INBOX",
        ) or []
        log.info(f"Found {len(messages)} unread '{SUBJECT_FILTER}' messages")

        if not messages:
            return []

        target_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[Path] = []

        # Save attachments per-message so identical filenames across emails
        # don't collide.
        for idx, msg in enumerate(messages):
            uid = str(msg.get("uid") or msg.get("UID") or idx)
            subj = str(msg.get("Subject") or msg.get("subject") or "no-subject")
            msg_dir = target_dir / f"{uid}_{_safe_token(subj)}"
            msg_dir.mkdir(parents=True, exist_ok=True)

            saved = mail.save_attachments(
                messages=[msg],
                target_folder=str(msg_dir),
                overwrite=True,
            ) or []

            for entry in saved:
                if isinstance(entry, dict):
                    raw_path = entry.get("Saved-Path") or entry.get("path")
                else:
                    raw_path = entry
                if not raw_path:
                    continue
                path = Path(str(raw_path))
                if not path.is_file():
                    continue
                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    log.info(f"Skipping unsupported attachment: {path.name}")
                    continue
                downloaded.append(path)

        # Mark read so the next run only sees new emails
        mail.mark_as_read(messages=messages)
        log.info(f"Saved {len(downloaded)} attachment(s); marked {len(messages)} emails as read")

        return downloaded
    finally:
        try:
            mail.close_connection()
        except Exception:
            pass

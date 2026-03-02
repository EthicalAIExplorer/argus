from __future__ import annotations

import imaplib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email import message_from_bytes
from email.message import Message
from email.policy import default
from typing import Any

from .config import ImapConfig, load_imap_config
from .paths import RAW_DIR, STATE_PATH


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    fetched: int
    last_run: str
    date_dir: str | None


def _load_last_run() -> datetime:
    if not STATE_PATH.exists():
        return datetime.now(UTC) - timedelta(days=1)
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    raw = data.get("last_run")
    if not raw:
        return datetime.now(UTC) - timedelta(days=1)
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)


def _save_last_run(ts: datetime) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_run": ts.astimezone(UTC).isoformat().replace("+00:00", "Z")}
    STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _extract_payloads(msg: Message) -> tuple[str, str]:
    text_parts: list[str] = []
    html_parts: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain":
                text_parts.append(_decode_part(part))
            elif ctype == "text/html":
                html_parts.append(_decode_part(part))
    else:
        ctype = msg.get_content_type()
        if ctype == "text/plain":
            text_parts.append(_decode_part(msg))
        elif ctype == "text/html":
            html_parts.append(_decode_part(msg))

    return "\n".join(text_parts).strip(), "\n".join(html_parts).strip()


def _parse_message(raw_bytes: bytes, uid: str, internal_date: str | None) -> dict[str, Any]:
    msg = message_from_bytes(raw_bytes, policy=default)
    subject = msg.get("subject", "")
    sender = msg.get("from", "")
    message_id = msg.get("message-id", "")
    date_hdr = msg.get("date", "")
    received_at = date_hdr
    if not received_at and internal_date:
        received_at = internal_date

    text_body, html_body = _extract_payloads(msg)

    headers = {k: v for (k, v) in msg.items()}
    return {
        "uid": uid,
        "message_id": message_id,
        "received_at": received_at,
        "subject": subject,
        "sender": sender,
        "headers": headers,
        "text_body": text_body,
        "html_body": html_body,
    }


def run(config: ImapConfig | None = None) -> IngestResult:
    cfg = config or load_imap_config()
    last_run = _load_last_run()
    since_date = last_run.strftime("%d-%b-%Y")

    fetched = 0
    today_dir_name: str | None = None

    with imaplib.IMAP4_SSL(cfg.host) as imap:
        imap.login(cfg.user, cfg.password)
        imap.select(cfg.folder)
        status, data = imap.search(None, f"(SINCE {since_date})")
        if status != "OK":
            raise RuntimeError("IMAP search failed")
        uids = data[0].split()

        if uids:
            today_dir = RAW_DIR / datetime.now(UTC).date().isoformat()
            today_dir.mkdir(parents=True, exist_ok=True)
            today_dir_name = today_dir.name

            for uid in uids:
                status, msg_data = imap.fetch(uid, "(RFC822 INTERNALDATE)")
                if status != "OK" or not msg_data:
                    continue
                raw_bytes = msg_data[0][1]
                internal_date = None
                if len(msg_data[0]) > 2 and isinstance(msg_data[0][0], bytes):
                    meta = msg_data[0][0].decode("utf-8", errors="ignore")
                    if "INTERNALDATE" in meta:
                        internal_date = meta
                record = _parse_message(raw_bytes, uid.decode("utf-8", errors="ignore"), internal_date)
                out_path = today_dir / f"{record['uid']}.json"
                out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
                fetched += 1

    now = datetime.now(UTC)
    _save_last_run(now)
    logger.info("ingest complete fetched=%s since=%s", fetched, since_date)
    return IngestResult(fetched=fetched, last_run=now.isoformat(), date_dir=today_dir_name)

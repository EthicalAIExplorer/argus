from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from .paths import CLEAN_DIR, RAW_DIR


logger = logging.getLogger(__name__)
URL_RE = re.compile(r"https?://[^\s\)\]\>\"']+")


@dataclass(frozen=True)
class NormaliseResult:
    processed: int
    skipped: int


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _extract_links(text: str) -> list[str]:
    return list(dict.fromkeys(URL_RE.findall(text)))


def _detect_source(sender: str, subject: str) -> str:
    blob = f"{sender} {subject}".lower()
    if "tldr" in blob:
        return "tldr"
    if "nvidia" in blob:
        return "nvidia"
    if "evolving ai" in blob or "evolvingai" in blob:
        return "evolvingai"
    return "unknown"


def _fingerprint(message_id: str, sender: str, subject: str, clean_text: str) -> str:
    base = "|".join([message_id, sender, subject, clean_text])
    return hashlib.sha256(base.encode("utf-8", errors="replace")).hexdigest()


def _clean_record(raw: dict[str, Any]) -> dict[str, Any]:
    text_body = raw.get("text_body", "") or ""
    html_body = raw.get("html_body", "") or ""
    clean_text = text_body.strip()
    if not clean_text and html_body:
        clean_text = _strip_html(html_body)

    links = _extract_links(text_body + "\n" + html_body)

    subject = raw.get("subject", "")
    sender = raw.get("sender", "")
    message_id = raw.get("message_id", "")

    return {
        "source": _detect_source(sender, subject),
        "message_id": message_id,
        "received_at": raw.get("received_at", ""),
        "subject": subject,
        "sender": sender,
        "clean_text": clean_text,
        "links": links,
        "fingerprint": _fingerprint(message_id, sender, subject, clean_text),
    }


def iter_clean_records(date: str) -> list[dict[str, Any]]:
    path = CLEAN_DIR / date
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for file in sorted(path.glob("*.json")):
        records.append(json.loads(file.read_text(encoding="utf-8")))
    return records


def _process_dir(date_dir: Path) -> tuple[int, int]:
    processed = 0
    skipped = 0
    out_dir = CLEAN_DIR / date_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    for raw_file in sorted(date_dir.glob("*.json")):
        out_file = out_dir / raw_file.name
        if out_file.exists() and out_file.stat().st_mtime >= raw_file.stat().st_mtime:
            skipped += 1
            continue
        raw = json.loads(raw_file.read_text(encoding="utf-8"))
        clean = _clean_record(raw)
        out_file.write_text(json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8")
        processed += 1
    return processed, skipped


def run() -> NormaliseResult:
    if not RAW_DIR.exists():
        return NormaliseResult(processed=0, skipped=0)

    processed = 0
    skipped = 0
    for date_dir in sorted(p for p in RAW_DIR.iterdir() if p.is_dir()):
        dir_processed, dir_skipped = _process_dir(date_dir)
        processed += dir_processed
        skipped += dir_skipped

    logger.info("normalise complete processed=%s skipped=%s", processed, skipped)
    return NormaliseResult(processed=processed, skipped=skipped)

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .paths import CLEAN_DIR, DIGEST_DIR


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DigestResult:
    date: str
    item_count: int
    output_path: str


def _load_by_date(date: str) -> list[dict[str, Any]]:
    path = CLEAN_DIR / date
    if not path.exists():
        return []
    records = []
    for file in sorted(path.glob("*.json")):
        records.append(json.loads(file.read_text(encoding="utf-8")))
    return records


def digest_path_for_date(date: str) -> Path:
    return DIGEST_DIR / f"{date}.md"


def _bundle_for_llm(records: list[dict[str, Any]], date: str) -> dict[str, Any]:
    return {
        "date": date,
        "count": len(records),
        "items": [
            {
                "subject": r.get("subject", ""),
                "sender": r.get("sender", ""),
                "source": r.get("source", "unknown"),
                "text": r.get("clean_text", ""),
                "links": r.get("links", []),
            }
            for r in records
        ],
    }


def build_bundle_for_date(date: str) -> dict[str, Any]:
    return _bundle_for_llm(_load_by_date(date), date)


def _source_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(r.get("source", "unknown") for r in records)
    return dict(sorted(counts.items()))


def run(date: str | None = None, timezone: ZoneInfo | None = None) -> DigestResult:
    tz = timezone or ZoneInfo("UTC")
    digest_date = date or datetime.now(tz).date().isoformat()
    records = _load_by_date(digest_date)
    bundle = _bundle_for_llm(records, digest_date)

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    out_path = digest_path_for_date(digest_date)

    lines: list[str] = []
    lines.append(f"# Argus Digest - {digest_date}")
    lines.append("")
    lines.append(f"Generated at: {datetime.now(tz).isoformat()}")
    lines.append(f"Total items: {bundle['count']}")
    lines.append("")
    lines.append("## Source Counts")
    if records:
        for source, count in _source_counts(records).items():
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Headlines")
    if not records:
        lines.append("- No new items today.")
    else:
        for rec in records:
            subject = rec.get("subject", "(no subject)").strip() or "(no subject)"
            sender = rec.get("sender", "(unknown sender)").strip() or "(unknown sender)"
            lines.append(f"- {subject} - {sender}")
    lines.append("")
    lines.append("## Summary (ChatGPT via MCP)")
    lines.append("- Use the `argus_get_bundle` MCP tool with this date for narrative synthesis in ChatGPT.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("digest complete date=%s items=%s path=%s", digest_date, len(records), out_path)
    return DigestResult(date=digest_date, item_count=len(records), output_path=str(out_path))

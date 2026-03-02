from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CLEAN_DIR = Path("clean")
DIGEST_DIR = Path("digests")


def _load_today() -> list[dict[str, Any]]:
    today = datetime.now(UTC).date().isoformat()
    path = CLEAN_DIR / today
    if not path.exists():
        return []
    records = []
    for file in sorted(path.glob("*.json")):
        records.append(json.loads(file.read_text(encoding="utf-8")))
    return records


def _bundle_for_llm(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "date": datetime.now(UTC).date().isoformat(),
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


def run() -> None:
    records = _load_today()
    bundle = _bundle_for_llm(records)

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(UTC).date().isoformat()
    out_path = DIGEST_DIR / f"{today}.md"

    lines: list[str] = []
    lines.append(f"# Argus Digest — {today}")
    lines.append("")
    lines.append(f"Total items: {bundle['count']}")
    lines.append("")
    lines.append("## Headlines")
    if not records:
        lines.append("- No new items today.")
    else:
        for rec in records:
            subject = rec.get("subject", "(no subject)").strip() or "(no subject)"
            sender = rec.get("sender", "(unknown sender)").strip() or "(unknown sender)"
            lines.append(f"- {subject} — {sender}")
    lines.append("")
    lines.append("## Summary (placeholder)")
    lines.append("- LLM summary generation stubbed. Use bundle in code to call your model.")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .digest import digest_path_for_date
from .paths import CLEAN_DIR, RAW_DIR, STATE_PATH


@dataclass(frozen=True)
class PipelineStatus:
    date: str
    last_run: str | None
    raw_count: int
    clean_count: int
    digest_exists: bool
    digest_path: str


def _load_last_run() -> str | None:
    if not STATE_PATH.exists():
        return None
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return data.get("last_run")


def _count_json_files(path: Path) -> int:
    if not path.exists():
        return 0
    return len(list(path.glob("*.json")))


def get_pipeline_status(date: str | None = None, timezone: ZoneInfo | None = None) -> PipelineStatus:
    tz = timezone or ZoneInfo("UTC")
    target_date = date or datetime.now(tz).date().isoformat()
    raw_count = _count_json_files(RAW_DIR / target_date)
    clean_count = _count_json_files(CLEAN_DIR / target_date)
    digest_path = digest_path_for_date(target_date)
    return PipelineStatus(
        date=target_date,
        last_run=_load_last_run(),
        raw_count=raw_count,
        clean_count=clean_count,
        digest_exists=digest_path.exists(),
        digest_path=str(digest_path),
    )

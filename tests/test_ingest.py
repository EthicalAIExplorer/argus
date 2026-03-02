from __future__ import annotations

from datetime import UTC, datetime as real_datetime
from zoneinfo import ZoneInfo

from argus import ingest as ingest_mod


class _FixedDateTime:
    @classmethod
    def now(cls, tz):
        base = real_datetime(2026, 3, 2, 0, 30, tzinfo=UTC)
        return base.astimezone(tz)


def test_today_dir_date_uses_runtime_timezone(monkeypatch) -> None:
    monkeypatch.setattr(ingest_mod, "datetime", _FixedDateTime)
    assert ingest_mod._today_dir_date(ZoneInfo("UTC")) == "2026-03-02"
    assert ingest_mod._today_dir_date(ZoneInfo("America/Los_Angeles")) == "2026-03-01"

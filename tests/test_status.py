from __future__ import annotations

import json

from argus.status import get_pipeline_status


def test_status_counts_and_digest_presence(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "raw/2026-03-02").mkdir(parents=True)
    (tmp_path / "clean/2026-03-02").mkdir(parents=True)
    (tmp_path / "digests").mkdir()
    (tmp_path / "state").mkdir()

    (tmp_path / "raw/2026-03-02/1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "clean/2026-03-02/1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "digests/2026-03-02.md").write_text("# test", encoding="utf-8")
    (tmp_path / "state/last_run.json").write_text(json.dumps({"last_run": "2026-03-02T06:30:00Z"}), encoding="utf-8")

    status = get_pipeline_status(date="2026-03-02")
    assert status.raw_count == 1
    assert status.clean_count == 1
    assert status.digest_exists is True
    assert status.last_run == "2026-03-02T06:30:00Z"

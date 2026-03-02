from __future__ import annotations

import pytest

from argus.config import ConfigError, parse_recipients


def test_parse_recipients_splits_and_trims() -> None:
    parsed = parse_recipients("a@example.com, b@example.com ,c@example.com")
    assert parsed == ["a@example.com", "b@example.com", "c@example.com"]


def test_parse_recipients_rejects_empty() -> None:
    with pytest.raises(ConfigError):
        parse_recipients("  ,   ")

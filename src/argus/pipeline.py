from __future__ import annotations

import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from . import digest as digest_mod
from . import ingest as ingest_mod
from . import normalise as normalise_mod
from .mailer import EmailResult, send_digest_email


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DailyRunResult:
    fetched: int
    normalized: int
    digest_date: str
    digest_path: str
    item_count: int
    email: EmailResult | None


def run_daily(timezone: ZoneInfo, send_email: bool = True) -> DailyRunResult:
    ingest_result = ingest_mod.run(timezone=timezone)
    normalise_result = normalise_mod.run()
    digest_result = digest_mod.run(timezone=timezone)

    email_result: EmailResult | None = None
    if send_email:
        email_result = send_digest_email(
            digest_path=digest_mod.digest_path_for_date(digest_result.date),
            digest_date=digest_result.date,
            item_count=digest_result.item_count,
            timezone=timezone,
        )

    logger.info(
        "daily run complete fetched=%s normalized=%s digest=%s sent_email=%s",
        ingest_result.fetched,
        normalise_result.processed,
        digest_result.output_path,
        bool(email_result),
    )
    return DailyRunResult(
        fetched=ingest_result.fetched,
        normalized=normalise_result.processed,
        digest_date=digest_result.date,
        digest_path=digest_result.output_path,
        item_count=digest_result.item_count,
        email=email_result,
    )

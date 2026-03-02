from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import SmtpConfig, load_digest_recipients, load_smtp_config


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailResult:
    sent_to: list[str]
    subject: str


def send_digest_email(
    digest_path: Path,
    digest_date: str,
    item_count: int,
    timezone: ZoneInfo,
    smtp_config: SmtpConfig | None = None,
    recipients: list[str] | None = None,
) -> EmailResult:
    if not digest_path.exists():
        raise FileNotFoundError(f"Digest file not found: {digest_path}")

    cfg = smtp_config or load_smtp_config()
    to_list = recipients or load_digest_recipients()

    digest_text = digest_path.read_text(encoding="utf-8")
    subject = f"Argus Digest {digest_date} ({item_count} items)"

    msg = EmailMessage()
    msg["From"] = cfg.sender
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject
    msg.set_content(
        "\n".join(
            [
                f"Argus digest for {digest_date}",
                f"Generated at: {datetime.now(timezone).isoformat()}",
                f"Item count: {item_count}",
                "",
                digest_text,
            ]
        )
    )

    if cfg.use_ssl:
        with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=30) as smtp:
            smtp.login(cfg.user, cfg.password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(cfg.host, cfg.port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(cfg.user, cfg.password)
            smtp.send_message(msg)

    logger.info("digest email sent recipients=%s subject=%s", len(to_list), subject)
    return EmailResult(sent_to=to_list, subject=subject)

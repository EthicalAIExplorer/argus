from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImapConfig:
    host: str
    user: str
    password: str
    folder: str = "INBOX"


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    sender: str
    use_ssl: bool


@dataclass(frozen=True)
class RuntimeConfig:
    timezone: ZoneInfo


@dataclass(frozen=True)
class McpConfig:
    auth_token: str


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(f"Missing required env var: {name}")
    return value


def _optional(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip() or default


def _optional_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"Invalid boolean value for {name}: {value}")


def parse_recipients(raw: str) -> list[str]:
    recipients = [item.strip() for item in raw.split(",") if item.strip()]
    if not recipients:
        raise ConfigError("ARGUS_DIGEST_RECIPIENTS must include at least one email address")
    return recipients


def load_runtime_config() -> RuntimeConfig:
    timezone_name = _optional("ARGUS_TIMEZONE", "UTC")
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"Invalid ARGUS_TIMEZONE value: {timezone_name}") from exc
    return RuntimeConfig(timezone=timezone)


def load_imap_config() -> ImapConfig:
    return ImapConfig(
        host=_required("ARGUS_IMAP_HOST"),
        user=_required("ARGUS_IMAP_USER"),
        password=_required("ARGUS_IMAP_PASSWORD"),
        folder=_optional("ARGUS_IMAP_FOLDER", "INBOX"),
    )


def load_smtp_config() -> SmtpConfig:
    port = int(_optional("ARGUS_SMTP_PORT", "587"))
    use_ssl = _optional_bool("ARGUS_SMTP_USE_SSL", default=(port == 465))
    return SmtpConfig(
        host=_required("ARGUS_SMTP_HOST"),
        port=port,
        user=_required("ARGUS_SMTP_USER"),
        password=_required("ARGUS_SMTP_PASSWORD"),
        sender=_required("ARGUS_SMTP_FROM"),
        use_ssl=use_ssl,
    )


def load_digest_recipients() -> list[str]:
    return parse_recipients(_required("ARGUS_DIGEST_RECIPIENTS"))


def load_mcp_config() -> McpConfig:
    return McpConfig(auth_token=_required("ARGUS_AUTH_TOKEN"))

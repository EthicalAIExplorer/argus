# Argus

Argus is a file-based intelligence distillation pipeline for newsletter ingestion and daily synthesis.

It supports:
- Daily IMAP ingest from a dedicated mailbox.
- Raw-to-clean normalization.
- Daily Markdown digest generation.
- SMTP digest email delivery to configurable recipients.
- Local MCP server for ChatGPT UI connector access via private tunnel.

## Repository Layout

```text
argus/
  src/argus/
    cli.py
    config.py
    digest.py
    ingest.py
    logging_config.py
    mailer.py
    mcp_server.py
    normalise.py
    paths.py
    pipeline.py
    status.py
  tests/
  state/
  raw/
  clean/
  digests/
  .env.example
  pyproject.toml
```

## Requirements

- Python 3.12+
- Gmail account with IMAP enabled and App Passwords for IMAP/SMTP

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

## Configuration

All runtime configuration is env-driven. Copy `.env.example` and fill values.

Important variables:
- `ARGUS_TIMEZONE` (default `UTC`)
- `ARGUS_IMAP_*` for ingest
- `ARGUS_SMTP_*` for digest sending
- `ARGUS_DIGEST_RECIPIENTS` as comma-separated emails
- `ARGUS_AUTH_TOKEN` for MCP auth

## CLI Commands

```bash
argus ingest
argus normalise
argus digest
argus send-digest
argus status
argus run-daily
argus run-daily --skip-email
argus serve-mcp --host 127.0.0.1 --port 8765
```

`run-daily` executes:
1. Ingest new emails.
2. Normalize raw records.
3. Build digest for today.
4. Send digest email.

## Daily Cron (06:30 Local)

```cron
30 6 * * * cd /home/peter/argus && /home/peter/argus/.venv/bin/argus run-daily >> /home/peter/argus/state/cron.log 2>&1
```

## MCP Server for ChatGPT Connector

Run local MCP server:

```bash
argus serve-mcp --host 127.0.0.1 --port 8765
```

Expose through your existing private tunnel workflow (same operating model as `jobtracker-mcp`).

Auth header required for MCP endpoints:

```text
Authorization: Bearer <ARGUS_AUTH_TOKEN>
```

Implemented MCP tools:
- `argus_pipeline_status`
- `argus_list_items`
- `argus_get_digest`
- `argus_get_bundle`

## Testing

```bash
pytest
```

## Operational Notes

- Runtime artifacts are written to `raw/`, `clean/`, `digests/`, and `state/`.
- `state/last_run.json` stores the last successful ingest timestamp.
- Digest markdown files are in `digests/YYYY-MM-DD.md`.

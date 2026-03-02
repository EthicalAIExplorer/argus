# Argus

Argus is a minimal, file-based intelligence distillation pipeline for newsletter ingestion and daily synthesis. It ingests emails from a dedicated Gmail account, normalises them into machine-readable JSON, and produces a daily Markdown digest.

## Structure

```
argus/
  src/argus/
    __init__.py
    cli.py
    ingest.py
    normalise.py
    digest.py
  state/
    last_run.json
  raw/
  clean/
  digests/
  pyproject.toml
  README.md
```

## Setup

- Python 3.12+
- Create a virtual environment and install dependencies:

```
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Set IMAP credentials as environment variables:

- `ARGUS_IMAP_HOST` (e.g. `imap.gmail.com`)
- `ARGUS_IMAP_USER`
- `ARGUS_IMAP_PASSWORD`
- `ARGUS_IMAP_FOLDER` (optional, default: `INBOX`)

For Gmail, you may need an App Password and IMAP enabled on the account.

## Daily workflow

1) Ingest new emails since the last run:

```
argus ingest
```

2) Normalise raw JSON into cleaned JSON:

```
argus normalise
```

3) Generate today's digest:

```
argus digest
```

## Notes

- `state/last_run.json` stores the timestamp of the last successful ingest.
- Raw emails are stored in `raw/YYYY-MM-DD/`.
- Cleaned records are stored in `clean/YYYY-MM-DD/`.
- Digests are stored in `digests/YYYY-MM-DD.md`.
- LLM summarisation is stubbed; `digest.py` builds a structured bundle ready for an API call.

## Cleaned JSON schema

```json
{
  "source": "tldr|nvidia|evolvingai|unknown",
  "message_id": "...",
  "received_at": "ISO8601",
  "subject": "...",
  "sender": "...",
  "clean_text": "...",
  "links": ["..."],
  "fingerprint": "sha256..."
}
```

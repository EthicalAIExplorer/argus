from __future__ import annotations

import json

import typer
import uvicorn

from . import digest as digest_mod
from . import ingest as ingest_mod
from . import normalise as normalise_mod
from .config import load_runtime_config
from .digest import digest_path_for_date
from .logging_config import configure_logging
from .mailer import send_digest_email
from .mcp_server import create_app
from .pipeline import run_daily
from .status import get_pipeline_status

app = typer.Typer(add_completion=False, help="Argus: intelligence distillation pipeline.")


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging.")) -> None:
    configure_logging(verbose=verbose)


@app.command()
def ingest() -> None:
    """Fetch new emails and store raw JSON."""
    result = ingest_mod.run()
    typer.echo(json.dumps({"fetched": result.fetched, "last_run": result.last_run, "date_dir": result.date_dir}))


@app.command()
def normalise() -> None:
    """Normalise raw JSON into cleaned JSON."""
    result = normalise_mod.run()
    typer.echo(json.dumps({"processed": result.processed, "skipped": result.skipped}))


@app.command()
def digest(date: str | None = typer.Option(None, help="Digest date in YYYY-MM-DD format.")) -> None:
    """Generate a daily digest Markdown file."""
    runtime = load_runtime_config()
    result = digest_mod.run(date=date, timezone=runtime.timezone)
    typer.echo(json.dumps({"date": result.date, "item_count": result.item_count, "path": result.output_path}))


@app.command("send-digest")
def send_digest(date: str | None = typer.Option(None, help="Digest date in YYYY-MM-DD format.")) -> None:
    """Send digest by email to configured recipients."""
    runtime = load_runtime_config()
    target_date = date
    if target_date is None:
        target_date = digest_mod.run(timezone=runtime.timezone).date
    digest_path = digest_path_for_date(target_date)
    item_count = len(digest_mod.build_bundle_for_date(target_date)["items"])
    result = send_digest_email(
        digest_path=digest_path,
        digest_date=target_date,
        item_count=item_count,
        timezone=runtime.timezone,
    )
    typer.echo(json.dumps({"subject": result.subject, "sent_to": result.sent_to}))


@app.command("run-daily")
def run_daily_cmd(skip_email: bool = typer.Option(False, help="Skip sending digest email.")) -> None:
    """Run ingest, normalise, digest, and email delivery in one command."""
    runtime = load_runtime_config()
    result = run_daily(timezone=runtime.timezone, send_email=not skip_email)
    payload = {
        "fetched": result.fetched,
        "normalized": result.normalized,
        "digest_date": result.digest_date,
        "digest_path": result.digest_path,
        "item_count": result.item_count,
        "email_sent": bool(result.email),
    }
    if result.email:
        payload["recipients"] = result.email.sent_to
    typer.echo(json.dumps(payload))


@app.command()
def status(date: str | None = typer.Option(None, help="Status date in YYYY-MM-DD format.")) -> None:
    """Show current pipeline status and artifact presence."""
    runtime = load_runtime_config()
    status_obj = get_pipeline_status(date=date, timezone=runtime.timezone)
    typer.echo(
        json.dumps(
            {
                "date": status_obj.date,
                "last_run": status_obj.last_run,
                "raw_count": status_obj.raw_count,
                "clean_count": status_obj.clean_count,
                "digest_exists": status_obj.digest_exists,
                "digest_path": status_obj.digest_path,
            }
        )
    )


@app.command("serve-mcp")
def serve_mcp(
    host: str = typer.Option("127.0.0.1", help="Host to bind MCP server."),
    port: int = typer.Option(8765, help="Port to bind MCP server."),
) -> None:
    """Run local MCP server for ChatGPT connector access."""
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    app()

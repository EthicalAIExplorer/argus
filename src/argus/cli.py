from __future__ import annotations

import typer

from . import digest as digest_mod
from . import ingest as ingest_mod
from . import normalise as normalise_mod

app = typer.Typer(add_completion=False, help="Argus: intelligence distillation pipeline.")


@app.command()
def ingest() -> None:
    """Fetch new emails and store raw JSON."""
    ingest_mod.run()


@app.command()
def normalise() -> None:
    """Normalise raw JSON into cleaned JSON."""
    normalise_mod.run()


@app.command()
def digest() -> None:
    """Generate a daily digest Markdown file."""
    digest_mod.run()


if __name__ == "__main__":
    app()

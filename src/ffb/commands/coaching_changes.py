"""ffb coaching-changes, UDK Coaching Changes article."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_COACHING_CHANGES_PAGE
from ..display.tables import prose_panel, console
from ._scrape import extract_article_paragraphs


def coaching_changes_command(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Coaching Changes: fantasy implications of offseason coaching moves. Requires login.

    \b
    The page is a narrative article; this prints the readable analysis. Use
    --json to get the paragraphs as a list.

    \b
    EXAMPLES:
      ffb coaching-changes             # read the analysis
      ffb coaching-changes --json      # paragraphs as JSON
    """
    paragraphs = extract_article_paragraphs(UDK_COACHING_CHANGES_PAGE)
    if not paragraphs:
        typer.echo("No coaching-changes content found.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(paragraphs))
    else:
        prose_panel(paragraphs, title="UDK Coaching Changes")

"""ffb dynasty rookie-overview, Rookie Class Overview narrative."""
from __future__ import annotations

import json

import typer

from ...api.dynasty_scrape import extract_headings_with_content, slice_main_content
from ...api.endpoints import DYNASTY_ROOKIE_OVERVIEW_PAGE
from ...display.tables import narrative_panels, console
from ._common import fetch_dynasty_page


def dynasty_rookie_overview_command(
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Rookie Class Overview: the dynasty outlook on the incoming class. Requires UDK+.

    \b
    A narrative breakdown of the rookie class by position. Use --json for the
    raw heading/body sections.

    \b
    EXAMPLES:
      ffb dynasty rookie-overview
      ffb dynasty rookie-overview --json
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_ROOKIE_OVERVIEW_PAGE))
    sections = [s for s in extract_headings_with_content(html, (2, 3)) if len(s["body"]) > 60]

    if not sections:
        typer.echo("No rookie-overview content found.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(sections))
    else:
        narrative_panels(sections, title="2026 Dynasty Rookie Class Overview")

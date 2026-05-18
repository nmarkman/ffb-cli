"""ffb dynasty tips , Baller dynasty tips (short-form advice)."""
from __future__ import annotations

import json

import typer

from ...api.dynasty_scrape import extract_headings_with_content, slice_main_content
from ...api.endpoints import DYNASTY_TIPS_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_tips_command(
    limit: int = typer.Option(15, "-n", "--limit", help="Max tips"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Baller Dynasty Tips, the short-form advice section.

    \b
    EXAMPLES:
      ffb dynasty tips           # first 15 tips
      ffb dynasty tips -n 5      # just five
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_TIPS_PAGE))
    items = extract_headings_with_content(html, (2, 3, 4))
    items = [i for i in items if i["body"]][:limit]

    if output_json:
        console.print_json(json.dumps(items, default=str))
    elif items:
        list_cards(items, title="Dynasty Tips",
                   fields=[("heading", "Tip"), ("body", "Detail")])
    else:
        typer.echo("No dynasty tips extracted.")

"""ffb dynasty lifecycles , dynasty lifecycles by position."""
from __future__ import annotations

import json

import typer

from ...api.dynasty_scrape import extract_post_grid, extract_headings_with_content, slice_main_content
from ...api.endpoints import DYNASTY_LIFECYCLES_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_lifecycles_command(
    limit: int = typer.Option(10, "-n", "--limit", help="Max articles"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Dynasty lifecycle articles by position.

    \b
    The lifecycles page is a curated article hub. We return the article cards
    with title, excerpt, and link.
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_LIFECYCLES_PAGE))
    cards = extract_post_grid(html)
    if not cards:
        cards = [{"title": h["heading"], "excerpt": h["body"][:300]}
                 for h in extract_headings_with_content(html, (2, 3))]
    cards = cards[:limit]

    if output_json:
        console.print_json(json.dumps(cards, default=str))
    elif cards:
        list_cards(cards, title="Dynasty Lifecycles",
                   fields=[("title", "Article"), ("excerpt", "Excerpt"), ("link", "URL")])
    else:
        typer.echo("No lifecycle articles extracted.")

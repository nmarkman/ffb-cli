"""ffb dynasty trade-targets , weekly dynasty trade targets list."""
from __future__ import annotations

import json

import typer

from ...api.dynasty_scrape import (
    extract_headings_with_content,
    extract_player_cards,
    slice_main_content,
)
from ...api.endpoints import DYNASTY_TRADE_TARGETS_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_trade_targets_command(
    limit: int = typer.Option(25, "-n", "--limit", help="Max items"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Dynasty trade targets curated by the Fantasy Footballers.

    \b
    Returns the current week's "buy / sell / hold" list with each player's
    reasoning blurb.
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_TRADE_TARGETS_PAGE))
    cards = extract_player_cards(html)
    if not cards:
        # Fall back to heading-based extraction if card classes have shifted.
        cards = [{"name": h["heading"], "blurb": h["body"][:400]} for h in extract_headings_with_content(html, (2, 3, 4))]

    items = cards[:limit]
    if output_json:
        console.print_json(json.dumps(items, default=str))
    else:
        list_cards(items, title="Dynasty Trade Targets",
                   fields=[("name", "Player"), ("position", "Pos"), ("team", "Team"), ("blurb", "Blurb")])

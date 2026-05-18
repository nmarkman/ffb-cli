"""ffb dynasty injuries , injury tracker."""
from __future__ import annotations

import json

import typer

from ...api.dynasty_scrape import extract_player_cards, extract_headings_with_content, slice_main_content
from ...api.endpoints import DYNASTY_INJURIES_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_injuries_command(
    position: str = typer.Argument(None, help="Position filter (QB, RB, WR, TE)"),
    limit: int = typer.Option(30, "-n", "--limit", help="Max items"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Dynasty-impact injury tracker.

    \b
    EXAMPLES:
      ffb dynasty injuries
      ffb dynasty injuries RB
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_INJURIES_PAGE))
    cards = extract_player_cards(html)
    if not cards:
        cards = [{"name": h["heading"], "blurb": h["body"][:400]}
                 for h in extract_headings_with_content(html, (2, 3, 4))]

    if position:
        position = position.upper()
        cards = [c for c in cards if (c.get("position", "") or "").upper() == position]

    cards = cards[:limit]
    if output_json:
        console.print_json(json.dumps(cards, default=str))
    elif cards:
        list_cards(cards, title="Dynasty Injury Tracker",
                   fields=[("name", "Player"), ("position", "Pos"),
                           ("team", "Team"), ("blurb", "Status / Outlook")])
    else:
        typer.echo("No injuries matched.")

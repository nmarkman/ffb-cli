"""ffb dynasty free-agents , free-agent tracker."""
from __future__ import annotations

import json

import typer

from ...api.dynasty_scrape import extract_player_cards, extract_headings_with_content, slice_main_content
from ...api.endpoints import DYNASTY_FREE_AGENTS_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_free_agents_command(
    team: str = typer.Argument(None, help="Team code to filter signings to (KC, BUF, etc.)"),
    limit: int = typer.Option(30, "-n", "--limit", help="Max items"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Free-agent signings and dynasty impact analysis.

    \b
    EXAMPLES:
      ffb dynasty free-agents          # all recent signings
      ffb dynasty free-agents KC       # signings to/from KC
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_FREE_AGENTS_PAGE))
    cards = extract_player_cards(html)

    # Page is grouped by team headings. If we got cards with team info, filter
    # by team flag; otherwise fall back to heading-based parse.
    if not cards:
        headings = extract_headings_with_content(html, (2, 3, 4))
        cards = [{"name": h["heading"], "blurb": h["body"][:400]} for h in headings]

    if team:
        team = team.upper()
        cards = [c for c in cards if team in (c.get("team", "") or "").upper() or
                 team in (c.get("blurb", "") or "").upper()]

    cards = cards[:limit]
    if output_json:
        console.print_json(json.dumps(cards, default=str))
    elif cards:
        list_cards(cards, title="Dynasty Free Agent Tracker",
                   fields=[("name", "Player"), ("position", "Pos"),
                           ("team", "Team"), ("blurb", "Dynasty Impact")])
    else:
        typer.echo("No free-agent entries matched.")

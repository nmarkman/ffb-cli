"""ffb dynasty team-opportunity , depth-chart opportunity scores by team."""
from __future__ import annotations

import json
import re

import typer

from ...api.dynasty_scrape import strip_html_tags, slice_main_content
from ...api.endpoints import DYNASTY_TEAM_OPPORTUNITY_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_team_opportunity_command(
    team: str = typer.Argument(None, help="3-letter team code to filter (KC, BUF, etc.)"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Team opportunity scores: vacated targets, snaps, and touchdown opportunity.

    \b
    EXAMPLES:
      ffb dynasty team-opportunity            # all 32 teams
      ffb dynasty team-opportunity KC         # Kansas City only
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_TEAM_OPPORTUNITY_PAGE))

    # Each team block: <div class="ffb-dynasty--opp--team" data-team="KC">
    teams = []
    for m in re.finditer(
        r'<div[^>]*class="[^"]*\bffb-dynasty--opp--team\b[^"]*"[^>]*?(?:data-team="([A-Z]{2,3})"[^>]*)?>(.*?)(?=<div[^>]*class="[^"]*\bffb-dynasty--opp--team\b|<footer\b|$)',
        html, flags=re.S | re.I,
    ):
        code = (m.group(1) or "").upper()
        block = m.group(2)
        # Find the team header inside the block if data-team wasn't captured
        if not code:
            h = re.search(r'<h[23][^>]*>(.+?)</h[23]>', block, flags=re.S)
            if h:
                code = strip_html_tags(h.group(1))[:6]
        summary_match = re.search(
            r'<div[^>]*class="[^"]*\bffb-dynasty--opp--summary\b[^"]*"[^>]*>(.*?)</div>',
            block, flags=re.S | re.I,
        )
        summary = strip_html_tags(summary_match.group(1)) if summary_match else ""
        vacated_match = re.search(
            r'<div[^>]*class="[^"]*\bffb-dynasty--opp--vacated\b[^"]*"[^>]*>(.*?)</div>',
            block, flags=re.S | re.I,
        )
        vacated = strip_html_tags(vacated_match.group(1)) if vacated_match else ""
        teams.append({"team": code, "summary": summary[:300], "vacated": vacated[:300]})

    if team:
        teams = [t for t in teams if t.get("team", "").upper() == team.upper()]

    if output_json:
        console.print_json(json.dumps(teams, default=str))
    elif teams:
        list_cards(teams, title="Dynasty Team Opportunity",
                   fields=[("team", "Team"), ("summary", "Summary"), ("vacated", "Vacated")])
    else:
        typer.echo("No team-opportunity data extracted.")

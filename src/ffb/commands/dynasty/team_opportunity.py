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

    # Each team block opens with
    #   <div class="ffb-dynasty--opp--team" data-team-name="..." data-qb="N" ...>
    # The 3-letter code lives in the team logo URL: team-nobg/<CODE>.png.
    teams = []
    block_starts = [
        m.start()
        for m in re.finditer(
            r'<div[^>]*class="[^"]*\bffb-dynasty--opp--team\b[^"]*"[^>]*>',
            html, flags=re.I,
        )
    ]
    block_starts.append(len(html))

    for i in range(len(block_starts) - 1):
        block = html[block_starts[i]:block_starts[i + 1]]

        name_m = re.search(r'data-team-name="([^"]+)"', block, flags=re.I)
        code_m = re.search(r'team-nobg/([A-Z]{2,4})\.', block, flags=re.I)
        depth_m = re.findall(r'\bdata-(qb|rb|wr|te)="(\d+)"', block, flags=re.I)
        depth = {k.upper(): int(v) for k, v in depth_m}

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

        teams.append({
            "team": (code_m.group(1).upper() if code_m else ""),
            "team_name": (name_m.group(1) if name_m else ""),
            "qb_rank": depth.get("QB"),
            "rb_rank": depth.get("RB"),
            "wr_rank": depth.get("WR"),
            "te_rank": depth.get("TE"),
            "summary": summary[:300],
            "vacated": vacated[:300],
        })

    if team:
        q = team.upper()
        teams = [
            t for t in teams
            if t.get("team", "").upper() == q
            or q in t.get("team_name", "").upper()
        ]

    if output_json:
        console.print_json(json.dumps(teams, default=str))
    elif teams:
        list_cards(teams, title="Dynasty Team Opportunity",
                   fields=[("team", "Team"), ("summary", "Summary"), ("vacated", "Vacated")])
    else:
        typer.echo("No team-opportunity data extracted.")

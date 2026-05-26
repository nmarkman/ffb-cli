"""ffb dynasty scouting , rookie scouting reports."""
from __future__ import annotations

import json
import re

import typer
from thefuzz import fuzz

from ...api.dynasty_scrape import strip_html_tags, slice_main_content
from ...api.endpoints import DYNASTY_SCOUTING_REPORTS_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import dynasty_player_card, list_cards


def _parse_reports(html: str) -> list[dict]:
    reports = []
    for m in re.finditer(
        r'<div[^>]*class="[^"]*\bffb-dynasty-scouting-report\b[^"]*"[^>]*>(.*?)(?=<div[^>]*class="[^"]*\bffb-dynasty-scouting-report\b|<footer\b|$)',
        html, flags=re.S | re.I,
    ):
        block = m.group(1)
        name_m = re.search(r'<h[23][^>]*>(.+?)</h[23]>', block, flags=re.S | re.I)
        pos_m = re.search(r'class="[^"]*(?:position|pos)[^"]*"[^>]*>(.+?)</', block, flags=re.S | re.I)
        team_m = re.search(r'class="[^"]*(?:team)[^"]*"[^>]*>(.+?)</', block, flags=re.S | re.I)
        body = strip_html_tags(block)
        if not name_m:
            continue
        reports.append({
            "name": strip_html_tags(name_m.group(1)),
            "position": strip_html_tags(pos_m.group(1)) if pos_m else "",
            "team": strip_html_tags(team_m.group(1)) if team_m else "",
            "report": body[:1500],
        })
    return reports


def dynasty_scouting_command(
    query: str = typer.Argument(None, help="Player name (fuzzy). Omit to list all."),
    limit: int = typer.Option(20, "-n", "--limit", help="Max reports when listing"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Rookie scouting reports.

    \b
    EXAMPLES:
      ffb dynasty scouting                     # first 20 reports
      ffb dynasty scouting "Jeremiyah Love"    # one 2026 prospect report
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_SCOUTING_REPORTS_PAGE))
    reports = _parse_reports(html)
    if not reports:
        typer.echo("No scouting reports extracted. Try `ffb dynasty open scouting`.")
        raise typer.Exit(1)

    if query:
        scored = []
        for r in reports:
            n = r.get("name", "")
            score = max(fuzz.token_sort_ratio(query.lower(), n.lower()),
                        fuzz.partial_ratio(query.lower(), n.lower()))
            if score >= 60:
                scored.append((score, r))
        scored.sort(key=lambda t: -t[0])
        reports = [r for _, r in scored[:limit]]

    reports = reports[:limit]
    if output_json:
        console.print_json(json.dumps(reports, default=str))
        return

    if query and len(reports) == 1:
        r = reports[0]
        dynasty_player_card(
            {"player_name": r["name"], "position": r["position"], "team": r["team"]},
            body=r["report"],
        )
    else:
        list_cards(reports, title="Dynasty Scouting Reports",
                   fields=[("name", "Player"), ("position", "Pos"), ("team", "Team"), ("report", "Report")])

"""ffb dynasty draft-results, 2026 NFL Draft results with dynasty context."""
from __future__ import annotations

import json
import re

import typer

from ...api.dynasty_scrape import slice_main_content, strip_html_tags
from ...api.endpoints import DYNASTY_DRAFT_RESULTS_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_draft_results_command(
    round_filter: int = typer.Option(None, "--round", "-r", help="Filter to a single NFL round (1-7)"),
    position: str = typer.Option(None, "--position", "-p", help="Filter to one position (QB, RB, WR, TE)"),
    team: str = typer.Option(None, "--team", "-t", help="Filter to an NFL team (KC, BUF, etc.)"),
    limit: int = typer.Option(50, "-n", "--limit", help="Max picks"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """2026 NFL Draft results with player position and college.

    \b
    EXAMPLES:
      ffb dynasty draft-results           # first 50 picks
      ffb dynasty draft-results -r 1      # round 1 only
      ffb dynasty draft-results -p RB     # rookie RBs taken
      ffb dynasty draft-results -t KC     # KC's picks
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_DRAFT_RESULTS_PAGE))

    picks: list[dict] = []
    current_round: int | None = None

    # Walk the main content sequentially. When we hit `<h2>Round N</h2>` update
    # the running round, when we hit a `<tr data-team="..." data-position="...">`
    # capture the row.
    pos = 0
    while pos < len(html):
        h2_m = re.search(r"<h[23][^>]*>\s*Round\s+(\d)\s*</h[23]>", html[pos:], flags=re.I)
        tr_m = re.search(r'<tr\s+[^>]*data-team="([a-z]+)"[^>]*data-position="([A-Z]+)"[^>]*>(.*?)</tr>',
                         html[pos:], flags=re.S | re.I)
        if not h2_m and not tr_m:
            break
        if h2_m and (not tr_m or h2_m.start() < tr_m.start()):
            current_round = int(h2_m.group(1))
            pos += h2_m.end()
            continue
        # Process row
        row_html = tr_m.group(3)
        nfl_team = tr_m.group(1).upper()
        position_code = tr_m.group(2).upper()
        pick_m = re.search(r'<td[^>]*class="[^"]*pick[^"]*"[^>]*>(\d+)', row_html, flags=re.I)
        name_m = re.search(
            r'<div[^>]*class="player-name"[^>]*>\s*(?:<a[^>]*>)?(.+?)(?:</a>)?\s*</div>',
            row_html, flags=re.S | re.I,
        )
        line_two_m = re.search(
            r'<div[^>]*class="player-right-line-two"[^>]*>(.+?)</div>',
            row_html, flags=re.S | re.I,
        )
        picks.append({
            "round": current_round,
            "pick": int(pick_m.group(1)) if pick_m else None,
            "team": nfl_team,
            "position": position_code,
            "name": strip_html_tags(name_m.group(1)) if name_m else "",
            "college": strip_html_tags(line_two_m.group(1)) if line_two_m else "",
        })
        pos += tr_m.end()

    if round_filter is not None:
        picks = [p for p in picks if p.get("round") == round_filter]
    if position:
        picks = [p for p in picks if p.get("position", "").upper() == position.upper()]
    if team:
        picks = [p for p in picks if p.get("team", "").upper() == team.upper()]

    picks = picks[:limit]
    if output_json:
        console.print_json(json.dumps(picks, default=str))
    elif picks:
        list_cards(picks, title="2026 NFL Draft Results",
                   fields=[("round", "Rd"), ("pick", "#"), ("name", "Player"),
                           ("position", "Pos"), ("team", "NFL Team"),
                           ("college", "College / Note")])
    else:
        typer.echo("No draft picks extracted.")

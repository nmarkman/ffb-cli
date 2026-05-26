"""ffb best-ball, DFS Pass best-ball rankings."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import DFS_BEST_BALL_PAGE
from ..display.tables import best_ball_table, console
from ._scrape import load_const_data, to_float

VALID_POSITIONS = {"QB", "RB", "WR", "TE"}


def best_ball_command(
    position: str = typer.Argument(None, help="Position filter (QB, RB, WR, TE)"),
    team: str = typer.Option(None, "-t", "--team", help="Filter by team abbreviation"),
    limit: int = typer.Option(50, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Best-ball rankings (DFS Pass) sorted by Underdog ADP. Requires login.

    \b
    'Betz' and 'Borg' are the Footclan analyst-specific best-ball ranks.

    \b
    EXAMPLES:
      ffb best-ball                # top 50 by ADP
      ffb best-ball WR -n 30       # top 30 WRs
      ffb best-ball -t KC          # all KC players
      ffb best-ball --json         # JSON output
    """
    data = load_const_data(DFS_BEST_BALL_PAGE)
    rows = []
    for r in data:
        rows.append({
            "name": r.get("name", ""),
            "fantasy_position": r.get("fantasy_position", ""),
            "team": r.get("team", "") or "",
            "bye_week": r.get("bye_week", ""),
            "adp": to_float(r.get("adp")),
            "betz": r.get("betz", ""),
            "borg": r.get("borg", ""),
        })

    if position:
        pos_u = position.upper()
        rows = [r for r in rows if r["fantasy_position"].upper() == pos_u]
    if team:
        team_u = team.upper()
        rows = [r for r in rows if r["team"].upper() == team_u]

    rows.sort(key=lambda r: r["adp"] if r["adp"] > 0 else float("inf"))
    rows = rows[:limit]

    if not rows:
        typer.echo("No players matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        best_ball_table(rows)

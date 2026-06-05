"""ffb rookie-report, UDK Rookie Report (per-rookie scouting writeups)."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_ROOKIE_REPORT_PAGE
from ..display.tables import player_report_table, console
from ._scrape import extract_player_sections

VALID_POSITIONS = {"QB", "RB", "WR", "TE"}


def rookie_report_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(sorted(VALID_POSITIONS))})"),
    query: str = typer.Option(None, "-q", "--query", help="Filter by player name"),
    limit: int = typer.Option(40, "-n", "--limit", help="Max items"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Rookie Report: scouting writeups for the incoming rookie class. Requires login.

    \b
    EXAMPLES:
      ffb rookie-report                # all rookies
      ffb rookie-report WR -n 20       # top 20 WR rookies
      ffb rookie-report -q mendoza     # one rookie
    """
    rows = extract_player_sections(UDK_ROOKIE_REPORT_PAGE)

    if position:
        pos_u = position.upper()
        rows = [r for r in rows if r["position"] == pos_u]
    if query:
        q = query.lower()
        rows = [r for r in rows if q in r["name"].lower()]

    rows = rows[:limit]
    if not rows:
        typer.echo("No rookies matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        player_report_table(rows, title="UDK Rookie Report")

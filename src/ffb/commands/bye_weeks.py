"""ffb bye-weeks, the UDK bye-weeks page."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_BYE_WEEKS_PAGE
from ..display.tables import bye_weeks_table, console
from ._scrape import load_const_data, to_int


def bye_weeks_command(
    week: int = typer.Option(None, "-w", "--week", help="Filter to a specific bye week"),
    team: str = typer.Option(None, "-t", "--team", help="Filter by team abbreviation (e.g. KC, BUF)"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """View 2026 NFL bye weeks. Requires login.

    \b
    Sorted by bye week, then team. Useful for draft prep and roster planning.

    \b
    EXAMPLES:
      ffb bye-weeks                 # all 32 teams
      ffb bye-weeks -w 8            # only teams on bye in week 8
      ffb bye-weeks -t KC           # one team
      ffb bye-weeks --json          # JSON output
    """
    data = load_const_data(UDK_BYE_WEEKS_PAGE)
    rows = [
        {
            "bye_week": to_int(r.get("bye_week")),
            "name": r.get("name", ""),
            "key": r.get("key", ""),
        }
        for r in data
    ]

    if week is not None:
        rows = [r for r in rows if r["bye_week"] == week]
    if team:
        team_u = team.upper()
        rows = [r for r in rows if r["key"].upper() == team_u]

    rows.sort(key=lambda r: (r["bye_week"], r["name"]))

    if not rows:
        typer.echo("No teams matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        bye_weeks_table(rows)

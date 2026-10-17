"""ffb games, this week's slate with Vegas lines and weather (FootClan)."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import FOOTCLAN_START_SIT_PAGE
from ..display.tables import console, games_table
from ._inseason import load_page_data, vegas_games


def games_command(
    team: str = typer.Option(None, "-t", "--team", help="Only this team's game"),
    sort_by: str = typer.Option("time", "-s", "--sort", help="Sort key: time | total"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """This week's games: spread, over/under, implied team totals, weather. Requires login.

    \b
    Implied total = over/under / 2 minus the team's spread / 2, the number the
    start/sit tool uses. High implied totals point to fantasy-friendly games;
    wind and precipitation flag passing and kicking risk.

    \b
    EXAMPLES:
      ffb games                    # full slate in kickoff order
      ffb games -s total           # highest-scoring games first
      ffb games -t KC              # one team's game
      ffb games --json
    """
    if sort_by not in ("time", "total"):
        typer.echo(f"Unknown sort '{sort_by}'. Valid: time, total.", err=True)
        raise typer.Exit(1)

    const, _ = load_page_data(FOOTCLAN_START_SIT_PAGE)
    week = int(const.get("week") or 0)
    rows = vegas_games(const.get("vegas") or [], const.get("weather") or {})

    # Byes come from the schedule, not the odds feed, so a game whose line
    # isn't posted yet doesn't read as a bye.
    schedule = const.get("allGames") or {}
    byes = sorted(t for t in (const.get("teams") or {}) if f"{t}{week}" not in schedule)
    # The odds feed keeps finished games at "Scheduled"; the schedule knows.
    for g in rows:
        g["status"] = (schedule.get(f"{g['home']}{week}") or {}).get("status") or g["status"]

    if team:
        t = team.upper()
        rows = [g for g in rows if t in (g["home"], g["away"])]
    if sort_by == "total":
        rows.sort(key=lambda g: g["over_under"] or 0, reverse=True)

    if not rows:
        typer.echo("No lines posted for this week yet." if not team else f"{team.upper()} has no game this week.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps({"week": week, "games": rows, "byes": byes}))
    else:
        games_table(rows, week=week, byes=byes)

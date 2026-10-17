"""ffb waivers, the FootClan Waiver Wire Rankings."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import FOOTCLAN_WAIVERS_PAGE
from ..display.tables import console, waiver_rankings_table
from ._inseason import (
    display_position,
    load_tool_data,
    matchup,
    normalize_position,
    waiver_rankings,
)

POSITIONS = ("QB", "RB", "WR", "TE", "D")


def waivers_command(
    position: str = typer.Argument(None, help="QB, RB, WR, TE or DST (default: all skill players)"),
    limit: int = typer.Option(40, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """This week's waiver wire rankings with suggested FAAB (FootClan). Requires login.

    \b
    Consensus waiver rank plus Andy, Jason and Mike's ranks, a suggested FAAB
    bid as a percent of your budget, and a STASH flag for players whose value
    should grow. Ranks are re-sequenced within a position when you filter.

    \b
    EXAMPLES:
      ffb waivers                  # every skill-player pickup, ranked
      ffb waivers RB               # RB adds only
      ffb waivers DST              # defense streamers on waivers
      ffb waivers --json
    """
    pos = normalize_position(position, POSITIONS)
    data = load_tool_data(FOOTCLAN_WAIVERS_PAGE, "waiverRankings")
    week = int(data.get("week") or 0)
    games = data.get("allGames") or {}

    source = data.get("defenseRankings") if pos == "D" else data.get("rankings")
    source = source or []
    if pos and pos != "D":
        source = [r for r in source if (r.get("fantasy_position") or "").upper() == pos]
    rows = waiver_rankings(source)

    if not rows:
        typer.echo("No waiver rankings are posted right now.")
        raise typer.Exit(0)

    for r in rows:
        r["position"] = display_position(r["position"])
        r["matchup"] = matchup(r["team"], week, games)
    rows = rows[:limit]

    label = display_position(pos) if pos else "ALL"
    if output_json:
        console.print_json(json.dumps({"week": week, "position": label, "players": rows}))
    else:
        waiver_rankings_table(rows, week=week, position=label)

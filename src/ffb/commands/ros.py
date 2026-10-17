"""ffb ros, the FootClan Rest-of-Season Rankings."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import FOOTCLAN_ROS_PAGE
from ..config import DEFAULT_SCORING, SCORING_FORMATS
from ..display.tables import console, ros_rankings_table
from ._inseason import FLEX_POSITIONS, consensus_rankings, load_tool_data, normalize_position, validate_pass_td
from .rankings import validate_scoring

POSITIONS = ("QB", "RB", "WR", "TE", "FLEX")


def ros_rows(data: list[dict], position: str, scoring: str, *, pass_td: int = 4) -> list[dict]:
    """Rank rest-of-season stat projections. Each row is one analyst's ROS line
    for a player, so this is the same consensus collapse as the weekly ranks,
    plus remaining games and points per remaining game."""
    positions = FLEX_POSITIONS if position == "FLEX" else (position,)
    remaining = {str(r.get("player_id")): r.get("remaining_games") for r in data}
    rows = consensus_rankings(data, SCORING_FORMATS[scoring], positions, pass_td=pass_td)
    for r in rows:
        r.pop("_avg", None)
        r.pop("injury_status", None)
        games = remaining.get(r["player_id"])
        try:
            games = int(games)
        except (TypeError, ValueError):
            games = None
        r["remaining_games"] = games
        r["ppg"] = round(r["points"] / games, 1) if games else None
    return rows


def ros_command(
    position: str = typer.Argument("FLEX", help="QB, RB, WR, TE or FLEX"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring: half, ppr, standard"),
    pass_td: int = typer.Option(4, "--pass-td", help="Points per passing TD: 4 or 6 (the site's default view uses 6)"),
    team: str = typer.Option(None, "-t", "--team", help="Team code filter (KC, BUF, ...)"),
    limit: int = typer.Option(40, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Rest-of-season rankings (FootClan, in-season). Requires login.

    \b
    Consensus from Andy, Jason and Mike's rest-of-season projections, with each
    analyst's rank, projected ROS points, games left and points per game. Use it
    for trades and long-term roster decisions; `ffb weekly` is for lineups.

    \b
    EXAMPLES:
      ffb ros                      # top 40 FLEX rest of season
      ffb ros QB -n 15             # ROS QB ranks
      ffb ros WR -s ppr            # PPR
      ffb ros TE --json
    """
    scoring = validate_scoring(scoring)
    validate_pass_td(pass_td)
    pos = normalize_position(position, POSITIONS)
    data = load_tool_data(FOOTCLAN_ROS_PAGE, "rosRankings")
    if not isinstance(data, list) or not data:
        typer.echo("No rest-of-season rankings are posted right now.")
        raise typer.Exit(0)

    week = int(data[0].get("week") or 0)
    rows = ros_rows(data, pos, scoring, pass_td=pass_td)
    if team:
        rows = [r for r in rows if r["team"].upper() == team.upper()]
    rows = rows[:limit]

    if output_json:
        console.print_json(json.dumps({"week": week, "position": pos, "scoring": scoring, "players": rows}))
    else:
        ros_rankings_table(rows, week=week, position=pos, scoring=scoring)

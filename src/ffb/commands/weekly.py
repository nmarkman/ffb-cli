"""ffb weekly, the FootClan Premium Rankings for the current week."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import FOOTCLAN_START_SIT_PAGE
from ..config import DEFAULT_SCORING, SCORING_FORMATS
from ..display.tables import console, weekly_rankings_table
from ._inseason import (
    FLEX_POSITIONS,
    consensus_rankings,
    display_position,
    load_page_data,
    matchup,
    normalize_position,
    simple_rankings,
    validate_pass_td,
)
from .rankings import validate_scoring

POSITIONS = ("QB", "RB", "WR", "TE", "FLEX", "D", "K")


def load_weekly(position: str, scoring: str, page: tuple[dict, list[dict]] | None = None,
                *, pass_td: int = 4) -> tuple[int, list[dict], dict]:
    """Return (week, ranked rows, page const data) for one weekly position.

    Shared by `ffb weekly` and `ffb start-sit`, which read the same page; pass
    an already-loaded ``page`` to rank several positions without re-parsing."""
    const, projections = page or load_page_data(FOOTCLAN_START_SIT_PAGE)
    week = int(const.get("week") or 0)
    games = const.get("allGames") or {}
    if position in ("D", "K"):
        ranks = const.get("defenseRanks" if position == "D" else "kickerRanks") or []
        rows = simple_rankings(ranks, const.get("simpleProjections") or [])
    else:
        positions = FLEX_POSITIONS if position == "FLEX" else (position,)
        rows = consensus_rankings(projections, SCORING_FORMATS[scoring], positions, pass_td=pass_td)
    for r in rows:
        r.pop("_avg", None)
        r["position"] = display_position(r["position"])
        r["matchup"] = matchup(r["team"], week, games)
    return week, rows, const


def weekly_command(
    position: str = typer.Argument("FLEX", help="QB, RB, WR, TE, FLEX, DST or K"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring: half, ppr, standard"),
    pass_td: int = typer.Option(4, "--pass-td", help="Points per passing TD: 4 or 6 (the site's default view uses 6)"),
    team: str = typer.Option(None, "-t", "--team", help="Team code filter (KC, BUF, ...)"),
    limit: int = typer.Option(40, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """This week's Premium Rankings (FootClan, in-season). Requires login.

    \b
    Consensus rank from Andy, Jason and Mike's weekly projections, plus each
    analyst's own rank and the week's matchup. QB-TE points are scored from the
    averaged stat line in your chosen format; DST/K points are the site's.

    \b
    EXAMPLES:
      ffb weekly                   # top 40 FLEX (RB/WR/TE) this week
      ffb weekly QB -n 12          # QB1s for the week
      ffb weekly WR -s ppr         # WR ranks, PPR
      ffb weekly QB --pass-td 6    # 6-pt passing TDs (matches the site's default)
      ffb weekly DST               # defense streamers
      ffb weekly RB -t KC --json   # one team's RBs as JSON
    """
    scoring = validate_scoring(scoring)
    validate_pass_td(pass_td)
    pos = normalize_position(position, POSITIONS)
    week, rows, _ = load_weekly(pos, scoring, pass_td=pass_td)

    if not rows:
        typer.echo("No weekly rankings are posted right now (offseason or between weeks).")
        raise typer.Exit(0)

    if team:
        rows = [r for r in rows if r["team"].upper() == team.upper()]
    rows = rows[:limit]

    if output_json:
        console.print_json(json.dumps({"week": week, "position": display_position(pos),
                                       "scoring": scoring, "players": rows}))
    else:
        weekly_rankings_table(rows, week=week, position=display_position(pos), scoring=scoring)

"""ffb stream, the FootClan Stream Finder (defense vs position)."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import FOOTCLAN_START_SIT_PAGE
from ..display.tables import console, stream_finder_table
from ._inseason import (
    completed_through,
    defense_vs_position,
    display_position,
    load_page_data,
    normalize_position,
)

POSITIONS = ("QB", "RB", "WR", "TE", "K", "D")


def stream_command(
    position: str = typer.Argument("QB", help="QB, RB, WR, TE, K or DST"),
    weeks: int = typer.Option(3, "-w", "--weeks", help="Upcoming weeks of opponents to show"),
    raw: bool = typer.Option(False, "--raw", help="Rank by raw points allowed instead of schedule-adjusted PAE"),
    limit: int = typer.Option(32, "-n", "--limit", help="Max teams"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Stream Finder: which defenses give up the most to a position (FootClan). Requires login.

    \b
    Ranks every team by how much it gives up to the position this season
    (softest first) and lists who it plays next. A soft defense's upcoming
    opponent is the stream: if the #1 defense vs QBs plays @NYJ next week, the
    Jets QB is a streaming option.

    \b
    Like the site, it ranks by PAE (points allowed above expectation: what the
    defense allowed minus what those offenses usually score) once three weeks
    of games are in, so a defense isn't penalized for a tough schedule. FPA (raw fantasy points
    allowed per game) is shown alongside; --raw ranks by it instead.

    \b
    For DST the logic flips: rows are offenses ranked by points they surrender
    to opposing defenses, so stream the defense that faces them.

    \b
    EXAMPLES:
      ffb stream                   # softest defenses vs QBs, next 3 weeks
      ffb stream TE -w 4           # TE matchups four weeks out
      ffb stream RB --raw          # rank by raw points allowed
      ffb stream DST               # offenses that feed opposing defenses
      ffb stream K --json
    """
    pos = normalize_position(position, POSITIONS)
    const, _ = load_page_data(FOOTCLAN_START_SIT_PAGE)
    rows = const.get("streamFinder") or []
    if isinstance(rows, str):  # the start-sit page embeds it JSON-encoded
        rows = json.loads(rows)
    week = int(const.get("week") or 0)
    season_weeks = int(const.get("seasonWeeks") or 18)
    through = completed_through(rows)

    if not rows or not through:
        typer.echo("No Stream Finder data yet (it fills in after Week 1).")
        raise typer.Exit(0)

    upcoming = list(range(week, min(week + max(weeks, 0), season_weeks + 1)))
    adjusted = not raw and through > 2  # the site's own switch point
    result = defense_vs_position(rows, pos, through_week=through, upcoming=upcoming,
                                 games=const.get("allGames") or {}, adjusted=adjusted)[:limit]

    if output_json:
        console.print_json(json.dumps({
            "position": display_position(pos), "through_week": through,
            "ranked_by": "pae" if adjusted else "avg_allowed",
            "upcoming_weeks": upcoming, "teams": result,
        }))
    else:
        stream_finder_table(result, position=display_position(pos), through_week=through,
                            upcoming=upcoming, adjusted=adjusted)

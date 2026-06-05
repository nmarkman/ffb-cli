"""ffb market-share, player share of team usage (UDK Market Share)."""
from __future__ import annotations

import json
from collections import defaultdict

import typer

from ..api.endpoints import UDK_MARKET_SHARE_PAGE
from ..display.tables import market_share_table, console
from ._scrape import load_const_data, to_float, to_int

VALID_POSITIONS = {"QB", "RB", "WR", "TE"}


def market_share_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(sorted(VALID_POSITIONS))})"),
    team: str = typer.Option(None, "-t", "--team", help="Team code filter (KC, BUF, ...)"),
    season: int = typer.Option(None, "-y", "--season", help="Season year (defaults to most recent)"),
    sort_by: str = typer.Option("targets", "-s", "--sort", help="Sort key: targets | rush | rec_yds | points"),
    min_games: int = typer.Option(4, "--min-games", help="Minimum games played to include"),
    limit: int = typer.Option(40, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Market Share: each player's share of his team's usage. Requires login.

    \b
    Aggregates a full season of game logs into the player's share of team
    receiving targets, rushing attempts, receiving yards, and fantasy points.
    A high target share with a low ADP is the classic value signal.

    \b
    EXAMPLES:
      ffb market-share                 # top 40 by target share
      ffb market-share WR -n 30        # top 30 WRs
      ffb market-share -t KC           # Chiefs players
      ffb market-share RB -s rush      # RBs by rushing-attempt share
    """
    raw = load_const_data(UDK_MARKET_SHARE_PAGE)

    if season is None:
        seasons = {to_int(r.get("season")) for r in raw if r.get("season")}
        season = max(seasons) if seasons else None

    # Accumulate player and team totals across weeks.
    agg: dict[str, dict] = {}
    for r in raw:
        if season is not None and to_int(r.get("season")) != season:
            continue
        pid = r.get("player_id", "")
        if not pid:
            continue
        a = agg.get(pid)
        if a is None:
            a = agg[pid] = {
                "name": r.get("name", ""),
                "fantasy_position": r.get("fantasy_position", "") or "",
                "team": r.get("team", "") or "",
                "games": 0,
                "tgt": 0.0, "team_tgt": 0.0,
                "rush": 0.0, "team_rush": 0.0,
                "rec_yd": 0.0, "team_rec_yd": 0.0,
                "pts": 0.0, "team_pts": 0.0,
            }
        a["games"] += 1
        a["tgt"] += to_float(r.get("receiving_targets"))
        a["team_tgt"] += to_float(r.get("total_receiving_targets"))
        a["rush"] += to_float(r.get("rushing_attempts"))
        a["team_rush"] += to_float(r.get("total_rushing_attempts"))
        a["rec_yd"] += to_float(r.get("receiving_yards"))
        a["team_rec_yd"] += to_float(r.get("total_receiving_yards"))
        a["pts"] += to_float(r.get("fantasy_points"))
        a["team_pts"] += to_float(r.get("total_fantasy_points"))

    def share(num: float, den: float):
        return round(num / den, 4) if den else None

    rows = []
    for a in agg.values():
        if a["games"] < min_games:
            continue
        rows.append({
            "name": a["name"],
            "fantasy_position": a["fantasy_position"],
            "team": a["team"],
            "games": a["games"],
            "target_share": share(a["tgt"], a["team_tgt"]),
            "rush_share": share(a["rush"], a["team_rush"]),
            "rec_yd_share": share(a["rec_yd"], a["team_rec_yd"]),
            "points_share": share(a["pts"], a["team_pts"]),
        })

    if position:
        pos_u = position.upper()
        rows = [r for r in rows if r["fantasy_position"].upper() == pos_u]
    if team:
        team_u = team.upper()
        rows = [r for r in rows if r["team"].upper() == team_u]

    sort_keys = {"targets": "target_share", "rush": "rush_share",
                 "rec_yds": "rec_yd_share", "points": "points_share"}
    sort_key = sort_keys.get(sort_by.lower())
    if not sort_key:
        typer.echo(f"Unknown sort key '{sort_by}'. Valid: {', '.join(sort_keys)}.", err=True)
        raise typer.Exit(1)

    rows.sort(key=lambda r: (r[sort_key] is None, -(r[sort_key] or 0)))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    rows = rows[:limit]

    if not rows:
        typer.echo("No players matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        market_share_table(rows, season)

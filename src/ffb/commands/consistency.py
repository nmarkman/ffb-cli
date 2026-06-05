"""ffb consistency, weekly boom/bust consistency (UDK Consistency / Weekly charts).

The UDK "Weekly Consistency" and "Consistency Percentages" tools share one
week-by-week payload (`const data = {"2025": [...], ...}`). This command computes
the season-level consistency summary (start-worthy / boom / bust rates) and can
also print any single player's week-by-week game log via --weekly.
"""
from __future__ import annotations

import json
import statistics

import typer

from ..api.endpoints import UDK_CONSISTENCY_PAGE
from ..display.tables import consistency_table, consistency_weekly_table, console
from ._scrape import load_const_data_raw, to_float, to_int

VALID_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DST"}

# Weekly position-rank cutoff to count as a "startable" week in a 12-team league.
STARTABLE = {"QB": 12, "RB": 24, "WR": 30, "TE": 12, "K": 12, "DST": 12}
BOOM_RANK = 5  # a top-5 weekly finish at the position is a "boom"
MAX_WEEK = 18


def _season_rows(data, season: int | None):
    """The payload is a dict keyed by season string. Pick the requested season
    (or the most recent) and return (season_int, rows)."""
    if isinstance(data, dict):
        seasons = sorted((int(k) for k in data.keys() if str(k).isdigit()), reverse=True)
        if not seasons:
            return None, []
        chosen = season if (season in seasons) else seasons[0]
        return chosen, data.get(str(chosen), [])
    return season, data  # already a list


def _player_weeks(row: dict, ppr: bool) -> list[dict]:
    pts_field = "fantasy_points_ppr" if ppr else "fantasy_points"
    weeks = []
    for wk in range(1, MAX_WEEK + 1):
        if to_int(row.get(f"week_{wk}_played", 0)) != 1:
            continue
        weeks.append({
            "week": wk,
            "opponent": row.get(f"week_{wk}_opponent", "") or "",
            "points": round(to_float(row.get(f"week_{wk}_{pts_field}")), 1),
            "position_rank": to_int(row.get(f"week_{wk}_position_rank")) or None,
            "started": to_int(row.get(f"week_{wk}_started", 0)) == 1,
        })
    return weeks


def consistency_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(sorted(VALID_POSITIONS))})"),
    weekly: str = typer.Option(None, "-w", "--weekly", help="Show one player's week-by-week game log"),
    ppr: bool = typer.Option(False, "--ppr", help="Use PPR weekly scoring (default: standard)"),
    season: int = typer.Option(None, "-y", "--season", help="Season year (defaults to most recent)"),
    sort_by: str = typer.Option("start", "-s", "--sort", help="Sort key: start | boom | ppg | bust"),
    min_games: int = typer.Option(6, "--min-games", help="Minimum games played to include"),
    limit: int = typer.Option(40, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Weekly consistency: start-worthy / boom / bust rates. Requires login.

    \b
    A player is "startable" in a week if he finishes within his position's
    12-team starter cutoff (QB/TE top-12, RB top-24, WR top-30). "Boom" = a
    top-5 weekly finish; "bust" = a played week outside the startable cutoff.

    \b
    EXAMPLES:
      ffb consistency                  # most consistent players (start-worthy rate)
      ffb consistency RB -s boom        # RBs by boom rate
      ffb consistency WR --ppr          # WRs, PPR scoring
      ffb consistency -w "Josh Allen"   # one player's week-by-week game log
    """
    season, raw = _season_rows(load_const_data_raw(UDK_CONSISTENCY_PAGE), season)
    if not raw:
        typer.echo("No consistency data found.")
        raise typer.Exit(1)

    # Single-player weekly game log.
    if weekly:
        q = weekly.lower()
        match = next((r for r in raw if q in (r.get("name", "") or "").lower()), None)
        if not match:
            typer.echo(f"No player matching '{weekly}'.", err=True)
            raise typer.Exit(1)
        weeks = _player_weeks(match, ppr)
        player = {
            "name": match.get("name", ""),
            "fantasy_position": match.get("fantasy_position", ""),
            "team": match.get("team_key", "") or "",
            "season": season,
        }
        if output_json:
            console.print_json(json.dumps({"player": player, "weeks": weeks}))
        else:
            consistency_weekly_table(player, weeks, scoring="ppr" if ppr else "std")
        return

    rows = []
    for r in raw:
        pos = (r.get("fantasy_position", "") or "").upper()
        weeks = _player_weeks(r, ppr)
        games = len(weeks)
        if games < min_games:
            continue
        cutoff = STARTABLE.get(pos, 24)
        pts = [w["points"] for w in weeks]
        ranks = [w["position_rank"] for w in weeks if w["position_rank"]]
        startable = sum(1 for rk in ranks if rk <= cutoff)
        boom = sum(1 for rk in ranks if rk <= BOOM_RANK)
        bust = sum(1 for rk in ranks if rk > cutoff)
        ppg = sum(pts) / games if games else 0.0
        stdev = statistics.pstdev(pts) if len(pts) > 1 else 0.0
        rows.append({
            "name": r.get("name", ""),
            "fantasy_position": pos,
            "team": r.get("team_key", "") or "",
            "games": games,
            "ppg": round(ppg, 1),
            "start_pct": round(startable / games, 4) if games else None,
            "boom_pct": round(boom / games, 4) if games else None,
            "bust_pct": round(bust / games, 4) if games else None,
            "stdev": round(stdev, 1),
        })

    if position:
        pos_u = position.upper()
        rows = [r for r in rows if r["fantasy_position"] == pos_u]

    sort_keys = {"start": "start_pct", "boom": "boom_pct", "ppg": "ppg", "bust": "bust_pct"}
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
        consistency_table(rows, season=season, scoring="ppr" if ppr else "std")

"""ffb dfs, DFS Pass weekly rankings with DraftKings / FanDuel salaries."""
from __future__ import annotations

import json

import typer

from ..api.dynasty_scrape import extract_const_assignment, parse_js_assignment
from ..api.endpoints import DFS_WEEKLY_PAGE, FOOTCLAN_START_SIT_PAGE
from ..config import CACHE_TTL_INSEASON
from ..display.tables import console, dfs_table
from ._scrape import fetch_page
from ._inseason import (
    FLEX_POSITIONS,
    STAT_FIELDS,
    _opt,
    display_position,
    load_page_data,
    normalize_position,
)
from .rankings import _num

POSITIONS = ("QB", "RB", "WR", "TE", "FLEX", "D", "K")

# Site scoring (offense). DraftKings' 300/100-yard bonuses are left out: they
# don't apply cleanly to an averaged projection.
DFS_SCORING = {
    "dk": {"passing_yards": 0.04, "passing_touchdowns": 4, "interceptions_thrown": -1,
           "rushing_yards": 0.1, "rushing_touchdowns": 6, "receptions": 1.0,
           "receiving_yards": 0.1, "receiving_touchdowns": 6, "fumbles_lost": -1},
    "fd": {"passing_yards": 0.04, "passing_touchdowns": 4, "interceptions_thrown": -1,
           "rushing_yards": 0.1, "rushing_touchdowns": 6, "receptions": 0.5,
           "receiving_yards": 0.1, "receiving_touchdowns": 6, "fumbles_lost": -2},
}
SALARY_FIELD = {"dk": "upcoming_draft_kings_salary", "fd": "upcoming_fan_duel_salary"}
SITE_NAMES = {"dk": "DraftKings", "fd": "FanDuel"}
SORTS = ("value", "points", "salary")


def dfs_points(stats: dict, site: str) -> float:
    cfg = DFS_SCORING[site]
    return sum(_num(stats.get(f)) * cfg[f] for f in STAT_FIELDS)


def dfs_rows(players: list[dict], projections: list[dict], simple: list[dict], site: str) -> list[dict]:
    """Join salaries to the analysts' averaged weekly projections.

    ``players`` is the DFS page's player list (salary, opponent, matchup rank);
    ``projections`` the one-row-per-analyst weekly stat lines; ``simple`` the
    D/ST + K projections, which carry their own salaries and points."""
    lines: dict[str, list[dict]] = {}
    for p in projections or []:
        lines.setdefault(str(p.get("player_id")), []).append(p)

    rows = []
    for pl in players or []:
        pid = str(pl.get("player_id", ""))
        salary = _opt(pl.get(SALARY_FIELD[site]))
        if not salary or pid not in lines:
            continue
        entries = lines[pid]
        avg = {f: sum(_num(e.get(f)) for e in entries) / len(entries) for f in STAT_FIELDS}
        points = dfs_points(avg, site)
        if points <= 0:
            continue
        rows.append(_row(pl.get("name", ""), (pl.get("fantasy_position") or "").upper(),
                         pl.get("team", "") or "", pl.get("upcoming_game_opponent"),
                         _opt(pl.get("upcoming_opponent_position_rank")), salary, points,
                         pl.get("injury_status")))

    for s in simple or []:
        salary = _opt(s.get(SALARY_FIELD[site]))
        points = _num(s.get("points"))
        if not salary or points <= 0:
            continue
        rows.append(_row(s.get("name", ""), display_position((s.get("fantasy_position") or "").upper()),
                         s.get("team", "") or "", s.get("upcoming_game_opponent"), None,
                         salary, points, None))
    return rows


def _row(name, pos, team, opp, opp_rank, salary, points, injury) -> dict:
    # Value comes from the rounded points so the two shown numbers agree.
    points = round(points, 1)
    return {
        "name": name,
        "position": pos,
        "team": team,
        "opponent": opp,
        "opp_pos_rank": int(opp_rank) if opp_rank else None,
        "salary": int(salary),
        "points": round(points, 1),
        "value": round(points / (salary / 1000), 2),
        "injury_status": injury,
    }


def dfs_command(
    position: str = typer.Argument(None, help="QB, RB, WR, TE, FLEX, DST or K (default: all)"),
    site: str = typer.Option("dk", "--site", help="dk (DraftKings) or fd (FanDuel)"),
    sort_by: str = typer.Option("value", "-s", "--sort", help="Sort key: value | points | salary"),
    max_salary: int = typer.Option(None, "--max-salary", help="Only players at or under this salary"),
    limit: int = typer.Option(30, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Weekly DFS values: salary, projected points and points per $1K (DFS Pass). Requires login.

    \b
    Projections are the Footballers' weekly stat lines (averaged across Andy,
    Jason and Mike) scored with DraftKings (full PPR) or FanDuel (half PPR)
    rules. Value = projected points per $1,000 of salary. "Opp Rk" is the
    opponent's rank against the position (higher = softer matchup). DST and K
    points are the site's own weekly projections, not DFS-specific scoring.

    \b
    EXAMPLES:
      ffb dfs                          # best DraftKings values
      ffb dfs RB --site fd             # FanDuel RB values
      ffb dfs WR --max-salary 5000     # cheap WRs
      ffb dfs QB -s points --json
    """
    site = site.lower()
    if site not in DFS_SCORING:
        typer.echo(f"Unknown site '{site}'. Valid: dk, fd.", err=True)
        raise typer.Exit(1)
    if sort_by not in SORTS:
        typer.echo(f"Unknown sort '{sort_by}'. Valid: {', '.join(SORTS)}.", err=True)
        raise typer.Exit(1)
    pos = normalize_position(position, POSITIONS)

    players, projections = _load_dfs_players()
    if not players:
        # The DFS page answers an expired or non-DFS-Pass session with an
        # empty 200, so this is usually auth, not an empty slate.
        typer.echo("No DFS data on the page. Your session may have expired (run `ffb login`), "
                   "or your account may not include the DFS Pass.", err=True)
        raise typer.Exit(1)
    simple_const, _ = load_page_data(FOOTCLAN_START_SIT_PAGE)
    rows = dfs_rows(players, projections, simple_const.get("simpleProjections") or [], site)

    if pos == "FLEX":
        rows = [r for r in rows if r["position"] in FLEX_POSITIONS]
    elif pos:
        rows = [r for r in rows if r["position"] == display_position(pos)]
    if max_salary:
        rows = [r for r in rows if r["salary"] <= max_salary]
    rows.sort(key=lambda r: r[sort_by], reverse=True)
    rows = rows[:limit]

    if not rows:
        typer.echo("No DFS salaries are posted right now.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps({"site": SITE_NAMES[site], "players": rows}))
    else:
        dfs_table(rows, site=SITE_NAMES[site], sort_by=sort_by)


def _load_dfs_players() -> tuple[list[dict], list[dict]]:
    """The DFS page's ``const data`` is a list of players, not a dict, so it
    can't go through ``load_page_data``."""
    html = fetch_page(DFS_WEEKLY_PAGE, ttl=CACHE_TTL_INSEASON, require="const data")
    players = extract_const_assignment(html, "data")
    udk = parse_js_assignment(html, "window.udk.data") or {}
    return (players if isinstance(players, list) else []), (udk.get("projections") or [])

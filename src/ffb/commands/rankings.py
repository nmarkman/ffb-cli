import json
from collections import defaultdict

import typer

from ..api.client import get_client, AuthExpiredError
from ..api.endpoints import UDK_PROJECTIONS
from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_PROJECTIONS, SCORING_FORMATS, DEFAULT_SCORING, VALID_POSITIONS
from ..display.tables import rankings_table, console

# Points per stat by scoring format
POINTS_CONFIG = {
    "HALF": {"pass_yd": 0.04, "pass_td": 4, "int": -2, "rush_yd": 0.1, "rush_td": 6, "rec": 0.5, "rec_yd": 0.1, "rec_td": 6, "fum": -2},
    "PPR":  {"pass_yd": 0.04, "pass_td": 4, "int": -2, "rush_yd": 0.1, "rush_td": 6, "rec": 1.0, "rec_yd": 0.1, "rec_td": 6, "fum": -2},
    "STD":  {"pass_yd": 0.04, "pass_td": 4, "int": -2, "rush_yd": 0.1, "rush_td": 6, "rec": 0.0, "rec_yd": 0.1, "rec_td": 6, "fum": -2},
}


def _calc_points(proj: dict, scoring_key: str) -> float:
    cfg = POINTS_CONFIG.get(scoring_key, POINTS_CONFIG["HALF"])
    return (
        _num(proj.get("passing_yards")) * cfg["pass_yd"]
        + _num(proj.get("passing_touchdowns")) * cfg["pass_td"]
        + _num(proj.get("interceptions_thrown")) * cfg["int"]
        + _num(proj.get("rushing_yards")) * cfg["rush_yd"]
        + _num(proj.get("rushing_touchdowns")) * cfg["rush_td"]
        + _num(proj.get("receptions")) * cfg["rec"]
        + _num(proj.get("receiving_yards")) * cfg["rec_yd"]
        + _num(proj.get("receiving_touchdowns")) * cfg["rec_td"]
        + _num(proj.get("fumbles_lost")) * cfg["fum"]
    )


def _num(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _fetch_projections(scoring: str) -> list[dict]:
    scoring_key = SCORING_FORMATS.get(scoring, scoring.upper())
    cache_key = f"projections_{scoring_key}"
    cached = get_cached(cache_key, CACHE_TTL_PROJECTIONS)
    if cached:
        return cached

    client = get_client(require_auth=True)
    resp = client.get(UDK_PROJECTIONS, params={"scoring": scoring_key})
    outer = resp.json()

    # API returns {"json": "<double-encoded JSON string>"}
    raw_json = outer.get("json", outer)
    if isinstance(raw_json, str):
        import json as json_mod
        inner = json_mod.loads(raw_json)
    else:
        inner = raw_json

    raw_projs = inner.get("projections", [])
    tiers_data = inner.get("tiers", {})

    # Average projections across analysts for each player
    by_player: dict[str, list[dict]] = defaultdict(list)
    player_meta: dict[str, dict] = {}
    for p in raw_projs:
        pid = p.get("player_id", "")
        by_player[pid].append(p)
        if pid not in player_meta:
            player_meta[pid] = {
                "player_name": p.get("name", ""),
                "position": p.get("fantasy_position", ""),
                "team": p.get("team", ""),
                "bye_week": p.get("bye_week", ""),
            }

    stat_fields = [
        "passing_yards", "passing_touchdowns", "interceptions_thrown",
        "rushing_yards", "rushing_touchdowns",
        "receptions", "receiving_yards", "receiving_touchdowns",
        "fumbles_lost",
    ]

    players = []
    for pid, entries in by_player.items():
        meta = player_meta[pid]
        # Average stats across analysts
        avg = {}
        for field in stat_fields:
            vals = [_num(e.get(field)) for e in entries]
            avg[field] = sum(vals) / len(vals) if vals else 0.0

        points = _calc_points(avg, scoring_key)
        players.append({
            "player_id": pid,
            "player_name": meta["player_name"],
            "position": meta["position"],
            "team": meta["team"],
            "bye_week": meta["bye_week"],
            "points": round(points, 1),
            "pass_yds": round(avg["passing_yards"], 1),
            "pass_tds": round(avg["passing_touchdowns"], 1),
            "ints": round(avg["interceptions_thrown"], 1),
            "rush_yds": round(avg["rushing_yards"], 1),
            "rush_tds": round(avg["rushing_touchdowns"], 1),
            "receptions": round(avg["receptions"], 1),
            "rec_yds": round(avg["receiving_yards"], 1),
            "rec_tds": round(avg["receiving_touchdowns"], 1),
        })

    # Sort by points descending, assign overall rank
    players.sort(key=lambda p: -p["points"])
    for i, p in enumerate(players, 1):
        p["rank"] = i

    # Assign tiers per position using tier breakpoints
    _assign_tiers(players, tiers_data, scoring_key)

    set_cached(cache_key, players)
    return players


def _assign_tiers(players: list[dict], tiers_data: dict, scoring_key: str) -> None:
    """Assign tier numbers based on tier breakpoint data."""
    # Group by position
    by_pos: dict[str, list[dict]] = defaultdict(list)
    for p in players:
        by_pos[p["position"]].append(p)

    # Tier keys use format like "QB.PPR", "RB.HALF", etc.
    scoring_map = {"HALF": "HALF", "PPR": "PPR", "STD": "STD"}
    tier_scoring = scoring_map.get(scoring_key, "HALF")

    for pos, pos_players in by_pos.items():
        tier_key = f"{pos}.{tier_scoring}"
        breakpoints = tiers_data.get(tier_key, [])
        if not breakpoints or not pos_players:
            for p in pos_players:
                p["tier"] = 1
            continue

        # Breakpoints are fractional values (1.0 = top, 0.0 = bottom)
        # They define tier boundaries as fraction of top player's points
        max_pts = pos_players[0]["points"] if pos_players else 1
        if max_pts <= 0:
            for p in pos_players:
                p["tier"] = 1
            continue

        for p in pos_players:
            frac = p["points"] / max_pts if max_pts > 0 else 0
            tier = 1
            for t_idx, threshold in enumerate(breakpoints):
                if frac < threshold:
                    tier = t_idx + 1
            p["tier"] = tier


def rankings_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(VALID_POSITIONS)})"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    limit: int = typer.Option(25, "-n", "--limit", help="Max results"),
    tier: int = typer.Option(None, "--tier", help="Filter by tier"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """View player rankings by position and scoring format. Requires login.

    \b
    Shows ranked players with tier, projected points, and bye week.

    \b
    SCORING FORMATS: half (default), ppr, standard
    POSITIONS:       QB, RB, WR, TE, K, DST

    \b
    EXAMPLES:
      ffb rankings                     # all positions, half-PPR
      ffb rankings QB -s ppr -n 10     # top 10 QBs, PPR scoring
      ffb rankings RB --tier 1         # tier 1 RBs only
      ffb rankings WR --json           # JSON output
    """
    try:
        players = _fetch_projections(scoring)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    if position:
        players = [p for p in players if p.get("position", "").upper() == position.upper()]
        # Re-rank within position
        for i, p in enumerate(players, 1):
            p["rank"] = i

    if tier is not None:
        players = [p for p in players if p.get("tier") == tier]

    players = players[:limit]

    if not players:
        typer.echo("No rankings found for the given filters.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(players))
    else:
        rankings_table(players, scoring)

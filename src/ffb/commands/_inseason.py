"""Shared data layer for the in-season FootClan tools.

The FootClan pages embed the current week's data inline (no REST endpoint), so
every command here is a page scrape plus a pure transform. The transforms are
plain functions over lists of dicts so the offline tests can feed fixtures.

Analyst ids follow the site's own mapping (ffb-udk.js `analystName`):
1 = Andy, 2 = Jason, 3 = Mike. Consensus ranks mirror the site: average each
player's stat line across the analysts who projected him, score it, and sort;
each analyst's rank is the sort order of that analyst's own score.
"""
from __future__ import annotations

from collections import defaultdict

import typer

from ..api.dynasty_scrape import extract_const_assignment, parse_js_assignment
from ..config import CACHE_TTL_INSEASON
from .rankings import _calc_points, _num
from ._scrape import fetch_page

ANALYSTS = {"1": "andy", "2": "jason", "3": "mike"}
ANALYST_NAMES = ("andy", "jason", "mike")

FLEX_POSITIONS = ("RB", "WR", "TE")

# The site stores team defenses as position "D". Accept the usual spellings.
_POSITION_ALIASES = {"DST": "D", "D/ST": "D", "DEF": "D", "D": "D"}

STAT_FIELDS = (
    "passing_yards", "passing_touchdowns", "interceptions_thrown",
    "rushing_yards", "rushing_touchdowns",
    "receptions", "receiving_yards", "receiving_touchdowns",
    "fumbles_lost",
)


def normalize_position(position: str | None, allowed: tuple[str, ...]) -> str | None:
    """Uppercase + alias a position argument, exiting cleanly if it isn't one
    of ``allowed`` (which uses the site's "D" for defenses)."""
    if not position:
        return None
    pos = _POSITION_ALIASES.get(position.upper(), position.upper())
    if pos not in allowed:
        shown = ", ".join("DST" if p == "D" else p for p in allowed)
        typer.echo(f"Unknown position '{position}'. Valid: {shown}.", err=True)
        raise typer.Exit(1)
    return pos


def validate_pass_td(pass_td: int) -> bool:
    if pass_td not in (4, 6):
        typer.echo(f"--pass-td must be 4 or 6, not {pass_td}.", err=True)
        raise typer.Exit(1)
    return True


def display_position(pos: str) -> str:
    return "DST" if pos == "D" else pos


# ---------------------------------------------------------------------------
# Page loaders
# ---------------------------------------------------------------------------

def load_page_data(path: str) -> tuple[dict, list[dict]]:
    """Return (``const data``, ``window.udk.data.projections``) for a FootClan
    page. Either part may be empty; callers check what they need."""
    html = fetch_page(path, ttl=CACHE_TTL_INSEASON, require="const data")
    const = extract_const_assignment(html, "data")
    udk = parse_js_assignment(html, "window.udk.data") or {}
    projections = udk.get("projections") if isinstance(udk, dict) else None
    return (const if isinstance(const, dict) else {}), (projections or [])


def load_tool_data(path: str, tool: str) -> dict:
    """Return ``window.tool.<tool>.data`` from a FootClan page, exiting with a
    clear message if the page no longer carries it."""
    html = fetch_page(path, ttl=CACHE_TTL_INSEASON, require=f"window.tool.{tool}.data")
    data = parse_js_assignment(html, f"window.tool.{tool}.data")
    if data is None:
        typer.echo(
            f"Could not find the {tool} data on {path}. The tool may be out of "
            "season or the page layout may have changed.",
            err=True,
        )
        raise typer.Exit(1)
    return data


# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

def matchup(team: str, week: int, games: dict) -> str:
    """'vs KC' / '@ KC' for a team's game that week, 'BYE' if it has none."""
    if not team:
        return "-"
    game = (games or {}).get(f"{team}{week}")
    if not game:
        return "BYE"
    if game.get("home_team") == team:
        return f"vs {game.get('away_team', '')}"
    return f"@ {game.get('home_team', '')}"


# ---------------------------------------------------------------------------
# Weekly / ROS consensus rankings (stat projections -> points -> ranks)
# ---------------------------------------------------------------------------

def score_line(stats: dict, scoring_key: str, pass_td: int = 4) -> float:
    """Fantasy points for a stat line. ``pass_td`` lets QBs use 6-point
    passing TDs (the site's default view) on top of the CLI's 4-point formats."""
    return _calc_points(stats, scoring_key) + (pass_td - 4) * _num(stats.get("passing_touchdowns"))


def consensus_rankings(rows: list[dict], scoring_key: str, positions: tuple[str, ...],
                       *, pass_td: int = 4) -> list[dict]:
    """Collapse one-row-per-analyst stat projections into consensus rankings.

    Every player gets ``points`` (the mean of the analysts' scores), a ``rank``
    by that consensus, and ``andy_rank`` / ``jason_rank`` / ``mike_rank`` from
    each analyst's own score. Ranks are computed across all ``positions``
    together, so pass one position for positional ranks or the FLEX trio for
    flex ranks. Mirrors ffb-udk.js exactly (verified against the rendered
    tables): an all-zero row still counts as that analyst's projection, and an
    analyst with no row scores 0 for his own ranking but is left out of the mean.
    """
    by_player: dict[str, dict] = {}
    analyst_lines: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in rows:
        pos = (r.get("fantasy_position") or "").upper()
        if pos not in positions:
            continue
        pid = str(r.get("player_id", ""))
        analyst = ANALYSTS.get(str(r.get("analyst_id")))
        if not pid or not analyst:
            continue
        analyst_lines[pid][analyst] = {f: _num(r.get(f)) for f in STAT_FIELDS}
        by_player.setdefault(pid, r)

    players = []
    for pid, lines in analyst_lines.items():
        meta = by_player[pid]
        scores = {a: score_line(lines[a], scoring_key, pass_td) for a in lines}
        player = {
            "player_id": pid,
            "name": meta.get("name", ""),
            "position": (meta.get("fantasy_position") or "").upper(),
            "team": meta.get("team", "") or "",
            "points": round(sum(scores.values()) / len(scores), 1),
            "injury_status": meta.get("injury_status"),
        }
        for a in ANALYST_NAMES:
            player[f"{a}_points"] = round(scores[a], 1) if a in scores else None
        player["_avg"] = {f: sum(l[f] for l in lines.values()) / len(lines) for f in STAT_FIELDS}
        player["_scores"] = scores
        players.append(player)

    for a in ANALYST_NAMES:
        players.sort(key=lambda p: p["_scores"].get(a, 0.0), reverse=True)
        for i, p in enumerate(players, 1):
            p[f"{a}_rank"] = i
    players.sort(key=lambda p: sum(p["_scores"].values()) / len(p["_scores"]), reverse=True)
    for i, p in enumerate(players, 1):
        p["rank"] = i
        del p["_scores"]
    return players


def simple_rankings(rank_rows: list[dict], projections: list[dict]) -> list[dict]:
    """D/ST and K ranks. The site publishes these as already-ranked rows with
    per-analyst ranks; points come from the matching ``simpleProjections`` row."""
    points = {str(p.get("player_id")): _num(p.get("points")) for p in projections or []}
    opp = {str(p.get("player_id")): p.get("upcoming_game_opponent") for p in projections or []}
    rows = []
    for r in rank_rows or []:
        pid = str(r.get("player_id", ""))
        rows.append({
            "player_id": pid,
            "name": r.get("name", ""),
            "position": (r.get("fantasy_position") or "").upper(),
            "team": r.get("team", "") or "",
            "points": round(points.get(pid, 0.0), 1),
            "rank": _rank_value(r.get("consensus")),
            "andy_rank": _rank_value(r.get("andy")),
            "jason_rank": _rank_value(r.get("jason")),
            "mike_rank": _rank_value(r.get("mike")),
            "opponent": opp.get(pid),
            "injury_status": None,
        })
    rows.sort(key=lambda p: (p["rank"] is None, p["rank"] or 0))
    return rows


def _rank_value(val) -> int | None:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Waiver wire
# ---------------------------------------------------------------------------

def waiver_rankings(rows: list[dict]) -> list[dict]:
    """Waiver ranks re-sequenced the way the site does: sort by each of the
    consensus / Andy / Jason / Mike values and assign 1..n. A blank analyst
    value means that analyst didn't list the player, so it sorts last."""
    out = []
    for r in rows or []:
        out.append({
            "player_id": str(r.get("player_id", "")),
            "name": r.get("name", ""),
            "position": (r.get("fantasy_position") or "").upper(),
            "team": r.get("team", "") or "",
            "bye_week": r.get("bye_week", ""),
            "faab": faab_range(r.get("faab_low"), r.get("faab_high")),
            "faab_low": _rank_value(r.get("faab_low")),
            "faab_high": _rank_value(r.get("faab_high")),
            "stash": r.get("pickup_type") == "stash",
            "_raw": {k: _rank_value(r.get(k)) for k in ("consensus", *ANALYST_NAMES)},
        })
    for key in ("consensus", *ANALYST_NAMES):
        out.sort(key=lambda p: (p["_raw"][key] is None, p["_raw"][key] or 0))
        for i, p in enumerate(out, 1):
            p["rank" if key == "consensus" else f"{key}_rank"] = (
                i if p["_raw"][key] is not None else None
            )
    out.sort(key=lambda p: p["rank"] or 10**6)
    for p in out:
        del p["_raw"]
    return out


def faab_range(low, high) -> str:
    """Format a suggested FAAB range the way the site does ("5-15%")."""
    lo, hi = _rank_value(low) or 0, _rank_value(high) or 0
    if hi > 0:
        return f"{lo}-{hi}%"
    if lo > 0:
        return f"{lo}%"
    return "-"


# ---------------------------------------------------------------------------
# Vegas / weather
# ---------------------------------------------------------------------------

def vegas_games(odds: list[dict], weather: dict) -> list[dict]:
    """One row per game with spread, total and each side's implied points
    (total / 2 - spread / 2, the same formula the start/sit tool uses)."""
    games = []
    for g in odds or []:
        total = _opt(g.get("over_under"))
        home_spread = _opt(g.get("home_point_spread"))
        away, home = g.get("away_team_key", ""), g.get("home_team_key", "")
        implied_home = implied_away = None
        if total is not None and home_spread is not None:
            implied_home = round(total / 2 - home_spread / 2, 2)
            implied_away = round(total / 2 + home_spread / 2, 2)
        wx = (weather or {}).get(home) or {}
        games.append({
            "date": g.get("date"),
            "away": away,
            "home": home,
            "home_spread": home_spread,
            "over_under": total,
            "away_implied": implied_away,
            "home_implied": implied_home,
            "status": g.get("status"),
            "weather": _weather(wx),
        })
    games.sort(key=lambda g: g["date"] or "")
    return games


def team_vegas(team: str, games: list[dict]) -> dict:
    """Spread / total / implied total for one team from ``vegas_games`` rows."""
    for g in games:
        if team == g["home"]:
            return {"spread": g["home_spread"], "over_under": g["over_under"],
                    "implied_total": g["home_implied"], "date": g["date"]}
        if team == g["away"]:
            spread = -g["home_spread"] if g["home_spread"] is not None else None
            return {"spread": spread, "over_under": g["over_under"],
                    "implied_total": g["away_implied"], "date": g["date"]}
    return {"spread": None, "over_under": None, "implied_total": None, "date": None}


def _weather(wx: dict) -> dict | None:
    if not wx:
        return None
    dome = (wx.get("stadium_type") or "") in ("Dome", "RetractableDome")
    return {
        "summary": wx.get("summary"),
        "temperature": _opt(wx.get("temperature")),
        "wind_mph": _opt(wx.get("wind_speed")),
        "precip_pct": round(_opt(wx.get("precip_probability")) * 100) if _opt(wx.get("precip_probability")) is not None else None,
        "stadium": wx.get("stadium_type"),
        "dome": dome,
    }


def _opt(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Stream Finder (defense vs position)
# ---------------------------------------------------------------------------

# Stream Finder row field stems per position.
STREAM_FIELDS = {
    "QB": "quarterback", "RB": "runningback", "WR": "wide_receiver",
    "TE": "tight_end", "K": "kicker", "D": "defense",
}


def defense_vs_position(rows: list[dict], position: str, *, through_week: int,
                        upcoming: list[int], games: dict, adjusted: bool = True) -> list[dict]:
    """Rank every team by how generous it is to ``position``, softest first,
    with the opponents it faces in the ``upcoming`` weeks. The opponent in a
    soft matchup is the stream: a defense that gives QBs the most makes its
    next opponent's QB a streaming option. For "D" the row team is the offense
    and the stat is points it surrenders to opposing defenses.

    Two measures, as on the site:
    - ``avg_allowed``: raw fantasy points allowed per game (FPA).
    - ``pae``: points allowed above expectation, i.e. FPA minus what those same
      opponents score at the position on average. Schedule-adjusted, so a
      defense isn't punished for facing good offenses. The site switches to it
      after Week 2; ``adjusted`` picks which one ranks the table.
    Ported from ffb-udk.js ``calcAvgPtsScored`` / ``calcAdjustedMatchupRanks``.
    """
    stem = STREAM_FIELDS[position]
    field = f"fan_duel_{stem}_fantasy_points_allowed"

    def played(r, w):
        return w <= through_week and r.get(f"week_{w}_opponent") and _opt(r.get(f"week_{w}_{field}")) is not None

    # How much each offense scores at the position per game: the points every
    # defense it faced allowed that week.
    scored: dict[str, list[float]] = defaultdict(list)
    for r in rows or []:
        for w in range(1, through_week + 1):
            if played(r, w):
                scored[r[f"week_{w}_opponent"]].append(_opt(r.get(f"week_{w}_{field}")))
    offense_avg = {t: sum(v) / len(v) for t, v in scored.items() if v}

    out = []
    for r in rows or []:
        team = r.get("team", "")
        allowed, expected = [], []
        for w in range(1, through_week + 1):
            if not played(r, w):
                continue
            allowed.append(_opt(r.get(f"week_{w}_{field}")))
            expected.append(offense_avg.get(r[f"week_{w}_opponent"], 0.0))
        if not allowed:
            continue
        out.append({
            "team": team,
            "name": r.get("name", ""),
            "games": len(allowed),
            "avg_allowed": round(sum(allowed) / len(allowed), 1),
            "pae": round((sum(allowed) - sum(expected)) / len(allowed), 1),
            "total_allowed": round(sum(allowed), 1),
            "upcoming": {str(w): _upcoming_cell(team, w, games) for w in upcoming},
        })
    key = "pae" if adjusted else "avg_allowed"
    out.sort(key=lambda r: r[key], reverse=True)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


def _upcoming_cell(team: str, week: int, games: dict) -> str:
    game = (games or {}).get(f"{team}{week}")
    if not game:
        return "BYE"
    if game.get("home_team") == team:
        return game.get("away_team", "")
    return f"@{game.get('home_team', '')}"


def completed_through(rows: list[dict]) -> int:
    """Last week with any recorded opponent in the Stream Finder rows."""
    last = 0
    for r in rows or []:
        for w in range(1, 23):
            if r.get(f"week_{w}_opponent"):
                last = max(last, w)
    return last

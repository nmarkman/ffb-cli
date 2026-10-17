"""ffb start-sit, the FootClan "Who Should I Start?" tool.

The site answers start/sit client-side: it loads the week's analyst
projections, D/ST + K ranks and Vegas lines into the page and picks the player
with the highest projected score (ties broken by consensus rank). The
`start-sit/save_query` REST call it makes only logs the search, so this command
reproduces the comparison from the same page data.
"""
from __future__ import annotations

import json
from typing import Annotated

import typer
from thefuzz import fuzz

from ..api.endpoints import FOOTCLAN_START_SIT_PAGE
from ..config import DEFAULT_SCORING
from ..display.tables import console, startsit_table
from ._inseason import load_page_data, team_vegas, validate_pass_td, vegas_games
from .players import _fetch_player_data
from .rankings import validate_scoring
from .weekly import load_weekly

MATCH_THRESHOLD = 70


def build_pool(scoring: str, pass_td: int = 4) -> tuple[int, list[dict], dict]:
    """Every rankable player this week (positional ranks) plus the page data."""
    page = load_page_data(FOOTCLAN_START_SIT_PAGE)
    pool: list[dict] = []
    week = 0
    for pos in ("QB", "RB", "WR", "TE", "D", "K"):
        week, rows, _ = load_weekly(pos, scoring, page, pass_td=pass_td)
        pool.extend(rows)
    return week, pool, page[0]


_DEFENSE_WORDS = {"dst", "d/st", "def", "defense", "d"}


def _name_score(query: str, name: str) -> int:
    """Fuzzy name score. partial_ratio only counts for queries long enough that
    a substring hit means something ("puka" -> "Puka Nacua"), so a short
    or unrelated query can't land on an arbitrary long name."""
    score = fuzz.token_sort_ratio(query, name)
    if len(query) >= 4:
        score = max(score, fuzz.partial_ratio(query, name))
    return score


def _defense_matches(query: str, p: dict) -> bool:
    """A defense matches on its team code, nickname or city ("KC", "Chiefs",
    "Kansas City DST"), never on a fuzzy hit against a player's name."""
    words = [w for w in query.replace("/", " ").split() if w not in _DEFENSE_WORDS]
    if not words:
        return False
    name = p["name"].lower()
    nickname = name.split()[-1]
    return " ".join(words) in (p["team"].lower(), nickname, name, name.rsplit(" ", 1)[0])


def resolve(query: str, pool: list[dict]) -> tuple[dict | None, int]:
    """Best match for a name in this week's ranked pool, with its score.
    Ties go to the higher-projected player, so a bare last name lands on the
    relevant one. Defenses match exactly (score 100) or not at all."""
    q = query.lower().strip()
    for p in pool:
        if p["position"] == "DST" and _defense_matches(q, p):
            return p, 100
    best, best_key = None, (0, 0.0)
    for p in pool:
        if p["position"] == "DST":
            continue
        key = (_name_score(q, p["name"].lower()), p.get("points") or 0.0)
        if key > best_key:
            best, best_key = p, key
    if best_key[0] < MATCH_THRESHOLD:
        return None, 0
    return best, best_key[0]


def is_exact(query: str, player: dict | None) -> bool:
    """A full-name hit, as opposed to a partial ("Jefferson") that could mean
    someone else."""
    return player is not None and fuzz.token_sort_ratio(query.lower().strip(), player["name"].lower()) >= 90


def directory_match(query: str, directory: list[dict], pool: list[dict]) -> tuple[dict | None, int]:
    """Best rostered player in the full directory who is NOT in this week's
    pool (on bye, injured, or not projected), with its score."""
    q = query.lower().strip()
    in_pool = {p["name"].lower() for p in pool}
    best, best_score = None, 0
    for p in directory:
        name = (p.get("name") or "").lower()
        # College prospects and free agents can't be this week's answer.
        if not name or not p.get("team") or p.get("path") == "college" or name in in_pool:
            continue
        score = _name_score(q, name)
        if score > best_score:
            best, best_score = p, score
    return (best, best_score) if best_score >= 85 else (None, 0)


def unavailable(player: dict, week: int, schedule: dict) -> dict:
    """Row for a directory player with no projection this week: BYE if his
    team has no game, otherwise NO PROJ (injured, inactive, not projected)."""
    team = player.get("team") or ""
    on_bye = bool(team) and f"{team}{week}" not in schedule
    return {
        "name": player.get("name", ""),
        "position": (player.get("pos") or player.get("position") or "").upper(),
        "team": team,
        "matchup": "BYE" if on_bye else "-",
        "points": None,
        "rank": None,
        "verdict": "BYE" if on_bye else "NO PROJ",
    }


def compare(players: list[dict], games: list[dict]) -> list[dict]:
    """Attach Vegas context and order best-first, flagging the top as START."""
    out = []
    for p in players:
        row = {k: p.get(k) for k in (
            "name", "position", "team", "matchup", "points", "rank",
            "andy_rank", "jason_rank", "mike_rank", "injury_status")}
        row.update(team_vegas(p["team"], games))
        out.append(row)
    out.sort(key=lambda r: (-(r["points"] or 0), r["rank"] or 10**6))
    for i, r in enumerate(out):
        r["verdict"] = "START" if i == 0 else "SIT"
    return out


def startsit_command(
    players: Annotated[list[str], typer.Argument(help="2-4 player names to compare")],
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring: half, ppr, standard"),
    pass_td: int = typer.Option(4, "--pass-td", help="Points per passing TD: 4 or 6 (the site's default view uses 6)"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Compare 2-4 players for this week's start/sit decision. Requires login.

    \b
    Uses the FootClan weekly projections: the player with the most projected
    points gets START, with consensus and per-analyst positional ranks, the
    matchup, spread, over/under and implied team total for context. Names are
    fuzzy-matched; defenses match on team code, nickname or city ("KC",
    "Chiefs DST"), so a bare city resolves to the defense. A player on bye or
    without a projection is listed as BYE / NO PROJ instead of being swapped
    for a similar name; a last name that could mean a player on bye asks for
    the full name. In-season only.

    \b
    JSON: {"available", "week", "scoring", "start", "players": [... "verdict":
    START | SIT | BYE | NO PROJ ...]}; offseason returns {"available": false}.

    \b
    EXAMPLES:
      ffb start-sit "Ja'Marr Chase" "CeeDee Lamb"
      ffb start-sit "Josh Allen" "Jalen Hurts" "Lamar Jackson"
      ffb start-sit "Chiefs DST" "Bills DST" --json
      ffb start-sit "Bijan Robinson" "Puka Nacua" -s ppr
      ffb start-sit "Josh Allen" "Lamar Jackson" --pass-td 6
    """
    if len(players) < 2 or len(players) > 4:
        typer.echo("Provide 2-4 player names to compare.", err=True)
        raise typer.Exit(1)
    scoring = validate_scoring(scoring)

    validate_pass_td(pass_td)
    week, pool, const = build_pool(scoring, pass_td)
    if not pool:
        msg = "Start/Sit has no weekly projections right now (offseason or between weeks)."
        if output_json:
            console.print_json(json.dumps({"available": False, "reason": msg}))
        else:
            typer.echo(msg)
        raise typer.Exit(0)

    chosen, out, unknown, ambiguous = [], [], [], []
    schedule = const.get("allGames") or {}
    for name in players:
        match, score = resolve(name, pool)
        other, other_score = (None, 0)
        # Short of a full-name pool hit, check the whole directory: a player
        # who isn't playing this week may be the one meant.
        if not is_exact(name, match):
            other, other_score = directory_match(name, _fetch_player_data(), pool)
        other_on_bye = other is not None and f"{other.get('team')}{week}" not in schedule
        if other is not None and (match is None or other_score > score):
            row = unavailable(other, week, schedule)
            if row not in out:
                out.append(row)
        elif other is not None and other_score == score and other_on_bye:
            # A tie only means something when the other player is on bye: a
            # bare "Allen" shouldn't stop on Josh Allen's unprojected backup,
            # but "Jefferson" with Justin Jefferson on bye really is unclear.
            ambiguous.append(f"'{name}' could be {match['name']} ({match['team']}) "
                             f"or {other.get('name')} ({other.get('team')}, on bye)")
        elif match is not None:
            if match not in chosen:
                chosen.append(match)
        else:
            unknown.append(name)
    if unknown:
        typer.echo(f"Couldn't find a player matching: {', '.join(unknown)}.", err=True)
        raise typer.Exit(1)
    if ambiguous:
        typer.echo("Ambiguous name. Use the full name:\n  " + "\n  ".join(ambiguous), err=True)
        raise typer.Exit(1)
    if not chosen:
        typer.echo("None of those players have a projection this week (bye or out).", err=True)
        raise typer.Exit(1)
    if len(chosen) + len(out) < 2:
        typer.echo("Those names resolve to the same player. Provide 2-4 different players.", err=True)
        raise typer.Exit(1)

    games = vegas_games(const.get("vegas") or [], const.get("weather") or {})
    result = compare(chosen, games) + out
    if output_json:
        console.print_json(json.dumps({
            "available": True, "week": week, "scoring": scoring,
            "start": result[0]["name"], "players": result,
        }))
    else:
        startsit_table(result, week=week, scoring=scoring)

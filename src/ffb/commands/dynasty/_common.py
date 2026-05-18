"""Shared helpers used by all `ffb dynasty *` subcommands.

Centralizes: fetching a dynasty page, projecting the analyst rows into per-player
averages, computing fantasy points, and bailing politely on missing data.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import typer

from ...api.client import AuthExpiredError, FFBClient, get_client
from ...api.dynasty_scrape import num, parse_dynasty_page_data, parse_js_assignment
from ...cache.store import get_cached, set_cached

# Points per stat by scoring format (matches src/ffb/commands/rankings.py).
POINTS_CONFIG = {
    "HALF": {"pass_yd": 0.04, "pass_td": 4, "int": -2, "rush_yd": 0.1, "rush_td": 6, "rec": 0.5, "rec_yd": 0.1, "rec_td": 6, "fum": -2},
    "PPR":  {"pass_yd": 0.04, "pass_td": 4, "int": -2, "rush_yd": 0.1, "rush_td": 6, "rec": 1.0, "rec_yd": 0.1, "rec_td": 6, "fum": -2},
    "STD":  {"pass_yd": 0.04, "pass_td": 4, "int": -2, "rush_yd": 0.1, "rush_td": 6, "rec": 0.0, "rec_yd": 0.1, "rec_td": 6, "fum": -2},
}

CACHE_TTL_DYNASTY_PAGE = 3600  # 1 hour. Pages are big; refetching is expensive.

ANALYSTS = {"andy": "1", "jason": "2", "mike": "3"}


def calc_points(proj: dict, scoring_key: str) -> float:
    cfg = POINTS_CONFIG.get(scoring_key, POINTS_CONFIG["HALF"])
    return (
        num(proj.get("passing_yards")) * cfg["pass_yd"]
        + num(proj.get("passing_touchdowns")) * cfg["pass_td"]
        + num(proj.get("interceptions_thrown")) * cfg["int"]
        + num(proj.get("rushing_yards")) * cfg["rush_yd"]
        + num(proj.get("rushing_touchdowns")) * cfg["rush_td"]
        + num(proj.get("receptions")) * cfg["rec"]
        + num(proj.get("receiving_yards")) * cfg["rec_yd"]
        + num(proj.get("receiving_touchdowns")) * cfg["rec_td"]
        + num(proj.get("fumbles_lost")) * cfg["fum"]
    )


def fetch_dynasty_page(path: str, *, ttl: int = CACHE_TTL_DYNASTY_PAGE) -> str:
    """Fetch a dynasty page HTML, returning the body. Cached on disk by path.

    Raises typer.Exit(1) on auth failure with a clear message."""
    cache_key = f"dynasty_page:{path}"
    cached = get_cached(cache_key, ttl)
    if cached:
        return cached
    try:
        client: FFBClient = get_client(require_auth=True)
        html = client.get_page(path)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)
    set_cached(cache_key, html)
    return html


def load_dynasty_data(path: str) -> dict:
    """Fetch a dynasty page and return the parsed primary data object.

    Tries window.udk.data first, then window.tool.tradeAnalyzer.data, then a
    bare `const data = [...]` (used by production-profiles). Returns the dict
    or list, never None: bails with typer.Exit on parse failure."""
    html = fetch_dynasty_page(path)
    data = parse_dynasty_page_data(html)
    if data is None:
        typer.echo(
            f"Could not find embedded data on {path}. "
            "The page layout may have changed.",
            err=True,
        )
        raise typer.Exit(1)
    return data


def project_average(projections: list[dict], analyst_filter: str | None = None) -> list[dict]:
    """Reduce per-analyst rows into per-player averaged stats. If analyst_filter
    is one of {andy, jason, mike}, only that analyst's rows are used.

    Returns a list of dicts with averaged stat fields plus meta (name, position,
    team, bye_week, adp, adp_ppr, adp_half_ppr, adp_2qb)."""
    if analyst_filter:
        wanted_id = ANALYSTS.get(analyst_filter.lower())
        if wanted_id is None:
            typer.echo(f"Unknown analyst '{analyst_filter}'. Pick one of: andy, jason, mike.", err=True)
            raise typer.Exit(1)
        projections = [p for p in projections if str(p.get("analyst_id")) == wanted_id]

    by_player: dict[str, list[dict]] = defaultdict(list)
    meta: dict[str, dict] = {}
    for p in projections:
        pid = p.get("player_id", "")
        by_player[pid].append(p)
        if pid not in meta:
            meta[pid] = {
                "player_id": pid,
                "player_name": p.get("name", ""),
                "position": p.get("fantasy_position", ""),
                "team": p.get("team", ""),
                "bye_week": p.get("bye_week", ""),
                "adp": _opt_num(p.get("adp")),
                "adp_ppr": _opt_num(p.get("adp_ppr")),
                "adp_half_ppr": _opt_num(p.get("adp_half_ppr")),
                "adp_2qb": _opt_num(p.get("adp_2qb")),
                "experience": p.get("experience"),
                "birth_date": p.get("birth_date"),
            }

    stat_fields = [
        "passing_yards", "passing_touchdowns", "interceptions_thrown",
        "rushing_yards", "rushing_touchdowns",
        "receptions", "receiving_yards", "receiving_touchdowns",
        "fumbles_lost", "receiving_targets", "passing_attempts",
        "passing_completions", "rushing_attempts",
    ]

    out = []
    for pid, rows in by_player.items():
        avg = {}
        for f in stat_fields:
            vals = [num(r.get(f)) for r in rows]
            avg[f] = sum(vals) / len(vals) if vals else 0.0
        row = dict(meta[pid])
        row["analysts"] = len(rows)
        for f in stat_fields:
            row[f] = round(avg[f], 1)
        out.append(row)
    return out


def _opt_num(val: Any) -> float | None:
    """Convert a populated string-number to float; treat empty/None as None."""
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def output_json_or_table(rows: list[dict], table_fn, *, output_json: bool, console) -> None:
    """Single exit point. Print JSON to stdout or hand off to a table renderer."""
    if output_json:
        console.print_json(json.dumps(rows, default=str))
    else:
        table_fn(rows)


def parse_window_udk_attr(html: str, attr: str) -> Any | None:
    """Convenience for window.udk.<attr>. Returns parsed JSON or None."""
    return parse_js_assignment(html, f"window.udk.{attr}")

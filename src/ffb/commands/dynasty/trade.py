"""ffb dynasty trade , analyze trades using dynasty trade values.

Pattern mirrors src/ffb/commands/trade.py (redraft trade analyzer) but pulls
from /2026-dynasty-pass/trade-analyzer/ where the data uses dynasty pricing.
"""
from __future__ import annotations

import json
from typing import Optional

import typer
from thefuzz import fuzz

from ...api.dynasty_scrape import parse_js_assignment
from ...api.endpoints import DYNASTY_TRADE_ANALYZER_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import dynasty_trade_table


def _fetch_dynasty_values() -> list[dict]:
    html = fetch_dynasty_page(DYNASTY_TRADE_ANALYZER_PAGE)
    data = parse_js_assignment(html, "window.tool.tradeAnalyzer.data")
    if data is None:
        # Some seasons keep dynasty payload at window.udk.data; try that as fallback.
        data = parse_js_assignment(html, "window.udk.data")
    if data is None:
        typer.echo("Could not find trade-analyzer data on the dynasty page.", err=True)
        raise typer.Exit(1)

    # Offseason: dynastyProjections is populated; in-season: projections.
    players = data.get("dynastyProjections") or data.get("projections") or []
    if not players:
        typer.echo("No dynasty trade-value data available right now.", err=True)
        raise typer.Exit(1)

    out = []
    for p in players:
        out.append({
            "player_name": p.get("name", ""),
            "position": p.get("fantasy_position", ""),
            "team": p.get("team", ""),
            "rank": p.get("rank", 0),
            "value": float(p.get("fantasy_points") or p.get("value") or 0),
        })
    return out


def _find_player(query: str, values: list[dict]) -> Optional[dict]:
    """Fuzzy-match a player name. On score ties (common with short surname
    queries like 'Daniels' matching both 'Jayden Daniels' and 'CJ Daniels'),
    prefer the higher-value player, which is almost always the one the user
    meant."""
    scored: list[tuple[int, float, dict]] = []
    for v in values:
        n = v.get("player_name", "")
        if not n:
            continue
        score = max(fuzz.token_sort_ratio(query.lower(), n.lower()),
                    fuzz.partial_ratio(query.lower(), n.lower()))
        if score >= 60:
            scored.append((score, float(v.get("value") or 0), v))
    if not scored:
        return None
    scored.sort(key=lambda t: (-t[0], -t[1]))
    return scored[0][2]


def dynasty_trade_command(
    give: Optional[str] = typer.Option(None, "--give", help='Players to give (comma-separated)'),
    get: Optional[str] = typer.Option(None, "--get", help='Players to get (comma-separated)'),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Analyze a trade using dynasty trade values.

    \b
    Identical interface to `ffb trade` but pulls dynasty-priced values from
    /2026-dynasty-pass/trade-analyzer/. Positive net means the get side wins.

    \b
    EXAMPLES:
      ffb dynasty trade --give "Mahomes" --get "Daniels"
      ffb dynasty trade --give "Kelce, Henry" --get "McBride, Hampton"
      ffb dynasty trade                  # interactive
    """
    if give is None and get is None:
        give = typer.prompt("Players to give (comma-separated)")
        get = typer.prompt("Players to get (comma-separated)")

    values = _fetch_dynasty_values()

    give_names = [s.strip() for s in (give or "").split(",") if s.strip()]
    get_names = [s.strip() for s in (get or "").split(",") if s.strip()]

    give_players, get_players, missing = [], [], []
    for q in give_names:
        m = _find_player(q, values)
        (give_players if m else missing).append(m or q)
    for q in get_names:
        m = _find_player(q, values)
        (get_players if m else missing).append(m or q)
    missing = [m for m in missing if isinstance(m, str)]

    give_total = sum(p["value"] for p in give_players)
    get_total = sum(p["value"] for p in get_players)
    analysis = {
        "give_players": give_players,
        "get_players": get_players,
        "give_total": round(give_total, 1),
        "get_total": round(get_total, 1),
        "difference": round(get_total - give_total, 1),
        "missing": missing,
    }

    if output_json:
        console.print_json(json.dumps(analysis, default=str))
    else:
        dynasty_trade_table(analysis, label="Dynasty Trade Analysis")
        if missing:
            typer.echo(f"\nCouldn't match: {', '.join(missing)}", err=True)

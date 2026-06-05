import json
from collections import defaultdict

import typer
from thefuzz import fuzz

from ..api.client import get_client, AuthExpiredError
from ..api.dynasty_scrape import num, parse_js_assignment
from ..api.endpoints import TRADE_ANALYZER_PAGE
from ..display.tables import trade_table, console
from .rankings import _calc_points


def _values_from_global_blob(blob: dict) -> list[dict]:
    """Draft-phase shape: `projections` is the full window.udk.data-style dict
    (per-analyst rows under `projections.projections`). Average each player's
    stats across analysts and use half-PPR projected points as the trade value."""
    rows = blob.get("projections", [])
    by_player: dict[str, list[dict]] = defaultdict(list)
    meta: dict[str, dict] = {}
    for r in rows:
        pid = str(r.get("player_id", ""))
        by_player[pid].append(r)
        meta.setdefault(pid, {
            "name": r.get("name", ""),
            "fantasy_position": r.get("fantasy_position", ""),
            "team": r.get("team", ""),
        })

    stat_fields = [
        "passing_yards", "passing_touchdowns", "interceptions_thrown",
        "rushing_yards", "rushing_touchdowns",
        "receptions", "receiving_yards", "receiving_touchdowns", "fumbles_lost",
    ]
    out = []
    for pid, entries in by_player.items():
        avg = {f: sum(num(e.get(f)) for e in entries) / len(entries) for f in stat_fields}
        out.append({
            "player_name": meta[pid]["name"],
            "position": meta[pid]["fantasy_position"],
            "team": meta[pid]["team"],
            "value": round(_calc_points(avg, "HALF"), 1),
        })
    out.sort(key=lambda p: -p["value"])
    for i, p in enumerate(out, 1):
        p["rank"] = i
    return out


def _values_from_list(players: list) -> list[dict]:
    """In-season shape: a flat list of player dicts that already carry
    `fantasy_points`."""
    return [{
        "player_name": p.get("name", ""),
        "position": p.get("fantasy_position", ""),
        "team": p.get("team", ""),
        "rank": p.get("rank", 0),
        "value": num(p.get("fantasy_points")),
    } for p in players]


def _fetch_trade_values(client) -> list[dict]:
    """Scrape trade values from the trade analyzer page HTML.

    The `window.tool.tradeAnalyzer.data.projections` payload changes shape by
    season phase: a flat list of scored players in-season, or the full
    window.udk.data-style dict during the draft phase. Handle both, falling back
    to the in-season `dynastyProjections` list if needed."""
    html = client.get_page(TRADE_ANALYZER_PAGE)
    data = parse_js_assignment(html, "window.tool.tradeAnalyzer.data")
    if not isinstance(data, dict):
        typer.echo("Could not find trade analyzer data on page.", err=True)
        raise typer.Exit(1)

    projections = data.get("projections")
    if isinstance(projections, dict) and projections.get("projections"):
        result = _values_from_global_blob(projections)
    elif isinstance(projections, list) and projections:
        result = _values_from_list(projections)
    else:
        dyn = data.get("dynastyProjections")
        result = _values_from_list(dyn) if isinstance(dyn, list) else []

    if not result:
        typer.echo("No trade value data available.", err=True)
        raise typer.Exit(1)
    return result


def _find_player(query: str, values: list[dict]) -> dict | None:
    best_score = 0
    best_match = None
    for v in values:
        name = v.get("player_name", "")
        score = max(
            fuzz.token_sort_ratio(query.lower(), name.lower()),
            fuzz.partial_ratio(query.lower(), name.lower()),
        )
        if score > best_score:
            best_score = score
            best_match = v
    if best_score >= 60:
        return best_match
    return None


def trade_command(
    give: str = typer.Option(None, "--give", help='Players to give (comma-separated, e.g. "Mahomes, Kelce")'),
    get: str = typer.Option(None, "--get", help='Players to get (comma-separated, e.g. "Allen")'),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Analyze a trade using FFB trade values. Requires login.

    \b
    Compares trade value totals for each side and shows the net difference.
    Player names are fuzzy-matched, so partial names usually work.
    A positive net means the "get" side wins; negative means "give" side wins.

    \b
    Use --give and --get with comma-separated player names,
    or run with no flags for interactive prompts.

    \b
    EXAMPLES:
      ffb trade --give "Travis Kelce, CeeDee Lamb" --get "Ja'Marr Chase"
      ffb trade --give "Mahomes" --get "Allen" --json
      ffb trade                        # interactive: prompts for give/get players
    """
    try:
        client = get_client(require_auth=True)
        values = _fetch_trade_values(client)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    if not give or not get:
        give = typer.prompt("Players to give (comma-separated)")
        get = typer.prompt("Players to get (comma-separated)")

    give_names = [n.strip() for n in give.split(",") if n.strip()]
    get_names = [n.strip() for n in get.split(",") if n.strip()]

    give_players = []
    for name in give_names:
        player = _find_player(name, values)
        if not player:
            typer.echo(f"Could not find player: {name}", err=True)
            raise typer.Exit(1)
        give_players.append(player)

    get_players = []
    for name in get_names:
        player = _find_player(name, values)
        if not player:
            typer.echo(f"Could not find player: {name}", err=True)
            raise typer.Exit(1)
        get_players.append(player)

    give_total = sum(p["value"] for p in give_players)
    get_total = sum(p["value"] for p in get_players)

    analysis = {
        "give_players": give_players,
        "get_players": get_players,
        "give_total": give_total,
        "get_total": get_total,
        "difference": get_total - give_total,
    }

    if output_json:
        console.print_json(json.dumps(analysis))
    else:
        trade_table(analysis)

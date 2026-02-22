import json
import re

import typer
from thefuzz import fuzz

from ..api.client import get_client, AuthExpiredError
from ..api.endpoints import TRADE_ANALYZER_PAGE
from ..display.tables import trade_table, console


def _fetch_trade_values(client) -> list[dict]:
    """Scrape trade values from the trade analyzer page HTML."""
    html = client.get_page(TRADE_ANALYZER_PAGE)

    # Data is at: window.tool.tradeAnalyzer.data = {...};
    match = re.search(r'window\.tool\.tradeAnalyzer\.data\s*=\s*(\{)', html)
    if not match:
        typer.echo("Could not find trade analyzer data on page.", err=True)
        raise typer.Exit(1)

    # Brace-match to extract the full JSON object
    start = match.start(1)
    depth = 0
    for i, c in enumerate(html[start:]):
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        if depth == 0:
            raw = html[start:start + i + 1]
            break
    else:
        typer.echo("Could not parse trade analyzer data.", err=True)
        raise typer.Exit(1)

    data = json.loads(raw)

    # In-season: "projections" has data. Offseason: "dynastyProjections" has data.
    players = data.get("projections") or data.get("dynastyProjections") or []
    if not players:
        typer.echo("No trade value data available.", err=True)
        raise typer.Exit(1)

    # Normalize into a consistent format with "value" based on fantasy_points
    result = []
    for p in players:
        result.append({
            "player_name": p.get("name", ""),
            "position": p.get("fantasy_position", ""),
            "team": p.get("team", ""),
            "rank": p.get("rank", 0),
            "value": float(p.get("fantasy_points", 0)),
        })
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

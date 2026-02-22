import json
import re

import typer
from thefuzz import fuzz

from ..api.client import get_client, AuthExpiredError
from ..api.endpoints import TRADE_ANALYZER_PAGE
from ..display.tables import trade_table, console

app = typer.Typer(help="Trade analyzer.")


def _fetch_trade_values(client) -> list[dict]:
    """Scrape trade values from the trade analyzer page HTML."""
    html = client.get_page(TRADE_ANALYZER_PAGE)

    match = re.search(r"window\.tradeAnalyzerRankings\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if not match:
        typer.echo("Could not extract trade data from page.", err=True)
        raise typer.Exit(1)

    return json.loads(match.group(1))


def _find_player(query: str, values: list[dict]) -> dict | None:
    best_score = 0
    best_match = None
    for v in values:
        name = v.get("player_name", "")
        score = fuzz.token_sort_ratio(query.lower(), name.lower())
        if score > best_score:
            best_score = score
            best_match = v
    if best_score >= 60:
        return best_match
    return None


@app.callback(invoke_without_command=True)
def trade(
    ctx: typer.Context,
    give: str = typer.Option(None, "--give", help='Players to give (comma-separated, e.g. "Mahomes, Kelce")'),
    get: str = typer.Option(None, "--get", help='Players to get (comma-separated, e.g. "Allen")'),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Analyze a trade. Use --give and --get, or run without args for interactive mode."""
    try:
        client = get_client(require_auth=True)
        values = _fetch_trade_values(client)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    if not give or not get:
        # Interactive mode
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

    give_total = sum(p.get("value", 0) for p in give_players)
    get_total = sum(p.get("value", 0) for p in get_players)

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

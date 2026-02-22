import json

import typer
from thefuzz import fuzz

from ..api.client import get_client
from ..api.endpoints import PLAYER_SEARCH
from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_PLAYERS, VALID_POSITIONS
from ..display.tables import player_search_table, console

app = typer.Typer(help="Player search.")


def _fetch_player_data() -> list[dict]:
    cache_key = "player_search_data"
    cached = get_cached(cache_key, CACHE_TTL_PLAYERS)
    if cached:
        return cached

    client = get_client(require_auth=False)
    resp = client.get(PLAYER_SEARCH)
    raw = resp.json()
    # API returns {"error": "", "data": [...]}
    data = raw.get("data", raw) if isinstance(raw, dict) else raw
    set_cached(cache_key, data)
    return data


def _search_players(
    query: str, players: list[dict], position: str | None, team: str | None, limit: int
) -> list[dict]:
    results = []
    for p in players:
        name = p.get("name", "")
        if not name:
            continue

        pos = p.get("pos", "") or p.get("position", "")
        tm = p.get("team", "")

        if position and pos.upper() != position.upper():
            continue
        if team and tm.upper() != team.upper():
            continue

        score = max(
            fuzz.token_sort_ratio(query.lower(), name.lower()),
            fuzz.partial_ratio(query.lower(), name.lower()),
        )
        if score >= 55:
            results.append({
                "id": p.get("player_id"),
                "name": name,
                "position": pos,
                "team": tm,
                "score": score,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


@app.command()
def search(
    query: str = typer.Argument(help="Player name to search for"),
    position: str = typer.Option(None, "-p", "--position", help=f"Filter by position ({', '.join(VALID_POSITIONS)})"),
    team: str = typer.Option(None, "-t", "--team", help="Filter by team abbreviation"),
    limit: int = typer.Option(10, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search for players by name."""
    players = _fetch_player_data()
    results = _search_players(query, players, position, team, limit)

    if not results:
        typer.echo("No matching players found.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(results))
    else:
        player_search_table(results)

import json
import re
from html import unescape

import typer
from thefuzz import fuzz
from simple_term_menu import TerminalMenu

from ..api.client import get_client
from ..api.endpoints import PLAYER_SEARCH, WP_POSTS
from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_PLAYERS, VALID_POSITIONS
from ..display.tables import player_search_table, player_info_card, console

app = typer.Typer(help="""Search for NFL players by name. No login required.

\b
Uses fuzzy matching so partial or misspelled names work.
Results are ranked by match confidence (0-100%).
After results appear, use arrow keys to select a player for more info.

\b
EXAMPLES:
  ffb players search "mahomes"              # search, then select for info
  ffb players search "jefferson" -p WR      # filter by position
  ffb players search "smith" -t KC -n 5     # filter by team, limit results
  ffb players search "kelce" --json         # JSON output (no interactive menu)
  ffb players search "mahomes" -I           # table only, skip interactive menu
""")


def _strip_html(text: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", text))


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
                "status": p.get("status"),
                "score": score,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def _fetch_player_news(player_name: str, limit: int = 3) -> list[dict]:
    client = get_client(require_auth=False)
    resp = client.get(WP_POSTS, params={
        "search": player_name,
        "per_page": limit,
        "_fields": "title,date,link",
    })
    articles = []
    for post in resp.json():
        articles.append({
            "title": _strip_html(post.get("title", {}).get("rendered", "")),
            "date": post.get("date", "")[:10],
            "link": post.get("link", ""),
        })
    return articles


@app.command()
def search(
    query: str = typer.Argument(help="Player name to search for"),
    position: str = typer.Option(None, "-p", "--position", help=f"Filter by position ({', '.join(VALID_POSITIONS)})"),
    team: str = typer.Option(None, "-t", "--team", help="Filter by team abbreviation"),
    limit: int = typer.Option(10, "-n", "--limit", help="Max results"),
    no_interactive: bool = typer.Option(False, "-I", "--no-interactive", help="Skip interactive selection menu"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search for players by name using fuzzy matching. No login required.

    Shows results in a table, then lets you select a player with arrow keys
    to view their info card with recent news articles."""
    players = _fetch_player_data()
    results = _search_players(query, players, position, team, limit)

    if not results:
        typer.echo("No matching players found.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(results))
        return

    player_search_table(results)

    if no_interactive:
        return

    # Interactive selection menu
    menu_items = [
        f"{r['name']}  ({r['position']} - {r['team'] or '?'})" for r in results
    ]
    terminal_menu = TerminalMenu(
        menu_items,
        title="\nSelect a player for more info (Esc to quit):",
    )
    selection = terminal_menu.show()

    if selection is None:
        return

    selected = results[selection]
    console.print(f"\n[dim]Fetching info for {selected['name']}...[/dim]")
    articles = _fetch_player_news(selected["name"])
    console.print()
    player_info_card(selected, articles)

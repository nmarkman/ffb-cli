import json

import typer

from ..api.client import get_client, AuthExpiredError
from ..api.endpoints import UDK_PROJECTIONS
from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_PROJECTIONS, SCORING_FORMATS, DEFAULT_SCORING, VALID_POSITIONS
from ..display.tables import rankings_table, console

app = typer.Typer(help="View player rankings.")


def _fetch_projections(scoring: str) -> list[dict]:
    scoring_key = SCORING_FORMATS.get(scoring, scoring.upper())
    cache_key = f"projections_{scoring_key}"
    cached = get_cached(cache_key, CACHE_TTL_PROJECTIONS)
    if cached:
        return cached

    client = get_client(require_auth=True)
    resp = client.get(UDK_PROJECTIONS, params={"scoring": scoring_key})
    data = resp.json()

    # Normalize: API may return dict with positions as keys or flat list
    players = []
    if isinstance(data, dict):
        for pos_group in data.values():
            if isinstance(pos_group, list):
                players.extend(pos_group)
            elif isinstance(pos_group, dict):
                for inner in pos_group.values():
                    if isinstance(inner, list):
                        players.extend(inner)
    elif isinstance(data, list):
        players = data

    set_cached(cache_key, players)
    return players


@app.callback(invoke_without_command=True)
def rankings(
    ctx: typer.Context,
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(VALID_POSITIONS)})"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    limit: int = typer.Option(25, "-n", "--limit", help="Max results"),
    tier: int = typer.Option(None, "--tier", help="Filter by tier"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show player rankings by position and scoring format."""
    try:
        players = _fetch_projections(scoring)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    if position:
        players = [p for p in players if p.get("position", "").upper() == position.upper()]

    if tier is not None:
        players = [p for p in players if p.get("tier") == tier]

    # Sort by rank or points
    players.sort(key=lambda p: (p.get("rank") or 9999, -(p.get("points") or 0)))
    players = players[:limit]

    if not players:
        typer.echo("No rankings found for the given filters.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(players))
    else:
        rankings_table(players, scoring)

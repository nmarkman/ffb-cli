"""ffb flex, RB/WR/TE flex board."""
from __future__ import annotations

import json

import typer

from ..api.client import AuthExpiredError
from ..config import DEFAULT_SCORING
from ..display.tables import rankings_table, console
from .rankings import _fetch_projections

FLEX_POSITIONS = {"RB", "WR", "TE"}


def flex_command(
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    limit: int = typer.Option(50, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Flex (RB/WR/TE) draft board. Requires login.

    \b
    RB, WR, TE blended into one ranked list. QBs, kickers, and defenses excluded.

    \b
    EXAMPLES:
      ffb flex                     # top 50 flex options, half-PPR
      ffb flex -s ppr -n 100       # top 100, PPR
      ffb flex --json
    """
    try:
        base = _fetch_projections(scoring)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    players = [p for p in base if p.get("position", "").upper() in FLEX_POSITIONS]
    players.sort(key=lambda p: -p["points"])
    for i, p in enumerate(players, 1):
        p["rank"] = i

    players = players[:limit]
    if not players:
        typer.echo("No flex rankings available.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(players))
    else:
        rankings_table(players, f"{scoring} flex")

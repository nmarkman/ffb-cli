"""ffb top200, overall top-N draft board across all positions."""
from __future__ import annotations

import json

import typer

from ..api.client import AuthExpiredError
from ..config import DEFAULT_SCORING
from ..display.tables import rankings_table, enriched_rankings_table, console
from .rankings import _fetch_projections, validate_scoring


def top200_command(
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    limit: int = typer.Option(200, "-n", "--limit", help="Max results"),
    enrich: bool = typer.Option(False, "--enrich", help="Add analyst risk/upside/targets (and blurb in --json)"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Overall top-N draft board across all positions. Requires login.

    \b
    Same projection model as `ffb rankings`, but blended across every position
    so you can see the global draft pecking order at a glance.

    \b
    EXAMPLES:
      ffb top200                   # top 200, half-PPR
      ffb top200 -s ppr -n 100     # top 100, PPR
      ffb top200 --json
    """
    scoring = validate_scoring(scoring)
    try:
        players = _fetch_projections(scoring)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    players = players[:limit]
    if not players:
        typer.echo("No rankings available.")
        raise typer.Exit(0)

    if enrich:
        from ..api.udk_global import enrich_players
        enrich_players(players)

    if output_json:
        console.print_json(json.dumps(players))
    elif enrich:
        enriched_rankings_table(players, scoring)
    else:
        rankings_table(players, scoring)

import json

import typer

from ..api.client import AuthExpiredError
from ..config import SCORING_FORMATS, DEFAULT_SCORING, VALID_POSITIONS
from ..display.tables import projections_table, console
from .rankings import _fetch_projections

app = typer.Typer(help="View player projections.")


@app.callback(invoke_without_command=True)
def projections(
    ctx: typer.Context,
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(VALID_POSITIONS)})"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    week: int = typer.Option(None, "-w", "--week", help="Week number"),
    limit: int = typer.Option(25, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show detailed stat projections."""
    try:
        players = _fetch_projections(scoring)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    if position:
        players = [p for p in players if p.get("position", "").upper() == position.upper()]

    players.sort(key=lambda p: (p.get("rank") or 9999, -(p.get("points") or 0)))
    players = players[:limit]

    if not players:
        typer.echo("No projections found for the given filters.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(players))
    else:
        projections_table(players, scoring)

import json

import typer

from ..api.client import AuthExpiredError
from ..config import DEFAULT_SCORING, VALID_POSITIONS
from ..display.tables import projections_table, console
from .rankings import _fetch_projections


def projections_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(VALID_POSITIONS)})"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    week: int = typer.Option(None, "-w", "--week", help="Week number"),
    limit: int = typer.Option(25, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """View detailed stat projections by position. Requires login.

    \b
    Shows projected stats (passing, rushing, receiving yards/TDs, etc.)
    in a tabular format. Same data source as rankings but stat-focused.

    \b
    SCORING FORMATS: half (default), ppr, standard
    POSITIONS:       QB, RB, WR, TE, K, DST

    \b
    EXAMPLES:
      ffb projections QB               # QB stat projections
      ffb projections RB -s ppr -n 15  # top 15 RB projections, PPR
      ffb projections --json           # all positions, JSON output
    """
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

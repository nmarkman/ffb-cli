"""ffb superflex, blended draft board with QBs boosted for 2QB / superflex leagues."""
from __future__ import annotations

import copy
import json

import typer

from ..api.client import AuthExpiredError
from ..config import DEFAULT_SCORING
from ..display.tables import rankings_table, console
from .rankings import _fetch_projections, validate_scoring


def superflex_command(
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    limit: int = typer.Option(200, "-n", "--limit", help="Max results"),
    qb_boost: float = typer.Option(
        1.30,
        "--qb-boost",
        help="QB points multiplier (default 1.30 reflects scarcity in 2QB / superflex)",
    ),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Superflex / 2QB draft board. Requires login.

    \b
    Applies a QB scoring multiplier (default 1.30x) to reflect the elevated
    value of QBs when a roster can start two. Tune with --qb-boost. Pass 1.0
    to disable.

    \b
    EXAMPLES:
      ffb superflex                       # default 1.30x QB boost, half-PPR
      ffb superflex -s ppr -n 100         # PPR, top 100
      ffb superflex --qb-boost 1.5        # heavier QB premium
      ffb superflex --qb-boost 1.0        # raw rankings, no boost
    """
    scoring = validate_scoring(scoring)
    try:
        base = _fetch_projections(scoring)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    players = copy.deepcopy(base)
    for p in players:
        if p.get("position", "").upper() == "QB":
            p["points"] = round(p.get("points", 0) * qb_boost, 1)

    players.sort(key=lambda p: -p["points"])
    for i, p in enumerate(players, 1):
        p["rank"] = i

    players = players[:limit]
    if not players:
        typer.echo("No rankings available.")
        raise typer.Exit(0)

    title_scoring = f"{scoring} superflex ({qb_boost:g}x QB)"
    if output_json:
        console.print_json(json.dumps(players))
    else:
        rankings_table(players, title_scoring)

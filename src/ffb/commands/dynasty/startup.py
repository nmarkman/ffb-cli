"""ffb dynasty startup , startup-draft board ordered by ADP."""
from __future__ import annotations

import json
from typing import Optional

import typer

from ...api.endpoints import DYNASTY_STARTUP_PAGE
from ...config import DEFAULT_SCORING, SCORING_FORMATS, VALID_POSITIONS
from ...display.tables import console
from ._common import calc_points, load_dynasty_data, project_average
from ._tables import dynasty_startup_table
from .rankings import _age_from_birth


def dynasty_startup_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(VALID_POSITIONS)})"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    superflex: bool = typer.Option(False, "--superflex", "--sf", "--2qb", help="SuperFlex draft board"),
    analyst: Optional[str] = typer.Option(None, "--analyst", "-a", help="Filter to a single analyst"),
    limit: int = typer.Option(100, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Dynasty startup draft board, ordered by ADP.

    \b
    EXAMPLES:
      ffb dynasty startup                 # top 100 by half-PPR ADP
      ffb dynasty startup --superflex     # SuperFlex ADP order
      ffb dynasty startup QB -n 30        # top 30 QBs by ADP
    """
    scoring_key = SCORING_FORMATS.get(scoring, scoring.upper())
    data = load_dynasty_data(DYNASTY_STARTUP_PAGE)
    rows = project_average(data.get("projections", []), analyst_filter=analyst)
    for r in rows:
        r["points"] = round(calc_points(r, scoring_key), 1)
        r["age"] = _age_from_birth(r.get("birth_date"))
        r["draft_adp"] = r.get("adp_2qb") if superflex else (r.get("adp_half_ppr") or r.get("adp"))

    if position:
        rows = [r for r in rows if r.get("position", "").upper() == position.upper()]

    # Players without an ADP go to the bottom; rest sort ascending.
    rows.sort(key=lambda r: (r.get("draft_adp") is None, r.get("draft_adp") or 9999))
    for i, r in enumerate(rows[:limit], 1):
        r["rank"] = i
    rows = rows[:limit]

    if not rows:
        typer.echo("No startup data matched the filters.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows, default=str))
    else:
        dynasty_startup_table(rows, scoring=scoring, superflex=superflex)

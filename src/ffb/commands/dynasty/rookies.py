"""ffb dynasty rookies , 2026 rookie class only."""
from __future__ import annotations

import json
from typing import Optional

import typer

from ...api.endpoints import DYNASTY_RANKINGS_PAGE
from ...config import DEFAULT_SCORING, SCORING_FORMATS, VALID_POSITIONS
from ...display.tables import console
from ._common import calc_points, load_dynasty_data, project_average
from ._tables import dynasty_rookies_table
from .rankings import _age_from_birth


def dynasty_rookies_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(VALID_POSITIONS)})"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format"),
    superflex: bool = typer.Option(False, "--superflex", "--sf", "--2qb", help="Sort by SuperFlex ADP"),
    analyst: Optional[str] = typer.Option(None, "--analyst", "-a", help="Filter to a single analyst"),
    limit: int = typer.Option(75, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """2026 rookie class rankings (filters projections to experience=0).

    \b
    EXAMPLES:
      ffb dynasty rookies              # top 75 rookies
      ffb dynasty rookies RB           # rookie RBs only
      ffb dynasty rookies --superflex  # by SF ADP
    """
    scoring_key = SCORING_FORMATS.get(scoring, scoring.upper())
    data = load_dynasty_data(DYNASTY_RANKINGS_PAGE)
    rows = project_average(data.get("projections", []), analyst_filter=analyst)
    rows = [r for r in rows if str(r.get("experience") or "").strip() in ("0", "R", "")]
    # Some "experience=0" rows are veterans with missing data; require an ADP signal too.
    rows = [r for r in rows if r.get("adp_2qb") or r.get("adp_half_ppr") or r.get("adp_ppr")]

    for r in rows:
        r["points"] = round(calc_points(r, scoring_key), 1)
        r["age"] = _age_from_birth(r.get("birth_date"))

    if position:
        rows = [r for r in rows if r.get("position", "").upper() == position.upper()]

    if superflex:
        rows.sort(key=lambda r: (r.get("adp_2qb") is None, r.get("adp_2qb") or 9999))
    else:
        rows.sort(key=lambda r: (r.get("adp_half_ppr") is None and r.get("adp") is None,
                                  r.get("adp_half_ppr") or r.get("adp") or 9999))
    for i, r in enumerate(rows[:limit], 1):
        r["rank"] = i
    rows = rows[:limit]

    if not rows:
        typer.echo("No rookies matched the filters.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows, default=str))
    else:
        dynasty_rookies_table(rows, scoring=scoring)

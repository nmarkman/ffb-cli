"""ffb dynasty rankings ...

Dynasty rankings derived from the /2026-dynasty-pass/rankings/ page. Averages
the three analysts' projections (Andy, Jason, Mike), computes fantasy points,
and surfaces both 1QB and SuperFlex ADP. Use --analyst to pin to a single voice.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import typer

from ...api.endpoints import DYNASTY_RANKINGS_PAGE
from ...config import DEFAULT_SCORING, SCORING_FORMATS, VALID_POSITIONS
from ...display.tables import console
from ._common import calc_points, load_dynasty_data, project_average
from ._tables import dynasty_rankings_table


def _age_from_birth(birth: str | None) -> Optional[float]:
    if not birth:
        return None
    try:
        bdate = datetime.fromisoformat(birth.replace("Z", "")).date()
    except ValueError:
        return None
    today = date.today()
    years = today.year - bdate.year - ((today.month, today.day) < (bdate.month, bdate.day))
    return float(years)


def dynasty_rankings_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(VALID_POSITIONS)})"),
    scoring: str = typer.Option(DEFAULT_SCORING, "-s", "--scoring", help="Scoring format (half/ppr/standard)"),
    superflex: bool = typer.Option(False, "--superflex", "--sf", "--2qb", help="Sort by SuperFlex ADP (ADP_2QB)"),
    analyst: Optional[str] = typer.Option(None, "--analyst", "-a", help="Filter to a single analyst (andy, jason, mike)"),
    limit: int = typer.Option(50, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """View dynasty rankings.

    \b
    EXAMPLES:
      ffb dynasty rankings                       # consensus top 50
      ffb dynasty rankings RB                    # top 50 RBs
      ffb dynasty rankings QB --superflex        # QBs sorted by SuperFlex ADP
      ffb dynasty rankings --analyst andy        # just Andy's view
      ffb dynasty rankings WR -s ppr --json      # PPR WR rankings, JSON
    """
    scoring_key = SCORING_FORMATS.get(scoring, scoring.upper())
    data = load_dynasty_data(DYNASTY_RANKINGS_PAGE)
    projections = data.get("projections", [])
    if not projections:
        typer.echo("No projections returned by the dynasty rankings page.", err=True)
        raise typer.Exit(1)

    rows = project_average(projections, analyst_filter=analyst)
    for r in rows:
        r["points"] = round(calc_points(r, scoring_key), 1)
        r["age"] = _age_from_birth(r.get("birth_date"))

    if position:
        rows = [r for r in rows if r.get("position", "").upper() == position.upper()]

    if superflex:
        # Sort by SF ADP ascending. Players without an ADP_2QB sink to bottom.
        rows.sort(key=lambda r: (r.get("adp_2qb") is None, r.get("adp_2qb") or 999.0))
    else:
        rows.sort(key=lambda r: -r.get("points", 0))

    for i, r in enumerate(rows[:limit], 1):
        r["rank"] = i

    rows = rows[:limit]
    if not rows:
        typer.echo("No dynasty rankings matched the filters.")
        raise typer.Exit(0)

    if output_json:
        import json
        console.print_json(json.dumps(rows, default=str))
    else:
        view = "SuperFlex" if superflex else (f"Analyst:{analyst}" if analyst else "Consensus")
        dynasty_rankings_table(rows, scoring=scoring, view=view)

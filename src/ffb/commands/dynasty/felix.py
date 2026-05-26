"""ffb dynasty felix, F.E.L.I.X. dynasty scores."""
from __future__ import annotations

import json

import typer

from ...api.dynasty_scrape import extract_const_assignment
from ...api.endpoints import DYNASTY_FELIX_PAGE
from ...display.tables import felix_table, console
from ._common import fetch_dynasty_page

DYNASTY_POSITIONS = {"QB", "RB", "WR", "TE"}


def _to_float(val, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def dynasty_felix_command(
    position: str = typer.Argument(None, help="Position filter (QB, RB, WR, TE)"),
    team: str = typer.Option(None, "-t", "--team", help="Filter by team abbreviation"),
    min_score: float = typer.Option(None, "--min", help="Minimum FELIX score"),
    limit: int = typer.Option(30, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """F.E.L.I.X. dynasty scores. Requires UDK+.

    \b
    FELIX combines a player's peak ceiling and floor reliability into a single
    dynasty score. Higher = better dynasty asset.

    \b
    EXAMPLES:
      ffb dynasty felix                # top 30 overall
      ffb dynasty felix WR -n 50       # top 50 WRs
      ffb dynasty felix RB --min 20    # RBs with FELIX >= 20
      ffb dynasty felix -t KC          # all KC players
    """
    html = fetch_dynasty_page(DYNASTY_FELIX_PAGE)
    data = extract_const_assignment(html, "data")
    if not isinstance(data, list):
        typer.echo("Could not find FELIX data on the page. Layout may have changed.", err=True)
        raise typer.Exit(1)

    rows = []
    for r in data:
        rows.append({
            "name": r.get("name", ""),
            "fantasy_position": r.get("fantasy_position", ""),
            "team": r.get("team", "") or "",
            "experience": r.get("experience", ""),
            "felix_score": _to_float(r.get("felix_score")),
            "felix_percentile": _to_float(r.get("felix_percentile")),
            "felix_peak": _to_float(r.get("felix_peak")),
            "felix_reliability": _to_float(r.get("felix_reliability")),
        })

    if position:
        pos_u = position.upper()
        rows = [r for r in rows if r["fantasy_position"].upper() == pos_u]
    if team:
        team_u = team.upper()
        rows = [r for r in rows if r["team"].upper() == team_u]
    if min_score is not None:
        rows = [r for r in rows if r["felix_score"] >= min_score]

    rows.sort(key=lambda r: -r["felix_score"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    rows = rows[:limit]

    if not rows:
        typer.echo("No players matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        felix_table(rows)

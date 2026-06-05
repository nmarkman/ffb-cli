"""ffb value-scout, UDK ADP reference across scoring formats."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_VALUE_SCOUT_PAGE
from ..display.tables import value_scout_table, console
from ._scrape import load_const_data, to_float

VALID_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DST"}


def value_scout_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(sorted(VALID_POSITIONS))})"),
    sort_by: str = typer.Option("adp", "-s", "--sort", help="Sort key: adp | ppr | 2qb | dynasty"),
    limit: int = typer.Option(50, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Value Scout: ADP reference across scoring formats. Requires login.

    \b
    Surfaces each player's average draft position in redraft, PPR, SuperFlex
    (2QB), and dynasty formats so you can spot where a player is going across
    league types heading into a draft.

    \b
    EXAMPLES:
      ffb value-scout                  # top 50 by overall ADP
      ffb value-scout RB -n 30         # top 30 RBs
      ffb value-scout QB -s 2qb        # QBs sorted by SuperFlex ADP
      ffb value-scout --json           # JSON output
    """
    raw = load_const_data(UDK_VALUE_SCOUT_PAGE)

    rows = []
    for r in raw:
        rows.append({
            "name": r.get("name", ""),
            "fantasy_position": r.get("fantasy_position", "") or "",
            "team": r.get("team", "") or "",
            "bye_week": r.get("bye_week", "") or "",
            "adp": to_float(r.get("adp"), None) if r.get("adp") not in (None, "") else None,
            "adp_ppr": to_float(r.get("adp_ppr"), None) if r.get("adp_ppr") not in (None, "") else None,
            "adp_2qb": to_float(r.get("adp_2qb"), None) if r.get("adp_2qb") not in (None, "") else None,
            "adp_dynasty": to_float(r.get("adp_dynasty"), None) if r.get("adp_dynasty") not in (None, "") else None,
        })

    if position:
        pos_u = position.upper()
        rows = [r for r in rows if r["fantasy_position"].upper() == pos_u]

    sort_keys = {"adp": "adp", "ppr": "adp_ppr", "2qb": "adp_2qb", "dynasty": "adp_dynasty"}
    sort_key = sort_keys.get(sort_by.lower())
    if not sort_key:
        typer.echo(f"Unknown sort key '{sort_by}'. Valid: {', '.join(sort_keys)}.", err=True)
        raise typer.Exit(1)

    # Sort ascending by ADP; players missing that ADP sink to the bottom.
    rows.sort(key=lambda r: (r[sort_key] is None, r[sort_key] if r[sort_key] is not None else 0))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    rows = rows[:limit]

    if not rows:
        typer.echo("No players matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        value_scout_table(rows)

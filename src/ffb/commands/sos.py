"""ffb sos, the UDK strength-of-schedule page."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_SOS_PAGE
from ..display.tables import sos_table, console
from ._scrape import load_const_data, to_float

POSITION_KEYS = {
    "QB": "qb_total",
    "RB": "rb_total",
    "WR": "wr_total",
    "TE": "te_total",
    "K":  "k_total",
    "DST": "d_total",
    "D":   "d_total",
}


def sos_command(
    position: str = typer.Argument(None, help="Sort by position SoS (QB, RB, WR, TE, K, DST)"),
    team: str = typer.Option(None, "-t", "--team", help="Filter by team abbreviation"),
    easy_first: bool = typer.Option(True, "--easy/--hard", help="Easiest schedule first (higher fantasy points allowed = easier)"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """View team strength-of-schedule by position. Requires login.

    \b
    Totals are projected fantasy points allowed to that position across the season.
    Higher total = easier schedule for that position.

    \b
    EXAMPLES:
      ffb sos                      # all teams, all positions
      ffb sos WR                   # sorted by easiest WR schedule
      ffb sos QB --hard            # toughest QB schedules first
      ffb sos -t KC                # one team's full SoS row
    """
    data = load_const_data(UDK_SOS_PAGE)
    rows = []
    for r in data:
        rows.append({
            "name": r.get("name", ""),
            "team": r.get("team", ""),
            "bye_week": r.get("bye_week", ""),
            "qb_total": to_float(r.get("qb_total")),
            "rb_total": to_float(r.get("rb_total")),
            "wr_total": to_float(r.get("wr_total")),
            "te_total": to_float(r.get("te_total")),
            "k_total":  to_float(r.get("k_total")),
            "d_total":  to_float(r.get("d_total")),
        })

    sort_pos_label: str | None = None
    if position:
        pos_u = position.upper()
        if pos_u not in POSITION_KEYS:
            typer.echo(f"Unknown position '{position}'. Valid: QB, RB, WR, TE, K, DST.", err=True)
            raise typer.Exit(1)
        key = POSITION_KEYS[pos_u]
        rows.sort(key=lambda r: r[key], reverse=easy_first)
        sort_pos_label = "DST" if pos_u == "D" else pos_u
    else:
        rows.sort(key=lambda r: r["name"])

    if team:
        team_u = team.upper()
        rows = [r for r in rows if r["team"].upper() == team_u]

    if not rows:
        typer.echo("No teams matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        sos_table(rows, highlight_position=sort_pos_label)

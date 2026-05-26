"""ffb red-zone, UDK red-zone usage report."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_RED_ZONE_PAGE
from ..display.tables import red_zone_table, console
from ._scrape import load_const_data, to_float

VALID_POSITIONS = {"QB", "RB", "WR", "TE", "FB"}


def red_zone_command(
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(sorted(VALID_POSITIONS))})"),
    season: int = typer.Option(None, "-y", "--season", help="Season year (defaults to most recent)"),
    sort_by: str = typer.Option(
        "touches",
        "-s", "--sort",
        help="Sort key: touches | tds | rec_targets | rec_tds | rush_attempts | rush_tds | pass_attempts | pass_tds",
    ),
    limit: int = typer.Option(25, "-n", "--limit", help="Max results"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Red-zone usage report (player-season). Requires login.

    \b
    Default sort 'touches' = RZ receiving targets + RZ rushing attempts + RZ
    passing attempts. Useful for surfacing TD upside heading into a draft.

    \b
    EXAMPLES:
      ffb red-zone                       # top 25 by RZ touches
      ffb red-zone RB -n 30              # top 30 RBs
      ffb red-zone WR -s rec_targets     # WRs by RZ targets
      ffb red-zone QB -s pass_tds        # QBs by RZ pass TDs
      ffb red-zone --json                # JSON output
    """
    raw = load_const_data(UDK_RED_ZONE_PAGE)

    # Default to the most recent season in the data.
    if season is None:
        seasons = {int(float(r.get("season"))) for r in raw if r.get("season")}
        season = max(seasons) if seasons else None

    rows = []
    for r in raw:
        try:
            row_season = int(float(r.get("season", 0)))
        except (TypeError, ValueError):
            row_season = 0
        if season is not None and row_season != season:
            continue

        rec_tgt = to_float(r.get("red_zone_receiving_targets"))
        rec     = to_float(r.get("red_zone_receptions"))
        rec_td  = to_float(r.get("red_zone_receiving_touchdowns"))
        rush_at = to_float(r.get("red_zone_rushing_attempts"))
        rush_td = to_float(r.get("red_zone_rushing_touchdowns"))
        pass_at = to_float(r.get("red_zone_passing_attempts"))
        pass_td = to_float(r.get("red_zone_passing_touchdowns"))

        rows.append({
            "name": r.get("name", ""),
            "fantasy_position": r.get("fantasy_position", ""),
            "team": r.get("team", "") or "",
            "season": row_season,
            "red_zone_receiving_targets": rec_tgt,
            "red_zone_receptions": rec,
            "red_zone_receiving_touchdowns": rec_td,
            "red_zone_rushing_attempts": rush_at,
            "red_zone_rushing_touchdowns": rush_td,
            "red_zone_passing_attempts": pass_at,
            "red_zone_passing_touchdowns": pass_td,
            "touches": rec_tgt + rush_at + pass_at,
            "tds": rec_td + rush_td + pass_td,
        })

    if position:
        pos_u = position.upper()
        rows = [r for r in rows if r["fantasy_position"].upper() == pos_u]

    sort_keys = {
        "touches": "touches",
        "tds": "tds",
        "rec_targets": "red_zone_receiving_targets",
        "rec_tds": "red_zone_receiving_touchdowns",
        "rush_attempts": "red_zone_rushing_attempts",
        "rush_tds": "red_zone_rushing_touchdowns",
        "pass_attempts": "red_zone_passing_attempts",
        "pass_tds": "red_zone_passing_touchdowns",
    }
    sort_key = sort_keys.get(sort_by.lower())
    if not sort_key:
        typer.echo(f"Unknown sort key '{sort_by}'. Valid: {', '.join(sort_keys)}.", err=True)
        raise typer.Exit(1)

    rows.sort(key=lambda r: -r[sort_key])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    rows = rows[:limit]

    if not rows:
        typer.echo("No players matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        red_zone_table(rows)

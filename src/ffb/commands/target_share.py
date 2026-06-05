"""ffb target-share, team positional target distribution (UDK Target Breakdown)."""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_TARGET_SHARE_PAGE
from ..display.tables import target_share_table, console
from ._scrape import load_const_data, to_float, to_int


def target_share_command(
    team: str = typer.Argument(None, help="Team code filter (KC, BUF, ...)"),
    season: int = typer.Option(None, "-y", "--season", help="Season year (defaults to most recent)"),
    sort_by: str = typer.Option("wr", "-s", "--sort", help="Sort key: wr | rb | te | volume"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Target Breakdown: how each team splits targets across WR/RB/TE. Requires login.

    \b
    Aggregates a full season of team target distribution. Useful for finding
    which offenses funnel volume to a position group (e.g. high TE-target teams
    for a streaming tight end).

    \b
    EXAMPLES:
      ffb target-share                 # all teams, sorted by WR target share
      ffb target-share -s te           # teams that target TEs most
      ffb target-share KC              # one team's distribution
      ffb target-share -s volume       # busiest passing offenses
    """
    raw = load_const_data(UDK_TARGET_SHARE_PAGE)

    if season is None:
        seasons = {to_int(r.get("season")) for r in raw if r.get("season")}
        season = max(seasons) if seasons else None

    agg: dict[str, dict] = {}
    for r in raw:
        if season is not None and to_int(r.get("season")) != season:
            continue
        key = r.get("key", "") or r.get("team_id", "")
        a = agg.get(key)
        if a is None:
            a = agg[key] = {
                "name": r.get("name", ""),
                "key": r.get("key", ""),
                "weeks": 0,
                "wr": 0.0, "rb": 0.0, "te": 0.0, "total": 0.0,
            }
        a["weeks"] += 1
        a["wr"] += to_float(r.get("wr_targets"))
        a["rb"] += to_float(r.get("rb_targets"))
        a["te"] += to_float(r.get("te_targets"))
        a["total"] += to_float(r.get("total_targets"))

    def share(num: float, den: float):
        return round(num / den, 4) if den else None

    rows = []
    for a in agg.values():
        rows.append({
            "name": a["name"],
            "key": a["key"],
            "targets_per_game": round(a["total"] / a["weeks"], 1) if a["weeks"] else None,
            "wr_share": share(a["wr"], a["total"]),
            "rb_share": share(a["rb"], a["total"]),
            "te_share": share(a["te"], a["total"]),
        })

    if team:
        team_u = team.upper()
        rows = [r for r in rows if (r["key"] or "").upper() == team_u]

    sort_keys = {"wr": "wr_share", "rb": "rb_share", "te": "te_share", "volume": "targets_per_game"}
    sort_key = sort_keys.get(sort_by.lower())
    if not sort_key:
        typer.echo(f"Unknown sort key '{sort_by}'. Valid: {', '.join(sort_keys)}.", err=True)
        raise typer.Exit(1)

    rows.sort(key=lambda r: (r[sort_key] is None, -(r[sort_key] or 0)))
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    if not rows:
        typer.echo("No teams matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        target_share_table(rows, season)

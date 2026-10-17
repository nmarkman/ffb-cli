"""ffb player-news, the Ultimate Dashboard's player news + injury feed."""
from __future__ import annotations

import json

import typer
from thefuzz import fuzz

from ..api.endpoints import FOOTCLAN_DASHBOARD_PAGE
from ..display.tables import console, player_news_table
from ._inseason import display_position, load_tool_data, normalize_position

POSITIONS = ("QB", "RB", "WR", "TE", "K", "D")

# Statuses that mean a player is (or may be) unavailable.
INJURY_STATUSES = {"QUESTIONABLE", "DOUBTFUL", "OUT", "IR", "IR-R", "PUP", "PUP-R", "INACTIVE", "SUSPENDED"}


def news_rows(items: list[dict]) -> list[dict]:
    rows = []
    for n in items or []:
        rows.append({
            "date": n.get("date_iso") or n.get("date_time"),
            "time_ago": n.get("time_ago"),
            "name": n.get("name", ""),
            "position": display_position((n.get("fantasy_position") or "").upper()),
            "team": n.get("team", "") or "",
            "headline": n.get("headline", ""),
            "notes": n.get("notes", ""),
            "analysis": n.get("analysis", ""),
            "injury_status": n.get("injury_status"),
            "injury": " ".join(x for x in (n.get("injury_side"), n.get("injury_location"),
                                           n.get("injury_type")) if x) or None,
            "url": n.get("url"),
        })
    rows.sort(key=lambda r: r["date"] or "", reverse=True)
    return rows


def player_news_command(
    player: str = typer.Argument(None, help="Player name (fuzzy). Omit for the latest news."),
    position: str = typer.Option(None, "-p", "--position", help="Position filter (QB, RB, WR, TE, K, DST)"),
    team: str = typer.Option(None, "-t", "--team", help="Team code filter (KC, BUF, ...)"),
    injuries: bool = typer.Option(False, "--injuries", help="Only players with an injury designation"),
    full: bool = typer.Option(False, "--full", help="Show the full notes + analysis for each item"),
    limit: int = typer.Option(15, "-n", "--limit", help="Max items"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Player news, injury updates and analysis from the past ~2 weeks (FootClan). Requires login.

    \b
    The Ultimate Dashboard news feed: each item has the headline, the news,
    the analysis of what it means for fantasy, and the player's injury status.
    `ffb news` is the site's articles; this is per-player news.

    \b
    EXAMPLES:
      ffb player-news                      # latest 15 items
      ffb player-news "Mayfield" --full    # one player's news with analysis
      ffb player-news --injuries -p RB     # RB injury report
      ffb player-news -t KC --json
    """
    data = load_tool_data(FOOTCLAN_DASHBOARD_PAGE, "ultimateDashboard")
    rows = news_rows(data.get("news") or [])

    if player:
        q = player.lower()
        rows = [r for r in rows if max(fuzz.token_sort_ratio(q, r["name"].lower()),
                                       fuzz.partial_ratio(q, r["name"].lower())) >= 80]
    if position:
        pos = display_position(normalize_position(position, POSITIONS))
        rows = [r for r in rows if r["position"] == pos]
    if team:
        rows = [r for r in rows if r["team"].upper() == team.upper()]
    if injuries:
        rows = [r for r in rows if (r["injury_status"] or "").upper() in INJURY_STATUSES]
    rows = rows[:limit]

    if not rows:
        typer.echo("No player news matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        player_news_table(rows, full=full)

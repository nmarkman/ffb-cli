"""ffb dynasty production , production-profiles lookup."""
from __future__ import annotations

import json
from typing import Optional

import typer
from thefuzz import fuzz

from ...api.endpoints import DYNASTY_PRODUCTION_PROFILES_PAGE
from ...api.dynasty_scrape import extract_const_assignment
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import dynasty_production_table, dynasty_player_card


def dynasty_production_command(
    query: Optional[str] = typer.Argument(None, help="Player name (partial match). Omit to list all."),
    limit: int = typer.Option(25, "-n", "--limit", help="Max results when listing"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Production profiles for active dynasty assets.

    \b
    The production-profiles page tracks each player's year-over-year scoring,
    target share, snap%, and similar dynasty-relevant inputs. Without a query,
    shows the first N profiles. With a query, fuzzy-matches by name.

    \b
    EXAMPLES:
      ffb dynasty production                    # first 25 profiles
      ffb dynasty production "Bijan Robinson"   # one profile
      ffb dynasty production "Robinson" --json  # all matches as JSON
    """
    html = fetch_dynasty_page(DYNASTY_PRODUCTION_PROFILES_PAGE)
    rows = extract_const_assignment(html, "data")
    if not rows:
        typer.echo("Could not extract production-profiles data.", err=True)
        raise typer.Exit(1)

    if query:
        # Score each row by best fuzzy match against a "name"-like field.
        def name_of(r: dict) -> str:
            for k in ("player_name", "name", "Player", "player"):
                if r.get(k):
                    return str(r[k])
            return ""
        scored = []
        for r in rows:
            n = name_of(r)
            if not n:
                continue
            score = max(fuzz.token_sort_ratio(query.lower(), n.lower()),
                        fuzz.partial_ratio(query.lower(), n.lower()))
            if score >= 60:
                scored.append((score, r))
        scored.sort(key=lambda t: -t[0])
        rows = [r for _, r in scored[:limit]]

    rows = rows[:limit]
    if not rows:
        typer.echo("No production profiles matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows, default=str))
        return

    if query and len(rows) == 1:
        # Single-player render: show as a card with stats
        r = rows[0]
        body = "\n".join(f"[bold]{k}[/bold]: {v}" for k, v in r.items() if v not in (None, "", 0))
        dynasty_player_card(
            {"player_name": r.get("player_name") or r.get("name") or "Unknown",
             "position": r.get("position") or r.get("Position", ""),
             "team": r.get("team") or r.get("Team", ""),
             "age": r.get("age") or r.get("Age")},
            body=body,
        )
    else:
        dynasty_production_table(rows)

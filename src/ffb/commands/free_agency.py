"""ffb free-agency, UDK Free Agency Review (offseason signings + analysis)."""
from __future__ import annotations

import json

import typer

from ..api.dynasty_scrape import extract_ffb_snippets, slice_main_content
from ..api.endpoints import UDK_FREE_AGENCY_REVIEW_PAGE
from ..display.tables import free_agency_table, console
from ._scrape import fetch_page


def free_agency_command(
    query: str = typer.Argument(None, help="Filter by player name or team code"),
    limit: int = typer.Option(30, "-n", "--limit", help="Max items"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Free Agency Review: offseason signings with fantasy analysis. Requires login.

    \b
    EXAMPLES:
      ffb free-agency                  # all signings
      ffb free-agency jones            # filter by name
      ffb free-agency IND              # filter by team mentioned in the move
    """
    snippets = extract_ffb_snippets(slice_main_content(fetch_page(UDK_FREE_AGENCY_REVIEW_PAGE)))

    rows = []
    for s in snippets:
        name = s.get("name", "")
        blurb = s.get("meta", "")          # extract_ffb_snippets puts the writeup in meta
        content = s.get("content", "")
        # The content opens with the move header ("Player Signed | Age TEAM | terms")
        # then repeats the blurb. Slice the header off the front.
        move = content
        if blurb:
            idx = content.find(blurb[:25])
            if idx > 0:
                move = content[:idx].strip(" |")
        rows.append({"name": name, "move": move.strip(), "blurb": blurb})

    if query:
        q = query.lower()
        rows = [r for r in rows if q in r["name"].lower() or q in r["move"].lower()]

    rows = rows[:limit]
    if not rows:
        typer.echo("No free-agency entries matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
    else:
        free_agency_table(rows)

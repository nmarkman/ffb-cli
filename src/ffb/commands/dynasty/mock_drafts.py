"""ffb dynasty mock , rookie mock drafts."""
from __future__ import annotations

import json
import re

import typer

from ...api.dynasty_scrape import (
    extract_ffb_snippets,
    slice_main_content,
    strip_html_tags,
)
from ...api.endpoints import DYNASTY_MOCK_DRAFTS_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_mock_drafts_command(
    limit: int = typer.Option(40, "-n", "--limit", help="Max picks to show"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Recent rookie mock-draft results.

    \b
    The page renders one card per pick. We extract pick number, player, position,
    team, and any analyst note.
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_MOCK_DRAFTS_PAGE))

    # Each pick is an `ffb-snippet` block. Pick numbers are within
    # the snippet text or in a preceding label.
    snippets = extract_ffb_snippets(html)
    picks = []
    for i, s in enumerate(snippets, 1):
        meta = s.get("meta", "")
        pick_m = re.search(r"(?:Pick\s*|#)(\d{1,3})", meta + " " + s.get("content", ""))
        picks.append({
            "pick": int(pick_m.group(1)) if pick_m else i,
            "name": s.get("name", ""),
            "position": meta.split()[0] if meta else "",
            "team": meta.split()[1] if len(meta.split()) > 1 else "",
            "note": s.get("content", "")[:160],
        })

    picks = picks[:limit]
    if output_json:
        console.print_json(json.dumps(picks, default=str))
    elif picks:
        list_cards(picks, title="Rookie Mock Draft",
                   fields=[("pick", "#"), ("name", "Player"), ("position", "Pos"),
                           ("team", "Team"), ("note", "Note")])
    else:
        typer.echo("No mock-draft picks extracted. Page may render via AJAX. Try `ffb dynasty open mock`.")

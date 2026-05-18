"""ffb dynasty movers, risers and fallers."""
from __future__ import annotations

import json
import re

import typer

from ...api.dynasty_scrape import (
    extract_ffb_snippets,
    extract_player_cards,
    slice_main_content,
)
from ...api.endpoints import DYNASTY_RISERS_FALLERS_PAGE
from ...display.tables import console
from ._common import fetch_dynasty_page
from ._tables import list_cards


def dynasty_movers_command(
    direction: str = typer.Argument("both", help="risers, fallers, or both"),
    limit: int = typer.Option(15, "-n", "--limit", help="Max per direction"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Dynasty risers and fallers.

    \b
    EXAMPLES:
      ffb dynasty movers              # both sides, 15 each
      ffb dynasty movers risers       # only risers
      ffb dynasty movers fallers -n 5
    """
    html = slice_main_content(fetch_dynasty_page(DYNASTY_RISERS_FALLERS_PAGE))

    # Page renders risers above fallers; split on the "Fallers" heading.
    split_m = re.search(r"(?i)<h[23][^>]*>\s*Fallers\b[^<]*</", html)
    risers_html = html[:split_m.start()] if split_m else html
    fallers_html = html[split_m.start():] if split_m else ""

    def collect(section_html: str) -> list[dict]:
        items = extract_ffb_snippets(section_html)
        if not items:
            items = extract_player_cards(section_html)
            for c in items:
                c.setdefault("meta", " ".join(filter(None, [c.get("position", ""), c.get("team", "")])).strip())
                c.setdefault("content", c.get("blurb", ""))
        return items

    risers = collect(risers_html)
    fallers = collect(fallers_html)

    direction = direction.lower()
    out: list[dict] = []
    if direction in ("risers", "both"):
        for c in risers[:limit]:
            c["direction"] = "Riser"
            out.append(c)
    if direction in ("fallers", "both"):
        for c in fallers[:limit]:
            c["direction"] = "Faller"
            out.append(c)

    if output_json:
        console.print_json(json.dumps(out, default=str))
    elif out:
        list_cards(out, title="Dynasty Movers",
                   fields=[("direction", ""), ("name", "Player"), ("meta", "Pos / Team"),
                           ("content", "Why")])
    else:
        typer.echo("No movers extracted from the page.")

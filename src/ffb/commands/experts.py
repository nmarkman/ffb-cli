"""ffb experts, UDK Expert Lists (Sleepers / Breakouts / Values / Busts).

Unlike the other tools, the expert picks are assembled in the browser from
window.udk.data with no inline list and no REST endpoint, so this command
renders the page headlessly (reusing the Playwright login dependency) and scrapes
the rendered DOM. Results are cached so repeat runs don't re-launch a browser.
"""
from __future__ import annotations

import json

import typer

from ..api.endpoints import UDK_EXPERT_LIST_PAGES
from ..api.render import render_expert_picks
from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_UDK_PAGE
from ..display.tables import expert_list_table, console

VALID_POSITIONS = {"QB", "RB", "WR", "TE"}


def experts_command(
    list_type: str = typer.Argument(..., help="Which list: sleepers | breakouts | values | busts"),
    position: str = typer.Argument(None, help=f"Position filter ({', '.join(sorted(VALID_POSITIONS))})"),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cache and re-render"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Expert Lists: the Footballers' Sleepers, Breakouts, Values, and Busts.

    \b
    Renders the page in a headless browser (requires login + Playwright's
    Chromium). Each pick includes the player's current ADP and the analyst's
    reasoning.

    \b
    EXAMPLES:
      ffb experts sleepers             # all sleeper picks
      ffb experts breakouts WR         # WR breakouts only
      ffb experts busts                # players to avoid
      ffb experts values --json        # JSON output
    """
    key = list_type.lower()
    path = UDK_EXPERT_LIST_PAGES.get(key)
    if not path:
        typer.echo(
            f"Unknown list '{list_type}'. Choose one of: "
            f"{', '.join(sorted(UDK_EXPERT_LIST_PAGES))}.",
            err=True,
        )
        raise typer.Exit(1)

    cache_key = f"udk_expert_list:{key}"
    picks = None if refresh else get_cached(cache_key, CACHE_TTL_UDK_PAGE)
    if picks is None:
        picks = render_expert_picks(path)
        set_cached(cache_key, picks)

    if position:
        pos_u = position.upper()
        picks = [p for p in picks if (p.get("position") or "").upper() == pos_u]

    if not picks:
        typer.echo("No picks found.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(picks))
    else:
        expert_list_table(picks, list_type=key)

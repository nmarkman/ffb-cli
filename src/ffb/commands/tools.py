"""ffb tools, catalog of FFB tools, access tiers, and CLI coverage."""
from __future__ import annotations

import json

import typer
from rich.table import Table

from ..catalog import CATALOG, coverage_summary
from ..display.tables import console

_TIER_STYLE = {
    "free": "green",
    "UDK": "cyan",
    "UDK+": "magenta",
    "DFS Pass": "yellow",
    "FootClan": "blue",
}


def tools_command(
    tier: str = typer.Option(None, "-t", "--tier", help="Filter by tier: free | UDK | UDK+ | DFS | FootClan"),
    covered_only: bool = typer.Option(False, "--covered", help="Only tools the CLI exposes"),
    missing: bool = typer.Option(False, "--missing", help="Only tools the CLI does NOT expose"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Catalog of Fantasy Footballers tools: what's free, what's paywalled, and
    which CLI command (if any) covers each.

    \b
    The Footballers gate almost everything behind the Ultimate Draft Kit (UDK),
    the Dynasty Pass (UDK+), or the DFS Pass. Only player search and news are
    free. This command shows the full map so you know what your account unlocks.

    \b
    EXAMPLES:
      ffb tools                        # full catalog
      ffb tools --tier free            # what works without an account
      ffb tools --covered              # everything the CLI exposes
      ffb tools --missing              # tools not yet wrapped
      ffb tools --json                 # machine-readable
    """
    rows = list(CATALOG)

    if tier:
        t = tier.lower()
        aliases = {"dfs": "dfs pass", "udk+": "udk+", "footclan": "footclan", "free": "free", "udk": "udk"}
        want = aliases.get(t, t)
        rows = [r for r in rows if r["tier"].lower() == want]
    if covered_only:
        rows = [r for r in rows if r["command"]]
    if missing:
        rows = [r for r in rows if not r["command"]]

    if not rows:
        typer.echo("No tools matched.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(rows))
        return

    covered_n, total_n = coverage_summary()
    table = Table(title=f"Fantasy Footballers Tool Catalog  ({covered_n}/{total_n} CLI-covered)")
    table.add_column("Category", style="dim")
    table.add_column("Tool", style="bold")
    table.add_column("Tier")
    table.add_column("CLI Command", style="green")
    table.add_column("What it is", overflow="fold")

    last_cat = None
    for r in rows:
        cat = r["category"] if r["category"] != last_cat else ""
        last_cat = r["category"]
        tier_style = _TIER_STYLE.get(r["tier"], "")
        tier_cell = f"[{tier_style}]{r['tier']}[/{tier_style}]" if tier_style else r["tier"]
        cmd = r["command"] or "[dim](not in CLI)[/dim]"
        table.add_row(cat, r["tool"], tier_cell, cmd, r["summary"])
    console.print(table)
    console.print(
        "\n[dim]Tiers: [green]free[/green] (no account) · [cyan]UDK[/cyan] (Ultimate Draft Kit) · "
        "[magenta]UDK+[/magenta] (Dynasty Pass) · [yellow]DFS Pass[/yellow] · [blue]FootClan[/blue] (in-season). "
        "Everything except free requires a purchase.[/dim]"
    )

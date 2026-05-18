"""ffb dynasty open <slug> , open a dynasty page in the default browser.

Escape hatch for pages whose data is JS-driven and not yet fully scraped.
"""
from __future__ import annotations

import subprocess

import typer

from ...config import BASE_URL


SLUG_TO_PATH = {
    "rankings": "/2026-dynasty-pass/rankings/",
    "startup": "/2026-dynasty-pass/startup-rankings/",
    "production": "/2026-dynasty-pass/production-profiles/",
    "mock": "/2026-dynasty-pass/mock-drafts/",
    "trade": "/2026-dynasty-pass/trade-analyzer/",
    "trade-targets": "/2026-dynasty-pass/dynasty-trade-targets/",
    "team-opportunity": "/2026-dynasty-pass/team-opportunity/",
    "movers": "/2026-dynasty-pass/risers-fallers/",
    "scouting": "/2026-dynasty-pass/scouting-reports/",
    "lifecycles": "/2026-dynasty-pass/dynasty-lifecycles/",
    "free-agents": "/2026-dynasty-pass/free-agent-tracker/",
    "injuries": "/2026-dynasty-pass/injury-tracker/",
    "draft-results": "/2026-dynasty-pass/nfl-draft-results/",
    "tips": "/2026-dynasty-pass/dynasty-tips/",
    "landing": "/2026-dynasty-pass/",
}


def dynasty_open_command(
    slug: str = typer.Argument("landing", help="Page slug (rankings, startup, scouting, etc.) or 'landing'"),
):
    """Open a Dynasty Pass page in the default browser.

    \b
    EXAMPLES:
      ffb dynasty open                     # open the Dynasty Pass landing page
      ffb dynasty open scouting            # scouting reports
      ffb dynasty open mock                # rookie mock drafts
    """
    path = SLUG_TO_PATH.get(slug.lower())
    if not path:
        typer.echo(f"Unknown slug '{slug}'. Available: {', '.join(sorted(SLUG_TO_PATH))}", err=True)
        raise typer.Exit(1)
    url = f"{BASE_URL}{path}"
    subprocess.run(["open", url], check=False)
    typer.echo(f"Opened {url}")

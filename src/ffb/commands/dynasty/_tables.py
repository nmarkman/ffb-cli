"""Rich table renderers for dynasty subcommands. Kept in the dynasty package to
avoid bloating the global display module."""
from __future__ import annotations

from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ...display.tables import console


def _fmt(val, fmt="{}"):
    if val is None or val == "":
        return ""
    try:
        return fmt.format(val)
    except (ValueError, TypeError):
        return str(val)


def dynasty_rankings_table(rows: list[dict], *, scoring: str, view: str) -> None:
    title = f"Dynasty Rankings ({view.upper()}, {scoring.upper()})"
    table = Table(title=title)
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Age", justify="right", style="dim")
    table.add_column("Exp", justify="right", style="dim")
    table.add_column("Pts", justify="right", style="yellow")
    table.add_column("ADP", justify="right")
    table.add_column("SF ADP", justify="right")
    table.add_column("Bye", justify="right", style="dim")

    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("player_name", ""),
            r.get("position", ""),
            r.get("team", ""),
            _fmt(r.get("age"), "{:.0f}"),
            _fmt(r.get("experience")),
            _fmt(r.get("points"), "{:.1f}"),
            _fmt(r.get("adp_half_ppr") or r.get("adp"), "{:.1f}"),
            _fmt(r.get("adp_2qb"), "{:.1f}"),
            _fmt(r.get("bye_week")),
        )
    console.print(table)


def dynasty_startup_table(rows: list[dict], *, scoring: str, superflex: bool) -> None:
    label = "SuperFlex" if superflex else "1QB"
    table = Table(title=f"Dynasty Startup Board ({label}, {scoring.upper()})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Age", justify="right", style="dim")
    table.add_column("ADP", justify="right", style="yellow")
    table.add_column("Pts", justify="right")

    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("player_name", ""),
            r.get("position", ""),
            r.get("team", ""),
            _fmt(r.get("age"), "{:.0f}"),
            _fmt(r.get("draft_adp"), "{:.1f}"),
            _fmt(r.get("points"), "{:.1f}"),
        )
    console.print(table)


def dynasty_rookies_table(rows: list[dict], *, scoring: str) -> None:
    table = Table(title=f"2026 Rookie Rankings ({scoring.upper()})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Age", justify="right", style="dim")
    table.add_column("Pts", justify="right", style="yellow")
    table.add_column("ADP", justify="right")
    table.add_column("SF ADP", justify="right")

    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("player_name", ""),
            r.get("position", ""),
            r.get("team", ""),
            _fmt(r.get("age"), "{:.0f}"),
            _fmt(r.get("points"), "{:.1f}"),
            _fmt(r.get("adp_half_ppr") or r.get("adp"), "{:.1f}"),
            _fmt(r.get("adp_2qb"), "{:.1f}"),
        )
    console.print(table)


def dynasty_production_table(rows: list[dict]) -> None:
    """Curated columns only. The raw payload has 60+ fields including nested
    objects; surfacing all of them makes the table unreadable. Use --json for
    full payloads."""
    table = Table(title="Dynasty Production Profiles")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("College", style="green")
    table.add_column("Class")
    table.add_column("Ht", justify="right", style="dim")
    table.add_column("Wt", justify="right", style="dim")
    table.add_column("Rank", justify="right", style="yellow")
    table.add_column("Featured Yr", justify="right", style="dim")
    for r in rows:
        height = r.get("height") or r.get("combine_height")
        weight = r.get("weight") or r.get("combine_weight")
        height_str = ""
        try:
            h = int(height) if height else None
            if h:
                height_str = f"{h // 12}'{h % 12}\""
        except (ValueError, TypeError):
            height_str = _fmt(height)
        table.add_row(
            r.get("name") or f"{r.get('first_name', '')} {r.get('last_name', '')}".strip(),
            r.get("position", ""),
            r.get("school") or r.get("team", ""),
            r.get("class", ""),
            height_str,
            _fmt(weight),
            _fmt(r.get("rank")),
            _fmt(r.get("featured_year")),
        )
    console.print(table)


def dynasty_player_card(player: dict, blurb: str | None = None, body: str | None = None) -> None:
    header = Text()
    header.append(player.get("player_name", "Unknown"), style="bold white")
    header.append(f"  {player.get('position', '')}", style="cyan")
    header.append(f"  {player.get('team', '')}", style="green")
    if player.get("age") is not None:
        header.append(f"  age {player['age']:.0f}", style="dim")

    content_lines = []
    if blurb:
        content_lines.append(f"[bold]Blurb[/bold]\n{blurb}\n")
    if body:
        content_lines.append(body)
    body_text = "\n".join(content_lines) if content_lines else "[dim]No details available.[/dim]"
    console.print(Panel(body_text, title=str(header), border_style="blue"))


def dynasty_trade_table(analysis: dict, *, label: str = "Dynasty Trade") -> None:
    table = Table(title=label)
    table.add_column("Side", style="bold")
    table.add_column("Player", style="cyan")
    table.add_column("Pos")
    table.add_column("Value", justify="right", style="yellow")

    for p in analysis.get("give_players", []):
        table.add_row("GIVE", p["player_name"], p.get("position", ""), f"{p['value']:.1f}")
    for p in analysis.get("get_players", []):
        table.add_row("GET", p["player_name"], p.get("position", ""), f"{p['value']:.1f}")

    table.add_section()
    diff = analysis.get("difference", 0)
    color = "green" if diff >= 0 else "red"
    table.add_row("", "Give Total", "", f"{analysis.get('give_total', 0):.1f}")
    table.add_row("", "Get Total", "", f"{analysis.get('get_total', 0):.1f}")
    table.add_row("", f"[{color}]Net[/{color}]", "", f"[{color}]{diff:+.1f}[/{color}]")
    console.print(table)


def list_cards(items: list[dict], *, title: str, fields: list[tuple[str, str]]) -> None:
    """Generic renderer for list-of-card pages (trade targets, tips, scouting).

    `fields` is a list of (key, label) pairs. Empty values are omitted."""
    table = Table(title=title)
    for _, label in fields:
        table.add_column(label, overflow="fold")
    for item in items:
        table.add_row(*[_fmt(item.get(k)) for k, _ in fields])
    console.print(table)

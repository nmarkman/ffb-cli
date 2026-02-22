from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def player_search_table(results: list[dict]) -> None:
    table = Table(title="Player Search Results")
    table.add_column("Name", style="bold")
    table.add_column("Position", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Match", justify="right")

    for r in results:
        table.add_row(
            r.get("name", ""),
            r.get("position", ""),
            r.get("team", ""),
            f"{r.get('score', 0)}%",
        )
    console.print(table)


def rankings_table(players: list[dict], scoring: str) -> None:
    table = Table(title=f"Rankings ({scoring.upper()})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Tier", justify="right")
    table.add_column("Pts", justify="right", style="yellow")
    table.add_column("Bye", justify="right", style="dim")

    for p in players:
        table.add_row(
            str(p.get("rank", "")),
            p.get("player_name", ""),
            p.get("position", ""),
            p.get("team", ""),
            str(p.get("tier", "")),
            f"{p.get('points', 0):.1f}",
            str(p.get("bye_week", "")),
        )
    console.print(table)


def projections_table(players: list[dict], scoring: str) -> None:
    table = Table(title=f"Projections ({scoring.upper()})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Pts", justify="right", style="yellow")
    table.add_column("Pass Yds", justify="right")
    table.add_column("Pass TD", justify="right")
    table.add_column("Rush Yds", justify="right")
    table.add_column("Rush TD", justify="right")
    table.add_column("Rec", justify="right")
    table.add_column("Rec Yds", justify="right")
    table.add_column("Rec TD", justify="right")

    for p in players:
        table.add_row(
            str(p.get("rank", "")),
            p.get("player_name", ""),
            p.get("position", ""),
            p.get("team", ""),
            f"{p.get('points', 0):.1f}",
            f"{p.get('pass_yds', 0):.0f}",
            f"{p.get('pass_tds', 0):.1f}",
            f"{p.get('rush_yds', 0):.0f}",
            f"{p.get('rush_tds', 0):.1f}",
            f"{p.get('receptions', 0):.1f}",
            f"{p.get('rec_yds', 0):.0f}",
            f"{p.get('rec_tds', 0):.1f}",
        )
    console.print(table)


def trade_table(analysis: dict) -> None:
    table = Table(title="Trade Analysis")
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


def startsit_table(result: dict) -> None:
    table = Table(title="Start/Sit Recommendation")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Matchup")
    table.add_column("Verdict", style="yellow bold")

    for p in result.get("players", []):
        table.add_row(
            p.get("name", ""),
            p.get("position", ""),
            p.get("team", ""),
            p.get("matchup", ""),
            p.get("verdict", ""),
        )

    if result.get("analysis"):
        console.print(f"\n[dim]{result['analysis']}[/dim]")
    console.print(table)


def player_info_card(player: dict, articles: list[dict]) -> None:
    name = player.get("name", "Unknown")
    pos = player.get("position", "")
    team = player.get("team", "") or "Free Agent"
    status = player.get("status") or "Active"

    header = Text()
    header.append(f"{name}", style="bold white")
    header.append(f"  {pos}", style="cyan")
    header.append(f"  {team}", style="green")
    header.append(f"  ({status})", style="dim")

    if articles:
        news = Table(show_header=True, box=None, padding=(0, 2))
        news.add_column("Date", style="dim", no_wrap=True)
        news.add_column("Title", style="bold")
        news.add_column("Link", style="cyan")
        for a in articles:
            news.add_row(a.get("date", ""), a.get("title", ""), a.get("link", ""))
        console.print(Panel(news, title=str(header), subtitle="Recent News", border_style="blue"))
    else:
        console.print(Panel("[dim]No recent articles found.[/dim]", title=str(header), border_style="blue"))


def news_table(articles: list[dict]) -> None:
    table = Table(title="Fantasy Footballers News")
    table.add_column("Date", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Link", style="cyan")

    for a in articles:
        table.add_row(
            a.get("date", ""),
            a.get("title", ""),
            a.get("link", ""),
        )
    console.print(table)

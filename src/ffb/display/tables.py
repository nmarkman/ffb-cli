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


def bye_weeks_table(rows: list[dict]) -> None:
    table = Table(title="2026 Bye Weeks")
    table.add_column("Week", justify="right", style="yellow bold")
    table.add_column("Team", style="bold")
    table.add_column("Abbr", style="cyan")

    for r in rows:
        table.add_row(
            str(r.get("bye_week", "")),
            r.get("name", ""),
            r.get("key", ""),
        )
    console.print(table)


def sos_table(rows: list[dict], highlight_position: str | None = None) -> None:
    """32-team SoS grid. Each *_total is total fantasy points allowed at that
    position (higher = easier schedule)."""
    label = f", sorted by {highlight_position}" if highlight_position else ""
    table = Table(title=f"2026 Strength of Schedule{label}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Team", style="bold")
    table.add_column("Abbr", style="cyan")
    table.add_column("Bye", justify="right", style="dim")
    pos_columns = [
        ("qb_total", "QB"),
        ("rb_total", "RB"),
        ("wr_total", "WR"),
        ("te_total", "TE"),
        ("k_total", "K"),
        ("d_total", "DST"),
    ]
    for _, label in pos_columns:
        style = "yellow bold" if highlight_position and label == highlight_position else None
        table.add_column(label, justify="right", style=style)

    for i, r in enumerate(rows, 1):
        cells = [
            str(i),
            r.get("name", ""),
            r.get("team", ""),
            str(r.get("bye_week", "")),
        ]
        for key, _ in pos_columns:
            val = r.get(key, "")
            try:
                cells.append(f"{float(val):.1f}")
            except (TypeError, ValueError):
                cells.append(str(val))
        table.add_row(*cells)
    console.print(table)


def red_zone_table(rows: list[dict]) -> None:
    table = Table(title="Red Zone Usage")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Season", style="dim")
    table.add_column("RZ Tgts", justify="right")
    table.add_column("RZ Rec", justify="right")
    table.add_column("RZ TDs", justify="right", style="yellow")
    table.add_column("RZ Rush", justify="right")
    table.add_column("RZ RushTD", justify="right", style="yellow")
    table.add_column("RZ PassAtt", justify="right")
    table.add_column("RZ PassTD", justify="right", style="yellow")

    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("fantasy_position", ""),
            r.get("team", "") or "",
            str(r.get("season", "")),
            _fmt_num(r.get("red_zone_receiving_targets")),
            _fmt_num(r.get("red_zone_receptions")),
            _fmt_num(r.get("red_zone_receiving_touchdowns")),
            _fmt_num(r.get("red_zone_rushing_attempts")),
            _fmt_num(r.get("red_zone_rushing_touchdowns")),
            _fmt_num(r.get("red_zone_passing_attempts")),
            _fmt_num(r.get("red_zone_passing_touchdowns")),
        )
    console.print(table)


def best_ball_table(rows: list[dict]) -> None:
    table = Table(title="Best Ball Rankings (DFS Pass)")
    table.add_column("ADP", justify="right", style="yellow bold")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Bye", justify="right", style="dim")
    table.add_column("Betz", justify="right")
    table.add_column("Borg", justify="right")

    for r in rows:
        table.add_row(
            _fmt_num(r.get("adp")),
            r.get("name", ""),
            r.get("fantasy_position", ""),
            r.get("team", "") or "",
            str(r.get("bye_week", "")),
            _fmt_int(r.get("betz")),
            _fmt_int(r.get("borg")),
        )
    console.print(table)


def felix_table(rows: list[dict]) -> None:
    table = Table(title="F.E.L.I.X. Scores")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Exp", justify="right", style="dim")
    table.add_column("FELIX", justify="right", style="yellow bold")
    table.add_column("Pctile", justify="right")
    table.add_column("Peak", justify="right")
    table.add_column("Reliability", justify="right")

    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("fantasy_position", ""),
            r.get("team", "") or "",
            str(r.get("experience", "") or ""),
            _fmt_num(r.get("felix_score")),
            _fmt_num(r.get("felix_percentile")),
            _fmt_num(r.get("felix_peak")),
            _fmt_num(r.get("felix_reliability")),
        )
    console.print(table)


def _fmt_num(val, places: int = 1) -> str:
    if val is None or val == "":
        return ""
    try:
        return f"{float(val):.{places}f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_int(val) -> str:
    if val is None or val == "":
        return ""
    try:
        return str(int(float(val)))
    except (TypeError, ValueError):
        return str(val)

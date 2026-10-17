from datetime import datetime, timezone

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


def enriched_rankings_table(players: list[dict], scoring: str) -> None:
    """Rankings with the richer global-blob fields: analyst risk (1-10, lower is
    safer), upside (1-10), and projected targets."""
    table = Table(title=f"Rankings ({scoring.upper()}) , enriched")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Tier", justify="right")
    table.add_column("Pts", justify="right", style="yellow")
    table.add_column("Risk", justify="right")
    table.add_column("Upside", justify="right")
    table.add_column("Tgts", justify="right")
    table.add_column("Bye", justify="right", style="dim")
    for p in players:
        table.add_row(
            str(p.get("rank", "")),
            p.get("player_name", ""),
            p.get("position", ""),
            p.get("team", ""),
            str(p.get("tier", "")),
            f"{p.get('points', 0):.1f}",
            _fmt_num(p.get("risk")),
            _fmt_num(p.get("upside")),
            _fmt_num(p.get("targets"), 0),
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


def startsit_table(players: list[dict], *, week: int, scoring: str) -> None:
    # Kept narrow enough for an 80-column terminal; the per-analyst ranks and
    # the over/under are in --json.
    table = Table(title=f"Who Should I Start? Week {week} ({scoring.upper()})")
    table.add_column("", style="bold")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Matchup")
    table.add_column("Proj", justify="right", style="yellow")
    table.add_column("Rk", justify="right")
    table.add_column("Spread", justify="right")
    table.add_column("Impl", justify="right")
    table.add_column("Status", style="red")

    styles = {"START": "[green]START[/green]", "SIT": "[dim]SIT[/dim]"}
    for p in players:
        verdict = p.get("verdict", "")
        matchup = p.get("matchup", "")
        if p.get("team") and matchup not in ("BYE", "-"):
            matchup = f"{p['team']} {matchup}"
        table.add_row(
            styles.get(verdict, f"[red]{verdict}[/red]"),
            p.get("name", ""),
            p.get("position", ""),
            matchup,
            _fmt_num(p.get("points"), 1),
            _fmt_int(p.get("rank")),
            _fmt_spread(p.get("spread")),
            _fmt_num(p.get("implied_total"), 1),
            p.get("injury_status") or "",
        )
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


def value_scout_table(rows: list[dict]) -> None:
    table = Table(title="Value Scout (ADP across formats)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("ADP", justify="right", style="yellow")
    table.add_column("PPR ADP", justify="right")
    table.add_column("2QB ADP", justify="right")
    table.add_column("Dyn ADP", justify="right")
    table.add_column("Bye", justify="right", style="dim")
    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("fantasy_position", ""),
            r.get("team", "") or "",
            _fmt_num(r.get("adp"), 1),
            _fmt_num(r.get("adp_ppr"), 1),
            _fmt_num(r.get("adp_2qb"), 1),
            _fmt_num(r.get("adp_dynasty"), 1),
            str(r.get("bye_week", "") or ""),
        )
    console.print(table)


def market_share_table(rows: list[dict], season: int) -> None:
    table = Table(title=f"Market Share ({season}, share of team usage)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Gms", justify="right", style="dim")
    table.add_column("Tgt %", justify="right", style="yellow")
    table.add_column("Rush %", justify="right")
    table.add_column("RecYd %", justify="right")
    table.add_column("Pts %", justify="right")
    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("fantasy_position", ""),
            r.get("team", "") or "",
            str(r.get("games", "")),
            _fmt_pct(r.get("target_share")),
            _fmt_pct(r.get("rush_share")),
            _fmt_pct(r.get("rec_yd_share")),
            _fmt_pct(r.get("points_share")),
        )
    console.print(table)


def target_share_table(rows: list[dict], season: int) -> None:
    table = Table(title=f"Target Breakdown ({season}, team target distribution)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Team", style="bold")
    table.add_column("Abbr", style="cyan")
    table.add_column("Tgts/Gm", justify="right", style="dim")
    table.add_column("WR %", justify="right", style="yellow")
    table.add_column("RB %", justify="right")
    table.add_column("TE %", justify="right")
    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("key", "") or "",
            _fmt_num(r.get("targets_per_game"), 1),
            _fmt_pct(r.get("wr_share")),
            _fmt_pct(r.get("rb_share")),
            _fmt_pct(r.get("te_share")),
        )
    console.print(table)


def free_agency_table(rows: list[dict]) -> None:
    table = Table(title="UDK Free Agency Review")
    table.add_column("Player", style="bold", no_wrap=True)
    table.add_column("Move", style="cyan", overflow="fold")
    table.add_column("Analysis", overflow="fold")
    for r in rows:
        table.add_row(r.get("name", ""), r.get("move", ""), r.get("blurb", ""))
    console.print(table)


def player_report_table(rows: list[dict], *, title: str) -> None:
    table = Table(title=title)
    table.add_column("Player", style="bold", no_wrap=True)
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Report", overflow="fold")
    for r in rows:
        table.add_row(
            r.get("name", ""),
            r.get("position", ""),
            r.get("team", "") or "",
            r.get("blurb", ""),
        )
    console.print(table)


def narrative_panels(sections: list[dict], *, title: str) -> None:
    """Render heading/body sections as stacked panels (narrative pages)."""
    console.print(f"[bold]{title}[/bold]\n")
    for s in sections:
        console.print(Panel(s.get("body", ""), title=s.get("heading", ""), border_style="blue"))


def prose_panel(paragraphs: list[str], *, title: str) -> None:
    """Render a list of paragraphs as one readable block."""
    console.print(Panel("\n\n".join(paragraphs), title=title, border_style="blue"))


def expert_list_table(rows: list[dict], *, list_type: str) -> None:
    table = Table(title=f"UDK Expert List: {list_type.title()}")
    table.add_column("Player", style="bold", no_wrap=True)
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("ADP", justify="right", style="yellow")
    table.add_column("Why", overflow="fold")
    for r in rows:
        table.add_row(
            r.get("name", ""),
            r.get("position", ""),
            r.get("team", "") or "",
            _fmt_num(r.get("adp"), 2),
            r.get("blurb", ""),
        )
    console.print(table)


def consistency_table(rows: list[dict], *, season: int, scoring: str) -> None:
    table = Table(title=f"Consistency ({season}, {scoring.upper()})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Gms", justify="right", style="dim")
    table.add_column("PPG", justify="right", style="yellow")
    table.add_column("Start%", justify="right")
    table.add_column("Boom%", justify="right", style="green")
    table.add_column("Bust%", justify="right", style="red")
    table.add_column("StdDev", justify="right")
    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("fantasy_position", ""),
            r.get("team", "") or "",
            str(r.get("games", "")),
            _fmt_num(r.get("ppg"), 1),
            _fmt_pct(r.get("start_pct")),
            _fmt_pct(r.get("boom_pct")),
            _fmt_pct(r.get("bust_pct")),
            _fmt_num(r.get("stdev"), 1),
        )
    console.print(table)


def consistency_weekly_table(player: dict, weeks: list[dict], *, scoring: str) -> None:
    title = f"{player.get('name', '')} ({player.get('fantasy_position', '')} {player.get('team', '')}) , {player.get('season', '')} {scoring.upper()} game log"
    table = Table(title=title)
    table.add_column("Wk", justify="right", style="dim")
    table.add_column("Opp", style="cyan")
    table.add_column("Pts", justify="right", style="yellow")
    table.add_column("Pos Rank", justify="right")
    table.add_column("Started", justify="center")
    for w in weeks:
        table.add_row(
            str(w.get("week", "")),
            w.get("opponent", "") or "-",
            _fmt_num(w.get("points"), 1),
            (f"{w.get('position_rank')}" if w.get("position_rank") else "-"),
            "Y" if w.get("started") else "-",
        )
    console.print(table)


def weekly_rankings_table(rows: list[dict], *, week: int, position: str, scoring: str) -> None:
    table = Table(title=f"Week {week} Premium Rankings: {position} ({scoring.upper()})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    if position == "FLEX":
        table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Matchup")
    table.add_column("Proj", justify="right", style="yellow")
    table.add_column("Andy", justify="right", style="dim")
    table.add_column("Jason", justify="right", style="dim")
    table.add_column("Mike", justify="right", style="dim")
    table.add_column("Status", style="red")
    for r in rows:
        cells = [str(r.get("rank", "")), r.get("name", "")]
        if position == "FLEX":
            cells.append(r.get("position", ""))
        cells += [
            r.get("team", ""),
            r.get("matchup", ""),
            _fmt_num(r.get("points"), 1),
            _fmt_int(r.get("andy_rank")),
            _fmt_int(r.get("jason_rank")),
            _fmt_int(r.get("mike_rank")),
            r.get("injury_status") or "",
        ]
        table.add_row(*cells)
    console.print(table)


def ros_rankings_table(rows: list[dict], *, week: int, position: str, scoring: str) -> None:
    table = Table(title=f"Rest-of-Season Rankings: {position} ({scoring.upper()}, as of Week {week})")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    if position == "FLEX":
        table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("ROS Pts", justify="right", style="yellow")
    table.add_column("Gms", justify="right", style="dim")
    table.add_column("PPG", justify="right")
    table.add_column("Andy", justify="right", style="dim")
    table.add_column("Jason", justify="right", style="dim")
    table.add_column("Mike", justify="right", style="dim")
    for r in rows:
        cells = [str(r.get("rank", "")), r.get("name", "")]
        if position == "FLEX":
            cells.append(r.get("position", ""))
        cells += [
            r.get("team", ""),
            _fmt_num(r.get("points"), 1),
            _fmt_int(r.get("remaining_games")),
            _fmt_num(r.get("ppg"), 1),
            _fmt_int(r.get("andy_rank")),
            _fmt_int(r.get("jason_rank")),
            _fmt_int(r.get("mike_rank")),
        ]
        table.add_row(*cells)
    console.print(table)


def waiver_rankings_table(rows: list[dict], *, week: int, position: str) -> None:
    table = Table(title=f"Week {week} Waiver Wire Rankings: {position}")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Matchup")
    table.add_column("FAAB", justify="right", style="yellow")
    table.add_column("Andy", justify="right", style="dim")
    table.add_column("Jason", justify="right", style="dim")
    table.add_column("Mike", justify="right", style="dim")
    table.add_column("Note", style="magenta")
    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("name", ""),
            r.get("position", ""),
            r.get("team", ""),
            r.get("matchup", ""),
            r.get("faab", "-"),
            _fmt_int(r.get("andy_rank")),
            _fmt_int(r.get("jason_rank")),
            _fmt_int(r.get("mike_rank")),
            "STASH" if r.get("stash") else "",
        )
    console.print(table)


def stream_finder_table(rows: list[dict], *, position: str, through_week: int,
                        upcoming: list[int], adjusted: bool) -> None:
    subject = "Offense" if position == "DST" else "Defense"
    basis = "schedule-adjusted" if adjusted else "raw points allowed"
    table = Table(title=f"Stream Finder vs {position}, Weeks 1-{through_week} ({basis})")
    table.add_column("#", justify="right", style="dim")
    table.add_column(subject, style="bold")
    table.add_column("Gms", justify="right", style="dim")
    table.add_column("PAE", justify="right", style="yellow" if adjusted else "dim")
    table.add_column("FPA", justify="right", style="dim" if adjusted else "yellow")
    for w in upcoming:
        table.add_column(f"Wk {w}", justify="center", style="cyan")
    for r in rows:
        table.add_row(
            str(r.get("rank", "")),
            r.get("team", ""),
            str(r.get("games", "")),
            _fmt_spread(r.get("pae")),
            _fmt_num(r.get("avg_allowed"), 1),
            *[r.get("upcoming", {}).get(str(w), "") for w in upcoming],
        )
    console.print(table)
    console.print(
        f"[dim]Week columns show the opponent ('@' = away). Opponents of the top rows are "
        f"the {position} streams.[/dim]"
    )


def games_table(rows: list[dict], *, week: int, byes: list[str]) -> None:
    table = Table(title=f"Week {week} Games")
    table.add_column("Kickoff", style="dim")
    table.add_column("Matchup", style="bold")
    table.add_column("Spread", justify="right")
    table.add_column("O/U", justify="right", style="yellow")
    table.add_column("Implied", justify="right")
    table.add_column("Weather")
    for g in rows:
        spread = g.get("home_spread")
        line = f"{g['home']} {_fmt_spread(spread)}" if spread is not None else "-"
        implied = (
            f"{g['away']} {_fmt_num(g.get('away_implied'), 1)} / {g['home']} {_fmt_num(g.get('home_implied'), 1)}"
            if g.get("home_implied") is not None else "-"
        )
        status = g.get("status") or ""
        table.add_row(
            status if status.startswith("F") else _fmt_kickoff(g.get("date")),
            f"{g['away']} @ {g['home']}",
            line,
            _fmt_num(g.get("over_under"), 1),
            implied,
            _fmt_weather(g.get("weather")),
        )
    console.print(table)
    if byes:
        console.print(f"[dim]Byes: {', '.join(byes)}[/dim]")


def player_news_table(rows: list[dict], *, full: bool) -> None:
    if full:
        for r in rows:
            status = f" [red]{r['injury_status']}[/red]" if r.get("injury_status") else ""
            body = r.get("notes") or ""
            if r.get("analysis"):
                body += f"\n\n[dim]{r['analysis']}[/dim]"
            console.print(Panel(
                body,
                title=f"{r.get('name', '')} ({r.get('position', '')} {r.get('team', '')}): {r.get('headline', '')}{status}",
                subtitle=r.get("time_ago") or "",
            ))
        return
    table = Table(title="Player News")
    table.add_column("When", style="dim")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Headline")
    table.add_column("Status", style="red")
    for r in rows:
        table.add_row(
            r.get("time_ago") or "",
            r.get("name", ""),
            r.get("position", ""),
            r.get("team", ""),
            r.get("headline", ""),
            r.get("injury_status") or "",
        )
    console.print(table)


def dfs_table(rows: list[dict], *, site: str, sort_by: str) -> None:
    table = Table(title=f"{site} Weekly Values (sorted by {sort_by})")
    table.add_column("Player", style="bold")
    table.add_column("Pos", style="cyan")
    table.add_column("Team", style="green")
    table.add_column("Opp")
    table.add_column("Opp Rk", justify="right", style="dim")
    table.add_column("Salary", justify="right")
    table.add_column("Proj", justify="right", style="yellow")
    table.add_column("Pts/$1K", justify="right", style="green")
    table.add_column("Status", style="red")
    for r in rows:
        table.add_row(
            r.get("name", ""),
            r.get("position", ""),
            r.get("team", ""),
            r.get("opponent") or "",
            _fmt_int(r.get("opp_pos_rank")),
            f"${r.get('salary', 0):,}",
            _fmt_num(r.get("points"), 1),
            _fmt_num(r.get("value"), 2),
            r.get("injury_status") or "",
        )
    console.print(table)


def _fmt_spread(val) -> str:
    if val is None or val == "":
        return ""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return str(val)
    return "PK" if v == 0 else f"{v:+.1f}"


def _fmt_kickoff(date: str | None) -> str:
    """The site's game times are UTC ("2026-10-18 17:00:00"); show local."""
    if not date:
        return ""
    try:
        dt = datetime.fromisoformat(date).replace(tzinfo=timezone.utc).astimezone()
    except ValueError:
        return date
    # %I, not %-I: the dash flag isn't portable (fails on Windows).
    return dt.strftime("%a %I:%M %p").replace(" 0", " ", 1)


def _fmt_weather(wx: dict | None) -> str:
    if not wx:
        return ""
    if wx.get("dome"):
        return "Dome"
    parts = [wx.get("summary") or ""]
    if wx.get("temperature") is not None:
        parts.append(f"{wx['temperature']:.0f}F")
    if wx.get("wind_mph") is not None:
        parts.append(f"wind {wx['wind_mph']:.0f}")
    if wx.get("precip_pct"):
        parts.append(f"{wx['precip_pct']}% precip")
    return ", ".join(p for p in parts if p)


def _fmt_pct(val) -> str:
    if val is None or val == "":
        return ""
    try:
        return f"{float(val) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(val)


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

import typer

from .commands import login, players
from .commands import dynasty as dynasty_pkg
from .commands.rankings import rankings_command
from .commands.projections import projections_command
from .commands.trade import trade_command
from .commands.startsit import startsit_command
from .commands.news import news_command
from .commands.bye_weeks import bye_weeks_command
from .commands.sos import sos_command
from .commands.red_zone import red_zone_command
from .commands.best_ball import best_ball_command
from .commands.top200 import top200_command
from .commands.superflex import superflex_command
from .commands.flex import flex_command
from .commands.value_scout import value_scout_command
from .commands.market_share import market_share_command
from .commands.target_share import target_share_command
from .commands.free_agency import free_agency_command
from .commands.coaching_changes import coaching_changes_command
from .commands.rookie_report import rookie_report_command
from .commands.consistency import consistency_command
from .commands.experts import experts_command
from .commands.tools import tools_command

app = typer.Typer(
    name="ffb",
    help="""CLI for The Fantasy Footballers (thefantasyfootballers.com).

Wraps their premium tools (rankings, projections, trade analyzer, start/sit)
and public features (player search, news).

\b
AUTH: Most commands require a premium account. Run `ffb login` first to
authenticate via browser. Session is saved to ~/.config/ffb/session.json
and lasts ~24 hours. Public commands (players, news) work without login.

\b
COMMANDS REQUIRING LOGIN: rankings, projections, trade, start-sit, dynasty,
                          bye-weeks, sos, red-zone, best-ball,
                          top200, superflex, flex, value-scout, market-share,
                          target-share, consistency, free-agency,
                          coaching-changes, rookie-report, experts
COMMANDS WITHOUT LOGIN:   players, news, tools

\b
TOOLS MAP: Run `ffb tools` to see every Fantasy Footballers tool, what's free
vs paywalled (UDK / UDK+ / DFS Pass), and which CLI command covers it.

\b
DYNASTY: Run `ffb dynasty --help` for the full dynasty toolkit (rankings,
startup, rookies, trade values, scouting reports, FELIX, etc.). Requires UDK+.

\b
EXAMPLES:
  ffb login                                  # authenticate via browser
  ffb players search "justin jefferson"      # fuzzy player search (no login)
  ffb rankings QB -s ppr -n 10               # top 10 QB rankings, PPR scoring
  ffb top200 -n 50                           # overall top 50 draft board
  ffb superflex --qb-boost 1.4               # superflex board with QB premium
  ffb flex -n 60                             # top 60 RB/WR/TE flex options
  ffb projections RB                         # RB stat projections
  ffb trade --give "Kelce, Lamb" --get "Chase"  # analyze a trade
  ffb start-sit "Ja'Marr Chase" "CeeDee Lamb"  # start/sit comparison
  ffb bye-weeks -w 8                         # teams on bye in week 8
  ffb sos WR                                 # easiest WR schedules
  ffb red-zone RB -n 30                      # top 30 RBs by RZ usage
  ffb best-ball WR                           # best-ball WR rankings
  ffb value-scout RB                         # ADP across formats
  ffb market-share WR                        # WR share of team usage
  ffb target-share -s te                     # teams that target TEs most
  ffb consistency RB -s boom                 # RB boom-rate leaders
  ffb experts sleepers                       # the Footballers' sleeper picks
  ffb rankings WR --enrich                   # rankings + risk/upside/targets
  ffb tools --tier free                      # what works without an account
  ffb news -n 5                              # latest 5 articles (no login)
  ffb dynasty rankings                       # dynasty consensus rankings
  ffb dynasty startup --superflex -n 50      # SuperFlex startup draft board
  ffb dynasty rookies                        # 2026 rookie class
  ffb dynasty felix WR                       # F.E.L.I.X. dynasty scores by WR
  ffb dynasty trade --give "Mahomes" --get "Daniels"  # dynasty trade values

\b
All commands support --json for machine-readable output.
""",
    no_args_is_help=True,
)

app.add_typer(login.app, name="login")
app.add_typer(players.app, name="players")
app.add_typer(dynasty_pkg.app, name="dynasty")
app.command(name="rankings")(rankings_command)
app.command(name="projections")(projections_command)
app.command(name="trade")(trade_command)
app.command(name="start-sit")(startsit_command)
app.command(name="news")(news_command)
app.command(name="bye-weeks")(bye_weeks_command)
app.command(name="sos")(sos_command)
app.command(name="red-zone")(red_zone_command)
app.command(name="best-ball")(best_ball_command)
app.command(name="top200")(top200_command)
app.command(name="superflex")(superflex_command)
app.command(name="flex")(flex_command)
app.command(name="value-scout")(value_scout_command)
app.command(name="market-share")(market_share_command)
app.command(name="target-share")(target_share_command)
app.command(name="free-agency")(free_agency_command)
app.command(name="coaching-changes")(coaching_changes_command)
app.command(name="rookie-report")(rookie_report_command)
app.command(name="consistency")(consistency_command)
app.command(name="experts")(experts_command)
app.command(name="tools")(tools_command)


if __name__ == "__main__":
    app()

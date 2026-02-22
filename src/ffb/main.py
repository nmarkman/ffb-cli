import typer

from .commands import login, players
from .commands.rankings import rankings_command
from .commands.projections import projections_command
from .commands.trade import trade_command
from .commands.startsit import startsit_command
from .commands.news import news_command

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
COMMANDS REQUIRING LOGIN: rankings, projections, trade, start-sit
COMMANDS WITHOUT LOGIN:   players, news

\b
EXAMPLES:
  ffb login                                  # authenticate via browser
  ffb players search "justin jefferson"      # fuzzy player search (no login)
  ffb rankings QB -s ppr -n 10               # top 10 QB rankings, PPR scoring
  ffb projections RB                         # RB stat projections
  ffb trade --give "Kelce, Lamb" --get "Chase"  # analyze a trade
  ffb start-sit "Ja'Marr Chase" "CeeDee Lamb"  # start/sit comparison
  ffb news -n 5                              # latest 5 articles (no login)

\b
All commands support --json for machine-readable output.
""",
    no_args_is_help=True,
)

app.add_typer(login.app, name="login")
app.add_typer(players.app, name="players")
app.command(name="rankings")(rankings_command)
app.command(name="projections")(projections_command)
app.command(name="trade")(trade_command)
app.command(name="start-sit")(startsit_command)
app.command(name="news")(news_command)


if __name__ == "__main__":
    app()

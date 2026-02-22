import typer

from .commands import login, players, rankings, projections, trade, startsit, news

app = typer.Typer(
    name="ffb",
    help="Fantasy Footballers CLI - access premium tools from your terminal.",
    no_args_is_help=True,
)

app.add_typer(login.app, name="login")
app.add_typer(players.app, name="players")
app.add_typer(rankings.app, name="rankings")
app.add_typer(projections.app, name="projections")
app.add_typer(trade.app, name="trade")
app.add_typer(startsit.app, name="start-sit")
app.add_typer(news.app, name="news")


if __name__ == "__main__":
    app()

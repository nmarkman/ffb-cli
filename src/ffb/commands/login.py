import typer

from ..auth.login import run_login_flow
from ..auth.session import load_session, clear_session, session_age_hours
from ..api.client import get_client, AuthExpiredError

app = typer.Typer(help="Manage authentication.")


@app.callback(invoke_without_command=True)
def login(
    ctx: typer.Context,
    status: bool = typer.Option(False, "--status", help="Check login status"),
    logout: bool = typer.Option(False, "--logout", help="Clear saved session"),
):
    if ctx.invoked_subcommand is not None:
        return

    if logout:
        clear_session()
        typer.echo("Logged out. Session cleared.")
        return

    if status:
        session = load_session()
        if not session:
            typer.echo("Not logged in.")
            raise typer.Exit(1)
        age = session_age_hours()
        typer.echo(f"Logged in (session age: {age:.1f}h)")
        # Verify with API
        try:
            client = get_client(require_auth=True)
            resp = client.get("/ffb/v1/auth")
            typer.echo("Session is valid.")
        except AuthExpiredError:
            typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
            raise typer.Exit(1)
        except Exception as e:
            typer.echo(f"Could not verify session: {e}", err=True)
        return

    run_login_flow()

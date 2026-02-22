import os

import typer

from ..auth.login import run_login_flow, run_headless_login_flow
from ..auth.session import load_session, clear_session, session_age_hours
from ..api.client import get_client, AuthExpiredError

app = typer.Typer(help="""Manage authentication with The Fantasy Footballers.

\b
Running `ffb login` with no flags opens a headed Chromium browser window.
You must manually log in with your premium account credentials in that
browser. The CLI captures cookies and an API token once login completes
(up to 2 minute timeout). This is the ONLY command that requires a browser.

\b
HEADLESS MODE (for AI agents / CI):
  Use --headless to log in without a visible browser. Credentials can be
  passed via --username/--password flags or FFB_USERNAME/FFB_PASSWORD
  environment variables.

\b
Session is saved to ~/.config/ffb/session.json and lasts ~24 hours.
If any command returns a 401/403 error, re-run `ffb login`.

\b
EXAMPLES:
  ffb login                                          # interactive browser login
  ffb login --headless -u me@email.com -p hunter2    # headless with flags
  FFB_USERNAME=me@email.com FFB_PASSWORD=hunter2 ffb login --headless  # env vars
  ffb login --status                                 # check if session is valid
  ffb login --logout                                 # clear saved session
""")


@app.callback(invoke_without_command=True)
def login(
    ctx: typer.Context,
    status: bool = typer.Option(False, "--status", help="Check login status"),
    logout: bool = typer.Option(False, "--logout", help="Clear saved session"),
    headless: bool = typer.Option(
        False, "--headless", help="Headless login (no browser window). For AI agents and CI."
    ),
    username: str = typer.Option(
        None, "--username", "-u",
        help="Username/email for headless login. Falls back to FFB_USERNAME env var.",
    ),
    password: str = typer.Option(
        None, "--password", "-p",
        help="Password for headless login. Falls back to FFB_PASSWORD env var.",
    ),
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

    if headless:
        username = username or os.environ.get("FFB_USERNAME")
        password = password or os.environ.get("FFB_PASSWORD")
        if not username or not password:
            typer.echo(
                "Headless login requires credentials. Provide --username/--password "
                "or set FFB_USERNAME/FFB_PASSWORD environment variables.",
                err=True,
            )
            raise typer.Exit(1)
        run_headless_login_flow(username, password)
    else:
        run_login_flow()

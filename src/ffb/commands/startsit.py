import json
from typing import Annotated

import typer

from ..api.client import get_client, AuthExpiredError
from ..api.endpoints import START_SIT
from ..display.tables import startsit_table, console

app = typer.Typer(help="Start/Sit comparisons.")


@app.callback(invoke_without_command=True)
def startsit(
    ctx: typer.Context,
    players: Annotated[list[str], typer.Argument(help="2-4 player names to compare")],
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Compare players for start/sit decisions (2-4 players)."""
    if len(players) < 2 or len(players) > 4:
        typer.echo("Provide 2-4 player names to compare.", err=True)
        raise typer.Exit(1)

    try:
        client = get_client(require_auth=True)
        resp = client.post(START_SIT, json={"players": players})
        data = resp.json()
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    if output_json:
        console.print_json(json.dumps(data))
    else:
        startsit_table(data)

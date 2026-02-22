import json
from typing import Annotated

import typer

from ..api.client import get_client, AuthExpiredError
from ..api.endpoints import START_SIT
from ..display.tables import startsit_table, console


def startsit_command(
    players: Annotated[list[str], typer.Argument(help="2-4 player names to compare")],
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Compare 2-4 players for start/sit decisions. Requires login.

    \b
    Pass player names as separate arguments (quote names with spaces).
    Returns a recommendation for which player(s) to start.
    NOTE: This tool is only available during the NFL season.

    \b
    EXAMPLES:
      ffb start-sit "Ja'Marr Chase" "CeeDee Lamb"
      ffb start-sit "Josh Allen" "Jalen Hurts" "Lamar Jackson"
      ffb start-sit "Derrick Henry" "Saquon Barkley" --json
    """
    if len(players) < 2 or len(players) > 4:
        typer.echo("Provide 2-4 player names to compare.", err=True)
        raise typer.Exit(1)

    try:
        client = get_client(require_auth=True)
        slugs = [n.lower().replace("'", "").replace(" ", "-") for n in players]
        uri = "/start-sit/" + "-vs-".join(slugs) + "/"
        resp = client.post(START_SIT, json={
            "uri": uri,
            "rankings_type": "weekly",
            "player_ids": [],
        })
        data = resp.json()
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)

    # API returns ["error", "message"] during offseason
    if isinstance(data, list) and len(data) >= 2 and data[0] == "error":
        typer.echo("Start/Sit tool is not available right now (offseason). It opens the week before kickoff.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(data))
    else:
        startsit_table(data)

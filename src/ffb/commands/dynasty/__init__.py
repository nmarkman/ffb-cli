"""Dynasty Pass subcommands.

Every command here scrapes a page under /2026-dynasty-pass/. All commands
require login via UDK+ subscription. Cookie-only auth, no nonce header needed.
"""
import typer

from . import (
    draft_results,
    felix,
    free_agents,
    injuries,
    lifecycles,
    mock_drafts,
    movers,
    open_page,
    production,
    rankings,
    rookie_overview,
    rookies,
    scouting,
    startup,
    team_opportunity,
    tips,
    trade,
    trade_targets,
)

app = typer.Typer(
    name="dynasty",
    help="""Dynasty Pass commands. Requires UDK+ subscription.

\b
Wraps all 15 surfaces of /2026-dynasty-pass/.

\b
EXAMPLES:
  ffb dynasty rankings QB                # dynasty rankings (1QB)
  ffb dynasty rankings --superflex       # SuperFlex / 2QB rankings
  ffb dynasty startup -n 100             # startup draft board, top 100
  ffb dynasty rookies                    # 2026 rookie class rankings
  ffb dynasty trade --give "Kelce" --get "McBride"  # dynasty trade values
  ffb dynasty trade-targets              # weekly dynasty trade targets
  ffb dynasty production "Bijan"         # production profile lookup
  ffb dynasty scouting "Jeremiyah Love"  # 2026 prospect scouting report
  ffb dynasty team-opportunity           # depth chart opportunity scores
  ffb dynasty movers                     # risers and fallers
  ffb dynasty mock                       # recent rookie mock drafts
  ffb dynasty free-agents                # free agent tracker
  ffb dynasty injuries                   # dynasty-impact injuries
  ffb dynasty draft-results              # 2026 NFL draft results
  ffb dynasty tips                       # baller dynasty tips
  ffb dynasty lifecycles                 # dynasty lifecycles by position
  ffb dynasty felix WR                   # F.E.L.I.X. dynasty scores
""",
    no_args_is_help=True,
)

app.command(name="rankings")(rankings.dynasty_rankings_command)
app.command(name="startup")(startup.dynasty_startup_command)
app.command(name="rookies")(rookies.dynasty_rookies_command)
app.command(name="rookie-overview")(rookie_overview.dynasty_rookie_overview_command)
app.command(name="production")(production.dynasty_production_command)
app.command(name="trade")(trade.dynasty_trade_command)
app.command(name="trade-targets")(trade_targets.dynasty_trade_targets_command)
app.command(name="team-opportunity")(team_opportunity.dynasty_team_opportunity_command)
app.command(name="movers")(movers.dynasty_movers_command)
app.command(name="mock")(mock_drafts.dynasty_mock_drafts_command)
app.command(name="scouting")(scouting.dynasty_scouting_command)
app.command(name="free-agents")(free_agents.dynasty_free_agents_command)
app.command(name="injuries")(injuries.dynasty_injuries_command)
app.command(name="draft-results")(draft_results.dynasty_draft_results_command)
app.command(name="tips")(tips.dynasty_tips_command)
app.command(name="lifecycles")(lifecycles.dynasty_lifecycles_command)
app.command(name="felix")(felix.dynasty_felix_command)
app.command(name="open")(open_page.dynasty_open_command)

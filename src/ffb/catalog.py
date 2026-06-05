"""Catalog of The Fantasy Footballers' tools and how the CLI maps to them.

Single source of truth for the `ffb tools` command. Each entry records the
tool, the access tier (what you must pay for), the CLI command that covers it
(or None if the CLI doesn't expose it), and a one-line summary.

Tiers
-----
- ``free``      : usable without an account.
- ``UDK``       : included with the Ultimate Draft Kit (redraft draft-prep).
- ``UDK+``      : the Dynasty Pass add-on (dynasty leagues).
- ``DFS Pass``  : the separate DFS / best-ball product.
- ``FootClan``  : in-season member tools (some bundled with the UDK).
"""
from __future__ import annotations

FREE = "free"
UDK = "UDK"
UDK_PLUS = "UDK+"
DFS = "DFS Pass"
FOOTCLAN = "FootClan"

# category, tool, tier, command (None = not exposed by the CLI), summary
CATALOG: list[dict] = [
    # ---- Free ----
    {"category": "Free", "tool": "Player Search", "tier": FREE, "command": "ffb players search", "summary": "Fuzzy player lookup with recent news"},
    {"category": "Free", "tool": "News / Podcast", "tier": FREE, "command": "ffb news", "summary": "Latest articles and episodes"},

    # ---- UDK draft board ----
    {"category": "Draft Board (UDK)", "tool": "Rankings (Tiered)", "tier": UDK, "command": "ffb rankings", "summary": "Positional rankings with tiers (add --enrich for risk/upside)"},
    {"category": "Draft Board (UDK)", "tool": "Premium Projections", "tier": UDK, "command": "ffb projections", "summary": "Stat projections, 3-analyst average"},
    {"category": "Draft Board (UDK)", "tool": "Top 200", "tier": UDK, "command": "ffb top200", "summary": "Overall cross-position draft board"},
    {"category": "Draft Board (UDK)", "tool": "Superflex Rankings", "tier": UDK, "command": "ffb superflex", "summary": "2QB / SuperFlex board with QB premium"},
    {"category": "Draft Board (UDK)", "tool": "Flex Rankings", "tier": UDK, "command": "ffb flex", "summary": "RB/WR/TE flex board"},
    {"category": "Draft Board (UDK)", "tool": "Value Scout", "tier": UDK, "command": "ffb value-scout", "summary": "ADP across redraft / PPR / 2QB / dynasty"},
    {"category": "Draft Board (UDK)", "tool": "Cheatsheet Creator", "tier": UDK, "command": None, "summary": "Interactive in-app draft cheatsheet builder"},
    {"category": "Draft Board (UDK)", "tool": "Video Profiles", "tier": UDK, "command": None, "summary": "Player video breakdowns (not text data)"},

    # ---- UDK research ----
    {"category": "Research (UDK)", "tool": "Market Share", "tier": UDK, "command": "ffb market-share", "summary": "Player share of team targets/rush/yards/points"},
    {"category": "Research (UDK)", "tool": "Target Breakdown", "tier": UDK, "command": "ffb target-share", "summary": "Team target distribution across WR/RB/TE"},
    {"category": "Research (UDK)", "tool": "Weekly Consistency", "tier": UDK, "command": "ffb consistency", "summary": "Start-worthy / boom / bust rates + weekly game log"},
    {"category": "Research (UDK)", "tool": "Red Zone Report", "tier": UDK, "command": "ffb red-zone", "summary": "Red-zone usage by player"},
    {"category": "Research (UDK)", "tool": "Strength of Schedule", "tier": UDK, "command": "ffb sos", "summary": "Team SoS grid by position"},
    {"category": "Research (UDK)", "tool": "Bye Weeks", "tier": UDK, "command": "ffb bye-weeks", "summary": "2026 bye weeks by team"},
    {"category": "Research (UDK)", "tool": "Free Agency Review", "tier": UDK, "command": "ffb free-agency", "summary": "Offseason signings with fantasy analysis"},
    {"category": "Research (UDK)", "tool": "Coaching Changes", "tier": UDK, "command": "ffb coaching-changes", "summary": "Fantasy impact of coaching moves"},
    {"category": "Research (UDK)", "tool": "Rookie Report", "tier": UDK, "command": "ffb rookie-report", "summary": "Scouting writeups for the rookie class"},
    {"category": "Research (UDK)", "tool": "Expert Lists", "tier": UDK, "command": "ffb experts", "summary": "Sleepers / Breakouts / Values / Busts"},

    # ---- Dynasty (UDK+) ----
    {"category": "Dynasty (UDK+)", "tool": "Rookie Rankings", "tier": UDK_PLUS, "command": "ffb dynasty rankings / rookies", "summary": "Dynasty + rookie rankings (1QB / SF)"},
    {"category": "Dynasty (UDK+)", "tool": "Startup Rankings", "tier": UDK_PLUS, "command": "ffb dynasty startup", "summary": "Startup draft board"},
    {"category": "Dynasty (UDK+)", "tool": "Rookie Class Overview", "tier": UDK_PLUS, "command": "ffb dynasty rookie-overview", "summary": "Narrative outlook on the rookie class"},
    {"category": "Dynasty (UDK+)", "tool": "Production Profiles", "tier": UDK_PLUS, "command": "ffb dynasty production", "summary": "College production profiles"},
    {"category": "Dynasty (UDK+)", "tool": "Team Opportunity", "tier": UDK_PLUS, "command": "ffb dynasty team-opportunity", "summary": "Depth-chart opportunity scores"},
    {"category": "Dynasty (UDK+)", "tool": "F.E.L.I.X. Scores", "tier": UDK_PLUS, "command": "ffb dynasty felix", "summary": "Rookie reliability metric"},
    {"category": "Dynasty (UDK+)", "tool": "Trade Analyzer", "tier": UDK_PLUS, "command": "ffb dynasty trade", "summary": "Dynasty trade values"},
    {"category": "Dynasty (UDK+)", "tool": "Trade Targets", "tier": UDK_PLUS, "command": "ffb dynasty trade-targets", "summary": "Weekly dynasty trade targets"},
    {"category": "Dynasty (UDK+)", "tool": "Risers & Fallers", "tier": UDK_PLUS, "command": "ffb dynasty movers", "summary": "Stock up / stock down"},
    {"category": "Dynasty (UDK+)", "tool": "Rookie Mock Drafts", "tier": UDK_PLUS, "command": "ffb dynasty mock", "summary": "Recent rookie mock drafts"},
    {"category": "Dynasty (UDK+)", "tool": "Scouting Reports", "tier": UDK_PLUS, "command": "ffb dynasty scouting", "summary": "Prospect scouting reports"},
    {"category": "Dynasty (UDK+)", "tool": "Free Agent Tracker", "tier": UDK_PLUS, "command": "ffb dynasty free-agents", "summary": "Dynasty-impact signings"},
    {"category": "Dynasty (UDK+)", "tool": "Injury Tracker", "tier": UDK_PLUS, "command": "ffb dynasty injuries", "summary": "Dynasty-impact injuries"},
    {"category": "Dynasty (UDK+)", "tool": "NFL Draft Results", "tier": UDK_PLUS, "command": "ffb dynasty draft-results", "summary": "2026 NFL draft picks"},
    {"category": "Dynasty (UDK+)", "tool": "Dynasty Tips", "tier": UDK_PLUS, "command": "ffb dynasty tips", "summary": "Baller dynasty strategy tips"},
    {"category": "Dynasty (UDK+)", "tool": "Dynasty Lifecycles", "tier": UDK_PLUS, "command": "ffb dynasty lifecycles", "summary": "Positional aging curves"},

    # ---- DFS Pass ----
    {"category": "DFS Pass", "tool": "Best Ball Rankings", "tier": DFS, "command": "ffb best-ball", "summary": "Best-ball rankings by ADP"},
    {"category": "DFS Pass", "tool": "Best Ball Primer", "tier": DFS, "command": None, "summary": "Strategy article (no data table)"},
    {"category": "DFS Pass", "tool": "Lineup Optimizer", "tier": DFS, "command": None, "summary": "In-season DFS optimizer (seasonal)"},

    # ---- In-season FootClan ----
    {"category": "In-Season (FootClan)", "tool": "Trade Analyzer", "tier": FOOTCLAN, "command": "ffb trade", "summary": "Redraft trade values"},
    {"category": "In-Season (FootClan)", "tool": "Start/Sit Tool", "tier": FOOTCLAN, "command": "ffb start-sit", "summary": "Weekly start/sit comparison (in-season)"},
    {"category": "In-Season (FootClan)", "tool": "Stream Finder", "tier": FOOTCLAN, "command": None, "summary": "Weekly streaming options (seasonal)"},
    {"category": "In-Season (FootClan)", "tool": "Rest-of-Season Ranks", "tier": FOOTCLAN, "command": None, "summary": "ROS rankings (seasonal)"},
]


def covered() -> list[dict]:
    return [e for e in CATALOG if e["command"]]


def uncovered() -> list[dict]:
    return [e for e in CATALOG if not e["command"]]


def coverage_summary() -> tuple[int, int]:
    """Return (covered_count, total_count)."""
    return len(covered()), len(CATALOG)

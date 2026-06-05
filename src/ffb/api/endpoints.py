"""API endpoint path constants."""

# Public
PLAYER_SEARCH = "/ffb/v1/player/search_data"
WP_POSTS = "/wp/v2/posts"

# Premium (require auth)
AUTH_VERIFY = "/ffb/v1/auth"
UDK_PROJECTIONS = "/ffb/v1/udk/projections"
START_SIT = "/ffb/v1/start-sit/save_query"

# HTML scrape (cookies only, no nonce needed in header)
TRADE_ANALYZER_PAGE = "/footclan/trade-analyzer/"

# UDK pages that embed data via `const data = [...]` (DataTables pattern).
# Same scrape approach as the dynasty pages below.
UDK_BYE_WEEKS_PAGE = "/2026-ultimate-draft-kit/udk-bye-weeks/"
UDK_SOS_PAGE = "/2026-ultimate-draft-kit/udk-strength-of-schedule/"
UDK_RED_ZONE_PAGE = "/2026-ultimate-draft-kit/udk-red-zone/"

# UDK research tables (also `const data = [...]`, cookies-only scrape).
UDK_TARGET_SHARE_PAGE = "/2026-ultimate-draft-kit/udk-target-share/"
UDK_MARKET_SHARE_PAGE = "/2026-ultimate-draft-kit/udk-market-share/"
UDK_VALUE_SCOUT_PAGE = "/2026-ultimate-draft-kit/udk-value-scout/"
# Consistency: `const data = {"2025": [...], "2024": [...], "2023": [...]}`,
# week-by-week fantasy points + snaps + position rank. Same payload backs both
# the "Weekly Consistency" and "Consistency Percentages" tools on the site.
UDK_CONSISTENCY_PAGE = "/2026-ultimate-draft-kit/udk-consistency-percentages/"
UDK_WEEKLY_CONSISTENCY_PAGE = "/2026-ultimate-draft-kit/udk-weekly-consistency-charts/"

# UDK content pages (HTML body scrape: snippets / heading sections, no table).
UDK_FREE_AGENCY_REVIEW_PAGE = "/2026-ultimate-draft-kit/udk-free-agency-review/"
UDK_COACHING_CHANGES_PAGE = "/2026-ultimate-draft-kit/udk-coaching-changes/"
UDK_ROOKIE_REPORT_PAGE = "/2026-ultimate-draft-kit/udk-rookie-report/"

# UDK Expert Lists. These render client-side from window.udk.data with no inline
# picks and no REST endpoint, so they require a headless render (see api/render.py).
UDK_EXPERT_LIST_PAGES = {
    "sleepers": "/2026-ultimate-draft-kit/udk-expert-lists-sleepers/",
    "breakouts": "/2026-ultimate-draft-kit/udk-expert-lists-breakouts/",
    "values": "/2026-ultimate-draft-kit/udk-expert-lists-values/",
    "busts": "/2026-ultimate-draft-kit/udk-expert-lists-busts/",
}

# The UDK "tool" pages inject the full `window.udk.data` global (projections with
# risk/upside/targets, per-player blurbs in `essentials`, tiers, multipliers);
# the lighter table pages (bye-weeks, red-zone) carry only an empty stub. We use
# the Strength of Schedule page as the enrichment source because the CLI already
# fetches and caches it for `ffb sos`, so enrichment is usually a cache hit.
UDK_GLOBAL_DATA_PAGE = UDK_SOS_PAGE

# DFS Pass (best ball rankings, also `const data = [...]`).
DFS_BEST_BALL_PAGE = "/2026-ultimate-dfs-pass/dfs-pass-best-ball-rankings/"

# Dynasty F.E.L.I.X. scores (rookie reliability metric, `const data = [...]`).
DYNASTY_FELIX_PAGE = "/2026-dynasty-pass/felix-scores/"

# Dynasty Rookie Class Overview (positional narrative; heading-section scrape).
DYNASTY_ROOKIE_OVERVIEW_PAGE = "/2026-dynasty-pass/rookie-class-overview/"

# Dynasty Pass pages (HTML scrape, cookies only).
# All gated behind UDK+ subscription. Data is rendered inline as JS assignments
# (window.udk.data, window.tool.tradeAnalyzer.data, const data = [...]) or
# inside the static HTML body itself.
DYNASTY_RANKINGS_PAGE = "/2026-dynasty-pass/rankings/"
DYNASTY_STARTUP_PAGE = "/2026-dynasty-pass/startup-rankings/"
DYNASTY_PRODUCTION_PROFILES_PAGE = "/2026-dynasty-pass/production-profiles/"
DYNASTY_MOCK_DRAFTS_PAGE = "/2026-dynasty-pass/mock-drafts/"
DYNASTY_TRADE_ANALYZER_PAGE = "/2026-dynasty-pass/trade-analyzer/"
DYNASTY_TRADE_TARGETS_PAGE = "/2026-dynasty-pass/dynasty-trade-targets/"
DYNASTY_TEAM_OPPORTUNITY_PAGE = "/2026-dynasty-pass/team-opportunity/"
DYNASTY_RISERS_FALLERS_PAGE = "/2026-dynasty-pass/risers-fallers/"
DYNASTY_SCOUTING_REPORTS_PAGE = "/2026-dynasty-pass/scouting-reports/"
DYNASTY_LIFECYCLES_PAGE = "/2026-dynasty-pass/dynasty-lifecycles/"
DYNASTY_FREE_AGENTS_PAGE = "/2026-dynasty-pass/free-agent-tracker/"
DYNASTY_INJURIES_PAGE = "/2026-dynasty-pass/injury-tracker/"
DYNASTY_DRAFT_RESULTS_PAGE = "/2026-dynasty-pass/nfl-draft-results/"
DYNASTY_TIPS_PAGE = "/2026-dynasty-pass/dynasty-tips/"

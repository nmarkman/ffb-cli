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

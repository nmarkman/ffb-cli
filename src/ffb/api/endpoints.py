"""API endpoint path constants."""

# Public
PLAYER_SEARCH = "/ffb/v1/player/search_data"
WP_POSTS = "/wp/v2/posts"

# Premium (require auth)
AUTH_VERIFY = "/ffb/v1/auth"
UDK_PROJECTIONS = "/ffb/v1/udk/projections"
START_SIT = "/ffb/v1/start-sit/save_query"

# HTML scrape (cookies only, no nonce needed in header)
TRADE_ANALYZER_PAGE = "/trade-value-calculator/"

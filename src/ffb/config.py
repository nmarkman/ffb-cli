from pathlib import Path

# Paths
CONFIG_DIR = Path.home() / ".config" / "ffb"
SESSION_FILE = CONFIG_DIR / "session.json"
CACHE_DIR = CONFIG_DIR / "cache"

# Site
BASE_URL = "https://www.thefantasyfootballers.com"
API_BASE = f"{BASE_URL}/wp-json"

# Auth
LOGIN_URL = f"{BASE_URL}/login/"
UDK_URL = f"{BASE_URL}/2026-ultimate-draft-kit/"
LOGIN_TIMEOUT_MS = 120_000  # 2 minutes for user to log in

# Scoring formats
SCORING_FORMATS = {
    "half": "HALF",
    "ppr": "PPR",
    "standard": "STD",
}
DEFAULT_SCORING = "half"

# Positions
VALID_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]

# Cache TTLs (seconds)
CACHE_TTL_PLAYERS = 86_400  # 24 hours
CACHE_TTL_PROJECTIONS = 3_600  # 1 hour
CACHE_TTL_NEWS = 1_800  # 30 minutes

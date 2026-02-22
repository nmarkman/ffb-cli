import json
import time
from pathlib import Path

from ..config import CACHE_DIR


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_key = key.replace("/", "_").replace("?", "_").replace("&", "_")
    return CACHE_DIR / f"{safe_key}.json"


def get_cached(key: str, ttl: int) -> dict | list | None:
    """Return cached data if fresh, else None."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data.get("_ts", 0) > ttl:
            return None
        return data.get("payload")
    except (json.JSONDecodeError, KeyError):
        return None


def set_cached(key: str, payload: dict | list) -> None:
    path = _cache_path(key)
    data = {"_ts": time.time(), "payload": payload}
    path.write_text(json.dumps(data))


def clear_cache() -> None:
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()

import json
import os
from datetime import datetime, timezone

from ..config import CONFIG_DIR, SESSION_FILE
from ..models.session import SessionData


def save_session(data: SessionData) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_text(data.model_dump_json(indent=2))
    os.chmod(SESSION_FILE, 0o600)


def load_session() -> SessionData | None:
    if not SESSION_FILE.exists():
        return None
    try:
        raw = json.loads(SESSION_FILE.read_text())
        return SessionData.model_validate(raw)
    except (json.JSONDecodeError, Exception):
        return None


def clear_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def session_age_hours() -> float | None:
    session = load_session()
    if not session:
        return None
    created = datetime.fromisoformat(session.created_at)
    delta = datetime.now(timezone.utc) - created
    return delta.total_seconds() / 3600

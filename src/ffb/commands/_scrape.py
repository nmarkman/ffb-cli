"""Shared helpers for scraping non-dynasty paywalled pages (UDK, DFS Pass).

Mirrors the pattern in `commands/dynasty/_common.py` but generic across page
families. Each command imports `fetch_page` + `load_const_data` and stays small.
"""
from __future__ import annotations

import typer

from ..api.client import AuthExpiredError, FFBClient, get_client
from ..api.dynasty_scrape import extract_const_assignment
from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_UDK_PAGE


def fetch_page(path: str, *, ttl: int = CACHE_TTL_UDK_PAGE) -> str:
    """Fetch a paywalled page HTML, cache by path. Bails on auth failure."""
    cache_key = f"udk_page:{path}"
    cached = get_cached(cache_key, ttl)
    if cached:
        return cached
    try:
        client: FFBClient = get_client(require_auth=True)
        html = client.get_page(path)
    except AuthExpiredError:
        typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
        raise typer.Exit(1)
    set_cached(cache_key, html)
    return html


def load_const_data(path: str, var_name: str = "data") -> list:
    """Fetch a page and return the parsed `const <var_name> = [...]` payload.

    Bails with typer.Exit(1) on parse failure."""
    html = fetch_page(path)
    data = extract_const_assignment(html, var_name)
    if not isinstance(data, list):
        typer.echo(
            f"Could not find `{var_name}` array on {path}. "
            "The page layout may have changed.",
            err=True,
        )
        raise typer.Exit(1)
    return data


def to_float(val, default: float = 0.0) -> float:
    """Coerce stringified numerics from the FFB page payloads to float."""
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def to_int(val, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default

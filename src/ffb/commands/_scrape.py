"""Shared helpers for scraping non-dynasty paywalled pages (UDK, DFS Pass).

Mirrors the pattern in `commands/dynasty/_common.py` but generic across page
families. Each command imports `fetch_page` + `load_const_data` and stays small.
"""
from __future__ import annotations

import re

import typer

from ..api.client import AuthExpiredError, FFBClient, get_client
from ..api.dynasty_scrape import (
    extract_const_assignment,
    extract_headings_with_content,
    slice_main_content,
    strip_html_tags,
)
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


def load_const_data_raw(path: str, var_name: str = "data"):
    """Fetch a page and return the parsed `const <var_name> = ...` payload as-is
    (list OR dict). Used by season-keyed tables like consistency, where the data
    is `{"2025": [...], "2024": [...]}`. Bails on parse failure."""
    html = fetch_page(path)
    data = extract_const_assignment(html, var_name)
    if data is None:
        typer.echo(
            f"Could not find `{var_name}` on {path}. The page layout may have changed.",
            err=True,
        )
        raise typer.Exit(1)
    return data


# Sidebar / chrome headings that leak into the main-content slice on the article
# pages ("The Latest" episode rail, subscribe CTAs, etc.). Drop these so the
# article scrape only keeps real body sections.
_ARTICLE_NOISE = re.compile(
    r"latest episode|subscribe|dfs & betting|dynasty|footclan|"
    r"sign up|newsletter|podcast|^the latest$|^videos$|^analysis$",
    re.I,
)


def extract_article_sections(path: str, *, min_body: int = 40) -> list[dict]:
    """Fetch a UDK content page and return [{heading, body}] for each real
    article section, filtering out sidebar/nav noise.

    The article pages (coaching changes, rookie report) render as H2/H3 player or
    team headings followed by paragraphs inside `.ffb-content`. The main-content
    slice still carries a "Latest Episodes" rail whose titles match our heading
    pattern, so we drop sections whose heading looks like chrome or whose body is
    too short to be real analysis."""
    html = slice_main_content(fetch_page(path))
    sections = extract_headings_with_content(html, (2, 3))
    out = []
    for s in sections:
        heading = s["heading"].strip()
        body = s["body"].strip()
        if not heading or _ARTICLE_NOISE.search(heading):
            continue
        if len(body) < min_body:
            continue
        out.append({"heading": heading, "body": body})
    return out


# Player-section heading like "Fernando Mendoza , (QB) LV" (rookie report).
_PLAYER_HEADING_RE = re.compile(
    r"^(.*?)\s*,\s*\((QB|RB|WR|TE|K|DST)\)\s*([A-Z]{2,4})\b", re.I
)


def extract_player_sections(path: str, *, min_body: int = 40, dynasty: bool = False) -> list[dict]:
    """Return [{name, position, team, blurb}] for pages whose body is a series of
    "Name , (POS) TEAM" headings followed by a writeup (UDK Rookie Report).

    `dynasty=True` routes through the dynasty page cache (cookies-only)."""
    html = slice_main_content(_fetch(path, dynasty))
    out = []
    for s in extract_headings_with_content(html, (2, 3, 4)):
        m = _PLAYER_HEADING_RE.match(s["heading"].strip())
        if not m:
            continue
        body = s["body"].strip()
        if len(body) < min_body:
            continue
        out.append({
            "name": m.group(1).strip(),
            "position": m.group(2).upper(),
            "team": m.group(3).upper(),
            "blurb": body,
        })
    return out


# Chrome phrases that mark a paragraph as nav/sidebar rather than article prose.
_PARA_NOISE = re.compile(
    r"latest episode|recent (news|articles)|more articles|newest articles|"
    r"subscribe|fantasy football 101|dynasty pass|premium (tools|perks)|"
    r"other resources|about us|^podcasts?$|^videos?$",
    re.I,
)


def extract_article_paragraphs(path: str, *, min_len: int = 120, dynasty: bool = False) -> list[str]:
    """Return the substantive prose paragraphs of an article page (UDK Coaching
    Changes), dropping short and chrome paragraphs."""
    html = slice_main_content(_fetch(path, dynasty))
    paras = []
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", html, flags=re.S | re.I):
        text = strip_html_tags(m.group(1)).strip()
        if len(text) < min_len or _PARA_NOISE.search(text):
            continue
        paras.append(text)
    return paras


def _fetch(path: str, dynasty: bool) -> str:
    """Fetch a page through the right cache namespace."""
    if dynasty:
        from .dynasty._common import fetch_dynasty_page
        return fetch_dynasty_page(path)
    return fetch_page(path)


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

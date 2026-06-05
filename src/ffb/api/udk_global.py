"""Loader for the global `window.udk.data` blob.

Every UDK page injects the same ~2MB `window.udk.data` object. It is a superset
of the `/ffb/v1/udk/projections` API the CLI normally uses: in addition to the
stat projections it carries per-analyst `risk` (1-10, lower is safer), `upside`
(1-10), `receiving_targets`, and per-player editorial blurbs in `essentials`.

This module exposes `load_enrichment_index()` which returns a
`player_id -> {risk, upside, targets, blurb}` map, averaged across analysts, so
the rankings/projections commands can graft those extra fields onto their rows.
The computed index is cached on disk so enrichment costs one parse, not 2MB per
command run.
"""
from __future__ import annotations

from collections import defaultdict

import typer

from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_PROJECTIONS, CACHE_TTL_UDK_PAGE
from .client import AuthExpiredError, get_client
from .dynasty_scrape import num, parse_js_assignment
from .endpoints import UDK_GLOBAL_DATA_PAGE

_INDEX_CACHE_KEY = "udk_enrichment_index"


def load_global_udk_data() -> dict | None:
    """Fetch a UDK page and return the parsed `window.udk.data` dict, or None.

    Caches the page HTML by path (shared with the rest of the UDK scrapers)."""
    cache_key = f"udk_page:{UDK_GLOBAL_DATA_PAGE}"
    html = get_cached(cache_key, CACHE_TTL_UDK_PAGE)
    if html is None:
        try:
            html = get_client(require_auth=True).get_page(UDK_GLOBAL_DATA_PAGE)
        except AuthExpiredError:
            typer.echo("Session expired. Run `ffb login` to re-authenticate.", err=True)
            raise typer.Exit(1)
        set_cached(cache_key, html)
    return parse_js_assignment(html, "window.udk.data")


def load_enrichment_index(*, ttl: int = CACHE_TTL_PROJECTIONS) -> dict[str, dict]:
    """Return {player_id: {risk, upside, targets, blurb}} averaged across analysts.

    Returns an empty dict if the global blob can't be parsed, so callers can
    enrich best-effort without failing the whole command."""
    cached = get_cached(_INDEX_CACHE_KEY, ttl)
    if cached is not None:
        return cached

    data = load_global_udk_data()
    if not isinstance(data, dict):
        return {}

    by_player: dict[str, list[dict]] = defaultdict(list)
    for row in data.get("projections", []):
        by_player[str(row.get("player_id", ""))].append(row)

    essentials = data.get("essentials", {}) or {}

    index: dict[str, dict] = {}
    for pid, rows in by_player.items():
        if not pid:
            continue
        risk = [num(r.get("risk")) for r in rows if r.get("risk") not in (None, "")]
        upside = [num(r.get("upside")) for r in rows if r.get("upside") not in (None, "")]
        targets = [num(r.get("receiving_targets")) for r in rows
                   if r.get("receiving_targets") not in (None, "")]
        blurb = ""
        ess = essentials.get(pid)
        if isinstance(ess, dict):
            blurb = (ess.get("blurb") or "").strip()
        index[pid] = {
            "risk": round(sum(risk) / len(risk), 1) if risk else None,
            "upside": round(sum(upside) / len(upside), 1) if upside else None,
            "targets": round(sum(targets) / len(targets), 1) if targets else None,
            "blurb": blurb,
        }

    set_cached(_INDEX_CACHE_KEY, index)
    return index


def enrich_players(players: list[dict]) -> list[dict]:
    """Attach risk / upside / targets / blurb to each player dict in place,
    matched by `player_id`. Players missing from the global blob get None fields.
    Returns the same list for convenience."""
    index = load_enrichment_index()
    for p in players:
        extra = index.get(str(p.get("player_id", "")), {})
        p["risk"] = extra.get("risk")
        p["upside"] = extra.get("upside")
        p["targets"] = extra.get("targets")
        p["blurb"] = extra.get("blurb", "")
    return players

"""Shared helpers for scraping data off /2026-dynasty-pass/* pages.

Pattern overview:
- Most dynasty pages render with a giant inline JavaScript assignment like
  `window.udk.data = {...};` or `window.tool.<tool>.data = {...};`.
- This module exposes one extractor (`extract_js_assignment`) that brace-matches
  the value past any nested objects/arrays/strings, plus convenience wrappers
  for the two common namespaces.
- Static HTML pages (e.g. dynasty-tips) fall back to BeautifulSoup-free
  regex extraction of card content; helpers for that live here too.
"""
from __future__ import annotations

import json
import re
from typing import Any

DYNASTY_BASE = "/2026-dynasty-pass"


def dynasty_path(slug: str) -> str:
    """Return the URL path for a dynasty page slug (no trailing slash logic; we
    always include the trailing slash to match canonical URLs)."""
    return f"{DYNASTY_BASE}/{slug}/"


def extract_js_assignment(html: str, lhs: str) -> str | None:
    """Find an assignment like `<lhs> = <value>;` in the given HTML/JS and return
    the raw value as a string. Supports `{...}` and `[...]` values; handles nested
    structures, strings, and escapes. Returns None if not found or unbalanced.

    `lhs` should be a regex-escapable string like ``window.udk.data`` or
    ``window.tool.tradeAnalyzer.data``.

    A page often assigns the same name multiple times (e.g. `window.udk.data = {};`
    as a stub, then `window.udk.data = {tiers: ..., projections: [...]}` with the
    real payload). We scan every occurrence and return the longest balanced value,
    which is JavaScript's effective "last write wins" in most page layouts.
    """
    pattern = re.escape(lhs) + r"\s*=\s*([\{\[])"
    best: str | None = None
    for m in re.finditer(pattern, html):
        opener_char = m.group(1)
        closer = {"{": "}", "[": "]"}[opener_char]
        start = m.end() - 1
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(html)):
            c = html[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == opener_char:
                    depth += 1
                elif c == closer:
                    depth -= 1
                    if depth == 0:
                        candidate = html[start:i + 1]
                        if best is None or len(candidate) > len(best):
                            best = candidate
                        break
    return best


def parse_js_assignment(html: str, lhs: str) -> Any | None:
    """Convenience wrapper: extract the assignment and json.loads it."""
    raw = extract_js_assignment(html, lhs)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def extract_const_assignment(html: str, name: str) -> Any | None:
    """Extract a `const <name> = [...]` or `const <name> = {...}` JSON-parseable
    value. Used by pages like /2026-dynasty-pass/production-profiles/ that use
    jQuery DataTables with inline `const data = [{...}]`."""
    pattern = r"\b(?:const|let|var)\s+" + re.escape(name) + r"\s*=\s*([\{\[])"
    m = re.search(pattern, html)
    if not m:
        return None
    opener_char = m.group(1)
    closer = {"{": "}", "[": "]"}[opener_char]
    start = m.end() - 1
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(html)):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == opener_char:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    raw = html[start:i + 1]
                    try:
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        return None
    return None


def parse_dynasty_page_data(html: str) -> dict | None:
    """Fetch the primary data object from a standard dynasty page.

    Tries, in order:
    1. window.udk.data        (rankings, startup-rankings)
    2. window.tool.tradeAnalyzer.data  (trade-analyzer)
    3. const data = [...]     (production-profiles tables)
    """
    for lhs in ("window.udk.data", "window.tool.tradeAnalyzer.data"):
        data = parse_js_assignment(html, lhs)
        if data:
            return data
    data = extract_const_assignment(html, "data")
    if data:
        return data
    return None


def strip_html_tags(text: str) -> str:
    """Cheap tag stripper for short text fragments (card titles, blurbs)."""
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&#039;", "'")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&bull;", "*")
        .replace("&middot;", "*")
        .replace("&hellip;", "...")
        .replace("&mdash;", ",")
        .replace("&ndash;", ",")
        .replace("&rsquo;", "'")
        .replace("&lsquo;", "'")
        .replace("&ldquo;", '"')
        .replace("&rdquo;", '"')
    )
    return re.sub(r"\s+", " ", text).strip()


def num(val: Any) -> float:
    """Coerce a mixed value (str/int/float/None) into a float for arithmetic."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def slice_main_content(html: str) -> str:
    """Return just the `<main>...</main>` block, or the ffb-content--fullwidth
    div if that's how the page is structured. Falls back to the original HTML if
    neither selector matches. This is critical for the static-HTML dynasty pages
    because the sidebar carries "The Latest" article listings that match the same
    extraction patterns we use for main content, polluting results."""
    # Prefer balanced <main>...</main>. Some pages have nested <main>; pick the
    # outermost one by depth-counting.
    main_open = re.search(r"<main\b[^>]*>", html, flags=re.I)
    if main_open:
        depth = 0
        start = main_open.start()
        body_start = main_open.end()
        i = body_start
        while i < len(html):
            open_m = re.search(r"<main\b[^>]*>", html[i:i + 50000], flags=re.I)
            close_m = re.search(r"</main\s*>", html[i:i + 50000], flags=re.I)
            if close_m and (not open_m or close_m.start() < open_m.start()):
                if depth == 0:
                    return html[body_start:i + close_m.start()]
                depth -= 1
                i += close_m.end()
            elif open_m:
                depth += 1
                i += open_m.end()
            else:
                break
    # Fallback: ffb-content--fullwidth div
    div_m = re.search(r'<div[^>]*class="[^"]*\bffb-content--fullwidth\b[^"]*"[^>]*>', html, flags=re.I)
    if div_m:
        # Slice from the open tag through the next </footer>, which is conservative
        # but reliable. The dynasty pages all have a <footer> after content.
        footer_m = re.search(r"<footer\b", html[div_m.end():], flags=re.I)
        if footer_m:
            return html[div_m.end():div_m.end() + footer_m.start()]
    return html


def extract_player_cards(html: str) -> list[dict]:
    """Extract `.ffb-news--grid--player` card content from a dynasty page.

    Returns a list of dicts with keys: name, position, team, blurb, link.
    These cards appear on most dynasty pages (risers-fallers, free-agent-tracker,
    dynasty-trade-targets, etc.). The structure across the site is roughly:

        <div class="ffb-news--grid--player ...">
          <div class="ffb-news--grid--player--info">
            <h3 class="ffb-news--grid--player--name">
              <a href="/player/...">Player Name</a>
            </h3>
            <span class="ffb-news--grid--player--position">POS</span>
            <span class="ffb-news--grid--player--team">TEAM</span>
          </div>
          <div class="ffb-news--grid--player--blurb">...</div>
        </div>

    The exact subclass names vary between pages, so we extract loosely and
    fall back to text scraping when needed.
    """
    cards = []
    # Each card is one big div opened by class="ffb-news--grid--player" and
    # closed by its matching </div>. We can't do balanced-div parsing with
    # regex reliably, so we slice on the next card's start instead.
    starts = [m.start() for m in re.finditer(r'<div\s+class="[^"]*\bffb-news--grid--player\b[^"]*"', html)]
    starts.append(len(html))
    for i in range(len(starts) - 1):
        block = html[starts[i]:starts[i + 1]]
        name = _extract_text(block, r'class="[^"]*\b(?:ffb-news--grid--player--name|player-name)\b[^"]*"[^>]*>(.+?)</')
        position = _extract_text(block, r'class="[^"]*\b(?:ffb-news--grid--player--position|player-pos)\b[^"]*"[^>]*>(.+?)</')
        team = _extract_text(block, r'class="[^"]*\b(?:ffb-news--grid--player--team|player-team)\b[^"]*"[^>]*>(.+?)</')
        blurb = _extract_text(block, r'class="[^"]*\b(?:ffb-news--grid--player--blurb|player-blurb|player-content)\b[^"]*"[^>]*>(.+?)</div>')
        link_m = re.search(r'href="(/player/[^"]+)"', block)
        link = link_m.group(1) if link_m else None
        if not name:
            continue
        cards.append({
            "name": name,
            "position": position,
            "team": team,
            "blurb": blurb,
            "link": link,
        })
    return cards


def _extract_text(block: str, pattern: str) -> str:
    m = re.search(pattern, block, flags=re.S | re.I)
    if not m:
        return ""
    return strip_html_tags(m.group(1))


def extract_ffb_snippets(html: str) -> list[dict]:
    """Extract `.ffb-snippet` blocks. Used on risers-fallers and mock-drafts
    where each player is a snippet with an avatar + content area."""
    cards = []
    starts = [m.start() for m in re.finditer(
        r'<(?:div|li|a)\s+[^>]*class="[^"]*\bffb-snippet\b(?!--)',
        html, flags=re.I,
    )]
    starts.append(len(html))
    for i in range(len(starts) - 1):
        block = html[starts[i]:starts[i + 1]]
        content_m = re.search(
            r'<(?:div|span)[^>]*class="[^"]*\bffb-snippet--content\b[^"]*"[^>]*>(.*?)</(?:div|span)>',
            block, flags=re.S | re.I,
        )
        content_html = content_m.group(1) if content_m else block
        name_m = re.search(r'<(?:h\d|a|strong)[^>]*>(.+?)</', content_html, flags=re.S | re.I)
        meta_m = re.search(r'<(?:span|p)[^>]*>(.+?)</', content_html[name_m.end() if name_m else 0:], flags=re.S | re.I)
        if not name_m:
            continue
        cards.append({
            "name": strip_html_tags(name_m.group(1)),
            "meta": strip_html_tags(meta_m.group(1)) if meta_m else "",
            "content": strip_html_tags(content_html)[:600],
        })
    return cards


def extract_dynasty_table(html: str) -> list[dict]:
    """Extract rows from `.ffb-dynasty--table` (NFL Draft Results page). Each row
    is rendered as a series of div cells, so we look for the row container then
    pick out the text of each child cell."""
    rows = []
    for m in re.finditer(
        r'<(?:tr|div)\s+[^>]*class="[^"]*\b(?:ffb-dynasty--table--row|ffb-data--row|draft-pick)\b[^"]*"[^>]*>(.*?)</(?:tr|div)>',
        html, flags=re.S | re.I,
    ):
        block = m.group(1)
        cells = [strip_html_tags(c.group(1)) for c in re.finditer(
            r'<(?:td|div|span)[^>]*>(.*?)</(?:td|div|span)>', block, flags=re.S | re.I
        )]
        cells = [c for c in cells if c]
        if cells:
            rows.append({"cells": cells})
    return rows


def extract_post_grid(html: str) -> list[dict]:
    """Extract `.ffb-post-grid--post` cards (used by dynasty-lifecycles and similar
    article-listing pages). Each card has a title, excerpt, and link."""
    cards = []
    starts = [m.start() for m in re.finditer(r'<(?:article|div)\s+class="[^"]*\bffb-post-grid--post\b[^"]*"', html)]
    starts.append(len(html))
    for i in range(len(starts) - 1):
        block = html[starts[i]:starts[i + 1]]
        title_m = re.search(r'<h\d[^>]*>\s*<a\s+href="([^"]+)"[^>]*>(.+?)</a>', block, flags=re.S | re.I)
        excerpt_m = re.search(r'class="[^"]*\b(?:ffb-post-grid--post--content|excerpt|description)\b[^"]*"[^>]*>(.+?)</', block, flags=re.S | re.I)
        if not title_m:
            continue
        cards.append({
            "title": strip_html_tags(title_m.group(2)),
            "link": title_m.group(1),
            "excerpt": strip_html_tags(excerpt_m.group(1)) if excerpt_m else "",
        })
    return cards


def extract_headings_with_content(html: str, heading_levels: tuple[int, ...] = (2, 3)) -> list[dict]:
    """Walk through the body picking up each H2/H3 and the paragraph(s) immediately
    after it. Returns a list of {heading, level, body}. Useful for dynasty-tips and
    free-agent-tracker which use heading-keyed sections."""
    pattern = r'<h([' + ''.join(str(l) for l in heading_levels) + r'])[^>]*>(.+?)</h\1>(.*?)(?=<h[' + ''.join(str(l) for l in heading_levels) + r']\b|$)'
    out = []
    for m in re.finditer(pattern, html, flags=re.S | re.I):
        level = int(m.group(1))
        heading = strip_html_tags(m.group(2))
        body = strip_html_tags(m.group(3))
        if heading:
            out.append({"level": level, "heading": heading, "body": body[:2000]})
    return out

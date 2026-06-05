"""Headless-render helper for pages whose data is built client-side.

Most FFB tools embed their data inline (a `const data = [...]` blob or
`window.udk.data`), so the lightweight `requests`-based scrapers can read them
without a browser. The UDK Expert Lists (Sleepers / Breakouts / Values / Busts)
are the exception: the picks are assembled in the browser from `window.udk.data`
with no inline list and no REST endpoint, so we render the page in headless
Chromium (reusing the Playwright dependency already required for login) with the
saved session cookies, then scrape the rendered DOM.
"""
from __future__ import annotations

import re

import typer

from ..auth.session import load_session
from ..config import BASE_URL

# Each pick renders as an <h3> like "Malik Willis, (QB) MIA" followed by a blurb
# that opens with "Current ADP: 8.10".
_HEADING_RE = re.compile(r"^(.*?),\s*\((QB|RB|WR|TE|K|DST)\)\s*([A-Z]{2,4})", re.I)
_ADP_RE = re.compile(r"Current ADP:\s*([0-9]+\.[0-9]+)")

# Pulled out of JS so it's easy to read/maintain. Returns the raw heading + the
# concatenated text of the following siblings up to the next heading.
_PICKS_JS = r"""() => {
  const isPick = t => /,\s*\((QB|RB|WR|TE|K|DST)\)\s*[A-Z]{2,4}/.test(t);
  const heads = [...document.querySelectorAll('h2,h3,h4')]
      .filter(h => isPick(h.textContent.trim()));
  return heads.map(h => {
    let blurb = '', el = h.nextElementSibling, n = 0;
    while (el && !/^H[2-4]$/.test(el.tagName) && n < 8) {
      if (el.textContent) blurb += ' ' + el.textContent.trim();
      el = el.nextElementSibling; n++;
    }
    return { heading: h.textContent.trim().replace(/\s+/g, ' '),
             blurb: blurb.trim().replace(/\s+/g, ' ') };
  });
}"""


def render_expert_picks(path: str, *, wait_ms: int = 6000) -> list[dict]:
    """Render a UDK expert-list page and return [{name, position, team, adp, blurb}].

    Requires a saved session (cookies). Raises typer.Exit(1) with a clear message
    if not logged in or if Playwright isn't available."""
    session = load_session()
    if not session:
        typer.echo("Not logged in. Run `ffb login` first.", err=True)
        raise typer.Exit(1)

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        typer.echo(
            "Playwright is required for expert lists. Install with "
            "`python -m playwright install chromium`.",
            err=True,
        )
        raise typer.Exit(1)

    cookies = [
        {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
        for c in session.cookies
    ]
    url = f"{BASE_URL}{path}"

    raw_picks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(wait_ms)
            raw_picks = page.evaluate(_PICKS_JS)
        except PWTimeout:
            browser.close()
            typer.echo(f"Timed out rendering {path}. Try again.", err=True)
            raise typer.Exit(1)
        browser.close()

    return [parsed for rp in raw_picks if (parsed := _parse_pick(rp))]


def _parse_pick(raw: dict) -> dict | None:
    heading = raw.get("heading", "")
    m = _HEADING_RE.match(heading)
    if not m:
        return None
    blurb = raw.get("blurb", "")
    adp_m = _ADP_RE.search(blurb)
    # Trim the leading "Current ADP: X.XX" off the blurb body.
    body = _ADP_RE.sub("", blurb, count=1).strip()
    return {
        "name": m.group(1).strip(),
        "position": m.group(2).upper(),
        "team": m.group(3).upper(),
        "adp": adp_m.group(1) if adp_m else None,
        "blurb": body,
    }

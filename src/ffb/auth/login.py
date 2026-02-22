from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import typer

from ..config import LOGIN_URL, UDK_URL, LOGIN_TIMEOUT_MS, BASE_URL
from ..models.session import SessionData, CookieData
from .session import save_session


def run_login_flow() -> SessionData:
    """Launch headed browser, let user log in, capture session."""
    typer.echo("Launching browser for login...")
    typer.echo("Log in to your Fantasy Footballers account in the browser window.")
    typer.echo(f"Waiting up to {LOGIN_TIMEOUT_MS // 1000}s for login to complete...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Start at the login page
        page.goto(LOGIN_URL)

        # Wait for user to log in (URL changes away from /login/)
        try:
            page.wait_for_url(
                lambda url: "/login" not in url,
                timeout=LOGIN_TIMEOUT_MS,
            )
        except PWTimeout:
            browser.close()
            typer.echo("Login timed out. Please try again.", err=True)
            raise typer.Exit(1)

        # Navigate to the UDK (premium page) to ensure full auth context
        page.goto(UDK_URL)
        page.wait_for_load_state("networkidle", timeout=30_000)

        # Extract nonce - try multiple sources
        nonce = _extract_nonce(page)
        if not nonce:
            browser.close()
            typer.echo("Logged in but could not capture API nonce. Try again.", err=True)
            raise typer.Exit(1)

        # Extract cookies for the FFB domain
        all_cookies = context.cookies()
        ffb_cookies = [
            CookieData(
                name=c["name"],
                value=c["value"],
                domain=c["domain"],
                path=c.get("path", "/"),
            )
            for c in all_cookies
            if "thefantasyfootballers.com" in c.get("domain", "")
        ]

        browser.close()

    if not ffb_cookies:
        typer.echo("No cookies captured. Login may have failed.", err=True)
        raise typer.Exit(1)

    session = SessionData(
        cookies=ffb_cookies,
        nonce=nonce,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    save_session(session)
    typer.echo(f"Login successful! Captured {len(ffb_cookies)} cookies.")
    return session


def _extract_nonce(page) -> str | None:
    """Try multiple methods to extract a WP REST API nonce from the page."""
    # Method 1: window.udk.rest_api.api_nonce (original UDK location)
    nonce = page.evaluate("""() => {
        try { return window.udk.rest_api.api_nonce } catch(e) { return null }
    }""")
    if nonce:
        return nonce

    # Method 2: WP standard admin-ajax nonce generation
    nonce = page.evaluate("""async () => {
        try {
            const resp = await fetch('/wp-admin/admin-ajax.php?action=rest-nonce', {
                credentials: 'same-origin'
            });
            if (resp.ok) {
                const text = await resp.text();
                if (text && text.length < 20 && text !== '0') return text.trim();
            }
        } catch(e) {}
        return null;
    }""")
    if nonce:
        return nonce

    # Method 3: wpApiSettings (some WP pages expose this)
    nonce = page.evaluate("""() => {
        try { return window.wpApiSettings && window.wpApiSettings.nonce } catch(e) { return null }
    }""")
    if nonce:
        return nonce

    # Method 4: Search inline scripts for nonce patterns
    nonce = page.evaluate(r"""() => {
        const scripts = document.querySelectorAll('script:not([src])');
        for (const s of scripts) {
            const match = s.textContent.match(/api_nonce['":\s]+['"]([a-f0-9]{10})['"]/);
            if (match) return match[1];
            const match2 = s.textContent.match(/"nonce"\s*:\s*"([a-f0-9]{10})"/);
            if (match2) return match2[1];
        }
        return null;
    }""")
    return nonce

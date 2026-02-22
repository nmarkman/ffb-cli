from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import typer

from ..config import UDK_URL, LOGIN_TIMEOUT_MS, BASE_URL
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

        page.goto(UDK_URL)

        # Wait for the nonce to appear (signals successful auth + page load)
        try:
            page.wait_for_function(
                "() => window.udk && window.udk.rest_api && window.udk.rest_api.api_nonce",
                timeout=LOGIN_TIMEOUT_MS,
            )
        except PWTimeout:
            browser.close()
            typer.echo("Login timed out. Please try again.", err=True)
            raise typer.Exit(1)

        # Extract nonce
        nonce = page.evaluate("() => window.udk.rest_api.api_nonce")

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

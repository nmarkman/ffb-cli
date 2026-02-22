import json
from html import unescape
import re

import typer

from ..api.client import get_client
from ..api.endpoints import WP_POSTS
from ..cache.store import get_cached, set_cached
from ..config import CACHE_TTL_NEWS
from ..display.tables import news_table, console


def _strip_html(text: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", text))


def news_command(
    limit: int = typer.Option(10, "-n", "--limit", help="Number of articles"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Show recent Fantasy Footballers articles. No login required.

    \b
    Fetches the latest posts with title, date, and link.
    Results are cached for 30 minutes.

    \b
    EXAMPLES:
      ffb news                  # latest 10 articles
      ffb news -n 5             # latest 5 articles
      ffb news --json           # JSON output
    """
    cache_key = f"news_{limit}"
    cached = get_cached(cache_key, CACHE_TTL_NEWS)

    if cached:
        articles = cached
    else:
        client = get_client(require_auth=False)
        resp = client.get(WP_POSTS, params={"per_page": limit, "_fields": "title,date,link,excerpt"})
        raw = resp.json()

        articles = []
        for post in raw:
            articles.append({
                "title": _strip_html(post.get("title", {}).get("rendered", "")),
                "date": post.get("date", "")[:10],
                "link": post.get("link", ""),
                "excerpt": _strip_html(post.get("excerpt", {}).get("rendered", ""))[:200],
            })
        set_cached(cache_key, articles)

    if not articles:
        typer.echo("No news articles found.")
        raise typer.Exit(0)

    if output_json:
        console.print_json(json.dumps(articles))
    else:
        news_table(articles)

import requests
import typer

from ..config import API_BASE, BASE_URL
from ..auth.session import load_session
from ..models.session import SessionData


class AuthExpiredError(Exception):
    pass


class FFBClient:
    """HTTP client with FFB cookie/nonce auth injection."""

    def __init__(self, session_data: SessionData | None = None):
        self._http = requests.Session()
        self._session_data = session_data
        if session_data:
            self._inject_auth(session_data)

    def _inject_auth(self, data: SessionData) -> None:
        for cookie in data.cookies:
            self._http.cookies.set(
                cookie.name,
                cookie.value,
                domain=cookie.domain,
                path=cookie.path,
            )
        self._http.headers["X-WP-Nonce"] = data.nonce

    def _check_response(self, resp: requests.Response) -> None:
        if resp.status_code in (401, 403):
            raise AuthExpiredError(
                "Session expired or invalid. Run `ffb login` to re-authenticate."
            )
        resp.raise_for_status()

    def get(self, endpoint: str, params: dict | None = None) -> requests.Response:
        url = f"{API_BASE}{endpoint}"
        resp = self._http.get(url, params=params)
        self._check_response(resp)
        return resp

    def post(self, endpoint: str, json: dict | None = None) -> requests.Response:
        url = f"{API_BASE}{endpoint}"
        resp = self._http.post(url, json=json)
        self._check_response(resp)
        return resp

    def get_page(self, path: str) -> str:
        """Fetch raw HTML page (for trade analyzer scrape)."""
        url = f"{BASE_URL}{path}"
        resp = self._http.get(url)
        self._check_response(resp)
        return resp.text


def get_client(require_auth: bool = False) -> FFBClient:
    """Create client, optionally requiring auth."""
    session = load_session()
    if require_auth and not session:
        typer.echo("Not logged in. Run `ffb login` first.", err=True)
        raise typer.Exit(1)
    return FFBClient(session)

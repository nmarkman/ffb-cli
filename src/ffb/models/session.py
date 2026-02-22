from pydantic import BaseModel


class CookieData(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"


class SessionData(BaseModel):
    cookies: list[CookieData]
    nonce: str
    created_at: str  # ISO format timestamp

from pydantic import BaseModel


class TradeValue(BaseModel):
    player_name: str = ""
    position: str = ""
    team: str = ""
    value: float = 0.0
    rank: int = 0
    tier: int = 0


class TradeAnalysis(BaseModel):
    give_players: list[TradeValue]
    get_players: list[TradeValue]
    give_total: float = 0.0
    get_total: float = 0.0
    difference: float = 0.0

from pydantic import BaseModel


class Projection(BaseModel):
    rank: int = 0
    player_name: str = ""
    team: str = ""
    position: str = ""
    tier: int = 0
    bye_week: int | None = None
    points: float = 0.0
    # Passing
    pass_yds: float = 0.0
    pass_tds: float = 0.0
    ints: float = 0.0
    # Rushing
    rush_yds: float = 0.0
    rush_tds: float = 0.0
    # Receiving
    receptions: float = 0.0
    rec_yds: float = 0.0
    rec_tds: float = 0.0
    # Kicking
    fg: float = 0.0
    xp: float = 0.0

    model_config = {"extra": "allow"}

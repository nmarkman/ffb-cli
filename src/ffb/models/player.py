from pydantic import BaseModel, Field


class Player(BaseModel):
    id: int | None = None
    name: str
    position: str = ""
    team: str = ""
    bye_week: int | None = None


class PlayerSearchResult(BaseModel):
    id: int
    name: str = Field(alias="player_name", default="")
    first_name: str = ""
    last_name: str = ""
    position: str = ""
    team: str = ""
    score: int = 0  # fuzzy match score

    model_config = {"populate_by_name": True}

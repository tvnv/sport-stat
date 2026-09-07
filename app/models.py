from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Team(BaseModel):
    id: str
    name: str
    short_name: str = ""


class Match(BaseModel):
    id: str
    league_id: str
    matchday: int
    date: str
    home_team: Team
    away_team: Team
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = "SCHEDULED"  # SCHEDULED | TIMED | LIVE | FINISHED

    def finished(self) -> bool:
        return self.status == "FINISHED" and self.home_score is not None and self.away_score is not None


class StandingRow(BaseModel):
    position: int
    team_id: str
    team_name: str
    points: int
    goal_diff: int
    goals_for: int
    played: int
    won: int
    drawn: int
    lost: int


class Standings(BaseModel):
    league_id: str
    matchday: int
    rows: list[StandingRow]


class MatchdayView(BaseModel):
    league_id: str
    league_name: str
    country: str
    matchday: int
    label: str  # last | today | next
    matches: list[Match]
    standings_before: Standings
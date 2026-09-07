from dataclasses import dataclass, field


@dataclass
class Match:
    id: int
    league_id: int
    season: int
    round: str
    date: str
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_goals: int | None
    away_goals: int | None
    status_short: str
    elapsed: int | None


@dataclass
class TeamStanding:
    team_id: int
    team_name: str
    played: int
    win: int
    draw: int
    loss: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    rank: int = 0


@dataclass
class FixtureDisplay:
    home_team: str
    home_position: int | None
    away_team: str
    away_position: int | None
    home_goals: int | None
    away_goals: int | None
    status: str
    score_str: str

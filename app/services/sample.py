"""Provider de démonstration déterministe.

Utilisé en l'absence de token API (développement local, tests, démo). Génère des
matchs reproductibles afin que l'application soit utilisable immédiatement.
"""
from datetime import datetime, timedelta
from typing import List

from ..models import Match, Team
from .provider import FootballProvider

TEAMS = {
    "PL": ["Arsenal", "Chelsea", "Liverpool", "Man City", "Man United"],
    "PD": ["Real Madrid", "Barcelona", "Atletico", "Sevilla", "Valencia"],
    "SA": ["Inter", "Milan", "Juventus", "Napoli", "Roma"],
    "BL1": ["Bayern", "Dortmund", "Leipzig", "Leverkusen", "Frankfurt"],
    "FL1": ["PSG", "Marseille", "Lyon", "Monaco", "Lille"],
}


def _team(tid: str) -> Team:
    return Team(id=tid.lower(), name=tid)


def generate_sample(league_id: str, season: int, matchdays: int = 6, teams: int = 5) -> List[Match]:
    names = TEAMS.get(league_id, [f"Team{i}" for i in range(1, teams + 1)])
    teams_list = [_team(n) for n in names]
    matches: List[Match] = []
    now = datetime(2024, 9, 1, 15, 0, 0)
    mid = len(teams_list) // 2
    for md in range(1, matchdays + 1):
        for i in range(mid):
            home = teams_list[i]
            away = teams_list[(i + md) % len(teams_list)]
            if home.id == away.id:
                away = teams_list[(i + md + 1) % len(teams_list)]
            finished = md < matchdays
            h = (md * 3 + i) % 5
            a = (md * 2 + i) % 4
            matches.append(
                Match(
                    id=f"{league_id}-{md}-{i}",
                    league_id=league_id,
                    matchday=md,
                    date=(now + timedelta(days=md * 7)).isoformat(),
                    home_team=home,
                    away_team=away,
                    home_score=h if finished else None,
                    away_score=a if finished else None,
                    status="FINISHED" if finished else "SCHEDULED",
                )
            )
    return matches


class SampleFootballProvider(FootballProvider):
    """Provider de démonstration ne nécessitant aucune clé."""

    def fetch_league_matches(self, league_id: str, season: int) -> List[Match]:
        return generate_sample(league_id, season)
import os
from dataclasses import dataclass, asdict
from typing import List, Optional

import yaml


@dataclass(frozen=True)
class LeagueConfig:
    id: str
    name: str
    country: str
    provider_id: Optional[int] = None
    logo: str = ""
    season: int = 2026
    enabled: bool = True


def _default_leagues() -> List[LeagueConfig]:
    return [
        LeagueConfig("ligue_1", "Ligue 1", "France", 61),
        LeagueConfig("ligue_2", "Ligue 2", "France", 62),
        LeagueConfig("premier_league", "Premier League", "Angleterre", 39),
        LeagueConfig("la_liga", "La Liga", "Espagne", 140),
        LeagueConfig("serie_a", "Serie A", "Italie", 135),
        LeagueConfig("serie_b", "Serie B", "Italie", 136),
        LeagueConfig("bundesliga", "Bundesliga", "Allemagne", 78),
        LeagueConfig("primeira_liga", "Primeira Liga", "Portugal", 94),
        LeagueConfig("super_league_greece", "Super League Greece", "Grèce", 197),
        LeagueConfig("swiss_super_league", "Swiss Super League", "Suisse", 207),
        LeagueConfig("super_lig", "Süper Lig", "Turquie", 203),
    ]


class Settings:
    def __init__(self, config_path: str = "config/leagues.yaml"):
        self.leagues: List[LeagueConfig] = []
        path = os.environ.get("LEAGUES_CONFIG", config_path)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            for item in raw.get("leagues", []):
                self.leagues.append(LeagueConfig(**item))
        else:
            self.leagues = _default_leagues()
        self.leagues = [l for l in self.leagues if l.enabled]

    def league_by_id(self, league_id: str) -> LeagueConfig:
        for l in self.leagues:
            if l.id == league_id:
                return l
        raise KeyError(league_id)

    def as_dict(self) -> List[dict]:
        return [asdict(l) for l in self.leagues]

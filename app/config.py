import os
from dataclasses import dataclass, asdict
from typing import List

import yaml


@dataclass(frozen=True)
class LeagueConfig:
    id: str
    name: str
    country: str
    logo: str = ""
    season: int = 2024
    enabled: bool = True


def _default_leagues() -> List[LeagueConfig]:
    return [
        LeagueConfig("PL", "Premier League", "England"),
        LeagueConfig("PD", "La Liga", "Spain"),
        LeagueConfig("SA", "Serie A", "Italy"),
        LeagueConfig("BL1", "Bundesliga", "Germany"),
        LeagueConfig("FL1", "Ligue 1", "France"),
        LeagueConfig("PPL", "Primeira Liga", "Portugal"),
        LeagueConfig("EER", "Eredivisie", "Netherlands"),
        LeagueConfig("BSA", "Brasileirão Série A", "Brazil"),
        LeagueConfig("DED", "Jupiler Pro League", "Belgium"),
        LeagueConfig("CL", "Champions League", "Europe"),
        LeagueConfig("EL", "Europa League", "Europe"),
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

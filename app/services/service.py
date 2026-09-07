"""Logique applicative : vues de journée avec classement strictement pré-journée."""
from datetime import datetime
from typing import Dict, List, Optional

from ..config import LeagueConfig, Settings
from ..models import Match, MatchdayView, Standings
from .provider import FootballProvider
from .standings import Tiebreak, compute_standings

COMPETITION_TIEBREAKS: Dict[str, Tiebreak] = {}


class AppService:
    def __init__(self, settings: Settings, provider: FootballProvider, now: Optional[datetime] = None):
        self._settings = settings
        self._provider = provider
        self._now = now or datetime.now()

    def _tiebreak(self, league_id: str) -> Optional[Tiebreak]:
        return COMPETITION_TIEBREAKS.get(league_id)

    def _matches(self, league: LeagueConfig) -> List[Match]:
        provider_id = str(league.provider_id) if league.provider_id is not None else league.id
        return self._provider.fetch_league_matches(provider_id, league.season)

    def _standings(self, league: LeagueConfig, matches: List[Match], matchday: int) -> Standings:
        return compute_standings(matches, league.id, matchday, self._tiebreak(league.id))

    def _target_matchday(self, matches_by_md: Dict[int, List[Match]], label: str) -> Optional[int]:
        today = self._now.date().isoformat()
        matchdays = sorted(md for md in matches_by_md if md > 0)
        if not matchdays:
            return None

        if label == "today":
            return next(
                (md for md in matchdays if any(m.date[:10] == today for m in matches_by_md[md])),
                None,
            )

        if label == "next":
            # Une journée s'étend parfois sur plusieurs jours (vendredi → lundi).
            # "prochaine" doit être strictement après la journée en cours, sinon
            # les vues today/next montreraient le même matchday.
            current = next(
                (md for md in matchdays if any(m.date[:10] == today for m in matches_by_md[md])),
                None,
            )
            floor = current if current is not None else 0
            return next(
                (
                    md for md in matchdays if md > floor
                    and any(m.date[:10] > today and not m.finished() for m in matches_by_md[md])
                ),
                None,
            )

        # Dernière journée = dernière journée entièrement terminée. Une journée
        # partiellement jouée n'est pas utilisée comme historique complet.
        completed = [
            md for md in matchdays
            if matches_by_md[md] and all(m.finished() for m in matches_by_md[md])
        ]
        return max(completed) if completed else None

    def league_view(self, league: LeagueConfig, label: Optional[str] = None) -> MatchdayView:
        matches = self._matches(league)
        matches_by_md: Dict[int, List[Match]] = {}
        for m in matches:
            if m.matchday > 0:
                matches_by_md.setdefault(m.matchday, []).append(m)

        label = label if label in {"last", "today", "next"} else "last"
        target = self._target_matchday(matches_by_md, label)
        if target is None:
            return MatchdayView(
                league_id=league.id,
                league_name=league.name,
                country=league.country,
                matchday=0,
                label=label,
                matches=[],
                standings_before=Standings(league_id=league.id, matchday=0, rows=[]),
            )

        md_matches = sorted(matches_by_md[target], key=lambda m: m.date)
        standings = self._standings(league, matches, target)
        return MatchdayView(
            league_id=league.id,
            league_name=league.name,
            country=league.country,
            matchday=target,
            label=label,
            matches=md_matches,
            standings_before=standings,
        )

    def dashboard(self, label: str = "last") -> List[MatchdayView]:
        return [self.league_view(l, label) for l in self._settings.leagues]

    def view_for(self, league_id: str, label: Optional[str] = None) -> MatchdayView:
        return self.league_view(self._settings.league_by_id(league_id), label)

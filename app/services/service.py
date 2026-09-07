"""Logique applicative : assemblage des vues de journée avec classement avant journée."""
from datetime import datetime
from typing import Dict, List, Optional

from ..config import LeagueConfig, Settings
from ..models import Match, MatchdayView, Standings, StandingRow
from .provider import FootballProvider
from .standings import Tiebreak, compute_standings

# Tie-breaks isolables par compétition. Vide = stratégie par défaut.
COMPETITION_TIEBREAKS: Dict[str, Tiebreak] = {}


class AppService:
    def __init__(self, settings: Settings, provider: FootballProvider, now: Optional[datetime] = None):
        self._settings = settings
        self._provider = provider
        self._now = now or datetime.now()

    def _tiebreak(self, league_id: str) -> Tiebreak:
        return COMPETITION_TIEBREAKS.get(league_id)

    def _matches(self, league: LeagueConfig) -> List[Match]:
        return self._provider.fetch_league_matches(league.id, league.season)

    def _standings(self, league: LeagueConfig, matches: List[Match], matchday: int) -> Standings:
        return compute_standings(matches, league.id, matchday, self._tiebreak(league.id))

    def _matchday_label(self, matches: List[Match]) -> str:
        if not matches:
            return "next"
        today = self._now.date().isoformat()
        dates = sorted(m.date[:10] for m in matches if m.status in ("SCHEDULED", "TIMED", "LIVE"))
        if not dates:
            return "last"
        first_future = next((d for d in dates if d >= today), None)
        if first_future is None:
            return "last"
        if first_future == today:
            return "today"
        return "next"

    def league_view(self, league: LeagueConfig, label: Optional[str] = None) -> MatchdayView:
        matches = self._matches(league)
        matches_by_md: Dict[int, List[Match]] = {}
        for m in matches:
            matches_by_md.setdefault(m.matchday, []).append(m)
        if not matches_by_md:
            return MatchdayView(
                league_id=league.id, league_name=league.name, country=league.country,
                matchday=0, label=label or "next", matches=[], standings_before=Standings(league_id=league.id, matchday=0, rows=[]),
            )

        # Determine target matchday based on label.
        if label is None:
            label = self._matchday_label(matches)
        matchdays = sorted(matches_by_md.keys())
        today = self._now.date().isoformat()
        if label == "today":
            target = next(
                (md for md in matchdays if any(m.date[:10] == today for m in matches_by_md[md])),
                max(matchdays),
            )
        elif label == "next":
            target = next(
                (md for md in matchdays if any(m.date[:10] >= today for m in matches_by_md[md])),
                max(matchdays),
            )
        else:  # last
            target = max(matchdays)

        md_matches = sorted(matches_by_md.get(target, []), key=lambda m: m.date)
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

    def dashboard(self) -> List[MatchdayView]:
        return [self.league_view(l) for l in self._settings.leagues]

    def view_for(self, league_id: str, label: Optional[str] = None) -> MatchdayView:
        league = self._settings.league_by_id(league_id)
        return self.league_view(league, label)
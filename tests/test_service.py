from datetime import datetime

from app.config import LeagueConfig, Settings
from app.models import Match, Team
from app.services.provider import FootballProvider
from app.services.service import AppService


def mk(mid, md, date, status="FINISHED", hs=1, aw=0):
    return Match(
        id=mid,
        league_id="61",
        matchday=md,
        date=date,
        home_team=Team(id=f"h{mid}", name=f"H{mid}"),
        away_team=Team(id=f"a{mid}", name=f"A{mid}"),
        home_score=hs if status == "FINISHED" else None,
        away_score=aw if status == "FINISHED" else None,
        status=status,
    )


class FakeProvider(FootballProvider):
    def __init__(self, matches):
        self.matches = matches

    def fetch_league_matches(self, league_id: str, season: int):
        return self.matches


def service(matches):
    settings = Settings(config_path="/definitely/missing.yaml")
    settings.leagues = [LeagueConfig("ligue_1", "Ligue 1", "France", 61, season=2026)]
    return AppService(settings, FakeProvider(matches), now=datetime(2026, 9, 7, 12, 0, 0)), settings.leagues[0]


def test_last_is_latest_fully_completed_matchday():
    matches = [
        mk("1", 1, "2026-08-20T18:00:00Z"),
        mk("2", 2, "2026-08-27T18:00:00Z"),
        mk("3", 3, "2026-09-07T18:00:00Z", status="SCHEDULED"),
    ]
    svc, league = service(matches)
    view = svc.league_view(league, "last")
    assert view.matchday == 2
    assert view.label == "last"


def test_today_selects_matchday_playing_today():
    matches = [mk("1", 3, "2026-09-07T18:00:00Z", status="SCHEDULED")]
    svc, league = service(matches)
    assert svc.league_view(league, "today").matchday == 3


def test_next_is_strictly_future():
    matches = [
        mk("1", 3, "2026-09-07T18:00:00Z", status="SCHEDULED"),
        mk("2", 4, "2026-09-14T18:00:00Z", status="SCHEDULED"),
    ]
    svc, league = service(matches)
    assert svc.league_view(league, "next").matchday == 4


def test_next_is_strictly_after_current_spanning_matchday():
    # Une journée s'étale parfois vendredi → lundi : "prochaine" doit désigner
    # la journée suivante, pas la journée en cours déjà couverte par "aujourd'hui".
    matches = [
        mk("1", 3, "2026-09-04T18:00:00Z"),                       # jeudi, fini
        mk("2", 3, "2026-09-07T18:00:00Z", status="SCHEDULED"),   # lundi (aujourd'hui)
        mk("3", 4, "2026-09-14T18:00:00Z", status="SCHEDULED"),   # lundi suivant
    ]
    svc, league = service(matches)
    assert svc.league_view(league, "today").matchday == 3
    assert svc.league_view(league, "next").matchday == 4


def test_next_without_match_today_targets_first_future_matchday():
    matches = [
        mk("1", 2, "2026-09-01T18:00:00Z"),                      # fini
        mk("2", 3, "2026-09-14T18:00:00Z", status="SCHEDULED"),  # futur
    ]
    svc, league = service(matches)
    assert svc.league_view(league, "today").matchday == 0
    assert svc.league_view(league, "next").matchday == 3

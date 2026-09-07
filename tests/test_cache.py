import tempfile
from pathlib import Path

import app.services.provider as provider_mod
from app.models import Match, Team
from app.services.provider import CachedFootballProvider


class FlakyProvider:
    def __init__(self, data):
        self._data = data
        self.calls = 0

    def fetch_league_matches(self, league_id, season):
        self.calls += 1
        if self.calls == 1:
            return self._data
        raise RuntimeError("external provider down")


def make_match(i):
    return Match(
        id=str(i), league_id="TST", matchday=1, date="2024-01-01T10:00:00Z",
        home_team=Team(id="A", name="A"), away_team=Team(id="B", name="B"),
        home_score=2, away_score=0, status="FINISHED",
    )


def test_cache_avoids_second_external_call(monkeypatch):
    monkeypatch.setattr(provider_mod, "CACHE_TTL_SECONDS", 21600)
    data = [make_match(1)]
    raw = FlakyProvider(data)
    with tempfile.TemporaryDirectory() as d:
        cached = CachedFootballProvider(raw, db_path=str(Path(d) / "t.db"))
        cached.fetch_league_matches("TST", 2024)
        cached.fetch_league_matches("TST", 2024)
        assert raw.calls == 1  # cache frais -> pas d'appel externe à chaque page


def test_cache_fallback_on_provider_failure(monkeypatch):
    # TTL à 0 -> le cache n'est jamais frais, on appelle le provider qui échoue,
    # on retombe alors sur les dernières données connues.
    monkeypatch.setattr(provider_mod, "CACHE_TTL_SECONDS", 0)
    data = [make_match(1)]
    raw = FlakyProvider(data)
    with tempfile.TemporaryDirectory() as d:
        cached = CachedFootballProvider(raw, db_path=str(Path(d) / "t.db"))
        cached.fetch_league_matches("TST", 2024)
        second = cached.fetch_league_matches("TST", 2024)
        assert len(second) == 1
        assert second[0].id == "1"
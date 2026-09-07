import tempfile
from pathlib import Path

import pytest

import app.services.provider as provider_mod
from app.models import Match, Team
from app.services.provider import CachedFootballProvider, HttpFootballProvider


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


class ShrinkingThenDown:
    """1) 2 matchs, 2) réponse partielle (1 match), 3) panne."""

    def __init__(self):
        self.calls = 0

    def fetch_league_matches(self, league_id, season):
        self.calls += 1
        if self.calls == 1:
            return [make_match(1), make_match(2)]
        if self.calls == 2:
            return [make_match(1)]
        raise RuntimeError("external provider down")


def test_cache_partial_refresh_does_not_contaminate_fallback(monkeypatch):
    # Un rafraîchissement partiel ne doit pas laisser resurgir d'anciens matchs
    # dans le fallback : la dernière réponse réussie est la seule référence.
    monkeypatch.setattr(provider_mod, "CACHE_TTL_SECONDS", 0)
    raw = ShrinkingThenDown()
    with tempfile.TemporaryDirectory() as d:
        cached = CachedFootballProvider(raw, db_path=str(Path(d) / "t.db"))
        first = cached.fetch_league_matches("TST", 2024)
        assert {m.id for m in first} == {"1", "2"}
        second = cached.fetch_league_matches("TST", 2024)
        assert {m.id for m in second} == {"1"}
        # Provider en panne : le fallback doit refléter la dernière réponse et
        # ne pas réintroduire le match "2" retiré côté source.
        fallback = cached.fetch_league_matches("TST", 2024)
        assert {m.id for m in fallback} == {"1"}

class FakeResp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, resp):
        self._resp = resp

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, *a, **k):
        return self._resp


def test_http_provider_raises_on_api_error_body(monkeypatch):
    # API-Football renvoie parfois HTTP 200 avec un corps d'erreur (quota, clé
    # invalide). Cela doit lever pour que le wrapper cache serve le fallback
    # au lieu de considérer la réponse comme un succès vide.
    monkeypatch.setattr("httpx.Client", lambda *a, **k: FakeClient(FakeResp({"errors": {"requests": ["quota"]}})))
    p = HttpFootballProvider(api_token="t")
    with pytest.raises(RuntimeError):
        p.fetch_league_matches("61", 2026)


def test_http_provider_parses_valid_response(monkeypatch):
    payload = {
        "response": [{
            "fixture": {"id": 1, "date": "2026-09-07T18:00:00Z", "status": {"short": "FT"}},
            "teams": {"home": {"id": 11, "name": "PSG"}, "away": {"id": 12, "name": "OM"}},
            "goals": {"home": 2, "away": 1},
            "league": {"round": "Regular Season - 1"},
        }],
    }
    monkeypatch.setattr("httpx.Client", lambda *a, **k: FakeClient(FakeResp(payload)))
    p = HttpFootballProvider(api_token="t")
    matches = p.fetch_league_matches("61", 2026)
    assert len(matches) == 1
    assert matches[0].matchday == 1
    assert matches[0].status == "FINISHED"

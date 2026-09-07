from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services.provider import CachedFootballProvider
from app.services.sample import SampleFootballProvider
from app.services.service import AppService


def make_client(tmp_path, monkeypatch):
    provider = CachedFootballProvider(SampleFootballProvider(), db_path=str(tmp_path / "t.db"))
    settings = Settings(config_path="config/leagues.yaml")
    from app import main
    main.provider = provider
    main.settings = settings
    main.service = AppService(settings, provider)
    return TestClient(app)


def test_health(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_required_eleven_competitions_configured(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    r = client.get("/api/competitions")
    assert r.status_code == 200
    competitions = r.json()["competitions"]
    assert len(competitions) == 11
    ids = {c["id"] for c in competitions}
    assert {"ligue_1", "ligue_2", "premier_league", "la_liga", "serie_a", "serie_b", "bundesliga", "primeira_liga", "super_league_greece", "swiss_super_league", "super_lig"} == ids


def test_dashboard_defaults_to_last(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    assert r.json()["view"] == "last"
    assert len(r.json()["views"]) == 11


def test_contractual_competition_routes(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    for suffix, label in (("last-matchday", "last"), ("today", "today"), ("next-matchday", "next")):
        r = client.get(f"/api/competitions/ligue_1/{suffix}")
        assert r.status_code == 200
        assert r.json()["league_id"] == "ligue_1"
        assert r.json()["label"] == label


def test_competition_unknown_404(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/api/competitions/unknown/last-matchday").status_code == 404


def test_frontend_pages(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/").status_code == 200
    assert client.get("/competition/ligue_1").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200

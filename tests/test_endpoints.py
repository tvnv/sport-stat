import os
import tempfile
from pathlib import Path

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


def test_eleven_leagues_configured(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    r = client.get("/api/leagues")
    assert r.status_code == 200
    assert len(r.json()["leagues"]) == 11


def test_dashboard_endpoint(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    views = r.json()["views"]
    assert len(views) == 11
    # Les vues exposent les champs attendus : pays / ligue / journée / matchs / score / statut.
    v = views[0]
    for k in ("league_id", "league_name", "country", "matchday", "label", "matches"):
        assert k in v
    if v["matches"]:
        m = v["matches"][0]
        for k in ("home_team", "away_team", "home_score", "away_score", "status"):
            assert k in m


def test_competition_endpoint(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    r = client.get("/api/competition/PL")
    assert r.status_code == 200
    body = r.json()
    assert body["league_id"] == "PL"
    assert body["label"] in ("last", "today", "next")


def test_competition_unknown_404(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/api/competition/ZZZ").status_code == 404


def test_frontend_pages(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    assert client.get("/").status_code == 200
    assert client.get("/competition/PL").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200
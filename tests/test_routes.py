def _fixture(mid, league_id, season, round_str, date, home, away, hg, ag, status):
    return {
        "id": mid,
        "league_id": league_id,
        "season": season,
        "round": round_str,
        "date": date,
        "home_team_id": home[0],
        "home_team_name": home[1],
        "away_team_id": away[0],
        "away_team_name": away[1],
        "home_goals": hg,
        "away_goals": ag,
        "status_short": status,
        "elapsed": None,
    }


def test_index_renders_pre_matchday_positions(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))

    import importlib
    for module_name in ("app.config", "app.database", "app.api_client",
                        "app.routes", "app.main"):
        importlib.reload(importlib.import_module(module_name))

    import app.routes as routes
    import app.main as main

    season = 2026
    liga_fixtures = [
        _fixture(201, 61, season, "Regular Season - 1", "2026-08-09T15:00:00Z",
                 (1, "PSG"), (2, "Marseille"), 2, 1, "FT"),
        _fixture(202, 61, season, "Regular Season - 1", "2026-08-09T17:00:00Z",
                 (3, "Lyon"), (4, "Lille"), 1, 0, "FT"),
        # Matchday 2: standings displayed must be BEFORE this matchday.
        _fixture(203, 61, season, "Regular Season - 2", "2026-08-16T15:00:00Z",
                 (1, "PSG"), (4, "Lille"), 5, 5, "NS"),
        _fixture(204, 61, season, "Regular Season - 2", "2026-08-16T17:00:00Z",
                 (2, "Marseille"), (3, "Lyon"), 5, 5, "NS"),
    ]
    super_fixtures = [
        _fixture(301, 203, season, "Regular Season - 1", "2026-08-10T15:00:00Z",
                 (11, "Galatasaray"), (12, "Trabzonspor"), 3, 1, "FT"),
        _fixture(302, 203, season, "Regular Season - 1", "2026-08-10T17:00:00Z",
                 (13, "Fenerbahce"), (14, "Besiktas"), 1, 1, "FT"),
        _fixture(303, 203, season, "Regular Season - 2", "2026-08-17T15:00:00Z",
                 (14, "Besiktas"), (11, "Galatasaray"), 0, 0, "NS"),
        _fixture(304, 203, season, "Regular Season - 2", "2026-08-17T17:00:00Z",
                 (12, "Trabzonspor"), (13, "Fenerbahce"), 0, 0, "NS"),
    ]

    def fake_fetch(league_id, season_num, round_str=None):
        if league_id == 61:
            return list(liga_fixtures)
        if league_id == 203:
            return list(super_fixtures)
        return []

    monkeypatch.setattr(routes, "fetch_fixtures", fake_fetch)

    from app.api_client import _persist_matches
    _persist_matches(liga_fixtures)
    _persist_matches(super_fixtures)

    app_obj = main.create_app()
    client = TestClient(app_obj)

    resp = client.get("/", params={"view": "last"})
    assert resp.status_code == 200
    html = resp.text

    # Header / nav present
    assert "Dernière journée" in html
    assert "Aujourd'hui" in html
    assert "Prochaine journée" in html

    # Both competitions render
    assert "Ligue 1" in html
    assert "Süper Lig" in html

    # Default view is Dernière journée -> matchday 1 results shown.
    assert "Regular Season - 1" in html

    # Positions BEFORE matchday 1: nobody has played yet, but round-1 standings
    # are shown for the round-1 view (positions from before round 1 are all
    # unplayed -> rank shown as None; the score still renders).
    assert "PSG" in html
    assert "Marseille" in html
    assert "2 – 1" in html

    # Next-journee view: standings must be PRE-matchday-2 (round 1 results only).
    resp_next = client.get("/", params={"view": "next"})
    html_next = resp_next.text
    assert "Regular Season - 2" in html_next
    # PSG won round 1 -> position 1 in parentheses on round-2 fixture.
    assert "PSG (1)" in html_next
    # Lille lost round 1 -> position 4.
    assert "Lille (4)" in html_next
    # The unplayed matchday 2 must NOT leak a score.
    assert "5 – 5" not in html_next


def test_last_view_does_not_select_partial_matchday(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))

    import importlib
    for module_name in ("app.config", "app.database", "app.api_client",
                        "app.routes", "app.main"):
        importlib.reload(importlib.import_module(module_name))

    import app.routes as routes
    import app.main as main
    from app.api_client import _persist_matches

    season = 2026
    fixtures = [
        # Round 1 fully played.
        _fixture(501, 61, season, "Regular Season - 1", "2026-08-09T15:00:00Z",
                 (1, "PSG"), (2, "Marseille"), 2, 1, "FT"),
        _fixture(502, 61, season, "Regular Season - 1", "2026-08-09T17:00:00Z",
                 (3, "Lyon"), (4, "Lille"), 1, 0, "FT"),
        # Round 2 PARTIALLY played: only one match finished, the other is NS.
        _fixture(503, 61, season, "Regular Season - 2", "2026-08-16T15:00:00Z",
                 (1, "PSG"), (4, "Lille"), 3, 0, "FT"),
        _fixture(504, 61, season, "Regular Season - 2", "2026-08-16T17:00:00Z",
                 (2, "Marseille"), (3, "Lyon"), None, None, "NS"),
    ]
    _persist_matches(fixtures)

    def fake_fetch(league_id, season_num, round_str=None):
        return list(fixtures)

    monkeypatch.setattr(routes, "fetch_fixtures", fake_fetch)

    app_obj = main.create_app()
    client = TestClient(app_obj)

    resp = client.get("/", params={"view": "last"})
    assert resp.status_code == 200
    html = resp.text

    # The last fully-completed matchday is Round 1; the partially-played
    # Round 2 must NOT be chosen as "Dernière journée".
    assert "Regular Season - 1" in html
    assert "Regular Season - 2" not in html
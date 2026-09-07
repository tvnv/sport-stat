"""Abstraction provider externe (API-Football) + cache SQLite local."""
import json
import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from ..models import Match

DEFAULT_DB_PATH = os.environ.get("SPORTSTAT_DB", "data/sportstat.db")
DEFAULT_API_URL = "https://v3.football.api-sports.io"
CACHE_TTL_SECONDS = int(os.environ.get("SPORTSTAT_CACHE_TTL", "21600"))


class FootballProvider(ABC):
    @abstractmethod
    def fetch_league_matches(self, league_id: str, season: int) -> List[Match]:
        """Retourne les matchs normalisés d'une compétition/saison."""
        ...

    def get_competitions(self):
        return []

    def get_fixtures(self, league_id: str, season: int) -> List[Match]:
        return self.fetch_league_matches(league_id, season)

    def get_standings(self, league_id: str, season: int):
        return None

    def get_season(self, league_id: str) -> Optional[int]:
        return None


class HttpFootballProvider(FootballProvider):
    """Provider réel API-Football. `league_id` est l'id numérique API-Football."""

    def __init__(self, api_token: Optional[str] = None, base_url: str = DEFAULT_API_URL):
        self._token = api_token or os.environ.get("API_FOOTBALL_KEY", "")
        self._base_url = base_url.rstrip("/")

    def fetch_league_matches(self, league_id: str, season: int) -> List[Match]:
        if not self._token:
            raise RuntimeError("API_FOOTBALL_KEY is not configured")
        headers = {"x-apisports-key": self._token}
        params = {"league": league_id, "season": season}
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(f"{self._base_url}/fixtures", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return [self._parse(item, str(league_id)) for item in data.get("response", [])]

    @staticmethod
    def _parse(item, league_id: str) -> Match:
        fixture = item.get("fixture", {}) or {}
        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        league = item.get("league", {}) or {}
        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}
        short = ((fixture.get("status") or {}).get("short") or "NS").upper()
        if short in {"FT", "AET", "PEN"}:
            status = "FINISHED"
        elif short in {"1H", "HT", "2H", "ET", "BT", "P"}:
            status = "LIVE"
        elif short in {"PST", "CANC", "ABD", "AWD", "WO"}:
            status = "POSTPONED"
        else:
            status = "SCHEDULED"
        return Match(
            id=str(fixture.get("id", "")),
            league_id=league_id,
            matchday=int(league.get("round", "0").split("-")[-1].strip() or 0),
            date=fixture.get("date", ""),
            home_team={"id": str(home.get("id", "")), "name": home.get("name", "")},
            away_team={"id": str(away.get("id", "")), "name": away.get("name", "")},
            home_score=goals.get("home"),
            away_score=goals.get("away"),
            status=status,
        )


class CachedFootballProvider(FootballProvider):
    """Wrapper SQLite : cache agressif et fallback sur dernières données connues."""

    def __init__(self, provider: FootballProvider, db_path: str = DEFAULT_DB_PATH):
        self._provider = provider
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(os.path.abspath(self._db_path)), exist_ok=True)
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    league_id TEXT,
                    payload TEXT,
                    fetched_at REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_league ON matches(league_id)")

    def fetch_league_matches(self, league_id: str, season: int) -> List[Match]:
        cached = self._load(league_id)
        fresh = bool(cached) and (time.time() - self._last_fetched(league_id)) < CACHE_TTL_SECONDS
        if fresh:
            return cached
        try:
            matches = self._provider.fetch_league_matches(league_id, season)
            self._store(league_id, matches)
            return matches
        except Exception:
            return cached if cached else []

    def _last_fetched(self, league_id: str) -> float:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT MAX(fetched_at) FROM matches WHERE league_id = ?", (league_id,)).fetchone()
        return row[0] if row and row[0] is not None else 0.0

    def _load(self, league_id: str) -> List[Match]:
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT payload FROM matches WHERE league_id = ?", (league_id,)).fetchall()
        return [Match.model_validate_json(r[0]) for r in rows]

    def _store(self, league_id: str, matches: List[Match]) -> None:
        now = time.time()
        with self._lock, self._connect() as conn:
            for m in matches:
                conn.execute(
                    "INSERT OR REPLACE INTO matches(id, league_id, payload, fetched_at) VALUES (?,?,?,?)",
                    (m.id, league_id, m.model_dump_json(), now),
                )
            conn.commit()

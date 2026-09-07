"""Abstraction du provider externe (football-data.org) + cache SQLite local.

Le cache local évite un appel externe à chaque page et permet un fallback vers les
dernières données connues si le provider est indisponible.
"""
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
DEFAULT_API_URL = "https://api.football-data.org/v4"
CACHE_TTL_SECONDS = int(os.environ.get("SPORTSTAT_CACHE_TTL", "21600"))  # 6h par défaut


class FootballProvider(ABC):
    @abstractmethod
    def fetch_league_matches(self, league_id: str, season: int) -> List[Match]:
        """Retourne la liste des matchs d'une ligue pour une saison."""
        ...


class HttpFootballProvider(FootballProvider):
    """Provider réel via HTTP (football-data.org)."""

    def __init__(self, api_token: Optional[str] = None, base_url: str = DEFAULT_API_URL):
        self._token = api_token or os.environ.get("FOOTBALL_API_TOKEN", "")
        self._base_url = base_url

    def fetch_league_matches(self, league_id: str, season: int) -> List[Match]:
        if not self._token:
            raise RuntimeError("FOOTBALL_API_TOKEN is not configured")
        headers = {"X-Auth-Token": self._token}
        url = f"{self._base_url}/competitions/{league_id}/matches"
        params = {"season": season}
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return [self._parse(m) for m in data.get("matches", [])]

    @staticmethod
    def _parse(m) -> Match:
        home = m.get("homeTeam", {}) or {}
        away = m.get("awayTeam", {}) or {}
        score = m.get("score", {}) or {}
        return Match(
            id=str(m.get("id", "")),
            league_id=str(m.get("competition", {}).get("code", "")),
            matchday=int(m.get("matchday") or 0),
            date=m.get("utcDate", ""),
            home_team={"id": str(home.get("id", "")), "name": home.get("name", "")},
            away_team={"id": str(away.get("id", "")), "name": away.get("name", "")},
            home_score=score.get("fullTime", {}).get("home") if score else None,
            away_score=score.get("fullTime", {}).get("away") if score else None,
            status=m.get("status", "SCHEDULED"),
        )


class CachedFootballProvider(FootballProvider):
    """Wrapper avec persistance SQLite et fallback sur les dernières données connues."""

    def __init__(self, provider: FootballProvider, db_path: str = DEFAULT_DB_PATH):
        self._provider = provider
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(os.path.abspath(self._db_path)), exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS matches (
                    id TEXT PRIMARY KEY,
                    league_id TEXT,
                    payload TEXT,
                    fetched_at REAL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_league ON matches(league_id)")

    def fetch_league_matches(self, league_id: str, season: int) -> List[Match]:
        cached = self._load(league_id)
        fresh = cached and (time.time() - self._last_fetched(league_id)) < CACHE_TTL_SECONDS
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
            row = conn.execute(
                "SELECT MAX(fetched_at) FROM matches WHERE league_id = ?", (league_id,)
            ).fetchone()
        return row[0] if row and row[0] is not None else 0.0

    def _load(self, league_id: str) -> List[Match]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM matches WHERE league_id = ?",
                (league_id,),
            ).fetchall()
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
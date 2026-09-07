import sqlite3
from pathlib import Path

from .config import DATABASE_PATH


def get_db() -> sqlite3.Connection:
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY,
            league_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            round TEXT NOT NULL,
            date TEXT NOT NULL,
            home_team_id INTEGER NOT NULL,
            home_team_name TEXT NOT NULL,
            away_team_id INTEGER NOT NULL,
            away_team_name TEXT NOT NULL,
            home_goals INTEGER,
            away_goals INTEGER,
            status_short TEXT NOT NULL,
            elapsed INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            round TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            team_name TEXT NOT NULL,
            played INTEGER DEFAULT 0,
            win INTEGER DEFAULT 0,
            draw INTEGER DEFAULT 0,
            loss INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            goal_difference INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            rank INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_matches_league_season_round
            ON matches(league_id, season, round);
        CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
        CREATE INDEX IF NOT EXISTS idx_standings_league_season_round
            ON standings(league_id, season, round);
    """)
    conn.close()

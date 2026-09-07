import time
import httpx

from .config import API_FOOTBALL_KEY, API_FOOTBALL_BASE_URL, API_CACHE_TTL_SECONDS
from .database import get_db


def _is_cache_fresh(league_id: int, season: int, round_str: str | None = None) -> bool:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT MAX(updated_at) as last_update FROM matches WHERE league_id=? AND season=?",
            (league_id, season),
        ).fetchone()
        if not row or not row["last_update"]:
            return False
        last_ts = row["last_update"]
        if isinstance(last_ts, str):
            import datetime
            last_ts = datetime.datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        return (time.time() - last_ts.timestamp()) < API_CACHE_TTL_SECONDS
    finally:
        conn.close()


def fetch_fixtures(league_id: int, season: int, round_str: str | None = None) -> list[dict]:
    if _is_cache_fresh(league_id, season, round_str):
        return _load_cached(league_id, season)

    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params: dict = {"league": league_id, "season": season}
    if round_str:
        params["round"] = round_str

    results = []
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.get(f"{API_FOOTBALL_BASE_URL}/fixtures", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            for fx in data.get("response", []):
                fixture = fx["fixture"]
                teams = fx["teams"]
                goals = fx["goals"]
                league = fx["league"]
                results.append({
                    "id": fixture["id"],
                    "league_id": league["id"],
                    "season": league["season"],
                    "round": league["round"],
                    "date": fixture["date"],
                    "home_team_id": teams["home"]["id"],
                    "home_team_name": teams["home"]["name"],
                    "away_team_id": teams["away"]["id"],
                    "away_team_name": teams["away"]["name"],
                    "home_goals": goals["home"],
                    "away_goals": goals["away"],
                    "status_short": fixture["status"]["short"],
                    "elapsed": fixture["status"].get("elapsed"),
                })
    except Exception:
        results = _load_cached(league_id, season)

    if results:
        _persist_matches(results)
    return results


def _load_cached(league_id: int, season: int) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM matches WHERE league_id=? AND season=? ORDER BY date, round",
            (league_id, season),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _persist_matches(matches: list[dict]) -> None:
    conn = get_db()
    try:
        for m in matches:
            conn.execute(
                """INSERT OR REPLACE INTO matches
                   (id, league_id, season, round, date, home_team_id, home_team_name,
                    away_team_id, away_team_name, home_goals, away_goals, status_short, elapsed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (m["id"], m["league_id"], m["season"], m["round"], m["date"],
                 m["home_team_id"], m["home_team_name"],
                 m["away_team_id"], m["away_team_name"],
                 m["home_goals"], m["away_goals"],
                 m["status_short"], m["elapsed"]),
            )
        conn.commit()
    finally:
        conn.close()


def get_rounds_for_season(league_id: int, season: int) -> list[str]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT round FROM matches WHERE league_id=? AND season=? ORDER BY round",
            (league_id, season),
        ).fetchall()
        return [r["round"] for r in rows]
    finally:
        conn.close()


def persist_standings(league_id: int, season: int, round_str: str, standings: list[dict]) -> None:
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM standings WHERE league_id=? AND season=? AND round=?",
            (league_id, season, round_str),
        )
        for s in standings:
            conn.execute(
                """INSERT INTO standings
                   (league_id, season, round, team_id, team_name, played, win, draw, loss,
                    goals_for, goals_against, goal_difference, points, rank)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (league_id, season, round_str, s["team_id"], s["team_name"],
                 s["played"], s["win"], s["draw"], s["loss"],
                 s["goals_for"], s["goals_against"], s["goal_difference"], s["points"], s["rank"]),
            )
        conn.commit()
    finally:
        conn.close()


def load_cached_standings(league_id: int, season: int, round_str: str) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM standings WHERE league_id=? AND season=? AND round=? ORDER BY rank",
            (league_id, season, round_str),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

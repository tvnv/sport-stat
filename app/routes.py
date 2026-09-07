import re
from pathlib import Path

import yaml
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .config import COMPETITIONS_CONFIG
from .database import get_db
from .api_client import fetch_fixtures, get_rounds_for_season, persist_standings, load_cached_standings
from .standings import compute_standings_for_round, get_team_position
from .models import FixtureDisplay

router = APIRouter()

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _load_competitions() -> list[dict]:
    with open(COMPETITIONS_CONFIG) as f:
        data = yaml.safe_load(f)
    return data["competitions"]


def _extract_round_number(round_str: str) -> int:
    m = re.search(r"(\d+)", round_str)
    return int(m.group(1)) if m else 0


def _get_current_season() -> int:
    from datetime import date
    today = date.today()
    return today.year if today.month >= 8 else today.year - 1


def _get_latest_round(league_id: int, season: int) -> str | None:
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT round FROM matches
               WHERE league_id=? AND season=?
               GROUP BY round
               HAVING COUNT(*) = SUM(CASE WHEN status_short IN ('FT','P','AET','PEN') THEN 1 ELSE 0 END)""",
            (league_id, season),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return None
    # Select the most advanced fully-completed round by round number, not by
    # MAX(date): a postponed match from an older round played late must not
    # push that older round ahead of a higher, fully-completed round.
    return max(rows, key=lambda r: (_extract_round_number(r["round"]), r["round"]))["round"]


def _get_next_round(league_id: int, season: int, current_round: str | None) -> str | None:
    if not current_round:
        return None
    rounds = get_rounds_for_season(league_id, season)
    if not rounds:
        return None
    current_num = _extract_round_number(current_round)
    for r in rounds:
        if _extract_round_number(r) == current_num + 1:
            return r
    return None


def _get_fixtures_display(matches: list[dict], round_str: str, standings: list[dict]) -> list[FixtureDisplay]:
    display = []
    for m in matches:
        if m["round"] != round_str:
            continue
        home_pos = get_team_position(m["home_team_id"], standings)
        away_pos = get_team_position(m["away_team_id"], standings)

        if m["status_short"] in ("FT", "P", "AET", "PEN") and m["home_goals"] is not None:
            score_str = f"{m['home_goals']} – {m['away_goals']}"
            status = "Terminé"
        elif m["status_short"] in ("NS", "TBD"):
            score_str = "vs"
            status = "Programmé"
        else:
            score_str = f"{m['home_goals'] or '?'} – {m['away_goals'] or '?'}"
            status = m["status_short"]

        display.append(FixtureDisplay(
            home_team=m["home_team_name"],
            home_position=home_pos,
            away_team=m["away_team_name"],
            away_position=away_pos,
            home_goals=m["home_goals"],
            away_goals=m["away_goals"],
            status=status,
            score_str=score_str,
        ))
    return display


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def index(request: Request, view: str = Query(default="last")):
    competitions = _load_competitions()
    season = _get_current_season()

    sections = []
    for comp in competitions:
        lid = comp["api_football_id"]
        name = comp["name"]
        tie_break_rules = comp.get("tie_break_rules", [])

        all_matches = fetch_fixtures(lid, season)

        latest_round = _get_latest_round(lid, season)
        next_round = _get_next_round(lid, season, latest_round)
        today_round = _get_today_round(all_matches)

        if view == "next" and next_round:
            target_round = next_round
        elif view == "today" and today_round:
            target_round = today_round
        else:
            target_round = latest_round

        if not target_round:
            continue

        cached = load_cached_standings(lid, season, target_round)
        if cached:
            standings = cached
        else:
            standings = compute_standings_for_round(all_matches, lid, season, target_round, tie_break_rules)
            if standings:
                persist_standings(lid, season, target_round, standings)

        fixtures = _get_fixtures_display(all_matches, target_round, standings)

        sections.append({
            "competition": name,
            "round": target_round,
            "fixtures": fixtures,
        })

    return templates.TemplateResponse(request, "index.html", {
        "sections": sections,
        "current_view": view,
    })


def _get_today_round(matches: list[dict]) -> str | None:
    from datetime import date
    today = date.today().isoformat()
    for m in matches:
        if m["date"] and m["date"][:10] == today:
            return m["round"]
    return None

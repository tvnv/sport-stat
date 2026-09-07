import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import Settings
from .services.provider import CachedFootballProvider, HttpFootballProvider
from .services.sample import SampleFootballProvider
from .services.service import AppService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
settings = Settings()
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "..", "templates"))
static_dir = os.path.join(BASE_DIR, "..", "static")


def build_provider() -> CachedFootballProvider:
    raw = HttpFootballProvider() if os.environ.get("API_FOOTBALL_KEY") else SampleFootballProvider()
    return CachedFootballProvider(raw)


provider = build_provider()
service = AppService(settings, provider)

app = FastAPI(title="sport-stat", version="1.0.0")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"leagues": settings.as_dict()})


@app.get("/api/competitions")
@app.get("/api/leagues")
def api_competitions():
    return {"competitions": settings.as_dict(), "leagues": settings.as_dict()}


@app.get("/api/dashboard")
def api_dashboard(view: str = "last", label: str = None):
    selected = label or view or "last"
    views = [service.league_view(l, selected) for l in settings.leagues]
    return {"view": selected, "views": [v.model_dump(mode="json") for v in views]}


def _competition_view(league_id: str, label: str):
    try:
        return service.view_for(league_id, label).model_dump(mode="json")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown competition {league_id}")


@app.get("/api/competitions/{league_id}/last-matchday")
def api_last_matchday(league_id: str):
    return _competition_view(league_id, "last")


@app.get("/api/competitions/{league_id}/today")
def api_today(league_id: str):
    return _competition_view(league_id, "today")


@app.get("/api/competitions/{league_id}/next-matchday")
def api_next_matchday(league_id: str):
    return _competition_view(league_id, "next")


@app.get("/api/competition/{league_id}")
def api_competition_compat(league_id: str, label: str = "last"):
    return _competition_view(league_id, label)


@app.get("/competition/{league_id}", response_class=HTMLResponse)
def competition_page(league_id: str, request: Request):
    try:
        settings.league_by_id(league_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown competition {league_id}")
    return templates.TemplateResponse(
        request, "competition.html", {"league_id": league_id, "leagues": settings.as_dict()}
    )

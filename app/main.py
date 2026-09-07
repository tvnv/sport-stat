import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
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
    if os.environ.get("FOOTBALL_API_TOKEN"):
        raw = HttpFootballProvider()
    else:
        raw = SampleFootballProvider()
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


@app.get("/api/leagues")
def api_leagues():
    return {"leagues": settings.as_dict()}


@app.get("/api/dashboard")
def api_dashboard(label: str = None):
    views = [service.league_view(l, label) for l in settings.leagues]
    return {"views": [v.model_dump(mode="json") for v in views]}


@app.get("/api/competition/{league_id}")
def api_competition(league_id: str, label: str = None):
    try:
        view = service.view_for(league_id, label)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown league {league_id}")
    return view.model_dump(mode="json")


@app.get("/competition/{league_id}", response_class=HTMLResponse)
def competition_page(league_id: str, request: Request):
    try:
        settings.league_by_id(league_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown league {league_id}")
    return templates.TemplateResponse(
        request, "competition.html", {"league_id": league_id, "leagues": settings.as_dict()}
    )
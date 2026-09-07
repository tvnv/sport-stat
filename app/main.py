from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .database import init_db
from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Sport Stat")
    init_db()
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(router)
    return app


app = create_app()

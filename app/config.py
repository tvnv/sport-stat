import os
from pathlib import Path

DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/sport_stat.db")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"
COMPETITIONS_CONFIG = Path(__file__).parent.parent / "config" / "competitions.yaml"
API_CACHE_TTL_SECONDS = int(os.environ.get("API_CACHE_TTL_SECONDS", "3600"))

import os

def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    os.environ[key] = value

load_env()

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str = ""

    # Spatial database (PostGIS). Owner role for full-access reads/writes;
    # readonly role is what the LLM-generated SQL runs as (see docs/ARCHITECTURE.md §5.5).
    DATABASE_URL: str = "postgresql+asyncpg://geo:geo@localhost:5433/geo"
    DATABASE_URL_READONLY: str = "postgresql+asyncpg://geo_readonly:geo_readonly@localhost:5433/geo"

    # Vector tile server (Martin)
    MARTIN_URL: str = "http://localhost:3001"

    class Config:
        extra = "ignore"

settings = Settings()

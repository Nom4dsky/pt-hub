"""
FastAPI app for exercise database management (Phase 4a).

Run with:
    uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/ in a browser.

Scope: exercise CRUD + the movement_patterns/muscles/equipment lookup
tables only. Workouts, programs, and session logging (Phases 2-3) have no
UI yet — that's a later phase, per the brief.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import equipment, exercises, movement_patterns, muscles

app = FastAPI(title="Exercise Database", version="0.1.0")

app.include_router(exercises.router)
app.include_router(movement_patterns.router)
app.include_router(muscles.router)
app.include_router(equipment.router)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

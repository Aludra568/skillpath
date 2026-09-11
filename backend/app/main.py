from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import Base, engine
from .routers import analytics, auth, catalog, departments, meetings, plans, users

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Нужно только для локальной разработки, когда фронт крутится на Vite.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(departments.router)
app.include_router(users.router)
app.include_router(plans.router)
app.include_router(meetings.router)
app.include_router(meetings.issues_router)
app.include_router(analytics.router)
app.include_router(analytics.events_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


static_dir = settings.static_dir
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        # Отдаём собранный фронтенд, но неизвестные /api-пути — это 404, а не index.html.
        if path.startswith("api/"):
            raise HTTPException(404, "Неизвестный метод API")
        return FileResponse(static_dir / "index.html")

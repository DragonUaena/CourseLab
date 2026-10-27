from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import Settings
from app.database import Database
from app.worker import CourseLabQueue, build_cipher


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()
    database = Database(resolved_settings.database_url)
    cipher = build_cipher(resolved_settings)
    worker = CourseLabQueue(database, resolved_settings, cipher)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.create_all()
        worker.start()
        yield
        worker.stop()
        database.close()

    app = FastAPI(
        title="CourseLab API",
        version="0.1.0",
        description="Multi-agent learning route planning with CrewAI and Tavily.",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database = database
    app.state.cipher = cipher
    app.state.worker = worker
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()


def run() -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import create_db_and_tables
from app.llm.client import OllamaClient
from app.llm.gemini_client import GeminiClient
from app.llm.pipeline import GradingPipeline
from app.routers import student, teacher
from app.routers.auth import router as auth_router, _LoginRequired

app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.load_questionnaires()
    create_db_and_tables()

    client = OllamaClient(settings.ollama_base_url, settings.ollama_model)

    gemini_client = None
    if settings.gemini_enabled:
        gemini_client = GeminiClient(settings.gemini_api_key, settings.gemini_model)

    pipeline = GradingPipeline(client, settings.questionnaires, gemini_client)

    app_state["questionnaires"] = settings.questionnaires
    app_state["pipeline"] = pipeline
    app_state["ollama_client"] = client
    app_state["gemini_client"] = gemini_client

    yield
    app_state.clear()


app = FastAPI(title="EQ改作業小幫手", lifespan=lifespan)

# Session middleware for Google OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_router)
app.include_router(student.router)
app.include_router(teacher.router)


@app.exception_handler(_LoginRequired)
async def login_required_handler(request: Request, exc: _LoginRequired):
    return RedirectResponse(url="/login")


@app.get("/health")
async def health():
    client: OllamaClient = app_state.get("ollama_client")
    gemini: GeminiClient | None = app_state.get("gemini_client")
    ollama_ok = await client.health_check() if client else False
    gemini_ok = await gemini.health_check() if gemini else None
    return {
        "status": "ok" if ollama_ok else "degraded",
        "ollama": ollama_ok,
        "gemini": gemini_ok,
        "google_oauth": settings.google_oauth_enabled,
        "questionnaires_loaded": len(app_state.get("questionnaires", {})),
    }

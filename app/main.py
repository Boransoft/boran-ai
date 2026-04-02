from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.auth.routes import router as auth_router
from app.auth.utils import JwtAuthMiddleware
from app.config import settings
from app.learning.scheduler import consolidation_scheduler
from app.voice.routes import router as voice_router

app = FastAPI(title=settings.app_name, version=settings.app_version)
allow_origins = (
    ["*"]
    if settings.cors_allow_origins.strip() == "*"
    else [item.strip() for item in settings.cors_allow_origins.split(",") if item.strip()]
)
allow_methods = (
    ["*"]
    if settings.cors_allow_methods.strip() == "*"
    else [item.strip() for item in settings.cors_allow_methods.split(",") if item.strip()]
)
allow_headers = (
    ["*"]
    if settings.cors_allow_headers.strip() == "*"
    else [item.strip() for item in settings.cors_allow_headers.split(",") if item.strip()]
)

app.add_middleware(JwtAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(voice_router)


@app.on_event("startup")
def startup_event() -> None:
    consolidation_scheduler.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    consolidation_scheduler.stop()

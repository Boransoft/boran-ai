import logging
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.routes import router as admin_router
from app.api.routes import router as api_router
from app.auth.routes import router as auth_router
from app.auth.utils import JwtAuthMiddleware
from app.config import settings
from app.learning.scheduler import consolidation_scheduler
from app.voice.routes import router as voice_router


logger = logging.getLogger("uvicorn.error")

app = FastAPI(title=settings.app_name, version=settings.app_version)

DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://172.29.96.1:5173",
    "http://172.25.16.1:5173",
]


def parse_origin_setting(value: object) -> list[str]:
    if isinstance(value, str):
        if value.strip() == "*":
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip() and str(item).strip() != "*"]
    return []


def merge_origins(*origin_groups: list[str]) -> list[str]:
    merged: list[str] = []
    for origins in origin_groups:
        for origin in origins:
            if origin not in merged:
                merged.append(origin)
    return merged


allow_origins = merge_origins(
    parse_origin_setting(settings.cors_allow_origins),
    DEFAULT_DEV_ORIGINS,
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
app.include_router(admin_router)
app.include_router(voice_router)


@app.on_event("startup")
def startup_event() -> None:
    startup_begin = perf_counter()
    logger.info("startup_begin")

    step_begin = perf_counter()
    consolidation_scheduler.start()
    logger.info("startup_step scheduler_start_s=%.3f", perf_counter() - step_begin)

    # Keep startup non-blocking: voice/stt/tts warmup is lazy and runs on first use.
    logger.info(
        "startup_step voice_warmup_skipped lazy_init_enabled=true voice_warmup_enabled_setting=%s",
        settings.voice_warmup_enabled,
    )
    logger.info("startup_done total_s=%.3f", perf_counter() - startup_begin)


@app.on_event("shutdown")
def shutdown_event() -> None:
    consolidation_scheduler.stop()

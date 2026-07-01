from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

REQUIRED_TABLES = (
    "users",
    "conversations",
    "corrections",
    "memory_items",
    "knowledge_edges",
)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    return create_engine(settings.database_url, future=True, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory():
    engine = get_engine()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session() -> Session:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def check_db_health() -> tuple[bool, str]:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            inspector = inspect(conn)
            missing_tables = [table_name for table_name in REQUIRED_TABLES if not inspector.has_table(table_name)]
            if missing_tables:
                return False, f"database schema missing tables: {', '.join(missing_tables)}"
        return True, "database connection is healthy"
    except Exception as exc:
        return False, str(exc)

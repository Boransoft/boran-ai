from sqlalchemy import text

from app.db.models import Base
from app.db.session import get_engine


def _apply_auth_migrations() -> None:
    engine = get_engine()
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(64)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username ON users (username)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email ON users (email)",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def init_database() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _apply_auth_migrations()

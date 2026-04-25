from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.utils import create_access_token, hash_password, verify_password
from app.config import settings
from app.db.models import User
from app.db.session import get_session


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _normalize_username(value: str) -> str:
    return value.strip().lower()


def _to_user_public(user: User) -> dict[str, object]:
    return {
        "id": str(user.id),
        "external_id": str(user.external_id),
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": bool(user.is_active),
        "is_admin": bool(user.is_admin),
        "created_at": user.created_at,
    }


def _admin_identifier_set() -> set[str]:
    raw = str(settings.admin_identifiers or "")
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _should_be_admin(user: User) -> bool:
    if user.is_admin:
        return True

    configured = _admin_identifier_set()
    if not configured:
        return False

    candidates = {
        str(user.external_id or "").strip().lower(),
        str(user.username or "").strip().lower(),
        str(user.email or "").strip().lower(),
    }
    candidates.discard("")
    return any(candidate in configured for candidate in candidates)


def _find_user_by_email(session, normalized_email: str) -> User | None:
    return session.execute(
        select(User).where(User.email == normalized_email)
    ).scalar_one_or_none()


def _find_user_by_username(session, normalized_username: str) -> User | None:
    return session.execute(
        select(User).where(User.username == normalized_username)
    ).scalar_one_or_none()


def register_user(
    username: str,
    email: str,
    password: str,
    display_name: str | None = None,
) -> dict[str, object]:
    normalized_email = _normalize_email(email)
    normalized_username = _normalize_username(username)

    with get_session() as session:
        existing_email = _find_user_by_email(session, normalized_email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists.",
            )

        existing_username = _find_user_by_username(session, normalized_username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists.",
            )

        user = User(
            external_id=f"user_{uuid4().hex}",
            username=normalized_username,
            email=normalized_email,
            hashed_password=hash_password(password),
            display_name=(display_name.strip() if display_name else None),
            is_active=True,
        )
        user.is_admin = _should_be_admin(user)
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with same email or username already exists.",
            )
        session.refresh(user)

    token, expires_in = create_access_token(str(user.external_id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": _to_user_public(user),
    }


def login_user(identifier: str, password: str) -> dict[str, object]:
    normalized = identifier.strip().lower()
    with get_session() as session:
        user = _find_user_by_email(session, normalized)
        if not user:
            user = _find_user_by_username(session, normalized)

        if not user or not user.hashed_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive.",
            )
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
            )

        user.last_login_at = datetime.now(timezone.utc)
        if _should_be_admin(user) and not user.is_admin:
            user.is_admin = True
        session.commit()
        session.refresh(user)

    token, expires_in = create_access_token(str(user.external_id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": _to_user_public(user),
    }


def get_user_by_external_id(external_id: str) -> User:
    with get_session() as session:
        user = session.execute(
            select(User).where(User.external_id == external_id)
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive.",
            )
        if _should_be_admin(user) and not user.is_admin:
            user.is_admin = True
            session.commit()
            session.refresh(user)
        return user


def get_current_user_public(external_id: str) -> dict[str, object]:
    user = get_user_by_external_id(external_id=external_id)
    return _to_user_public(user)

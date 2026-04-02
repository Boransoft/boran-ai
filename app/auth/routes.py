from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.auth.service import (
    get_current_user_public,
    login_user,
    register_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_external_id(request: Request) -> str:
    external_id = getattr(request.state, "auth_external_id", None)
    if not external_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authenticated user.",
        )
    return str(external_id)


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest):
    return register_user(
        username=req.username,
        email=req.email,
        password=req.password,
        display_name=req.display_name,
    )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    return login_user(
        identifier=req.identifier,
        password=req.password,
    )


@router.get("/me", response_model=UserPublic)
def me(external_id: str = Depends(get_current_external_id)):
    return get_current_user_public(external_id)

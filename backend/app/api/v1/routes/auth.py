from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.domain.models.enums import UserRole
from app.api.dependencies import require_role
from fastapi.security import OAuth2PasswordRequestForm
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)

from app.domain.models.enums import UserRole
from app.domain.models.user import User

from app.domain.schemas.auth import (
    UserRegister,
    TokenResponse,
)

from app.domain.schemas.user import UserResponse

from app.repositories.user_repository import UserRepository

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
)
def register(
    payload: UserRegister,
    db: Session = Depends(get_db),
):

    repo = UserRepository(db)

    existing_user = repo.get_by_email(
        payload.email
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(
            payload.password
        ),
        role=UserRole.ANALYST,
    )

    return repo.create(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):

    repo = UserRepository(db)

    user = repo.get_by_email(
        form_data.username
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    if not verify_password(
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    access_token = create_access_token(
        {
            "sub": user.email,
            "role": user.role.value,
        }
    )

    return TokenResponse(
        access_token=access_token
    )

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user=Depends(
        get_current_user
    ),
):
    return current_user

@router.get("/admin-only")
def admin_only(
    current_user=Depends(
        require_role("ADMIN")
    )
):
    return {
        "message": "Admin Access Granted"
    }


@router.get("/analyst-only")
def analyst_only(
    current_user=Depends(
        require_role(
            "ADMIN",
            "ANALYST",
        )
    )
):
    return {
        "message": "Analyst Access Granted"
    }


@router.get("/viewer-only")
def viewer_only(
    current_user=Depends(
        require_role(
            "ADMIN",
            "ANALYST",
            "VIEWER",
        )
    )
):
    return {
        "message": "Viewer Access Granted"
    }
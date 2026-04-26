from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    decode_token,
)
from app.core.exceptions import AuthError
from app.dependencies import DBDep, UserDep
from app.models.user import User
from app.schemas.auth import (
    TokenRequest,
    TokenResponse,
    RefreshRequest,
    UserCreate,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

# ---------------------------------------------------------------------------
# Fallback stub users — used ONLY when the DB query returns None (dev mode)
# ---------------------------------------------------------------------------
_USERS = {
    "admin@bank.uz":    {"password": "admin123",    "role": "admin",          "id": 1, "full_name": "Admin User"},
    "officer@bank.uz":  {"password": "officer123",  "role": "credit_officer", "id": 2, "full_name": "Credit Officer"},
    "analyst@bank.uz":  {"password": "analyst123",  "role": "bank_analyst",   "id": 3, "full_name": "Bank Analyst"},
    "customer@bank.uz": {"password": "customer123", "role": "customer",       "id": 4, "full_name": "Demo Customer"},
}


# ---------------------------------------------------------------------------
# POST /auth/token  —  Login
# ---------------------------------------------------------------------------
@router.post("/token", response_model=TokenResponse)
async def login(body: TokenRequest, db: DBDep):
    user_id: int | str
    role: str
    email: str = body.email

    # 1. Try the real database first
    result = await db.execute(select(User).where(User.email == email))
    db_user: User | None = result.scalar_one_or_none()

    if db_user is not None:
        if not db_user.is_active:
            raise AuthError("Account is disabled")
        if not verify_password(body.password, db_user.hashed_password):
            raise AuthError("Invalid email or password")
        user_id = db_user.id
        role = db_user.role

    else:
        # 2. Fallback to hardcoded dict (development convenience)
        stub = _USERS.get(email)
        if not stub or body.password != stub["password"]:
            raise AuthError("Invalid email or password")
        user_id = stub["id"]
        role = stub["role"]

    payload = {"sub": str(user_id), "email": email, "role": role}
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        expires_in=3600,
    )


# ---------------------------------------------------------------------------
# POST /auth/refresh  —  Refresh access token
# ---------------------------------------------------------------------------
@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise AuthError("Invalid token type")
    except Exception:
        raise AuthError("Invalid or expired refresh token")

    new_payload = {
        "sub": payload["sub"],
        "email": payload.get("email", ""),
        "role": payload.get("role", "customer"),
    }
    return TokenResponse(
        access_token=create_access_token(new_payload),
        refresh_token=create_refresh_token(new_payload),
        expires_in=3600,
    )


# ---------------------------------------------------------------------------
# POST /auth/register  —  Create a new user in the database
# ---------------------------------------------------------------------------
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: DBDep):
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == body.email))
    existing: User | None = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    new_user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserOut(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
    )


# ---------------------------------------------------------------------------
# GET /auth/me  —  Current authenticated user info
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserOut)
async def me(current_user: UserDep, db: DBDep):
    # Try to fetch full user record from the DB
    result = await db.execute(
        select(User).where(User.email == current_user.email)
    )
    db_user: User | None = result.scalar_one_or_none()

    if db_user is not None:
        return UserOut(
            id=db_user.id,
            email=db_user.email,
            full_name=db_user.full_name,
            role=db_user.role,
            is_active=db_user.is_active,
        )

    # Fallback: synthesise from JWT payload (stub users)
    stub = _USERS.get(current_user.email, {})
    return UserOut(
        id=int(current_user.user_id) if current_user.user_id.isdigit() else 0,
        email=current_user.email,
        full_name=stub.get("full_name", current_user.email),
        role=current_user.role,
        is_active=True,
    )

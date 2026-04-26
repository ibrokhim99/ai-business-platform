from pydantic import BaseModel, EmailStr


class TokenRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "customer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

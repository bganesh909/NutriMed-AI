from pydantic import BaseModel, EmailStr, Field

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "TokenPayload",
]


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    model_config = {"json_schema_extra": {"examples": [{"name": "John Doe", "email": "john@example.com", "password": "securepass123"}]}}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {"json_schema_extra": {"examples": [{"email": "john@example.com", "password": "securepass123"}]}}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    role: str = "user"
    iat: float
    exp: float

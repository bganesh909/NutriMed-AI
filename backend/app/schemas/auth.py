from pydantic import BaseModel, EmailStr, Field

from app.models.user import ActivityLevel, Gender

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
    # Optional profile captured by the sign-up form. Persisted with the user so
    # the dashboard, nutrition maths and PDF report have a profile to work from.
    age: int | None = Field(None, ge=1, le=150)
    gender: Gender | None = None
    weight: float | None = Field(None, ge=10, le=500)
    height: float | None = Field(None, ge=50, le=300)
    activity_level: ActivityLevel | None = None
    goals: list[str] = Field(default_factory=list)
    # The web sign-up form requires this; the acceptance time is recorded.
    accepted_terms: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "John Doe", "email": "john@example.com", "password": "securepass123"}]
        }
    }


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

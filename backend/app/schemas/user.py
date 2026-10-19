from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import ActivityLevel, Gender

__all__ = ["UserCreate", "UserUpdate", "UserResponse", "UserProfile"]


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    age: int | None = Field(None, ge=1, le=150)
    gender: Gender | None = None
    weight: float | None = Field(None, ge=10, le=500)
    height: float | None = Field(None, ge=50, le=300)
    activity_level: ActivityLevel | None = None
    goals: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    name: str | None = Field(None, max_length=120)
    age: int | None = Field(None, ge=1, le=150)
    gender: Gender | None = None
    weight: float | None = Field(None, ge=10, le=500)
    height: float | None = Field(None, ge=50, le=300)
    activity_level: ActivityLevel | None = None
    goals: list[str] | None = None

    model_config = {"use_enum_values": True}


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    age: int | None = None
    gender: str | None = None
    weight: float | None = None
    height: float | None = None
    activity_level: str | None = None
    goals: list[str] = Field(default_factory=list)
    role: str = "user"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserProfile(UserResponse):
    updated_at: datetime | None = None

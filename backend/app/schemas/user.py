from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import ActivityLevel, Gender

__all__ = ["UserCreate", "UserUpdate", "UserResponse", "UserProfile"]


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[Gender] = None
    weight: Optional[float] = Field(None, ge=10, le=500)
    height: Optional[float] = Field(None, ge=50, le=300)
    activity_level: Optional[ActivityLevel] = None
    goals: List[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    age: Optional[int] = Field(None, ge=1, le=150)
    gender: Optional[Gender] = None
    weight: Optional[float] = Field(None, ge=10, le=500)
    height: Optional[float] = Field(None, ge=50, le=300)
    activity_level: Optional[ActivityLevel] = None
    goals: Optional[List[str]] = None

    model_config = {"use_enum_values": True}


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    activity_level: Optional[str] = None
    goals: List[str] = Field(default_factory=list)
    role: str = "user"
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserProfile(UserResponse):
    updated_at: Optional[datetime] = None

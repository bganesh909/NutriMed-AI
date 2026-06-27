from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTRA_ACTIVE = "extra_active"


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class UserModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    email: str
    hashed_password: str
    age: Optional[int] = None
    gender: Optional[Gender] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None
    goals: List[str] = Field(default_factory=list)
    role: UserRole = UserRole.USER
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }

    def to_dict(self) -> dict:
        """Return a dict suitable for MongoDB insertion (excludes 'id')."""
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "UserModel":
        """Build a UserModel from a MongoDB document."""
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)

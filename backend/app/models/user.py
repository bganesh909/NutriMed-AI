from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTRA_ACTIVE = "extra_active"


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class UserModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    name: str
    email: str
    hashed_password: str
    age: int | None = None
    gender: Gender | None = None
    weight: float | None = None
    height: float | None = None
    activity_level: ActivityLevel | None = None
    goals: list[str] = Field(default_factory=list)
    role: UserRole = UserRole.USER
    # When the user accepted the terms of use and medical disclaimer at sign-up.
    terms_accepted_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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

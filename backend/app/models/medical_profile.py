from datetime import UTC, datetime

from pydantic import BaseModel, Field


class MedicalProfileModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    injuries: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }

    def to_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "MedicalProfileModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)

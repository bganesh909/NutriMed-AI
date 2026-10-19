from datetime import UTC, datetime

from pydantic import BaseModel, Field


class NotificationModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    type: str
    title: str
    message: str
    read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {
        "populate_by_name": True,
    }

    def to_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "NotificationModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)

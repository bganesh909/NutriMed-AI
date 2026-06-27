from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    CBC = "CBC"
    LIPID = "LIPID"
    LFT = "LFT"
    KFT = "KFT"
    THYROID = "THYROID"
    VITAMIN = "VITAMIN"
    DIABETES = "DIABETES"


class ReportStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    report_type: ReportType
    file_path: str
    original_filename: str
    status: ReportStatus = ReportStatus.UPLOADED
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    encryption_key: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "use_enum_values": True,
    }

    def to_dict(self) -> dict:
        return self.model_dump(by_alias=False, exclude={"id"})

    @classmethod
    def from_dict(cls, data: dict) -> "ReportModel":
        doc = dict(data)
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)

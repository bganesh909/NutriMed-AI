from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ReportType(StrEnum):
    CBC = "CBC"
    LIPID = "LIPID"
    LFT = "LFT"
    KFT = "KFT"
    THYROID = "THYROID"
    VITAMIN = "VITAMIN"
    DIABETES = "DIABETES"
    GENERAL = "GENERAL"


class ReportStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportModel(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    report_type: ReportType
    file_path: str
    original_filename: str
    status: ReportStatus = ReportStatus.UPLOADED
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    processed_at: datetime | None = None
    encryption_key: str | None = None

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

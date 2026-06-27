from pydantic import BaseModel

__all__ = ["FitnessCalcResponse"]


class FitnessCalcResponse(BaseModel):
    message: str

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeliverableCreate(BaseModel):
    description: str = Field(min_length=10)
    file_urls: list[str] = Field(default_factory=list)


class DeliverableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    milestone_id: int
    submitted_by_id: int
    description: str
    file_urls: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
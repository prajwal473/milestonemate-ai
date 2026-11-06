from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgreementCreate(BaseModel):
    content: dict[str, Any]


class AgreementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    version: int
    content: dict[str, Any]
    status: str
    client_approved_at: datetime | None
    freelancer_approved_at: datetime | None


class AgreementApproval(BaseModel):
    approved: bool = True
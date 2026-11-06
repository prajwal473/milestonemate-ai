from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_date: datetime
    acceptance_criteria: list[str] = Field(min_length=1)


class MilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    agreement_id: int | None
    title: str
    description: str
    amount: Decimal
    due_date: datetime
    acceptance_criteria: list[str]
    status: str
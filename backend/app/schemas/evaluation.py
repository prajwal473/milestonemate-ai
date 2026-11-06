from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deliverable_id: int
    model_name: str | None
    score: Decimal | None
    findings: dict[str, Any]
    recommendation: str
    human_decision: str | None


class EvaluationDecisionCreate(BaseModel):
    decision: Literal["accepted", "revision_requested"]
from pydantic import BaseModel, Field
from typing import Any

class ClarificationRequest(BaseModel):
    brief: str = Field(min_length=10, max_length=20000)


class AgreementGenerationRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    extraction: dict = Field(default_factory=dict)


class TemplateAgreementRequest(BaseModel):
    custom_terms: list[str] = Field(default_factory=list)

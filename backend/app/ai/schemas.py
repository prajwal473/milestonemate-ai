from enum import Enum
from pydantic import BaseModel, Field


class CriterionStatus(str, Enum):
    MET = "MET"
    PARTIALLY_MET = "PARTIALLY_MET"
    NOT_MET = "NOT_MET"
    CANNOT_DETERMINE = "CANNOT_DETERMINE"


class Recommendation(str, Enum):
    MEETS = "MEETS"
    PARTIALLY_MEETS = "PARTIALLY_MEETS"
    DOES_NOT_MEET = "DOES_NOT_MEET"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceItem(BaseModel):
    file: str
    quote: str
    verified: bool = False


class CriterionResult(BaseModel):
    criterion_id: str
    status: CriterionStatus
    reasoning: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    gap: str | None = None


class EvaluationReportModelOutput(BaseModel):
    summary: str
    model_confidence: float = Field(ge=0, le=1)
    criteria_results: list[CriterionResult]
    missing_requirements: list[str] = Field(default_factory=list)
    unverifiable_items: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class EvaluationReport(EvaluationReportModelOutput):
    recommendation: Recommendation
    total_criteria: int = Field(ge=0)
    met_criteria: int = Field(ge=0)
    
    disclaimer: str = "AI-generated assessment. Final acceptance is decided by the client."

class QuestionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MissingInfo(BaseModel):
    id: str
    question: str
    why_it_matters: str
    severity: QuestionSeverity


class ClarificationResult(BaseModel):
    summary: str
    missing_information: list[MissingInfo] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    is_ready_for_agreement: bool = False
    
class AgreementModelOutput(BaseModel):
    project_title: str
    scope: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    milestones: list[dict] = Field(default_factory=list)
    total_budget: float = Field(gt=0)
    currency: str
    payment_terms: list[str] = Field(default_factory=list)
    deadline: str | None = None
    client_responsibilities: list[str] = Field(default_factory=list)
    freelancer_responsibilities: list[str] = Field(default_factory=list)
    incomplete_information: list[str] = Field(default_factory=list)
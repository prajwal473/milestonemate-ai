from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import (
    Deliverable,
    Evaluation,
    Milestone,
    Project,
    User,
)
from app.ai.evaluator import (
    evaluate_deliverable,
    EvaluationServiceError,
)
from app.schemas.evaluation import (
    EvaluationRead,
    EvaluationDecisionCreate,
)
router = APIRouter(prefix="/api", tags=["AI Evaluations"])


@router.post(
    "/deliverables/{deliverable_id}/evaluate",
    response_model=EvaluationRead,
)
def evaluate_submission(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deliverable = (
        db.query(Deliverable)
        .filter(Deliverable.id == deliverable_id)
        .first()
    )

    if deliverable is None:
        raise HTTPException(404, "Deliverable not found.")

    milestone = (
        db.query(Milestone)
        .filter(Milestone.id == deliverable.milestone_id)
        .first()
    )

    project = (
        db.query(Project)
        .filter(Project.id == milestone.project_id)
        .first()
    )

    if current_user.id not in (
        project.client_id,
        project.freelancer_id,
    ):
        raise HTTPException(
            403,
            "You do not have access to this deliverable."
        )

    if current_user.role != "client":
        raise HTTPException(
            403,
            "Only the client can request an AI evaluation."
        )

    if deliverable.status != "submitted":
        raise HTTPException(
            400,
            "Only submitted deliverables can be evaluated."
        )

    existing = (
        db.query(Evaluation)
        .filter(Evaluation.deliverable_id == deliverable_id)
        .first()
    )

    if existing:
        raise HTTPException(
            409,
            "This deliverable has already been evaluated."
        )

    try:
        result = evaluate_deliverable(
            milestone_title=milestone.title,
            milestone_description=milestone.description,
            acceptance_criteria=milestone.acceptance_criteria,
            deliverable_description=deliverable.description,
        )
    except EvaluationServiceError as exc:
        raise HTTPException(
            502,
            str(exc),
        )

    evaluation = Evaluation(
        deliverable_id=deliverable.id,
        model_name="gemini-3.8-flash",
        score=result["score"],
        findings={
            "summary": result["summary"],
            "criteria_results": result["criteria_results"],
            "missing_requirements": result["missing_requirements"],
        },
        recommendation=result["recommendation"],
        human_decision=None,
    )

    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    return evaluation
@router.post(
    "/evaluations/{evaluation_id}/decision",
    response_model=EvaluationRead,
)
def submit_evaluation_decision(
    evaluation_id: int,
    data: EvaluationDecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Only clients can make final decisions.
    if current_user.role != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can make evaluation decisions.",
        )

    # Find evaluation.
    evaluation = (
        db.query(Evaluation)
        .filter(Evaluation.id == evaluation_id)
        .first()
    )

    if evaluation is None:
        raise HTTPException(
            status_code=404,
            detail="Evaluation not found.",
        )

    # Find associated deliverable.
    deliverable = (
        db.query(Deliverable)
        .filter(Deliverable.id == evaluation.deliverable_id)
        .first()
    )

    if deliverable is None:
        raise HTTPException(
            status_code=404,
            detail="Deliverable not found.",
        )

    # Find milestone and project.
    milestone = (
        db.query(Milestone)
        .filter(Milestone.id == deliverable.milestone_id)
        .first()
    )

    if milestone is None:
        raise HTTPException(
            status_code=404,
            detail="Milestone not found.",
        )

    project = (
        db.query(Project)
        .filter(Project.id == milestone.project_id)
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    # Verify that this client owns the project.
    if project.client_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not the client of this project.",
        )

    # Prevent conflicting or repeated decisions.
    if evaluation.human_decision is not None:
        raise HTTPException(
            status_code=409,
            detail="A decision has already been submitted.",
        )

    if deliverable.status != "submitted":
        raise HTTPException(
            status_code=400,
            detail="This deliverable is not awaiting a decision.",
        )

    # Apply client's decision.
    evaluation.human_decision = data.decision

    if data.decision == "accepted":

        deliverable.status = "accepted"

        # Mark milestone approved, ready for payment processing.
        milestone.status = "approved"

    elif data.decision == "revision_requested":

        deliverable.status = "revision_requested"
        milestone.status = "revision_requested"

    db.commit()
    db.refresh(evaluation)

    return evaluation
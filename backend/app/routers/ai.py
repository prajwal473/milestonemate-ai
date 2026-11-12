from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.ai.summary import generate_project_summary
from app.ai.service import clarify_project
from app.ai.agreement import generate_agreement
from app.ai.fallbacks import template_agreement
from app.ai.ratelimit import check_ai_rate_limit
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import Agreement, Project, User
from app.schemas.ai import (
    ClarificationRequest,
    AgreementGenerationRequest,
    TemplateAgreementRequest,
)


router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post(
    "/projects/{project_id}/clarify",
    dependencies=[Depends(check_ai_rate_limit)],
)
def clarify_project_requirements(
    project_id: int,
    request: ClarificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    if current_user.id not in (
        project.client_id,
        project.freelancer_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project.",
        )

    try:
        return clarify_project(
            brief=request.brief,
            extraction={
                "project_title": project.title,
                "budget": str(project.budget),
                "currency": project.currency,
            },
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="AI clarification service is temporarily unavailable.",
        )


@router.post(
    "/projects/{project_id}/generate-agreement",
    dependencies=[Depends(check_ai_rate_limit)],
)
def generate_project_agreement(
    project_id: int,
    request: AgreementGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    if current_user.id != project.client_id:
        raise HTTPException(
            status_code=403,
            detail="Only the project client can generate an agreement.",
        )

    if project.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Agreements can only be generated for draft projects.",
        )

    try:
        agreement = generate_agreement(
            db=db,
            project=project,
            answers=request.answers,
            extraction=request.extraction,
        )
        return agreement

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="AI agreement generation service is temporarily unavailable.",
        )


@router.post("/projects/{project_id}/template-agreement")
@router.post("/projects/{project_id}/template")
def generate_project_template_agreement(
    project_id: int,
    request: TemplateAgreementRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    if current_user.id != project.client_id:
        raise HTTPException(
            status_code=403,
            detail="Only the project client can generate an agreement.",
        )

    if project.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Agreements can only be generated for draft projects.",
        )

    if not project.title or not project.title.strip():
        raise HTTPException(
            status_code=422,
            detail="Project title cannot be empty.",
        )

    if project.budget is None or project.budget <= 0:
        raise HTTPException(
            status_code=422,
            detail="Project budget must be greater than zero.",
        )

    existing_approved = (
        db.query(Agreement)
        .filter(
            Agreement.project_id == project_id,
            Agreement.status == "approved",
        )
        .first()
    )
    if existing_approved:
        raise HTTPException(
            status_code=400,
            detail="Cannot generate template for a project with an approved agreement.",
        )

    custom_terms = request.custom_terms if request else None

    try:
        agreement = template_agreement(
            project=project,
            db=db,
            custom_terms=custom_terms,
        )
        return agreement

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate template agreement.",
        )


@router.get("/projects/{project_id}/summary")
def get_project_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    if current_user.id not in (
        project.client_id,
        project.freelancer_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project.",
        )

    return generate_project_summary(project)
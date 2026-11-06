from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import Agreement, Project, User
from app.schemas.agreement import (
    AgreementCreate,
    AgreementRead,
    AgreementApproval,
)

router = APIRouter(prefix="/api/agreements", tags=["Agreements"])


def get_project_access(project_id: int, user: User, db: Session):
    project = db.query(Project).filter(Project.id == project_id).first()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    if user.id not in (project.client_id, project.freelancer_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project.",
        )

    return project


def get_agreement(agreement_id: int, user: User, db: Session):
    agreement = (
        db.query(Agreement)
        .filter(Agreement.id == agreement_id)
        .first()
    )

    if agreement is None:
        raise HTTPException(status_code=404, detail="Agreement not found.")

    get_project_access(agreement.project_id, user, db)

    return agreement


@router.post(
    "/projects/{project_id}",
    response_model=AgreementRead,
    status_code=status.HTTP_201_CREATED,
)
def create_agreement(
    project_id: int,
    data: AgreementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_access(project_id, current_user, db)

    if project.client_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the client can create an agreement.",
        )

    if project.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Agreements can only be created for draft projects.",
        )

    if not data.content:
        raise HTTPException(
            status_code=422,
            detail="Agreement content cannot be empty.",
        )

    latest = (
        db.query(Agreement)
        .filter(Agreement.project_id == project_id)
        .order_by(Agreement.version.desc())
        .first()
    )

    version = latest.version + 1 if latest else 1

    agreement = Agreement(
        project_id=project_id,
        version=version,
        content=data.content,
        status="draft",
    )

    db.add(agreement)
    db.commit()
    db.refresh(agreement)

    return agreement


@router.get(
    "/projects/{project_id}",
    response_model=list[AgreementRead],
)
def list_agreements(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_project_access(project_id, current_user, db)

    return (
        db.query(Agreement)
        .filter(Agreement.project_id == project_id)
        .order_by(Agreement.version.desc())
        .all()
    )


@router.get("/{agreement_id}", response_model=AgreementRead)
def read_agreement(
    agreement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_agreement(agreement_id, current_user, db)


@router.post("/{agreement_id}/approve", response_model=AgreementRead)
def approve_agreement(
    agreement_id: int,
    approval: AgreementApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agreement = get_agreement(agreement_id, current_user, db)

    project = db.query(Project).filter(
        Project.id == agreement.project_id
    ).first()

    if agreement.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="This agreement is no longer awaiting approval.",
        )

    if not approval.approved:
        agreement.status = "rejected"
        db.commit()
        db.refresh(agreement)
        return agreement

    now = datetime.now(timezone.utc)

    if current_user.id == project.client_id:
        if agreement.client_approved_at is not None:
            raise HTTPException(
                status_code=400,
                detail="The client has already approved this agreement.",
            )

        agreement.client_approved_at = now

    elif current_user.id == project.freelancer_id:
        if agreement.freelancer_approved_at is not None:
            raise HTTPException(
                status_code=400,
                detail="The freelancer has already approved this agreement.",
            )

        agreement.freelancer_approved_at = now

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this project.",
        )

    if (
        agreement.client_approved_at is not None
        and agreement.freelancer_approved_at is not None
    ):
        agreement.status = "approved"
        project.status = "active"

    db.commit()
    db.refresh(agreement)

    return agreement
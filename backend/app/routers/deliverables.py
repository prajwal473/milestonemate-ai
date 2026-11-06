from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import Deliverable, Milestone, Project, User
from app.schemas.deliverable import DeliverableCreate, DeliverableRead

router = APIRouter(prefix="/api/milestones", tags=["Deliverables"])


def get_accessible_milestone(
    milestone_id: int,
    current_user: User,
    db: Session,
):
    milestone = (
        db.query(Milestone)
        .filter(Milestone.id == milestone_id)
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

    if current_user.id not in (project.client_id, project.freelancer_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this milestone.",
        )

    return milestone, project


@router.post(
    "/{milestone_id}/deliverables",
    response_model=DeliverableRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_deliverable(
    milestone_id: int,
    data: DeliverableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone, project = get_accessible_milestone(
        milestone_id, current_user, db
    )

    if current_user.role != "freelancer":
        raise HTTPException(
            status_code=403,
            detail="Only freelancers can submit deliverables.",
        )

    if project.freelancer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not the freelancer assigned to this project.",
        )

    if project.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Deliverables can only be submitted for active projects.",
        )

    if milestone.status not in ("pending", "in_progress", "revision_requested"):
        raise HTTPException(
            status_code=400,
            detail="This milestone is not accepting submissions.",
        )

    deliverable = Deliverable(
        milestone_id=milestone.id,
        submitted_by_id=current_user.id,
        description=data.description,
        file_urls=data.file_urls,
        status="submitted",
    )

    milestone.status = "submitted"

    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)

    return deliverable


@router.get(
    "/{milestone_id}/deliverables",
    response_model=list[DeliverableRead],
)
def list_deliverables(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone, project = get_accessible_milestone(
        milestone_id, current_user, db
    )

    return (
        db.query(Deliverable)
        .filter(Deliverable.milestone_id == milestone.id)
        .order_by(Deliverable.created_at.desc())
        .all()
    )

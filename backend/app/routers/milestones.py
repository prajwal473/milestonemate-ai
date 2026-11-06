from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import Project, Agreement, Milestone, User
from app.schemas.milestone import MilestoneCreate, MilestoneRead

router = APIRouter(prefix="/api/milestones", tags=["Milestones"])


def get_project(project_id: int, user: User, db: Session):
    project = db.query(Project).filter(Project.id == project_id).first()

    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")

    if user.id not in (project.client_id, project.freelancer_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project.",
        )

    return project


@router.post(
    "/projects/{project_id}",
    response_model=MilestoneRead,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    project_id: int,
    data: MilestoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(project_id, current_user, db)

    if project.client_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the client can create milestones.",
        )

    if project.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Both parties must approve an agreement before creating milestones.",
        )

    agreement = (
        db.query(Agreement)
        .filter(
            Agreement.project_id == project_id,
            Agreement.status == "approved",
        )
        .order_by(Agreement.version.desc())
        .first()
    )

    if agreement is None:
        raise HTTPException(
            status_code=400,
            detail="No approved agreement exists for this project.",
        )

    existing_total = (
        db.query(func.coalesce(func.sum(Milestone.amount), 0))
        .filter(Milestone.project_id == project_id)
        .scalar()
    )

    if existing_total + data.amount > project.budget:
        raise HTTPException(
            status_code=400,
            detail="Total milestone amounts cannot exceed the project budget.",
        )

    if data.due_date.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail="Please provide a timezone-aware due date.",
        )

    milestone = Milestone(
        project_id=project_id,
        agreement_id=agreement.id,
        title=data.title,
        description=data.description,
        amount=data.amount,
        due_date=data.due_date,
        acceptance_criteria=data.acceptance_criteria,
        status="pending",
    )

    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    return milestone


@router.get(
    "/projects/{project_id}",
    response_model=list[MilestoneRead],
)
def list_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_project(project_id, current_user, db)

    return (
        db.query(Milestone)
        .filter(Milestone.project_id == project_id)
        .order_by(Milestone.due_date.asc())
        .all()
    )


@router.get("/{milestone_id}", response_model=MilestoneRead)
def read_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    milestone = (
        db.query(Milestone)
        .filter(Milestone.id == milestone_id)
        .first()
    )

    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found.")

    get_project(milestone.project_id, current_user, db)

    return milestone
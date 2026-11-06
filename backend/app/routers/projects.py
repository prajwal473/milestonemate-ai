from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.project import FreelancerAssignment
from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import Project, User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate


router = APIRouter(prefix="/api/projects", tags=["Projects"])


def get_accessible_project(
    project_id: int,
    current_user: User,
    db: Session,
) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    is_client = project.client_id == current_user.id
    is_freelancer = project.freelancer_id == current_user.id

    if not (is_client or is_freelancer):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project.",
        )

    return project


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "client":
        raise HTTPException(
            status_code=403,
            detail="Only clients can create projects.",
        )

    freelancer = None

    if project_data.freelancer_id is not None:
        freelancer = (
            db.query(User)
            .filter(
                User.id == project_data.freelancer_id,
                User.role == "freelancer",
                User.is_active.is_(True),
            )
            .first()
        )

        if freelancer is None:
            raise HTTPException(
                status_code=400,
                detail="The selected freelancer does not exist or is inactive.",
            )

    project = Project(
        title=project_data.title,
        description=project_data.description,
        budget=project_data.budget,
        currency=project_data.currency,
        client_id=current_user.id,
        freelancer_id=freelancer.id if freelancer else None,
        status="draft",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "client":
        return (
            db.query(Project)
            .filter(Project.client_id == current_user.id)
            .order_by(Project.created_at.desc())
            .all()
        )

    if current_user.role == "freelancer":
        return (
            db.query(Project)
            .filter(Project.freelancer_id == current_user.id)
            .order_by(Project.created_at.desc())
            .all()
        )

    raise HTTPException(
        status_code=403,
        detail="Your account role cannot access projects.",
    )


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_accessible_project(project_id, current_user, db)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_accessible_project(project_id, current_user, db)

    if project.client_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the project owner can update this project.",
        )

    if project.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft projects can be edited.",
        )

    updates = project_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update.",
        )

    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=422,
            detail="Project fields cannot be set to null.",
        )

    for field, value in updates.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_accessible_project(project_id, current_user, db)

    if project.client_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the project owner can delete this project.",
        )

    if project.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only draft projects can be deleted.",
        )

    if project.agreements or project.milestones:
        raise HTTPException(
            status_code=400,
            detail="Projects with agreements or milestones cannot be deleted.",
        )

    db.delete(project)
    db.commit()

    return None
@router.post(
    "/{project_id}/assign-freelancer",
    response_model=ProjectRead,
)
def assign_freelancer(
    project_id: int,
    assignment: FreelancerAssignment,
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

    if project.client_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the project owner can assign a freelancer.",
        )

    if project.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Freelancers can only be assigned to draft projects.",
        )

    freelancer = db.query(User).filter(
        User.id == assignment.freelancer_id
    ).first()

    if freelancer is None or not freelancer.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active freelancer not found.",
        )

    if freelancer.role != "freelancer":
        raise HTTPException(
            status_code=400,
            detail="The selected user is not a freelancer.",
        )

    if project.freelancer_id is not None:
        raise HTTPException(
            status_code=400,
            detail="A freelancer is already assigned to this project.",
        )

    project.freelancer_id = freelancer.id

    db.commit()
    db.refresh(project)

    return project
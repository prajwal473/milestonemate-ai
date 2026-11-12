from sqlalchemy.orm import Session

from app.models import Agreement, Project


def create_draft_version(
    db: Session,
    project_id: int,
    content: dict,
) -> Agreement:
    project = db.query(Project).filter(
        Project.id == project_id
    ).first()

    if project is None:
        raise ValueError("Project not found.")

    if project.status != "draft":
        raise ValueError(
            "Agreements can only be created for draft projects."
        )

    if not isinstance(content, dict) or not content:
        raise ValueError("Agreement content cannot be empty.")

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
        content=content,
        status="draft",
    )

    db.add(agreement)
    db.commit()
    db.refresh(agreement)

    return agreement
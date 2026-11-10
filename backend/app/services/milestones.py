from sqlalchemy.orm import Session, joinedload

from app.models import Milestone, Project


def get_for_payment(
    db: Session,
    milestone_id: int,
    actor_id: int,
) -> Milestone:
    """
    Retrieve a milestone for payment processing.

    Only the project's client can initiate milestone payment.
    The milestone must be approved before payment creation.
    """
    milestone = (
        db.query(Milestone)
        .options(joinedload(Milestone.project))
        .filter(Milestone.id == milestone_id)
        .first()
    )

    if milestone is None:
        raise ValueError("Milestone not found.")

    if milestone.project.client_id != actor_id:
        raise PermissionError("Only the project client can initiate payment.")

    if milestone.status != "approved":
        raise ValueError("Milestone must be approved before payment.")

    return milestone


def mark_paid(
    db: Session,
    milestone_id: int,
    payment_id: int,
) -> Milestone:
    """
    Mark a milestone as paid after a confirmed PayPal capture.

    This function does not commit. The payment service owns
    transaction commit and rollback.
    """
    if payment_id <= 0:
        raise ValueError("payment_id must be a positive integer.")

    milestone = (
        db.query(Milestone)
        .options(joinedload(Milestone.project))
        .filter(Milestone.id == milestone_id)
        .with_for_update()
        .first()
    )

    if milestone is None:
        raise ValueError("Milestone not found.")

    if milestone.status == "paid":
        return milestone

    if milestone.status != "approved":
        raise ValueError("Only approved milestones can be marked as paid.")

    milestone.status = "paid"
    db.flush()

    project_id = milestone.project_id
    unpaid_count = (
        db.query(Milestone)
        .filter(
            Milestone.project_id == project_id,
            Milestone.status != "paid",
        )
        .count()
    )

    if unpaid_count == 0:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is not None:
            project.status = "completed"

    db.flush()
    return milestone

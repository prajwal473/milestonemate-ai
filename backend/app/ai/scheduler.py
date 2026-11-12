from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.ai.runs import run_evaluation
from app.models import EvaluationRun


def schedule_evaluation(
    db: Session,
    background_tasks: BackgroundTasks,
    deliverable_id: int,
):
    existing_run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.deliverable_id == deliverable_id)
        .first()
    )

    if existing_run:
        raise ValueError("Evaluation run already exists.")

    run = EvaluationRun(
        deliverable_id=deliverable_id,
        status="PENDING",
        retry_count=0,
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(run_evaluation, run.id)

    return run
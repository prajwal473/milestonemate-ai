from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int,
    details: dict | None = None,
) -> AuditLog:
    if entity_id <= 0:
        raise ValueError("entity_id must be a positive integer.")

    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
    )

    db.add(entry)
    db.flush()

    return entry
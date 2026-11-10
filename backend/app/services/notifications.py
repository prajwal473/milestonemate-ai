from sqlalchemy.orm import Session

from app.models import Notification


def notify(
    db: Session,
    user_id: int,
    event_type: str,
    payload: dict,
) -> Notification:
    if user_id <= 0:
        raise ValueError("user_id must be a positive integer.")

    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        payload=payload,
    )

    db.add(notification)
    db.flush()

    return notification
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import Payment, Project, User
from app.payments.errors import (
    AmountMismatchError,
    InvalidPaymentStateError,
    PaymentAuthorizationError,
    PaymentNotFoundError,
    PayPalError,
)
from app.payments.service import (
    cancel_payment,
    capture_payment,
    create_order_for_milestone,
    sync_payment,
)
from app.schemas.payment import PaymentCaptureRequest, PaymentRead


router = APIRouter(prefix="/api/payments", tags=["Payments"])


def get_accessible_payment(
    payment_id: int,
    user: User,
    db: Session,
) -> Payment:
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found.",
        )

    project = (
        db.query(Project)
        .filter(Project.id == payment.project_id)
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found.",
        )

    if user.id not in (payment.payer_id, project.freelancer_id):
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this payment.",
        )

    return payment


@router.post(
    "/milestones/{milestone_id}",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    milestone_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return create_order_for_milestone(
            db,
            milestone_id=milestone_id,
            actor_id=current_user.id,
        )

    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get(
    "/projects/{project_id}",
    response_model=list[PaymentRead],
)
def list_project_payments(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

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

    return (
        db.query(Payment)
        .filter(Payment.project_id == project_id)
        .order_by(Payment.created_at.desc())
        .all()
    )


@router.get("/{payment_id}", response_model=PaymentRead)
def read_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_accessible_payment(payment_id, current_user, db)


@router.post(
    "/{payment_id}/capture",
    response_model=PaymentRead,
)
def capture_payment_endpoint(
    payment_id: int,
    data: PaymentCaptureRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return capture_payment(
            db,
            payment_id=payment_id,
            actor_id=current_user.id,
            paypal_order_id=data.paypal_order_id,
        )

    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except PaymentAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    except InvalidPaymentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    except AmountMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentRead,
)
def cancel_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return cancel_payment(
            db,
            payment_id=payment_id,
            actor_id=current_user.id,
        )

    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except PaymentAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    except InvalidPaymentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

@router.post(
    "/{payment_id}/sync",
    response_model=PaymentRead,
)
def sync_payment_endpoint(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return sync_payment(
            db,
            payment_id=payment_id,
            actor_id=current_user.id,
        )

    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except PaymentAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    except InvalidPaymentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    except AmountMismatchError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
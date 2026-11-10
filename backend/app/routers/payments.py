from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.dependencies import get_db
from app.models import Payment, PaymentEvent, PayPalWebhookEvent, Project, User
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
from app.schemas.payment import (
    PaymentCaptureRequest, PaymentRead, PaymentEventRead,
    ProjectPaymentList, PaymentTotals,
)


router = APIRouter(prefix="/api/payments", tags=["Payments"])
project_ledger_router = APIRouter(prefix="/api", tags=["Payments"])


def _payment_read(db: Session, payment: Payment) -> PaymentRead:
    result = PaymentRead.model_validate(payment)
    events = (
        db.query(PaymentEvent)
        .filter(PaymentEvent.payment_id == payment.id)
        .order_by(PaymentEvent.created_at.asc(), PaymentEvent.id.asc())
        .all()
    )
    resource = PayPalWebhookEvent.payload["resource"]
    related_ids = resource["supplementary_data"]["related_ids"]
    identifiers = [value for value in (payment.paypal_order_id, payment.paypal_capture_id) if value]
    verified = False
    if identifiers:
        matches = [
            PayPalWebhookEvent.resource_id.in_(identifiers),
            resource["id"].as_string().in_(identifiers),
        ]
        if payment.paypal_order_id:
            matches.append(related_ids["order_id"].as_string() == payment.paypal_order_id)
        if payment.paypal_capture_id:
            matches.append(related_ids["capture_id"].as_string() == payment.paypal_capture_id)
        verified = db.query(PayPalWebhookEvent.id).filter(
            PayPalWebhookEvent.verification_status == "SUCCESS",
            or_(*matches),
        ).first() is not None
    return result.model_copy(update={
        "milestone_title": payment.milestone.title,
        "milestone_status": payment.milestone.status,
        "events": [PaymentEventRead.model_validate(event) for event in events],
        "webhook_verified": verified,
    })


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


@project_ledger_router.post(
    "/milestones/{milestone_id}/payments",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_payment(
    milestone_id: int,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        payment = create_order_for_milestone(
            db,
            milestone_id=milestone_id,
            actor_id=current_user.id,
        )
        if getattr(payment, "_idempotent_reuse", False):
            response.status_code = status.HTTP_200_OK
        return _payment_read(db, payment)

    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    except PaymentAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    except InvalidPaymentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except PayPalError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/{payment_id}", response_model=PaymentRead)
def read_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = get_accessible_payment(payment_id, current_user, db)
    return _payment_read(db, payment)


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
        payment = capture_payment(
            db,
            payment_id=payment_id,
            actor_id=current_user.id,
            paypal_order_id=data.paypal_order_id,
        )
        return _payment_read(db, payment)

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


@project_ledger_router.get("/projects/{project_id}/payments", response_model=ProjectPaymentList)
def project_payment_ledger(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    if current_user.id not in (project.client_id, project.freelancer_id):
        raise HTTPException(status_code=403, detail="You do not have access to this project.")
    payments = db.query(Payment).filter(
        Payment.project_id == project_id
    ).order_by(Payment.created_at.desc()).all()
    financial_events = {payment.id: [] for payment in payments}
    if financial_events:
        event_rows = db.query(PaymentEvent).filter(
            PaymentEvent.payment_id.in_(financial_events),
            PaymentEvent.event_type.in_(("PAYMENT.CAPTURE.REFUNDED", "PAYMENT.CAPTURE.REVERSED")),
            PaymentEvent.source == "WEBHOOK",
        ).all()
        for event in event_rows:
            financial_events[event.payment_id].append(event)

    def net_paid(payment):
        if payment.status != "COMPLETED":
            return Decimal("0.00")
        capture = Decimal(str(payment.amount))
        deductions = Decimal("0.00")
        seen_event_ids = set()
        for event in financial_events[payment.id]:
            details = event.details or {}
            provider_event_id = details.get("provider_event_id")
            if not provider_event_id or provider_event_id in seen_event_ids:
                continue
            seen_event_ids.add(provider_event_id)
            try:
                amount = Decimal(str(details.get("amount")))
            except Exception:
                continue
            if details.get("currency") == "USD" and amount.is_finite() and amount > 0:
                deductions += amount
        return max(capture - deductions, Decimal("0.00"))

    paid = sum((net_paid(p) for p in payments), Decimal("0.00"))
    pending = sum((p.amount for p in payments if p.status in {
        "CREATED", "PENDING_APPROVAL", "APPROVED", "CAPTURE_PENDING",
    }), Decimal("0.00"))
    remaining = max(Decimal(str(project.budget)) - paid - pending, Decimal("0.00"))
    return ProjectPaymentList(
        items=[_payment_read(db, p) for p in payments],
        totals=PaymentTotals(paid=paid, pending=pending, remaining=remaining),
    )


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
        payment = cancel_payment(
            db,
            payment_id=payment_id,
            actor_id=current_user.id,
        )
        return _payment_read(db, payment)

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
        payment = sync_payment(
            db,
            payment_id=payment_id,
            actor_id=current_user.id,
        )
        return _payment_read(db, payment)

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

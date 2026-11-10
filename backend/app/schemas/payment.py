from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from pydantic import Field


class PaymentCaptureRequest(BaseModel):
    paypal_order_id: str = Field(min_length=1, max_length=100)


class PaymentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    from_status: str | None = None
    to_status: str | None = None
    source: str
    paypal_ref: str | None = None
    created_at: datetime


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    milestone_id: int
    milestone_title: str | None = None
    project_id: int
    amount: Decimal
    currency: str
    status: str
    provider: str
    paypal_order_id: str | None
    paypal_capture_id: str | None
    approve_url: str | None
    created_at: datetime
    approved_at: datetime | None
    captured_at: datetime | None
    failure_code: str | None = None
    failure_message: str | None = None
    payee_mode: str | None = None
    milestone_status: str | None = None
    milestone_status: str | None = None
    milestone_status: str | None = None
    events: list["PaymentEventRead"] = Field(default_factory=list)
    webhook_verified: bool = False


class PaymentTotals(BaseModel):
    paid: Decimal
    pending: Decimal
    remaining: Decimal


class ProjectPaymentList(BaseModel):
    items: list[PaymentRead]
    totals: PaymentTotals

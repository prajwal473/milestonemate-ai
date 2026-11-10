from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from pydantic import Field


class PaymentCaptureRequest(BaseModel):
    paypal_order_id: str = Field(min_length=1, max_length=100)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    milestone_id: int
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
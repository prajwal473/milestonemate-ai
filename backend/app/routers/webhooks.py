from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.payments.errors import WebhookVerificationError
from app.payments.webhook_service import process_webhook

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/paypal")
async def paypal_webhook(request: Request, db: Session = Depends(get_db)):
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 1_000_000:
            raise HTTPException(status_code=413, detail="Webhook payload is too large.")
        chunks.append(chunk)
    raw_body = b"".join(chunks)
    headers = dict(request.headers)
    try:
        result = process_webhook(db, headers=headers, raw_body=raw_body)
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result.get("status") == "failed":
        raise HTTPException(status_code=503, detail="Webhook processing failed; retry later.")
    return {"received": True, **result}

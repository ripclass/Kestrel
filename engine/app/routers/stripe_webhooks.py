"""V3 P7.1 — Stripe webhook endpoint.

POST /webhooks/stripe receives subscription + invoice events from
Stripe. The handler:

1. Verifies the Stripe-Signature header against
   ``STRIPE_WEBHOOK_SECRET``.
2. Dispatches the event to ``stripe_billing.handle_subscription_event``.
3. Returns 200 OK on every successfully-routed event (including no-ops)
   so Stripe's retry logic doesn't replay; 4xx only on signature
   failure or malformed body.

Auth bypass: this endpoint is public-by-design. Stripe doesn't carry a
Supabase JWT. Signature verification is the only security gate.

If ``STRIPE_WEBHOOK_SECRET`` is unset (the engine boot didn't wire
Stripe), every POST is rejected 400 — making it explicit that the
deployment hasn't been configured rather than silently accepting
requests.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.database import SessionLocal
from app.services.stripe_billing import (
    default_price_to_plan,
    handle_subscription_event,
    verify_signature,
)

logger = logging.getLogger("kestrel.routers.stripe_webhooks")

router = APIRouter()


def _price_mapping() -> dict[str, str]:
    return default_price_to_plan(
        starter=os.environ.get("STRIPE_PRICE_ID_STARTER"),
        professional=os.environ.get("STRIPE_PRICE_ID_PROFESSIONAL"),
        enterprise=os.environ.get("STRIPE_PRICE_ID_ENTERPRISE"),
    )


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, str]:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    body = await request.body()
    check = verify_signature(payload=body, header=stripe_signature, secret=secret)
    if not check.valid:
        logger.warning("stripe.webhook.signature_invalid", extra={"reason": check.reason})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"signature {check.reason}")
    try:
        event = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("stripe.webhook.malformed_body", extra={"error": str(exc)[:200]})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json") from exc
    event_type = str(event.get("type") or "")
    if not event_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_event_type")
    async with SessionLocal() as session:
        try:
            handled = await handle_subscription_event(
                session,
                event_type=event_type,
                payload=event,
                price_to_plan=_price_mapping(),
            )
        except Exception as exc:  # noqa: BLE001 — defence-in-depth; never surface internals to Stripe
            logger.exception("stripe.webhook.handler_failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="handler_failure",
            ) from exc
    logger.info(
        "stripe.webhook.handled",
        extra={
            "event_type": event_type,
            "summary": handled.summary,
            "org_id": handled.org_id,
        },
    )
    return {"status": "ok", "summary": handled.summary}

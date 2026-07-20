import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Annotated, Any

import razorpay
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET
from db import get_connection, row_to_dict
from modules.auth.dependencies import CurrentUser, get_current_user
from modules.subscriptions.plans import PLANS, TIER_RANK

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


def _razorpay_client():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET or "XXXX" in RAZORPAY_KEY_ID:
        return None
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def _set_user_tier(user_id: int, tier: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET subscription_tier = ? WHERE id = ?", (tier, user_id))
        conn.commit()


@router.get("/plans")
async def list_plans():
    return {
        "plans": [
            {**meta, "plan_key": key}
            for key, meta in PLANS.items()
        ]
    }


class CreateSubscriptionBody(BaseModel):
    plan_key: str


@router.get("/me")
async def my_subscription(user: Annotated[CurrentUser, Depends(get_current_user)]):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM subscriptions
            WHERE user_id = ? ORDER BY id DESC LIMIT 1
            """,
            (user.id,),
        ).fetchone()
    return {
        "tier": user.tier,
        "latest_subscription": row_to_dict(row),
    }


@router.post("/create")
async def create_subscription(
    body: CreateSubscriptionBody,
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    plan = PLANS.get(body.plan_key)
    if not plan:
        raise HTTPException(status_code=400, detail="Unknown plan")

    if body.plan_key == "lifetime":
        with get_connection() as conn:
            counter = conn.execute("SELECT sold, cap FROM lifetime_deal_counter WHERE id = 1").fetchone()
            if counter and counter["sold"] >= counter["cap"]:
                raise HTTPException(status_code=409, detail="Lifetime deal sold out")

    client = _razorpay_client()
    amount_paise = plan["price_inr"] * 100

    if not client:
        # Dev fallback — activate tier without payment gateway
        tier_code = plan["code"]
        expires = None
        if plan["billing_period"] == "monthly":
            expires = (datetime.utcnow() + timedelta(days=30)).isoformat()
        elif plan["billing_period"] == "yearly":
            expires = (datetime.utcnow() + timedelta(days=365)).isoformat()
        elif plan.get("duration_hours"):
            expires = (datetime.utcnow() + timedelta(hours=plan["duration_hours"])).isoformat()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions (user_id, plan_name, billing_period, status, amount_paid_paise, expires_at)
                VALUES (?, ?, ?, 'active', ?, ?)
                """,
                (
                    user.id,
                    body.plan_key,
                    plan["billing_period"],
                    amount_paise,
                    expires,
                ),
            )
            conn.commit()
        _set_user_tier(user.id, tier_code)
        return {
            "mode": "dev",
            "message": "Razorpay keys not configured — plan activated in dev mode",
            "tier": tier_code,
        }

    if plan["billing_period"] in ("monthly", "yearly") and plan.get("razorpay_plan_id"):
        sub = client.subscription.create(
            {
                "plan_id": plan["razorpay_plan_id"],
                "customer_notify": 1,
                "total_count": 12 if plan["billing_period"] == "yearly" else 120,
            }
        )
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO subscriptions (user_id, plan_name, billing_period, razorpay_subscription_id, status, amount_paid_paise)
                VALUES (?, ?, ?, ?, 'created', ?)
                """,
                (user.id, body.plan_key, plan["billing_period"], sub["id"], amount_paise),
            )
            conn.commit()
        return {"mode": "razorpay", "subscription": sub}

    order = client.order.create(
        {"amount": amount_paise, "currency": "INR", "payment_capture": 1}
    )
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (user_id, plan_name, billing_period, status, amount_paid_paise)
            VALUES (?, ?, ?, 'created', ?)
            """,
            (user.id, body.plan_key, plan["billing_period"], amount_paise),
        )
        conn.commit()
    return {"mode": "razorpay", "order": order, "key_id": RAZORPAY_KEY_ID}


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Annotated[str | None, Header()] = None,
):
    body = await request.body()
    signature_valid = 0
    if RAZORPAY_WEBHOOK_SECRET and x_razorpay_signature:
        expected = hmac.new(
            RAZORPAY_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        signature_valid = 1 if hmac.compare_digest(expected, x_razorpay_signature) else 0

    payload = json.loads(body.decode() or "{}")
    event = payload.get("event", "unknown")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO webhook_logs (event_type, payload, signature_valid, processed)
            VALUES (?, ?, ?, 0)
            """,
            (event, body.decode(), signature_valid),
        )
        conn.commit()

    if not signature_valid and RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Minimal handlers — extend as Razorpay events are configured
    if event in ("subscription.charged", "payment.captured"):
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {})
        notes = payment.get("notes") or {}
        user_id = notes.get("user_id")
        tier = notes.get("tier", "basic")
        if user_id:
            _set_user_tier(int(user_id), tier)

    with get_connection() as conn:
        conn.execute(
            "UPDATE webhook_logs SET processed = 1 WHERE id = (SELECT MAX(id) FROM webhook_logs)"
        )
        conn.commit()

    return {"status": "ok"}


def expire_subscriptions_job() -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT user_id FROM subscriptions
            WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at < ?
            """,
            (now,),
        ).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE users SET subscription_tier = 'free' WHERE id = ?",
                (row["user_id"],),
            )
            conn.execute(
                "UPDATE subscriptions SET status = 'expired' WHERE user_id = ? AND status = 'active'",
                (row["user_id"],),
            )
        conn.commit()

from fastapi import APIRouter, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from typing import Any, List, Union
from datetime import datetime
import hmac
import hashlib
import json
import logging
from resort_backend.database import get_db
from pydantic import BaseModel, Field
import os
import razorpay
import random
import string

router = APIRouter(tags=["payments"])


class CreateOrderRequest(BaseModel):
    amount: int = Field(..., description="Amount in paise (integer, required by Razorpay)")
    currency: str = "INR"
    receipt: str | None = None
    notes: dict | None = None
    booking_snapshot: dict | None = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def _get_client():
    key_id = os.getenv("RAZORPAY_KEY_ID") or os.getenv("RAZORPAY_KEY")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    # also support older env names from application.properties style
    if not key_id:
        key_id = os.getenv("razorpay.key_id")
    if not key_secret:
        key_secret = os.getenv("razorpay.key_secret")
    # If keys are missing, allow an explicit, opt-in test fallback for local development.
    if not key_id or not key_secret:
        allow_fallback = (os.getenv("ALLOW_RAZORPAY_TEST_FALLBACK") == "1") or (os.getenv("DEBUG") in ("1", "true", "True"))
        if allow_fallback:
            logging.getLogger("resort_backend").warning("Razorpay keys not configured — using test fallback because ALLOW_RAZORPAY_TEST_FALLBACK is enabled. Do NOT use this in production.")
            key_id = key_id or "rzp_test_RpZR4dDpG2dPnv"
            key_secret = key_secret or "CcN59mt21z556BN4ryhiI7Ks"
        else:
            logging.getLogger("resort_backend").error("Razorpay keys not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in environment.")
            raise RuntimeError("Razorpay keys not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
    # Log which key id is being used (do not log secrets)
    logging.getLogger("resort_backend").info(f"Razorpay client using key_id={key_id}")
    return razorpay.Client(auth=(key_id, key_secret)), key_id


@router.post("/order")
async def create_order(req: CreateOrderRequest):
    client, key_id = _get_client()
    # Razorpay expects amount in the smallest currency unit (paise)
    try:
        amount_paise = int(req.amount)
        if amount_paise <= 0:
            raise ValueError("Amount must be positive and in paise (integer)")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid amount: must be a positive integer (paise)")
    payload = {
        "amount": amount_paise,
        "currency": req.currency or "INR",
        "receipt": req.receipt or "rcpt_" + os.urandom(4).hex(),
        "payment_capture": 1,
    }
    if req.notes:
        payload["notes"] = req.notes
    try:
        order = client.order.create(data=payload)
        # persist a transaction record linking to this razorpay order (helpful for reconciliation)
        try:
            db = get_db()
            tx = {
                "razorpay_order_id": order.get("id") if isinstance(order, dict) else None,
                "amount": amount_paise,
                "currency": req.currency or "INR",
                "receipt": payload.get("receipt"),
                "status": "created",
                "created_at": datetime.utcnow(),
                "raw_order": order,
            }
            if getattr(req, 'booking_snapshot', None):
                tx["booking_payload"] = req.booking_snapshot
            try:
                await db.transactions.insert_one(tx)
            except Exception:
                logging.getLogger("resort_backend").exception("Failed to persist transaction for create-order")
        except Exception:
            logging.getLogger("resort_backend").exception("Failed to access DB to persist transaction")

        # Only return serializable fields (avoid returning raw order with non-serializable objects)
        order_response = {
            "id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "key": key_id,
            "razorpayKey": key_id,
        }
        # Optionally add more fields if needed, but avoid non-serializable ones
        return order_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify")
async def verify_payment(body: VerifyPaymentRequest):
    client, _ = _get_client()
    data = {
        "razorpay_order_id": body.razorpay_order_id,
        "razorpay_payment_id": body.razorpay_payment_id,
        "razorpay_signature": body.razorpay_signature,
    }
    # Log incoming verify attempt
    logging.getLogger("resort_backend").info(f"verify_payment called: order_id={data['razorpay_order_id']} payment_id={data['razorpay_payment_id']}")
    try:
        client.utility.verify_payment_signature(data)
        logging.getLogger("resort_backend").info(f"verify_payment: signature verified for payment_id={data['razorpay_payment_id']}")
        # persist verification to transactions table (mark paid)
        try:
            db = get_db()
            res = await db.transactions.update_one({"razorpay_order_id": data["razorpay_order_id"]}, {"$set": {"status": "paid", "razorpay_payment_id": data["razorpay_payment_id"], "verified_at": datetime.utcnow()}})
            if getattr(res, 'matched_count', 0) == 0:
                # create a bare transaction record if none exists
                try:
                    await db.transactions.insert_one({
                        "razorpay_order_id": data["razorpay_order_id"],
                        "razorpay_payment_id": data["razorpay_payment_id"],
                        "status": "paid",
                        "created_at": datetime.utcnow(),
                        "verified_at": datetime.utcnow(),
                    })
                except Exception:
                    logging.getLogger("resort_backend").exception("Failed to insert fallback transaction on verify")
        except Exception:
            logging.getLogger("resort_backend").exception("Failed to update/insert transaction on verify")

        return {"ok": True, "message": "Signature verified"}
    except Exception as e:
        logging.getLogger("resort_backend").exception(f"verify_payment: signature verification failed for payment_id={data['razorpay_payment_id']} error={e}")
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {e}")


@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """Endpoint to receive Razorpay webhooks. Verifies signature and updates bookings/transactions.

    Expected header: X-Razorpay-Signature
    """
    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8")
    signature = request.headers.get("X-Razorpay-Signature") or request.headers.get("x-razorpay-signature")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET") or os.getenv("RAZORPAY_KEY_SECRET") or os.getenv("razorpay.key_secret")
    logger = logging.getLogger("resort_backend")
    if not signature or not secret:
        logger.warning("Webhook received without signature or secret not configured")
        logger.debug(f"headers={dict(request.headers)} body={body_text[:1000]}")
        return JSONResponse({"ok": False, "detail": "Missing signature or secret"}, status_code=400)

    # verify signature
    computed = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    # log a masked comparison for debugging (show first 8 chars only)
    logger.info(f"webhook: received sig={(signature or '')[:8]} computed={(computed or '')[:8]} body_len={len(body_bytes)}")
    if not hmac.compare_digest(computed, signature):
        logger.warning("Webhook signature verification failed")
        logger.debug(f"computed={computed} signature={signature} body={body_text[:1000]}")
        return JSONResponse({"ok": False, "detail": "Invalid signature"}, status_code=400)

    try:
        payload = json.loads(body_text)
    except Exception:
        payload = {}

    ev = payload.get("event")
    data = payload.get("payload", {})
    db = get_db()

    # Example handling: payment.captured, payment.failed, order.paid
    try:
        if ev == "payment.captured":
            payment_obj = data.get("payment", {}).get("entity", {})
            # mark transaction/booking as paid if we can find by order_id or payment id
            order_id = payment_obj.get("order_id")
            payment_id = payment_obj.get("id")
            # Update transactions collection if present
            try:
                res = await db.transactions.update_one({"razorpay_order_id": order_id}, {"$set": {"status": "paid", "razorpay_payment_id": payment_id, "raw": payment_obj}})
                logger.debug(f"transactions.update_one matched={getattr(res, 'matched_count', None)} modified={getattr(res, 'modified_count', None)}")
                if getattr(res, 'matched_count', 0) == 0:
                    try:
                        await db.transactions.insert_one({
                            "razorpay_order_id": order_id,
                            "razorpay_payment_id": payment_id,
                            "status": "paid",
                            "created_at": datetime.utcnow(),
                            "raw": payment_obj,
                        })
                        logger.info(f"Inserted fallback transaction for order_id={order_id}")
                    except Exception:
                        logger.exception("Failed to insert fallback transaction in webhook payment.captured")
            except Exception:
                logger.exception("Failed to update transactions for payment.captured")

            # Attempt reconciliation: if payment captured but no booking exists, try to create one
            try:
                # look for existing booking linked to this order_id or payment_id
                existing_booking = await db.bookings.find_one({"$or": [{"payment.order_id": order_id}, {"payment.payment_id": payment_id}]})
                if not existing_booking:
                    # fetch transaction to see if booking payload was stored at order creation
                    tx = await db.transactions.find_one({"razorpay_order_id": order_id})
                    if tx and tx.get("booking_payload"):
                        bp = tx.get("booking_payload")
                        # ensure idempotency: double-check no booking exists for this payment
                        exists2 = await db.bookings.find_one({"$or": [{"payment.order_id": order_id}, {"payment.payment_id": payment_id}]})
                        if not exists2:
                            # build booking doc from payload with status 'confirmed'
                            try:
                                doc = {
                                    "reference": "RB-WEB-" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + ''.join(random.choices(string.digits, k=4)),
                                    "guest_name": bp.get("guest_name") or bp.get("guest_email") or "Auto-created",
                                    "guest_email": bp.get("guest_email"),
                                    "guest_phone": bp.get("guest_phone"),
                                    "guests": bp.get("guests") or 1,
                                    "selected_cottages": bp.get("selected_cottages") or [],
                                    "allocated_cottages": bp.get("allocated_cottages") or [],
                                    "payment": {"provider": "razorpay", "order_id": order_id, "payment_id": payment_id},
                                    "check_in": bp.get("check_in"),
                                    "check_out": bp.get("check_out"),
                                    "nights": bp.get("nights") or 0,
                                    "price_breakdown": bp.get("price_breakdown") or {},
                                    "status": "confirmed",
                                    "created_at": datetime.utcnow(),
                                    "updated_at": datetime.utcnow(),
                                    "auto_created_by_webhook": True,
                                }
                                await db.bookings.insert_one(doc)
                                logger.info(f"Webhook reconciliation: created booking for order_id={order_id}")
                            except Exception:
                                logger.exception("Failed to create booking from transaction booking_payload")
                    else:
                        # No booking payload available — create a minimal placeholder booking to record payment
                        try:
                            # create placeholder booking to record payment; admin must enrich later
                            placeholder = {
                                "reference": "RB-WEB-" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-" + ''.join(random.choices(string.digits, k=4)),
                                "guest_name": tx.get("receipt") or "Unknown",
                                "guest_email": tx.get("receipt") if tx and tx.get("receipt") else None,
                                "guest_phone": None,
                                "guests": 1,
                                "selected_cottages": [],
                                "allocated_cottages": [],
                                "payment": {"provider": "razorpay", "order_id": order_id, "payment_id": payment_id},
                                "check_in": None,
                                "check_out": None,
                                "nights": 0,
                                "price_breakdown": {"total": payment_obj.get("amount")/100 if payment_obj.get("amount") else None},
                                "status": "paid",
                                "created_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow(),
                                "auto_created_by_webhook": True,
                                "note": "Auto-created booking placeholder from payment webhook — enrich manually.",
                            }
                            resph = await db.bookings.insert_one(placeholder)
                            logger.info(f"Webhook reconciliation: created placeholder booking id={getattr(resph, 'inserted_id', None)} for order_id={order_id}")
                        except Exception:
                            logger.exception("Failed to insert placeholder booking on webhook reconciliation")
            except Exception:
                logger.exception("Error during webhook reconciliation step")

        elif ev == "payment.failed":
            payment_obj = data.get("payment", {}).get("entity", {})
            order_id = payment_obj.get("order_id")
            payment_id = payment_obj.get("id")
            try:
                res = await db.transactions.update_one({"razorpay_order_id": order_id}, {"$set": {"status": "failed", "razorpay_payment_id": payment_id, "raw": payment_obj}})
                logger.debug(f"transactions.update_one matched={getattr(res, 'matched_count', None)} modified={getattr(res, 'modified_count', None)}")
            except Exception:
                logger.exception("Failed to update transactions for payment.failed")

        elif ev == "order.paid":
            order_obj = data.get("order", {}).get("entity", {})
            order_id = order_obj.get("id")
            try:
                res = await db.orders.update_one({"id": order_id}, {"$set": {"status": "paid", "raw": order_obj}})
                logger.debug(f"orders.update_one matched={getattr(res, 'matched_count', None)} modified={getattr(res, 'modified_count', None)}")
            except Exception:
                logger.exception("Failed to update orders for order.paid")
        # Add other event handlers as needed
    except Exception:
        logger.exception("Error processing webhook event")

    return JSONResponse({"ok": True})

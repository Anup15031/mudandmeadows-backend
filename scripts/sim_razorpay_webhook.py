"""Simulate sending a Razorpay webhook to local server for testing reconciliation.

Usage:
    python sim_razorpay_webhook.py --url http://localhost:8000/payments/razorpay/webhook \
        --secret my_webhook_secret --event payment.captured --order_id ord_ABC123 --payment_id pay_ABC123 --amount 10000

This script uses httpx (already a dependency) and HMAC-SHA256 to sign the payload.
"""
import argparse
import json
import hmac
import hashlib
import time
import httpx


def build_payment_captured(order_id: str, payment_id: str, amount: int):
    return {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": amount,
                    "currency": "INR",
                    "status": "captured",
                    "method": "card",
                }
            }
        }
    }


def compute_sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000/payments/razorpay/webhook")
    p.add_argument("--secret", required=True)
    p.add_argument("--event", default="payment.captured")
    p.add_argument("--order_id", default="ord_test_" + str(int(time.time())))
    p.add_argument("--payment_id", default="pay_test_" + str(int(time.time())))
    p.add_argument("--amount", type=int, default=10000)
    args = p.parse_args()

    if args.event == "payment.captured":
        payload = build_payment_captured(args.order_id, args.payment_id, args.amount)
    else:
        print("Only payment.captured payload currently supported by this simulator.")
        return

    body = json.dumps(payload).encode("utf-8")
    sig = compute_sig(args.secret, body)

    headers = {"Content-Type": "application/json", "X-Razorpay-Signature": sig}

    print("POSTing webhook to", args.url)
    print("Payload:\n", json.dumps(payload, indent=2))
    print("Signature:", sig[:16] + "...")

    try:
        r = httpx.post(args.url, content=body, headers=headers, timeout=10.0)
        print("Response status:", r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text[:200])
    except Exception as e:
        print("Failed to post webhook:", e)


if __name__ == "__main__":
    main()

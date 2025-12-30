# Razorpay integration notes

This repository includes server endpoints for Razorpay order creation, verification and webhook reconciliation.

Quick start (local):

1. Copy `.env.example` to `.env` and set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET`.
2. Ensure MongoDB is running and `MONGODB_URI` is set.
3. Install dependencies listed in `requirements.txt`.
4. Start the FastAPI server (example):

```bash
uvicorn main:app --reload --port 8000
```

Simulate a webhook (local):

```bash
python scripts/sim_razorpay_webhook.py --secret "your_webhook_secret" --order_id ord_demo --payment_id pay_demo --amount 15000
```

Notes:
- The server will now require `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` to be set. This prevents accidental use of hardcoded test keys in production.
- The frontend now sends a `booking_snapshot` when creating an order so the webhook can recreate bookings when necessary.
- Use the simulator to validate webhook signature verification and reconciliation flows.

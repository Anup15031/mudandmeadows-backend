This project can be built into a Docker image that ensures required MongoDB indexes are created on startup.

Build:

- Set environment variables `MONGODB_URL` and `DATABASE_NAME` (and optionally `ADMIN_API_KEY`).
- From the repository root run:

  docker build -t resort-backend:latest .

Run:

  docker run -e MONGODB_URL="your_mongo_uri" -e DATABASE_NAME="adivasi" -p 8000:8000 resort-backend:latest

The container entrypoint will run `resort_backend/scripts/create_indexes.py` if `MONGODB_URL` is set, then start `uvicorn`.

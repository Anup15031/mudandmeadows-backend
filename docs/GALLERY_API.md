# Gallery API

This document describes the Gallery endpoints used by the frontend.

Environment
- `MONGODB_URL` — MongoDB connection string
- `DATABASE_NAME` — (optional) database name, default `resort_db`
- `ADMIN_API_KEY` — (optional) when set, write endpoints require the header `X-Admin-Key: <key>`

Endpoints

- GET /gallery
  - Query params: `category` (optional), `visible` (optional boolean), `limit`, `skip`
  - Response: `{ items: [...], count: N }` where each item has `{ id, imageUrl, caption?, category?, isVisible, createdAt }

- GET /gallery/{id}
  - Returns single gallery item or 404

- POST /gallery
  - Protected when `ADMIN_API_KEY` set — add header `X-Admin-Key`.
  - Accepts `multipart/form-data` or `application/x-www-form-urlencoded` with either:
    - `imageUrl` (string) OR
    - `file` (binary file)
  - Other fields: `caption`, `category`, `isVisible`
  - On file upload, file is stored under `/uploads/gallery/<filename>` and `imageUrl` will be returned as that path.

- PUT /gallery/{id}
  - Protected when `ADMIN_API_KEY` set.
  - Accepts JSON payload with fields to update (caption, category, isVisible, imageUrl).

- DELETE /gallery/{id}
  - Protected when `ADMIN_API_KEY` set.

Examples

Create with URL (curl):

```bash
curl -X POST "http://localhost:8000/gallery/" \
  -H "X-Admin-Key: ${ADMIN_API_KEY}" \
  -F "imageUrl=https://example.com/image.jpg" \
  -F "caption=Sunset" \
  -F "category=nature"
```

Upload file (curl):

```bash
curl -X POST "http://localhost:8000/gallery/" \
  -H "X-Admin-Key: ${ADMIN_API_KEY}" \
  -F "file=@./path/to/photo.jpg" \
  -F "caption=Room view" \
  -F "category=rooms"
```

Notes
- If `ADMIN_API_KEY` is not set in the environment, write endpoints are open (development convenience). Set `ADMIN_API_KEY` in production.
- Uploaded files are served from `/uploads/gallery/` by the backend StaticFiles mount.

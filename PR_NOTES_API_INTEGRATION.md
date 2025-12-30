# PR Notes: Frontend — Backend Integration (OpenAPI + client + mocks)

Summary of changes

- Added `openapi.yaml` (resort_backend/openapi.yaml) — machine-readable contract covering audited endpoints, auth headers, and file upload specs.
- **Consolidated** the detailed `api/bookings` schema into `resort_backend/openapi.yaml` and **deprecated** duplicate copies at `resort_backend/docs/openapi_booking_post.yaml` and `R1/backend_additions/openapi_booking_post.yaml`.
- Replaced/extended frontend API client: `resort_backend/frontend/src/api.js` — a fetch-based client with:
  - Environment-configurable `API_BASE` (supports `REACT_APP_API_BASE` and `VITE_API_URL`, default `/api` to use dev proxy)
  - Added robust `buildUrl` helper to avoid duplicate `/api` when running with relative base
  - `setAdminKey` / `setInternalKey` helpers to set `X-Admin-Key` and `X-Internal-Key`
  - Helpers for cottages, programs, bookings, navigation, menu-items, gallery (upload), extra-beds, internal status, and SSE events
  - `axiosClient` helper showing how to use axios if required
- Added JSON mocks: `resort_backend/frontend/mocks/db.json` and `routes.json`; updated README; includes a small `test_api_client.js` script to smoke-test endpoints locally with `json-server` (routes.json maps `/api/*` to mock resources).
- Added `frontend/README_API_CLIENT.md` usage docs and examples, and `frontend/ROOMS_README.md` with brief, sample responses, and QA checklist.
- Updated `R1/src/lib/api-client.ts` to map backend `rooms` into cottage objects and to default API base to `/api` (dev proxy supported via `vite.config.ts`).
- Extended `openapi.yaml` with a `Room` schema and documented `rooms` on `Cottage` responses.
- Added a simple test page: `R1/src/pages/RoomsTest.tsx` for quick verification of rooms mapping.

How to test locally

1. Start the JSON mock server:
   - cd `resort_backend/frontend/mocks`
   - `npx json-server --watch db.json --port 8001`
2. Set frontend env: `REACT_APP_API_BASE=http://localhost:8001` or `VITE_API_URL=http://localhost:8001`
3. Use the default exported client from `src/api.js` or run the small smoke test (`node test_api_client.js`) in the mocks folder.

Reviewer notes & suggestions

- The `openapi.yaml` is intentionally compact; it covers endpoints (paths, params, basic schemas, security schemes) and is suitable for using OpenAPI tools for codegen or mock servers.
- Consider adding a CI job that validates `openapi.yaml` (e.g., `openapi-cli validate`) to prevent drift.
- If you prefer TypeScript types for the frontend, we can run an OpenAPI codegen step (e.g., `openapi-generator` or `openapi-typescript`) to produce typed client wrappers.
- File upload is implemented using `FormData` in `uploadGallery` — ensure that `X-Admin-Key` is provided when admin keys are required.

Next steps (optional)

- Add integration tests covering key flows (create booking, upload gallery, fetch cottages) using mocked server or Playwright backed by the `mocks` data.
- Add Postman collection or automatically generated HTTP examples from `openapi.yaml`.

If you'd like, I can open a draft PR with these changes or generate TypeScript client types from the OpenAPI contract next. What would you prefer I do next?
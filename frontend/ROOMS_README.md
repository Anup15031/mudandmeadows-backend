# Rooms / Cottages Update — Frontend Brief

Brief

Please update the UI API client so cottages/accommodations include their linked rooms. Backend now returns a `rooms` array on:
- `GET /api/cottages` (paged) — each item includes `rooms`
- `GET /api/cottages/{id}` and `GET /accommodations/{id}` — single item includes `rooms`

Tasks / Acceptance criteria
- Map backend `rooms` into the cottage object the UI expects.
- Use `rooms[].id` (string), `rooms[].capacity` (int), `rooms[].price_per_night` (float), and `rooms[].available` when deciding availability and capacity.
- Update booking selection UI to allow selecting specific room(s) per cottage where applicable and to include chosen room ids in booking payload as `selected_rooms` (optional).
- Use `API_BASE` from env or default `/api` and ensure dev proxy forwards `/api` to `http://localhost:8000`.

Sample response

```json
{
  "page": 1,
  "limit": 20,
  "total": 1,
  "items": [
    {
      "id": "693b180ecd2db4226156ae2a",
      "slug": "jacuzzi-cottage",
      "name": "Jacuzzi Cottage",
      "pricePerNight": 250,
      "capacity": 4,
      "rooms": [
        { "id": "r1", "name": "Room A", "capacity": 2, "price_per_night": 125, "available": true },
        { "id": "r2", "name": "Room B", "capacity": 2, "price_per_night": 125, "available": false }
      ]
    }
  ]
}
```

QA checklist
- Dev setup:
  - Confirm backend running at `http://localhost:8000` and `/api/cottages` returns `rooms`.
  - Ensure dev proxy forwards `/api` to backend (Vite `server.proxy['/api'] = 'http://localhost:8000'` or CRA `proxy`).
- Functional:
  - Load Rooms/Cottages page and confirm each cottage object contains `rooms` in network response.
  - Verify UI displays room-level info (capacity, per-room price, availability).
  - Booking flow: select a room and complete booking — server returns `201` with `id`, `reference`, `status`.
- Edge cases:
  - If `rooms` is empty, UI should fall back to cottage-level capacity.
  - Handle missing fields gracefully (use defaults).

Quick console test (if dev server running on :3000 and proxy enabled)

```js
fetch('/api/cottages').then(r=>r.json()).then(console.log).catch(console.error)
```

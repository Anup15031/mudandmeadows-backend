# Frontend API client — usage & examples

Quick reference for the `frontend/src/api.js` client and how to run local mocks.

Environment variables
- `REACT_APP_API_BASE` or `VITE_API_URL` — base URL for API (default: `/api` — use a dev proxy to forward `/api` to your backend at `http://localhost:8000`)

Proxy note
- For Vite dev server, ensure `vite.config.ts` contains:

```js
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

Admin/Internal keys
- `setAdminKey(key)` — sets `X-Admin-Key` header for admin actions (e.g., gallery uploads)
- `setInternalKey(key)` — sets `X-Internal-Key` header for internal endpoints

Running local JSON mocks
1. `cd frontend/mocks`
2. `npx json-server --watch db.json --port 8001`
3. Set `REACT_APP_API_BASE=http://localhost:8001` when running the frontend

Examples

// using default exported client
import api from './src/api';

// set admin key for uploads
api.setAdminKey('my-admin-key');

// list cottages
const cottages = await api.getCottages(1, 10);

// create a compat booking
const booking = await api.createBooking({ guest_name: 'Alice', guest_email: 'a@x.com', guests: 2 }, { compat: true });

// upload gallery file (browser File object)
await api.uploadGallery({ file: myFile }, { useAdmin: true });

// SSE stream
const es = api.eventsStream(msg => console.log(msg.data));
// es.close() to stop

Axios
If your app uses axios, you can create an axios client:

import axios from 'axios';
import { axiosClient } from './src/api';

const client = axiosClient(axios.create({ baseURL: process.env.VITE_API_URL }));
const data = await client.getCottages(1, 5);

Testing
A small test script `frontend/mocks/test_api_client.js` demonstrates using the client against the mock server.

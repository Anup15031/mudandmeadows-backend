// Lightweight API client for Resort Backend (fetch-based implementation)
// Also includes an optional axios example export (if you prefer axios in your project).

const API_BASE = process.env.REACT_APP_API_BASE || process.env.VITE_API_URL || '/api';
let ADMIN_KEY = null;
let INTERNAL_KEY = null;

export function setAdminKey(key) {
  ADMIN_KEY = key;
}
export function setInternalKey(key) {
  INTERNAL_KEY = key;
}

function authHeaders({ useAdmin = false, useInternal = false, extraHeaders = {} } = {}) {
  const headers = { ...extraHeaders };
  if (useAdmin && ADMIN_KEY) headers['X-Admin-Key'] = ADMIN_KEY;
  if (useInternal && INTERNAL_KEY) headers['X-Internal-Key'] = INTERNAL_KEY;
  return headers;
}

function buildUrl(path) {
  // robustly join API_BASE with path and avoid duplicating '/api' if API_BASE already contains it
  if (!API_BASE) return path;
  if (API_BASE.endsWith('/api') && path.startsWith('/api')) return API_BASE + path.slice(4);
  if (API_BASE.endsWith('/') && path.startsWith('/')) return API_BASE.slice(0, -1) + path;
  return API_BASE + path;
}

async function handleRes(res) {
  const contentType = res.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) throw data || { message: 'Request failed' };
  return data;
}

// Cottages (compat)
export async function getCottages(page = 1, limit = 10) {
  const res = await fetch(buildUrl(`/api/cottages?page=${page}&limit=${limit}`));
  return handleRes(res);
}
export async function getCottageById(cottageId) {
  const res = await fetch(buildUrl(`/api/cottages/${encodeURIComponent(cottageId)}`));
  return handleRes(res);
}

// Programs
export async function getPrograms({ tag } = {}) {
  const q = tag ? `?tag=${encodeURIComponent(tag)}` : '';
  const res = await fetch(`${API_BASE}/programs/${q}`.replace('/programs/?', '/programs/?'));
  return handleRes(res);
}
export async function getProgramById(id) {
  const res = await fetch(`${API_BASE}/programs/${encodeURIComponent(id)}`);
  return handleRes(res);
}
export async function recommendPrograms(payload) {
  const res = await fetch(`${API_BASE}/programs/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleRes(res);
}

// Bookings
export async function listBookings() {
  const res = await fetch(`${API_BASE}/bookings/`);
  return handleRes(res);
}
export async function getBooking(bookingId) {
  const res = await fetch(`${API_BASE}/bookings/${encodeURIComponent(bookingId)}`);
  return handleRes(res);
}
export async function createBooking(payload, { compat = true } = {}) {
  if (compat) {
    const res = await fetch(buildUrl('/api/bookings'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleRes(res);
  }
  const res = await fetch(buildUrl('/bookings/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleRes(res);
}
export async function updateBooking(bookingId, payload) {
  const res = await fetch(`${API_BASE}/bookings/${encodeURIComponent(bookingId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleRes(res);
}
export async function deleteBooking(bookingId) {
  const res = await fetch(`${API_BASE}/bookings/${encodeURIComponent(bookingId)}`, {
    method: 'DELETE',
  });
  return handleRes(res);
}
export async function getBookingsForGuest(guestEmail) {
  const res = await fetch(`${API_BASE}/bookings/guest/${encodeURIComponent(guestEmail)}`);
  return handleRes(res);
}

// Navigation
export async function getNavigation({ publicOnly = true } = {}) {
  const res = await fetch(`${API_BASE}/navigation/?public=${publicOnly}`);
  return handleRes(res);
}
export async function createNavigation(payload) {
  const res = await fetch(`${API_BASE}/navigation/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleRes(res);
}

// Menu
export async function getMenuItems() {
  const res = await fetch(`${API_BASE}/menu-items/`);
  return handleRes(res);
}
export async function getMenuItem(id) {
  const res = await fetch(`${API_BASE}/menu-items/${encodeURIComponent(id)}`);
  return handleRes(res);
}

// Gallery
export async function getGallery({ category, visible, limit, skip } = {}) {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (typeof visible !== 'undefined') params.set('visible', String(visible));
  if (limit) params.set('limit', String(limit));
  if (skip) params.set('skip', String(skip));
  const res = await fetch(`${API_BASE}/gallery/?${params.toString()}`);
  return handleRes(res);
}
export async function getGalleryItem(id) {
  const res = await fetch(`${API_BASE}/gallery/${encodeURIComponent(id)}`);
  return handleRes(res);
}
export async function uploadGallery({ file, imageUrl, metadata } = {}, { useAdmin = true } = {}) {
  const headers = authHeaders({ useAdmin });
  if (file) {
    const fd = new FormData();
    fd.append('file', file);
    if (metadata) fd.append('metadata', JSON.stringify(metadata));
    const res = await fetch(`${API_BASE}/gallery/`, {
      method: 'POST',
      headers,
      body: fd,
    });
    return handleRes(res);
  }
  // imageUrl form
  const res = await fetch(`${API_BASE}/gallery/`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ imageUrl, metadata }),
  });
  return handleRes(res);
}
export async function updateGalleryItem(id, payload, { useAdmin = true } = {}) {
  const headers = { ...authHeaders({ useAdmin }), 'Content-Type': 'application/json' };
  const res = await fetch(`${API_BASE}/gallery/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(payload),
  });
  return handleRes(res);
}
export async function deleteGalleryItem(id, { useAdmin = true } = {}) {
  const headers = authHeaders({ useAdmin });
  const res = await fetch(`${API_BASE}/gallery/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers,
  });
  return handleRes(res);
}

// Extra beds
export async function listExtraBeds() {
  const res = await fetch(`${API_BASE}/extra-beds/`);
  return handleRes(res);
}
export async function getExtraBedItem(id) {
  const res = await fetch(`${API_BASE}/extra-beds/${encodeURIComponent(id)}`);
  return handleRes(res);
}
export async function requestExtraBed(payload) {
  const res = await fetch(`${API_BASE}/extra-beds/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleRes(res);
}

// Internal status (requires internal key)
export async function getDbStatus({ useInternal = true } = {}) {
  const headers = authHeaders({ useInternal });
  const res = await fetch(`${API_BASE}/internal/db-status`, { headers });
  return handleRes(res);
}

// SSE events (simple helper)
export function eventsStream(onMessage, onOpen, onError) {
  const es = new EventSource(buildUrl('/api/events/stream'));
  es.onmessage = (e) => onMessage && onMessage(e);
  es.onopen = (e) => onOpen && onOpen(e);
  es.onerror = (e) => onError && onError(e);
  return es; // caller should close via es.close()
}

// Optional axios example: if your project already uses axios, you can use this exported helper
export function axiosClient(axiosInstance) {
  if (!axiosInstance) throw new Error('Provide an axios instance');
  const q = (obj) => {
    const s = new URLSearchParams(obj).toString();
    return s ? `?${s}` : '';
  };
  return {
    getCottages: (page = 1, limit = 10) => axiosInstance.get(`/api/cottages?page=${page}&limit=${limit}`).then(r => r.data),
    postBooking: (payload, opts = {}) => axiosInstance.post(opts.compat ? '/api/bookings' : '/bookings/', payload).then(r => r.data),
    uploadGalleryFile: (file, opts = {}) => {
      const fd = new FormData();
      fd.append('file', file);
      const headers = {};
      if (opts.adminKey) headers['X-Admin-Key'] = opts.adminKey;
      return axiosInstance.post('/gallery/', fd, { headers }).then(r => r.data);
    }
  };
}

export default {
  // auth
  setAdminKey,
  setInternalKey,
  // cottages
  getCottages,
  getCottageById,
  // programs
  getPrograms,
  getProgramById,
  recommendPrograms,
  // bookings
  listBookings,
  getBooking,
  createBooking,
  updateBooking,
  deleteBooking,
  getBookingsForGuest,
  // menu & nav
  getNavigation,
  createNavigation,
  getMenuItems,
  getMenuItem,
  // gallery
  getGallery,
  getGalleryItem,
  uploadGallery,
  updateGalleryItem,
  deleteGalleryItem,
  // extra beds
  listExtraBeds,
  getExtraBedItem,
  requestExtraBed,
  // internal
  getDbStatus,
  // events
  eventsStream,
  // axios helper
  axiosClient,
};

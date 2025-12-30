Switching frontend from fixtures to live API

- Set environment variable `REACT_APP_API_BASE` to point at backend, e.g.:

  REACT_APP_API_BASE=http://localhost:8000

- Use the provided `frontend/src/api.js` helpers instead of fixtures. Example:

  import api from './api';
  const cottages = await api.getCottages(1,5);

- In development with Create React App, restart dev server after changing `.env`.

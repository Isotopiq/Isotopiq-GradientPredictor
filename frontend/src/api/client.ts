import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT from localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 -> clear tokens and let the app handle redirect via React Router.
// We do NOT use window.location.href here because it causes a hard page reload
// which loses all React state and makes the app feel like it "navigated away"
// when the user was interacting with it (e.g. clicking Calculate Descriptors).
//
// Instead, we clear the tokens and dispatch a custom event. The AuthContext
// listens for this event and updates its state, which causes ProtectedRoute
// to redirect to /login via React Router (no page reload).
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      // Dispatch a custom event so the React app can handle the redirect
      // via React Router instead of a hard page reload.
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }
    return Promise.reject(error);
  },
);

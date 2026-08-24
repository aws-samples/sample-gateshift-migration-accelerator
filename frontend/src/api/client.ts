import axios from 'axios';
import { getIdToken, clearSession } from '../store/authStore';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001',
  headers: { 'Content-Type': 'application/json' },
});

// Attach the Cognito ID token to every request when present.
apiClient.interceptors.request.use((config) => {
  const token = getIdToken();
  if (token) {
    config.headers.Authorization = token;
  }
  return config;
});

// On 401/403 the token is missing or expired: clear the session so the app
// falls back to the login screen.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      clearSession();
    }
    return Promise.reject(error);
  }
);

export default apiClient;

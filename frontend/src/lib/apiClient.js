import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// All backend calls go through the versioned API base.
export const API_BASE = `${BACKEND_URL}/api/v1`;

export const apiClient = axios.create({
  baseURL: API_BASE,
  // Cookie-based auth transport is wired in a later milestone; harmless now.
  withCredentials: false,
  headers: { "Content-Type": "application/json" },
});

// Normalize errors into { code, message, details, status } shape.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status ?? 0;
    const payload = error?.response?.data?.error;
    return Promise.reject({
      status,
      code: payload?.code ?? "network_error",
      message: payload?.message ?? error?.message ?? "Request failed.",
      details: payload?.details ?? null,
    });
  }
);

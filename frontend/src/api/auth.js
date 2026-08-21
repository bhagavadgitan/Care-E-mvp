import { apiClient } from "@/lib/apiClient";

export const authApi = {
  me: () => apiClient.get("/auth/me").then((r) => r.data),
  login: (email, password) => apiClient.post("/auth/login", { email, password }).then((r) => r.data),
  registerHospital: (data) => apiClient.post("/auth/register/hospital", data).then((r) => r.data),
  registerSupplier: (data) => apiClient.post("/auth/register/supplier", data).then((r) => r.data),
  logout: () => apiClient.post("/auth/logout").then((r) => r.data),
  updateProfile: (data) => apiClient.patch("/users/me", data).then((r) => r.data),
  googleCallback: (session_id) => apiClient.post("/auth/google/callback", { session_id }).then((r) => r.data),
  googleComplete: (data) => apiClient.post("/auth/google/complete", data).then((r) => r.data),
};

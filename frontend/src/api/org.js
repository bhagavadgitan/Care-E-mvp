import { apiClient } from "@/lib/apiClient";

export const orgApi = {
  list: (status) =>
    apiClient.get("/organisations", { params: status ? { status } : {} }).then((r) => r.data),
  updateStatus: (id, approval_status) =>
    apiClient.patch(`/organisations/${id}`, { approval_status }).then((r) => r.data),
};

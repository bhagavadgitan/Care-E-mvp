import { apiClient } from "@/lib/apiClient";

export async function getHealth() {
  const { data } = await apiClient.get("/health");
  return data;
}

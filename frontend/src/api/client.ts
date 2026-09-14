import axios from "axios";
import type {
  AssistantRequest,
  AssistantResponse,
  InvalidPlanResponse,
  PlanData,
} from "./types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  // The backend uses 422 to return a structured invalid-plan payload.
  validateStatus: (status) => status === 200 || status === 422,
});

export async function getPlan(): Promise<PlanData | InvalidPlanResponse> {
  const response = await api.get<PlanData | InvalidPlanResponse>("/api/plan");
  return response.data;
}

export async function askAssistant(
  body: AssistantRequest,
): Promise<AssistantResponse> {
  const response = await api.post<AssistantResponse>("/api/assistant", body);
  return response.data;
}

import { postJson, requestJson } from "../../shared/api/http";
import type { ScheduledTask } from "./types";

export function fetchTasks() {
  return requestJson<ScheduledTask[]>("/api/scheduled-tasks");
}

export function runTaskNow(taskId: string) {
  return postJson<{ message: string; instance_id?: string; document_id?: string }>(
    `/api/scheduled-tasks/${taskId}/run-now`,
    {},
  );
}

export function pauseTask(taskId: string) {
  return postJson<{ message: string }>(`/api/scheduled-tasks/${taskId}/pause`, {});
}

export function resumeTask(taskId: string) {
  return postJson<{ message: string }>(`/api/scheduled-tasks/${taskId}/resume`, {});
}

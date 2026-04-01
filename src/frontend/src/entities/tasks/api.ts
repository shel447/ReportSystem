import { chatbiPath, postJson, requestJson } from "../../shared/api/http";
import type { ScheduledTask, ScheduledTaskCreatePayload } from "./types";

export function fetchTasks() {
  return requestJson<ScheduledTask[]>(chatbiPath("/scheduled-tasks"));
}

export function createTask(payload: ScheduledTaskCreatePayload) {
  return postJson<ScheduledTask>(chatbiPath("/scheduled-tasks"), payload);
}

export function runTaskNow(taskId: string) {
  return postJson<{ message: string; instance_id?: string; document_id?: string }>(
    chatbiPath(`/scheduled-tasks/${taskId}/run-now`),
    {},
  );
}

export function pauseTask(taskId: string) {
  return postJson<{ message: string }>(chatbiPath(`/scheduled-tasks/${taskId}/pause`), {});
}

export function resumeTask(taskId: string) {
  return postJson<{ message: string }>(chatbiPath(`/scheduled-tasks/${taskId}/resume`), {});
}

import { postJson, requestJson } from "../../shared/api/http";
import type { ReportInstance } from "./types";

export function fetchInstances() {
  return requestJson<ReportInstance[]>("/api/instances");
}

export function fetchInstance(instanceId: string) {
  return requestJson<ReportInstance>(`/api/instances/${instanceId}`);
}

export function regenerateSection(instanceId: string, sectionIndex: number) {
  return postJson<ReportInstance>(`/api/instances/${instanceId}/regenerate/${sectionIndex}`, {});
}

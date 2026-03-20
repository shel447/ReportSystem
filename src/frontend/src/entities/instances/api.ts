import { postJson, requestJson } from "../../shared/api/http";
import type { InstanceBaseline, InstanceForkSource, ReportInstance } from "./types";

export function fetchInstances() {
  return requestJson<ReportInstance[]>("/api/instances");
}

export function fetchInstance(instanceId: string) {
  return requestJson<ReportInstance>(`/api/instances/${instanceId}`);
}

export function fetchInstanceBaseline(instanceId: string) {
  return requestJson<InstanceBaseline>(`/api/instances/${instanceId}/baseline`);
}

export function updateInstanceChat(instanceId: string) {
  return postJson<{ session_id: string }>(`/api/instances/${instanceId}/update-chat`, {});
}

export function fetchInstanceForkSources(instanceId: string) {
  return requestJson<InstanceForkSource[]>(`/api/instances/${instanceId}/fork-sources`);
}

export function forkInstanceChat(instanceId: string, sourceMessageId: string) {
  return postJson<{ session_id: string }>(`/api/instances/${instanceId}/fork-chat`, {
    source_message_id: sourceMessageId,
  });
}

export function regenerateSection(instanceId: string, sectionIndex: number) {
  return postJson<ReportInstance>(`/api/instances/${instanceId}/regenerate/${sectionIndex}`, {});
}

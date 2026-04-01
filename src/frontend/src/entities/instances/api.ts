import { chatbiPath, postJson, requestJson } from "../../shared/api/http";
import type { ChatSessionPayload } from "../chat/types";
import type { InstanceBaseline, InstanceForkSource, ReportInstance } from "./types";

export function fetchInstances() {
  return requestJson<ReportInstance[]>(chatbiPath("/instances"));
}

export function fetchInstance(instanceId: string) {
  return requestJson<ReportInstance>(chatbiPath(`/instances/${instanceId}`));
}

export function fetchInstanceBaseline(instanceId: string) {
  return requestJson<InstanceBaseline>(chatbiPath(`/instances/${instanceId}/baseline`));
}

export function updateInstanceChat(instanceId: string) {
  return postJson<ChatSessionPayload>(chatbiPath(`/instances/${instanceId}/update-chat`), {});
}

export function fetchInstanceForkSources(instanceId: string) {
  return requestJson<InstanceForkSource[]>(chatbiPath(`/instances/${instanceId}/fork-sources`));
}

export function forkInstanceChat(instanceId: string, sourceMessageId: string) {
  return postJson<{ session_id: string }>(chatbiPath(`/instances/${instanceId}/fork-chat`), {
    source_message_id: sourceMessageId,
  });
}

export function regenerateSection(instanceId: string, sectionIndex: number) {
  return postJson<ReportInstance>(chatbiPath(`/instances/${instanceId}/regenerate/${sectionIndex}`), {});
}

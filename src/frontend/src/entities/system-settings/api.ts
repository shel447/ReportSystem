import { devPath, postJson, putJson, requestJson } from "../../shared/api/http";
import type { SystemSettingsPayload } from "./types";

export function fetchSystemSettings() {
  return requestJson<SystemSettingsPayload>(devPath("/system-settings"));
}

export function updateSystemSettings(payload: unknown) {
  return putJson<SystemSettingsPayload>(devPath("/system-settings"), payload);
}

export function testSystemSettings(target: "completion" | "embedding" | "both") {
  return postJson<Record<string, unknown>>(devPath("/system-settings/test"), { target });
}

export function rebuildTemplateIndex() {
  return postJson<{ message: string; index_status: unknown }>(devPath("/system-settings/reindex"), {});
}

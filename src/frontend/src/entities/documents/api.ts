import { postJson, requestJson } from "../../shared/api/http";
import type { ReportDocument } from "./types";

export function fetchDocuments(instanceId?: string) {
  const suffix = instanceId ? `?instance_id=${encodeURIComponent(instanceId)}` : "";
  return requestJson<ReportDocument[]>(`/api/documents${suffix}`);
}

export function createDocument(instanceId: string) {
  return postJson<ReportDocument>("/api/documents", {
    instance_id: instanceId,
    format: "markdown",
  });
}

import { chatbiPath, postJson, requestJson } from "../../shared/api/http";
import type { ReportDocument } from "./types";

export function fetchDocuments(instanceId?: string) {
  const suffix = instanceId ? `?instance_id=${encodeURIComponent(instanceId)}` : "";
  return requestJson<ReportDocument[]>(`${chatbiPath("/documents")}${suffix}`);
}

export function createDocument(instanceId: string) {
  return postJson<ReportDocument>(chatbiPath("/documents"), {
    instance_id: instanceId,
    format: "markdown",
  });
}

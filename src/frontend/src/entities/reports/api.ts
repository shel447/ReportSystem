import { chatbiPath, postJson, requestJson } from "../../shared/api/http";
import type { DocumentGenerationRequest, DocumentGenerationResponse, ReportView } from "./types";

export function fetchReport(reportId: string) {
  return requestJson<ReportView>(chatbiPath(`/reports/${encodeURIComponent(reportId)}`));
}

export function generateReportDocuments(reportId: string, payload: DocumentGenerationRequest) {
  return postJson<DocumentGenerationResponse>(chatbiPath(`/reports/${encodeURIComponent(reportId)}/document-generations`), payload);
}

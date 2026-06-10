import { chatbiPath, postJson, requestJson, withQuery } from "../../shared/api/http";
import type { DocumentGenerationRequest, DocumentGenerationResponse, ReportView } from "./types";

export function fetchReport(reportId: string) {
  return requestJson<ReportView>(withQuery(chatbiPath("/reports/detail"), { reportId }));
}

export function generateReportDocuments(reportId: string, payload: DocumentGenerationRequest) {
  return postJson<DocumentGenerationResponse>(withQuery(chatbiPath("/reports/document-generations"), { reportId }), payload);
}

import { chatbiPath, requestJson } from "../../shared/api/http";
import type { ReportView } from "./types";

export function fetchReportView(reportId: string) {
  return requestJson<ReportView>(chatbiPath(`/reports/${encodeURIComponent(reportId)}`));
}

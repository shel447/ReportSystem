export type ReportStructureType = "flow" | "paged";

export function resolveReportStructureType(report: Record<string, unknown>): ReportStructureType | null {
  if (report.structureType === "flow" || report.structureType === "paged") {
    return report.structureType;
  }
  const basicInfo = isRecord(report.basicInfo) ? report.basicInfo : {};
  const reportType = String(basicInfo.reportType ?? "").toLowerCase();
  if (reportType === "ppt" || reportType === "pptx" || reportType === "presentation") {
    return "paged";
  }
  if (reportType === "word" || reportType === "docx" || reportType === "report") {
    return "flow";
  }
  if (Array.isArray(report.content)) {
    return "paged";
  }
  if (Array.isArray(report.catalogs)) {
    return "flow";
  }
  return null;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function listRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

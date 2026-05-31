import type { TemplateInstance } from "../chat/types";

export type ReportColumn = {
  key: string;
  title: string;
  width?: string;
  align?: string;
  children?: ReportColumn[];
};

export type ReportMergeRowInfo = {
  startRowIndex: number;
  rowSpan: number;
  column: string;
  mergedText?: string;
};

export type ReportTableDataProperties = {
  dataType: string;
  sourceId?: string;
  title?: string;
  columns?: ReportColumn[];
  data?: Array<Record<string, unknown>>;
  mergeRows?: ReportMergeRowInfo[];
};

export type ReportDocument = {
  id: string;
  format: string;
  mimeType: string;
  fileName: string;
  downloadUrl: string;
  status: string;
};

export type ReportAnswer = {
  reportId: string;
  status: "generating" | "available" | "failed";
  report: Record<string, unknown>;
  templateInstance: TemplateInstance;
  documents: ReportDocument[];
  generationProgress: {
    totalSections: number;
    completedSections: number;
  };
};

export type ReportView = {
  reportId: string;
  status: "generating" | "available" | "failed";
  answerType: "REPORT";
  answer: ReportAnswer;
};

export type DocumentGenerationRequest = {
  formats: Array<"word" | "ppt" | "pdf" | "markdown">;
  pdfSource?: "word" | "ppt" | null;
  theme?: string;
  strictValidation?: boolean;
  regenerateIfExists?: boolean;
};

export type DocumentGenerationResponse = {
  reportId: string;
  jobs: Array<{
    jobId: string;
    format: string;
    status: string;
    dependsOn?: string | null;
  }>;
  documents: ReportDocument[];
};

import { chatbiPath, deleteJson, postJson, putJson, requestJson } from "../../shared/api/http";
import type { ReportTemplate, TemplateImportPreview, TemplateSummary, TemplateUpsertPayload } from "./types";

export function fetchTemplates() {
  return requestJson<TemplateSummary[]>(chatbiPath("/templates"));
}

export function fetchTemplate(templateId: string) {
  return requestJson<ReportTemplate>(chatbiPath(`/templates/${encodeURIComponent(templateId)}`));
}

export function createTemplate(payload: TemplateUpsertPayload) {
  return postJson<ReportTemplate>(chatbiPath("/templates"), payload);
}

export function updateTemplate(templateId: string, payload: TemplateUpsertPayload) {
  return putJson<ReportTemplate>(chatbiPath(`/templates/${encodeURIComponent(templateId)}`), payload);
}

export function deleteTemplate(templateId: string) {
  return deleteJson(chatbiPath(`/templates/${encodeURIComponent(templateId)}`));
}

export function previewImportTemplate(content: unknown) {
  return postJson<TemplateImportPreview>(chatbiPath("/templates/import/preview"), { content });
}

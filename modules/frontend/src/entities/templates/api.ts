import { chatbiPath, deleteJson, postJson, putJson, requestJson, withQuery } from "../../shared/api/http";
import type { ReportTemplate, TemplateImportPreview, TemplateSummary, TemplateUpsertPayload } from "./types";

export function fetchTemplates() {
  return requestJson<TemplateSummary[]>(chatbiPath("/templates"));
}

export function fetchTemplate(templateId: string) {
  return requestJson<ReportTemplate>(withQuery(chatbiPath("/templates/detail"), { templateId }));
}

export function createTemplate(payload: TemplateUpsertPayload) {
  return postJson<ReportTemplate>(chatbiPath("/templates"), payload);
}

export function updateTemplate(templateId: string, payload: TemplateUpsertPayload) {
  return putJson<ReportTemplate>(withQuery(chatbiPath("/templates/detail"), { templateId }), payload);
}

export function deleteTemplate(templateId: string) {
  return deleteJson(withQuery(chatbiPath("/templates/detail"), { templateId }));
}

export function previewImportTemplate(content: unknown) {
  return postJson<TemplateImportPreview>(chatbiPath("/templates/import/preview"), { content });
}

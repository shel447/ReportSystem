import { deleteJson, postJson, putJson, requestJson } from "../../shared/api/http";
import type { TemplateDetail, TemplateSummary, TemplateUpsertPayload } from "./types";

export function fetchTemplates() {
  return requestJson<TemplateSummary[]>("/api/templates");
}

export function fetchTemplate(templateId: string) {
  return requestJson<TemplateDetail>(`/api/templates/${templateId}`);
}

export function createTemplate(payload: TemplateUpsertPayload) {
  return postJson<TemplateDetail>("/api/templates", payload);
}

export function updateTemplate(templateId: string, payload: TemplateUpsertPayload) {
  return putJson<TemplateDetail>(`/api/templates/${templateId}`, payload);
}

export function deleteTemplate(templateId: string) {
  return deleteJson(`/api/templates/${templateId}`);
}

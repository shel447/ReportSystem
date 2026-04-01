import { chatbiPath, deleteJson, postJson, putJson, requestJson } from "../../shared/api/http";
import type { TemplateDetail, TemplateSummary, TemplateUpsertPayload } from "./types";

export function fetchTemplates() {
  return requestJson<TemplateSummary[]>(chatbiPath("/templates"));
}

export function fetchTemplate(templateId: string) {
  return requestJson<TemplateDetail>(chatbiPath(`/templates/${templateId}`));
}

export function createTemplate(payload: TemplateUpsertPayload) {
  return postJson<TemplateDetail>(chatbiPath("/templates"), payload);
}

export function updateTemplate(templateId: string, payload: TemplateUpsertPayload) {
  return putJson<TemplateDetail>(chatbiPath(`/templates/${templateId}`), payload);
}

export function deleteTemplate(templateId: string) {
  return deleteJson(chatbiPath(`/templates/${templateId}`));
}

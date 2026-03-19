import { requestJson } from "../../shared/api/http";
import type { TemplateInstanceSummary } from "./types";

export function fetchTemplateInstances() {
  return requestJson<TemplateInstanceSummary[]>("/api/template-instances");
}

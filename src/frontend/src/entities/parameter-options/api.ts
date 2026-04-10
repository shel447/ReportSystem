import { chatbiPath, postJson } from "../../shared/api/http";

export type ParameterOptionItem = {
  label: string;
  value: string;
};

export type ParameterOptionsResolveResponse = {
  items: ParameterOptionItem[];
  meta: {
    source: string;
    limit: number;
    returned: number;
    has_more: boolean;
    truncated: boolean;
    retryable?: boolean;
    error_code?: string;
  };
};

export function resolveParameterOptions(payload: {
  template_id?: string;
  param_id: string;
  source: string;
  query?: string;
  selected_params?: Record<string, unknown>;
  limit?: number;
}) {
  return postJson<ParameterOptionsResolveResponse>(chatbiPath("/parameter-options/resolve"), payload);
}

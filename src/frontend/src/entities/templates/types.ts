export type TemplateSummary = {
  template_id: string;
  name: string;
  description: string;
  report_type: string;
  scenario: string;
  type?: string;
  scene?: string;
  created_at?: string;
};

export type TemplateDetail = TemplateSummary & {
  match_keywords: string[];
  content_params: unknown[];
  parameters: unknown[];
  outline: unknown[];
  sections: unknown[];
  schema_version: string;
  output_formats: string[];
  version?: string;
};

export type TemplateUpsertPayload = {
  name: string;
  description: string;
  report_type: string;
  scenario: string;
  type: string;
  scene: string;
  match_keywords: string[];
  content_params: unknown[];
  parameters: unknown[];
  outline: unknown[];
  sections: unknown[];
  schema_version: string;
  output_formats: string[];
};

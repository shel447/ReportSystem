export type TemplateSummary = {
  template_id: string;
  name: string;
  description: string;
  report_type: string;
  scenario: string;
  type?: string;
  scene?: string;
  schema_version?: string;
  parameter_count?: number;
  top_level_section_count?: number;
  created_at?: string;
};

export type TemplateParameter = {
  id: string;
  label: string;
  required: boolean;
  input_type: "free_text" | "date" | "enum" | "dynamic";
  interaction_mode?: "form" | "chat";
  multi?: boolean;
  options?: string[];
  source?: string;
};

export type TemplateForeach = {
  param: string;
  as: string;
};

export type TemplateOutlineBlock = {
  id: string;
  type: "indicator" | "time_range" | "scope" | "threshold" | "operator" | "enum_select" | "number" | "boolean" | "free_text" | "param_ref";
  hint?: string;
  default?: string;
  options?: string[];
  source?: string;
  param_id?: string;
  multi?: boolean;
  widget?: string;
};

export type TemplateOutlineBlueprint = {
  document: string;
  blocks: TemplateOutlineBlock[];
};

export type TemplateDatasetSource = {
  kind: "sql" | "nl2sql" | "ai_synthesis";
  query?: string;
  key_col?: string;
  value_col?: string;
  description?: string;
  context?: {
    refs?: string[];
    queries?: Array<{ id: string; query: string }>;
  };
  knowledge?: {
    query_template?: string;
    params?: {
      subject?: string;
      symptoms?: string;
      objective?: string;
    };
  };
  prompt?: string;
};

export type TemplateDataset = {
  id: string;
  depends_on?: string[];
  source: TemplateDatasetSource;
};

export type TemplateLayout = {
  type: "kv_grid" | "tabular";
  cols_per_row?: number;
  key_span?: number;
  value_span?: number;
  fields?: Array<{ key: string; value?: string; col?: string }>;
  headers?: Array<{ label: string; span: number; repeat?: boolean }>;
  columns?: Array<{ field: string; span: number; repeat?: boolean }>;
};

export type TemplateCompositeSection = {
  id?: string;
  band?: string | null;
  dataset_id?: string;
  layout: TemplateLayout;
};

export type TemplatePresentation = {
  type: "text" | "value" | "chart" | "simple_table" | "composite_table";
  template?: string;
  anchor?: string;
  dataset_id?: string;
  chart_type?: "bar" | "line" | "pie" | "area" | "scatter";
  columns?: number;
  sections?: TemplateCompositeSection[];
};

export type TemplateContent = {
  datasets?: TemplateDataset[];
  presentation: TemplatePresentation;
};

export type TemplateSection = {
  title: string;
  description?: string;
  outline?: TemplateOutlineBlueprint;
  foreach?: TemplateForeach;
  content?: TemplateContent;
  subsections?: TemplateSection[];
};

export type TemplateDetail = TemplateSummary & {
  match_keywords: string[];
  content_params: Record<string, unknown>[];
  parameters: TemplateParameter[];
  outline: Record<string, unknown>[];
  sections: TemplateSection[];
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
  content_params: Record<string, unknown>[];
  parameters: TemplateParameter[];
  outline: Record<string, unknown>[];
  sections: TemplateSection[];
  schema_version: string;
  output_formats: string[];
};

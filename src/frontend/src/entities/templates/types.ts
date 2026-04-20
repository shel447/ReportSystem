export type ParameterScalar = string | number | boolean;

export type ParameterValue = {
  label: ParameterScalar;
  value: ParameterScalar;
  query: ParameterScalar;
};

export type WarningItem = {
  code: string;
  message: string;
  path?: string;
  targetId?: string;
};

export type TemplateSummary = {
  id: string;
  category: string;
  name: string;
  description: string;
  schemaVersion: string;
  updatedAt?: string | null;
};

export type ParameterRuntimeContext = {
  valueSource?: "user_input" | "default" | "dynamic_candidate" | "parameter_ref" | "system_fill";
  queryContext?: Record<string, unknown>;
  confirmed?: boolean;
  confirmedAt?: string;
  optionSource?: string;
  optionsFetchedAt?: string;
};

export type TemplateParameter = {
  id: string;
  label: string;
  description?: string;
  inputType: "free_text" | "date" | "enum" | "dynamic";
  required: boolean;
  multi: boolean;
  interactionMode: "form" | "natural_language";
  placeholder?: string;
  defaultValue?: ParameterValue[];
  options?: ParameterValue[];
  values?: ParameterValue[];
  runtimeContext?: ParameterRuntimeContext;
  source?: string;
};

export type RequirementItemDefinition = {
  id: string;
  label: string;
  kind:
    | "search_target"
    | "search_condition"
    | "metric"
    | "time_range"
    | "filter"
    | "threshold"
    | "sort"
    | "free_text"
    | "parameter_ref";
  required: boolean;
  multi?: boolean;
  description?: string;
  sourceParameterId?: string;
  widget?: "input" | "textarea" | "select" | "multi_select" | "date" | "date_range";
  defaultValue?: ParameterValue[];
  values?: ParameterValue[];
  valueSource?: "user_input" | "default" | "parameter_ref" | "system_fill";
};

export type DatasetDefinition = {
  id: string;
  name?: string;
  sourceType: "sql" | "api" | "llm" | "compose";
  sourceRef: string;
  dependsOn?: string[];
  description?: string;
};

export type PresentationBlock = {
  id: string;
  type: "paragraph" | "bullet" | "kpi" | "table" | "chart" | "markdown" | "composite_table";
  title?: string;
  datasetId?: string;
  description?: string;
  parts?: Array<{
    id: string;
    title: string;
    description?: string;
    sourceType: "query" | "summary";
    datasetId?: string;
    summarySpec?: {
      partIds: string[];
      rows: Array<{ id: string; title: string }>;
      prompt?: string;
    };
    tableLayout?: {
      kind: "table";
      showHeader?: boolean;
      columns?: Array<{ key: string; title: string; width?: string; align?: "left" | "center" | "right" }>;
    };
  }>;
};

export type SectionDefinition = {
  id: string;
  description?: string;
  parameters?: TemplateParameter[];
  foreach?: {
    parameterId: string;
    as: string;
  };
  outline: {
    requirement: string;
    renderedRequirement?: string;
    items: RequirementItemDefinition[];
  };
  content: {
    datasets?: DatasetDefinition[];
    presentation: {
      kind: "narrative" | "table" | "chart" | "mixed";
      blocks: PresentationBlock[];
    };
  };
};

export type CatalogDefinition = {
  id: string;
  title: string;
  description?: string;
  parameters?: TemplateParameter[];
  foreach?: {
    parameterId: string;
    as: string;
  };
  subCatalogs?: CatalogDefinition[];
  sections?: SectionDefinition[];
};

export type ReportTemplate = {
  id: string;
  category: string;
  name: string;
  description: string;
  schemaVersion: string;
  tags?: string[];
  createdAt?: string | null;
  updatedAt?: string | null;
  parameters: TemplateParameter[];
  catalogs: CatalogDefinition[];
};

export type TemplateImportPreview = {
  normalizedTemplate: ReportTemplate;
  warnings: WarningItem[];
};

export type TemplateUpsertPayload = ReportTemplate;

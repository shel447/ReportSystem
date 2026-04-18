export type TrioValue = {
  display: string | number | boolean;
  value: string | number | boolean;
  query: string | number | boolean;
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

export type OpenSource = {
  url: string;
};

export type TemplateParameter = {
  id: string;
  label: string;
  description?: string;
  inputType: "free_text" | "date" | "enum" | "dynamic";
  required: boolean;
  multi: boolean;
  interactionMode: "form" | "natural_language";
  valueMode: "display" | "value" | "query";
  placeholder?: string;
  defaultValue?: TrioValue[];
  options?: TrioValue[];
  openSource?: OpenSource;
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
  defaultValue?: TrioValue[];
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
  type: "paragraph" | "bullet" | "kpi" | "table" | "chart" | "markdown";
  title?: string;
  datasetId?: string;
  description?: string;
};

export type SectionDefinition = {
  id: string;
  title: string;
  description?: string;
  order?: number;
  foreach?: {
    parameterId: string;
    as: string;
  };
  outline: {
    requirement: string;
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
  name: string;
  description?: string;
  order?: number;
  sections: SectionDefinition[];
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

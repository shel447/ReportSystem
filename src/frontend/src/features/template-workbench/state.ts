import type {
  TemplateCompositeSection,
  TemplateDataset,
  TemplateDetail,
  TemplateEditableDraft,
  TemplateLayout,
  TemplateParameter,
  TemplatePresentation,
  TemplateRequirementSlot,
  TemplateSection,
  TemplateSectionOutline,
  TemplateUpsertPayload,
} from "../../entities/templates/types";

export type ParameterInputType = "free_text" | "date" | "enum" | "dynamic";
export type SectionKind = "group" | "content";
export type PresentationType = "text" | "value" | "chart" | "simple_table" | "composite_table";
export type DatasetSourceKind = "sql" | "nl2sql" | "ai_synthesis";
export type LayoutType = "kv_grid" | "tabular";

export type TemplateWorkbenchState = {
  meta: WorkbenchMetaState;
  parameters: WorkbenchParameter[];
  sections: WorkbenchSection[];
  previewSamples: Record<string, string | string[]>;
};

export type WorkbenchMetaState = {
  templateId?: string;
  name: string;
  description: string;
  reportType: string;
  scenario: string;
  type: string;
  scene: string;
  schemaVersion: string;
  matchKeywords: string[];
  outputFormats: string[];
  compatibility: {
    contentParams: unknown[];
    outline: unknown[];
    migratedFromLegacy: boolean;
  };
};

export type WorkbenchParameter = {
  uiKey: string;
  id: string;
  label: string;
  required: boolean;
  inputType: ParameterInputType;
  interactionMode: "form" | "chat";
  multi: boolean;
  options: string[];
  source: string;
};

export type WorkbenchSection = {
  uiKey: string;
  title: string;
  description: string;
  foreachEnabled: boolean;
  foreachParam: string;
  foreachAlias: string;
  kind: SectionKind;
  outline: WorkbenchSectionOutline | null;
  content: WorkbenchContent | null;
  children: WorkbenchSection[];
};

export type RequirementSlotType = "indicator" | "time_range" | "scope" | "threshold" | "operator" | "enum_select" | "number" | "boolean" | "free_text" | "param_ref";

export type WorkbenchSectionOutline = {
  requirement: string;
  slots: WorkbenchRequirementSlot[];
};

export type WorkbenchRequirementSlot = {
  uiKey: string;
  id: string;
  type: RequirementSlotType;
  hint: string;
  defaultValue: string;
  options: string[];
  source: string;
  paramId: string;
  multi: boolean;
  widget: string;
};

export type WorkbenchContent = {
  datasets: WorkbenchDataset[];
  presentation: WorkbenchPresentation;
};

export type WorkbenchDataset = {
  uiKey: string;
  id: string;
  dependsOn: string[];
  source: WorkbenchDatasetSource;
};

export type WorkbenchDatasetSource = {
  kind: DatasetSourceKind;
  query: string;
  description: string;
  keyCol: string;
  valueCol: string;
  prompt: string;
  contextRefs: string[];
  contextQueries: Array<{ id: string; query: string }>;
  knowledgeQueryTemplate: string;
  knowledgeParams: {
    subject: string;
    symptoms: string;
    objective: string;
  };
};

export type WorkbenchPresentation = {
  type: PresentationType;
  template: string;
  anchor: string;
  datasetId: string;
  chartType: "bar" | "line" | "pie" | "area" | "scatter";
  columns?: number;
  sections: WorkbenchCompositeSection[];
};

export type WorkbenchCompositeSection = {
  uiKey: string;
  id: string;
  band: string;
  datasetId: string;
  layout: WorkbenchLayout;
};

export type WorkbenchLayout = {
  type: LayoutType;
  colsPerRow?: number;
  keySpan?: number;
  valueSpan?: number;
  fields: Array<{ key: string; value?: string; col?: string }>;
  headers: Array<{ label: string; span: number; repeat?: boolean }>;
  columns: Array<{ field: string; span: number; repeat?: boolean }>;
};

export function createEmptyWorkbenchState(): TemplateWorkbenchState {
  return {
    meta: {
      name: "",
      description: "",
      reportType: "daily",
      scenario: "",
      type: "",
      scene: "",
      schemaVersion: "v2.0",
      matchKeywords: [],
      outputFormats: ["md"],
      compatibility: {
        contentParams: [],
        outline: [],
        migratedFromLegacy: false,
      },
    },
    parameters: [],
    sections: [],
    previewSamples: {},
  };
}

export function toWorkbenchState(template: TemplateDetail | TemplateEditableDraft): TemplateWorkbenchState {
  const state = createEmptyWorkbenchState();
  state.meta = {
    templateId: template.template_id,
    name: template.name,
    description: template.description ?? "",
    reportType: template.report_type ?? "daily",
    scenario: template.scenario ?? "",
    type: template.type ?? "",
    scene: template.scene ?? "",
    schemaVersion: template.schema_version || "v2.0",
    matchKeywords: template.match_keywords ?? [],
    outputFormats: template.output_formats ?? ["md"],
    compatibility: {
      contentParams: template.content_params ?? [],
      outline: template.outline ?? [],
      migratedFromLegacy:
        !(template.sections?.length ?? 0) &&
        Boolean((template.outline?.length ?? 0) || (template.content_params?.length ?? 0)),
    },
  };
  state.parameters = (template.parameters ?? []).map((item, index) => normalizeParameter(item, `param-${index + 1}`));
  const sections = (template.sections?.length ? template.sections : normalizeLegacyOutline(template.outline ?? [])) as TemplateSection[];
  state.sections = sections.map((item, index) => normalizeSection(item, `section-${index + 1}`));
  return state;
}

export function toTemplatePayload(state: TemplateWorkbenchState): TemplateUpsertPayload {
  return {
    name: state.meta.name.trim(),
    description: state.meta.description.trim(),
    report_type: state.meta.reportType.trim() || "daily",
    scenario: state.meta.scenario.trim(),
    type: state.meta.type.trim(),
    scene: state.meta.scene.trim(),
    match_keywords: state.meta.matchKeywords.filter(Boolean),
    content_params: [],
    parameters: state.parameters.map(serializeParameter),
    outline: [],
    sections: state.sections.map(serializeSection),
    schema_version: state.meta.schemaVersion.trim() || "v2.0",
    output_formats: state.meta.outputFormats.filter(Boolean),
  };
}

function normalizeParameter(value: TemplateParameter, uiKey: string): WorkbenchParameter {
  return {
    uiKey,
    id: value.id ?? "",
    label: value.label ?? "",
    required: Boolean(value.required),
    inputType: value.input_type ?? "free_text",
    interactionMode: value.interaction_mode ?? "form",
    multi: Boolean(value.multi),
    options: value.options ?? [],
    source: value.source ?? "",
  };
}

function serializeParameter(value: WorkbenchParameter): TemplateParameter {
  const payload: TemplateParameter = {
    id: value.id.trim(),
    label: value.label.trim(),
    required: Boolean(value.required),
    input_type: value.inputType,
    interaction_mode: value.interactionMode,
  };
  if (value.inputType === "enum" && value.options.length) {
    payload.options = value.options.filter(Boolean);
  }
  if (value.inputType === "dynamic" && value.source.trim()) {
    payload.source = value.source.trim();
  }
  if (value.inputType !== "date" && value.multi) {
    payload.multi = true;
  }
  return payload;
}

function normalizeSection(value: TemplateSection, uiKey: string): WorkbenchSection {
  const hasChildren = Boolean(value.subsections?.length);
  return {
    uiKey,
    title: value.title ?? "",
    description: value.description ?? "",
    foreachEnabled: Boolean(value.foreach?.param),
    foreachParam: value.foreach?.param ?? "",
    foreachAlias: value.foreach?.as ?? "item",
    kind: hasChildren ? "group" : "content",
    outline: normalizeOutline(value.outline, `${uiKey}-outline`),
    content: hasChildren ? null : normalizeContent(value.content),
    children: (value.subsections ?? []).map((item, index) => normalizeSection(item, `${uiKey}-${index + 1}`)),
  };
}

function serializeSection(value: WorkbenchSection): TemplateSection {
  const payload: TemplateSection = {
    title: value.title.trim(),
  };
  if (value.description.trim()) {
    payload.description = value.description.trim();
  }
  if (value.foreachEnabled && value.foreachParam.trim()) {
    payload.foreach = {
      param: value.foreachParam.trim(),
      as: value.foreachAlias.trim() || "item",
    };
  }
  if (value.outline && (value.outline.requirement.trim() || value.outline.slots.length)) {
    payload.outline = serializeOutline(value.outline);
  }
  if (value.kind === "group") {
    payload.subsections = value.children.map(serializeSection);
    return payload;
  }
  if (value.content) {
    payload.content = serializeContent(value.content);
  }
  return payload;
}

function normalizeContent(value?: { datasets?: TemplateDataset[]; presentation?: TemplatePresentation } | null): WorkbenchContent {
  return {
    datasets: (value?.datasets ?? []).map((item, index) => normalizeDataset(item, `dataset-${index + 1}`)),
    presentation: normalizePresentation(value?.presentation),
  };
}

function normalizeOutline(value?: TemplateSectionOutline | null, keyPrefix = "outline"): WorkbenchSectionOutline | null {
  if (!value) {
    return null;
  }
  const legacyRequirement = (value as { document?: string }).document ?? "";
  const legacySlots = (value as { blocks?: TemplateRequirementSlot[] }).blocks ?? [];
  return {
    requirement: value.requirement ?? legacyRequirement,
    slots: (value.slots ?? legacySlots).map((item, index) => normalizeOutlineSlot(item, `${keyPrefix}-slot-${index + 1}`)),
  };
}

function serializeOutline(value: WorkbenchSectionOutline): TemplateSectionOutline {
  return {
    requirement: value.requirement,
    slots: value.slots.map(serializeOutlineSlot),
  };
}

function normalizeOutlineSlot(value: TemplateRequirementSlot, uiKey: string): WorkbenchRequirementSlot {
  return {
    uiKey,
    id: value.id ?? "",
    type: value.type,
    hint: value.hint ?? "",
    defaultValue: value.default ?? "",
    options: value.options ?? [],
    source: value.source ?? "",
    paramId: value.param_id ?? "",
    multi: Boolean(value.multi),
    widget: value.widget ?? "",
  };
}

function serializeOutlineSlot(value: WorkbenchRequirementSlot): TemplateRequirementSlot {
  const payload: TemplateRequirementSlot = {
    id: value.id.trim(),
    type: value.type,
  };
  if (value.hint.trim()) {
    payload.hint = value.hint.trim();
  }
  if (value.defaultValue.trim()) {
    payload.default = value.defaultValue.trim();
  }
  if (value.options.length) {
    payload.options = value.options.filter(Boolean);
  }
  if (value.source.trim()) {
    payload.source = value.source.trim();
  }
  if (value.paramId.trim()) {
    payload.param_id = value.paramId.trim();
  }
  if (value.multi) {
    payload.multi = true;
  }
  if (value.widget.trim()) {
    payload.widget = value.widget.trim();
  }
  return payload;
}

function serializeContent(value: WorkbenchContent): { datasets?: TemplateDataset[]; presentation: TemplatePresentation } {
  const payload: { datasets?: TemplateDataset[]; presentation: TemplatePresentation } = {
    presentation: serializePresentation(value.presentation),
  };
  if (value.datasets.length) {
    payload.datasets = value.datasets.map(serializeDataset);
  }
  return payload;
}

function normalizeDataset(value: TemplateDataset, uiKey: string): WorkbenchDataset {
  return {
    uiKey,
    id: value.id ?? "",
    dependsOn: value.depends_on ?? [],
    source: {
      kind: value.source.kind,
      query: value.source.query ?? "",
      description: value.source.description ?? "",
      keyCol: value.source.key_col ?? "",
      valueCol: value.source.value_col ?? "",
      prompt: value.source.prompt ?? "",
      contextRefs: value.source.context?.refs ?? [],
      contextQueries: value.source.context?.queries ?? [],
      knowledgeQueryTemplate: value.source.knowledge?.query_template ?? "",
      knowledgeParams: {
        subject: value.source.knowledge?.params?.subject ?? "",
        symptoms: value.source.knowledge?.params?.symptoms ?? "",
        objective: value.source.knowledge?.params?.objective ?? "",
      },
    },
  };
}

function serializeDataset(value: WorkbenchDataset): TemplateDataset {
  const payload: TemplateDataset = {
    id: value.id.trim(),
    source: {
      kind: value.source.kind,
    },
  };
  if (value.dependsOn.length) {
    payload.depends_on = value.dependsOn.filter(Boolean);
  }
  if (value.source.query.trim()) {
    payload.source.query = value.source.query.trim();
  }
  if (value.source.description.trim()) {
    payload.source.description = value.source.description.trim();
  }
  if (value.source.keyCol.trim()) {
    payload.source.key_col = value.source.keyCol.trim();
  }
  if (value.source.valueCol.trim()) {
    payload.source.value_col = value.source.valueCol.trim();
  }
  if (value.source.prompt.trim()) {
    payload.source.prompt = value.source.prompt.trim();
  }
  if (value.source.contextRefs.length || value.source.contextQueries.length) {
    payload.source.context = {};
    if (value.source.contextRefs.length) {
      payload.source.context.refs = value.source.contextRefs.filter(Boolean);
    }
    if (value.source.contextQueries.length) {
      payload.source.context.queries = value.source.contextQueries.filter((item) => item.id.trim() && item.query.trim());
    }
  }
  if (
    value.source.knowledgeQueryTemplate.trim() ||
    value.source.knowledgeParams.subject.trim() ||
    value.source.knowledgeParams.symptoms.trim() ||
    value.source.knowledgeParams.objective.trim()
  ) {
    payload.source.knowledge = {
      query_template: value.source.knowledgeQueryTemplate.trim(),
      params: {
        subject: value.source.knowledgeParams.subject.trim(),
        symptoms: value.source.knowledgeParams.symptoms.trim(),
        objective: value.source.knowledgeParams.objective.trim(),
      },
    };
  }
  return payload;
}

function normalizePresentation(value?: TemplatePresentation | null): WorkbenchPresentation {
  return {
    type: value?.type ?? "text",
    template: value?.template ?? "",
    anchor: value?.anchor ?? "{$value}",
    datasetId: value?.dataset_id ?? "",
    chartType: value?.chart_type ?? "bar",
    columns: value?.columns,
    sections: (value?.sections ?? []).map((item, index) => normalizeCompositeSection(item, `composite-${index + 1}`)),
  };
}

function serializePresentation(value: WorkbenchPresentation): TemplatePresentation {
  const payload: TemplatePresentation = {
    type: value.type,
  };
  const template = value.template ?? "";
  const anchor = value.anchor ?? "{$value}";
  const datasetId = value.datasetId ?? "";
  if (template.trim() && value.type === "text") {
    payload.template = template.trim();
  }
  if (anchor.trim() && value.type === "value") {
    payload.anchor = anchor.trim();
  }
  if (datasetId.trim() && ["value", "simple_table", "chart"].includes(value.type)) {
    payload.dataset_id = datasetId.trim();
  }
  if (value.type === "chart") {
    payload.chart_type = value.chartType;
  }
  if (typeof value.columns === "number" && value.type === "composite_table") {
    payload.columns = value.columns;
  }
  if (value.type === "composite_table" && value.sections.length) {
    payload.sections = value.sections.map(serializeCompositeSection);
  }
  return payload;
}

function normalizeCompositeSection(value: TemplateCompositeSection, uiKey: string): WorkbenchCompositeSection {
  return {
    uiKey,
    id: value.id ?? "",
    band: value.band ?? "",
    datasetId: value.dataset_id ?? "",
    layout: normalizeLayout(value.layout),
  };
}

function serializeCompositeSection(value: WorkbenchCompositeSection): TemplateCompositeSection {
  return {
    id: value.id.trim() || undefined,
    band: value.band.trim() || undefined,
    dataset_id: value.datasetId.trim() || undefined,
    layout: serializeLayout(value.layout),
  };
}

function normalizeLayout(value: TemplateLayout): WorkbenchLayout {
  return {
    type: value.type,
    colsPerRow: value.cols_per_row,
    keySpan: value.key_span,
    valueSpan: value.value_span,
    fields: value.fields ?? [],
    headers: value.headers ?? [],
    columns: value.columns ?? [],
  };
}

function serializeLayout(value: WorkbenchLayout): TemplateLayout {
  return {
    type: value.type,
    cols_per_row: value.colsPerRow,
    key_span: value.keySpan,
    value_span: value.valueSpan,
    fields: value.fields.length ? value.fields : undefined,
    headers: value.headers.length ? value.headers : undefined,
    columns: value.columns.length ? value.columns : undefined,
  };
}

function normalizeLegacyOutline(items: unknown[]): TemplateSection[] {
  return (items ?? []).filter(isRecord).map((item) => ({
    title: typeof item.title === "string" ? item.title : "未命名章节",
    description: typeof item.description === "string" ? item.description : "",
    content: {
      presentation: {
        type: "text",
        template: typeof item.description === "string" && item.description ? item.description : "章节内容占位",
      },
    },
  }));
}

function isRecord(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

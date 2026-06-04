import type { ReportTemplate, TemplateParameter, ParameterValue, ParameterRuntimeContext, RequirementItemDefinition, ParameterScalar, DatasetDefinition, TableLayout, PresentationProperty } from "../templates/types";

export type TemplateInstanceRequirementItem = RequirementItemDefinition;

export type TemplateInstanceCompositeTablePart = {
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
  tableLayout?: TableLayout;
  runtimeContext: {
    status: "pending" | "running" | "finished" | "failed";
    resolvedDatasetId?: string;
    resolvedQuery?: string;
    resolvedPartIds?: string[];
    prompt?: string;
    warnings?: Array<{ code: string; message: string; targetId?: string }>;
  };
};

export type TemplateInstancePresentationBlock = {
  id: string;
  type: "text" | "table" | "chart" | "composite_table";
  title?: string;
  datasetId?: string;
  properties?: PresentationProperty;
  description?: string;
  parts?: TemplateInstanceCompositeTablePart[];
};

export type DynamicContext = {
  type: "foreach" | "foreachCase" | "custom";
  parameterId?: string;
  itemValue?: ParameterValue;
  caseId?: string;
  url?: string;
  nodeType?: "catalog" | "section";
};

export type TemplateInstanceSection = {
  id: string;
  description?: string;
  parameters?: TemplateParameter[];
  dynamicContext?: DynamicContext;
  outline: {
    requirement: string;
    renderedRequirement?: string;
    items: TemplateInstanceRequirementItem[];
  };
  content: {
    datasets?: DatasetDefinition[];
    presentation: {
      kind: "text" | "table" | "chart" | "mixed";
      blocks: TemplateInstancePresentationBlock[];
    };
  };
  runtimeContext: {
    bindings: Array<{
      id: string;
      bindingType: string;
      sourceType: string;
      targetRef: string;
      multiValueQueryMode?: string;
      queryTemplate?: string;
      resolvedQuery?: string;
      notes?: string;
    }>;
    notes?: string;
  };
  skeletonStatus: "reusable" | "conditionally_reusable" | "broken";
  userEdited: boolean;
};

export type TemplateInstanceCatalog = {
  id: string;
  title: string;
  renderedTitle: string;
  description?: string;
  parameters?: TemplateParameter[];
  dynamicContext?: DynamicContext;
  subCatalogs?: TemplateInstanceCatalog[];
  sections?: TemplateInstanceSection[];
};

export type TemplateInstance = {
  id: string;
  schemaVersion: string;
  templateId: string;
  template: ReportTemplate;
  conversationId: string;
  chatId?: string;
  status:
    | "draft"
    | "collecting_parameters"
    | "ready_for_confirmation"
    | "confirmed"
    | "generating"
    | "completed"
    | "failed";
  captureStage: "fill_params" | "confirm_params" | "generate_report" | "report_ready";
  revision: number;
  parameters: TemplateParameter[];
  parameterConfirmation: {
    missingParameterIds: string[];
    confirmed: boolean;
    confirmedAt?: string;
  };
  catalogs: TemplateInstanceCatalog[];
  warnings?: Array<{ code: string; message: string; targetId?: string }>;
  createdAt: string;
  updatedAt: string;
};

export type ReportAnswerPayload = {
  reportId: string;
  status: "generating" | "available" | "failed";
  report: Record<string, unknown>;
  templateInstance: TemplateInstance;
  documents: Array<{
    id: string;
    format: string;
    mimeType: string;
    fileName: string;
    downloadUrl: string;
    status: string;
  }>;
  generationProgress: {
    totalSections: number;
    completedSections: number;
    totalCatalogs?: number;
    completedCatalogs?: number;
    currentCatalogPath?: string[];
    currentSectionId?: string;
  };
};

export type ChatAsk = {
  status: "pending" | "replied";
  mode: "form" | "natural_language";
  type: "fill_params" | "confirm_params" | "clarify_scenario";
  title: string;
  text: string;
  parameters?: TemplateParameter[];
  reportContext?: {
    templateInstance: TemplateInstance;
  };
};

export type ChatResponse = {
  conversationId: string;
  chatId: string;
  status: "waiting_user" | "running" | "finished" | "failed" | "cancelled" | "terminated" | "refused";
  steps: ChatStreamStep[];
  ask: ChatAsk | null;
  answer:
    | {
        answerType: "REPORT_TEMPLATE";
        answer: {
          normalizedTemplate: Record<string, unknown>;
          warnings: Array<{ code: string; message: string; path?: string }>;
          persisted: false;
        };
      }
    | {
        answerType: "REPORT";
        answer: ReportAnswerPayload;
      }
    | {
        answerType: "DATA_ANALYSIS";
        answer: {
          summary: string;
          querySpec: Record<string, unknown>;
          sql: string;
          data: { columns: Record<string, unknown>; results: Array<Record<string, unknown>> };
          visualizations: { components: Array<Record<string, unknown>> };
          warnings: Array<Record<string, unknown>>;
        };
      }
    | null;
  errors: unknown[];
  requestId?: string;
  timestamp: number;
  apiVersion: string;
};

export type ChatStreamStep = {
  code: string;
  stepId?: string;
  status: string;
  title?: string | null;
  detail?: string | null;
  parentStepId?: string | null;
  stepPath?: string[];
  sourceSubflow?: Record<string, unknown>;
};

export type ChatStreamDeltaParent = {
  type: "report" | "catalog" | "chapter" | "slide" | "section" | "subflow";
  id: string | null;
  path?: Array<string | number> | null;
};

export type ChatStreamDelta =
  | {
      action: "init_report";
      parent?: ChatStreamDeltaParent;
      report: {
        reportId: string;
        title: string;
        structureType?: "flow" | "paged";
      };
    }
  | {
      action: "add_catalog";
      structureType?: "flow";
      parent?: ChatStreamDeltaParent;
      parentCatalogId: string | null;
      parentCatalog: number[] | null;
      catalogs: Array<{
        catalogId: string;
        title: string;
      }>;
    }
  | {
      action: "add_chapter";
      structureType: "paged";
      parent?: ChatStreamDeltaParent;
      chapters: Array<{
        id: string;
        title: string;
      }>;
    }
  | {
      action: "add_slide";
      structureType: "paged";
      parent?: ChatStreamDeltaParent;
      chapterId: string | null;
      slides: Array<{
        id: string;
        title?: string;
        layout: Record<string, unknown>;
      }>;
    }
  | {
      action: "add_section";
      structureType?: "flow" | "paged";
      parent?: ChatStreamDeltaParent;
      parentCatalogId: string | null;
      parentCatalog: number[] | null;
      chapterId?: string | null;
      slideId?: string | null;
      sections: Array<{
        sectionId: string;
        status: string;
        requirement: string;
        components?: Array<Record<string, unknown>>;
      }>;
    };

export type ChatStreamEvent = {
  conversationId: string;
  chatId: string;
  eventType: "status" | "step_delta" | "ask" | "answer" | "error" | "done";
  sequence: number;
  timestamp: number;
  status: "waiting_user" | "running" | "finished" | "failed" | "cancelled" | "terminated" | "refused";
  step?: ChatStreamStep;
  steps?: ChatStreamStep[];
  ask?: ChatAsk | null;
  answer?: ChatResponse["answer"];
  error?: unknown;
  delta?: ChatStreamDelta[];
  toolCall?: Record<string, unknown>;
  toolResult?: Record<string, unknown>;
  refusal?: Record<string, unknown>;
  checkpoint?: Record<string, unknown>;
  sourceSubflow?: Record<string, unknown>;
};

export type ConversationSummary = {
  conversationId: string;
  title: string;
  status: string;
  updatedAt?: string | null;
  lastMessagePreview?: string;
};

export type ConversationDetail = {
  conversationId: string;
  title?: string;
  status?: string;
  records: ConversationRecord[];
};

export type ConversationRecord = {
  chatId: string;
  question: string;
  askTime?: string | number | null;
  answers: ConversationAnswer[];
};

export type ConversationAnswer = {
  type: "TEXT" | "PIU";
  content: string;
  answerTime?: string | number | null;
};

export type ChatRequest = {
  conversationId?: string;
  chatId?: string;
  question?: string;
  instruction?: "generate_report" | "extract_report_template" | "generate_report_segment" | "query_data";
  report?: {
    templateName: string;
    parameters?: TemplateParameter[];
  } | null;
  reply?: {
    type: "fill_params" | "confirm_params";
    sourceChatId: string;
    parameters?: Record<string, ParameterScalar[]>;
    reportContext?: {
      templateInstance: TemplateInstance;
    };
  } | null;
  attachments?: Array<Record<string, unknown>>;
  histories?: Array<Record<string, unknown>>;
  requestId?: string;
  apiVersion?: "v1";
};

export type ChatForkRequest = {
  source_kind: string;
  source_conversation_id?: string;
  source_chat_id?: string;
};

export type { ParameterValue, TemplateParameter, ParameterRuntimeContext };

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
  type: "paragraph" | "bullet" | "kpi" | "table" | "chart" | "markdown" | "composite_table";
  title?: string;
  datasetId?: string;
  properties?: PresentationProperty;
  description?: string;
  parts?: TemplateInstanceCompositeTablePart[];
};

export type TemplateInstanceSection = {
  id: string;
  description?: string;
  parameters?: TemplateParameter[];
  foreachContext?: {
    parameterId: string;
    itemValues: ParameterValue[];
  };
  outline: {
    requirement: string;
    renderedRequirement?: string;
    items: TemplateInstanceRequirementItem[];
  };
  content: {
    datasets?: DatasetDefinition[];
    presentation: {
      kind: "narrative" | "table" | "chart" | "mixed";
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
  foreachContext?: {
    parameterId: string;
    itemValues: ParameterValue[];
  };
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
  type: "fill_params" | "confirm_params";
  title: string;
  text: string;
  parameters: TemplateParameter[];
  reportContext: {
    templateInstance: TemplateInstance;
  };
};

export type ChatResponse = {
  conversationId: string;
  chatId: string;
  status: "waiting_user" | "running" | "finished" | "failed";
  steps: unknown[];
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
    | null;
  errors: unknown[];
  requestId?: string;
  timestamp: number;
  apiVersion: string;
};

export type ChatStreamDelta =
  | {
      action: "init_report";
      report: {
        reportId: string;
        title: string;
      };
    }
  | {
      action: "add_catalog";
      parentCatalogId: string | null;
      parentCatalog: number[] | null;
      catalogs: Array<{
        catalogId: string;
        title: string;
      }>;
    }
  | {
      action: "add_section";
      parentCatalogId: string | null;
      parentCatalog: number[] | null;
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
  status: "waiting_user" | "running" | "finished" | "failed";
  steps?: unknown[];
  ask?: ChatAsk | null;
  answer?: ChatResponse["answer"];
  error?: unknown;
  delta?: ChatStreamDelta[];
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
  messages: Array<{
    chatId: string;
    role: "user" | "assistant";
    content: Record<string, unknown>;
    action?: Record<string, unknown> | null;
    meta?: Record<string, unknown> | null;
    createdAt?: string | null;
  }>;
};

export type ChatRequest = {
  conversationId?: string;
  chatId?: string;
  question?: string;
  instruction?: "generate_report" | "extract_report_template";
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

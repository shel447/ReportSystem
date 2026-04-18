export type TrioValue = {
  display: string | number | boolean;
  value: string | number | boolean;
  query: string | number | boolean;
};

export type TemplateParameterProjection = {
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
  openSource?: { url: string };
};

export type TemplateInstance = {
  id: string;
  schemaVersion: string;
  templateId: string;
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
  parameterValues: Record<string, TrioValue[]>;
  catalogs: Array<{
    id: string;
    name: string;
    description?: string;
    order?: number;
    sections: Array<{
      id: string;
      title: string;
      description?: string;
      order?: number;
      requirementInstance: {
        text: string;
        items: Array<{
          id: string;
          label: string;
          kind: string;
          resolvedValues: TrioValue[];
          bindingSource: "parameter" | "user_input" | "system_fill";
          sourceParameterId?: string;
        }>;
      };
      executionBindings: Array<{
        id: string;
        bindingType: string;
        sourceType: string;
        targetRef: string;
        multiValueQueryMode?: string;
        queryTemplate?: string;
        resolvedQuery?: string;
        notes?: string;
      }>;
      skeletonStatus: "reusable" | "conditionally_reusable" | "broken";
      userEdited: boolean;
    }>;
  }>;
  deltaViews: Array<{
    targetType: string;
    targetId: string;
    changeKind: string;
    payload?: Record<string, unknown>;
  }>;
  templateSkeletonStatus: {
    internal: "reusable" | "conditionally_reusable" | "broken";
    ui: "not_broken" | "broken";
  };
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
  };
};

export type ChatAsk = {
  mode: "form" | "natural_language";
  type: "fill_params" | "confirm_params";
  title: string;
  text: string;
  parameters: Array<{
    parameter: TemplateParameterProjection;
    currentValue: TrioValue[];
  }>;
  reportContext: {
    templateInstance: TemplateInstance;
  };
};

export type ChatResponse = {
  conversationId: string;
  chatId: string;
  status: "waiting_user" | "finished" | "failed";
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
    parameters?: Record<string, TrioValue[]>;
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

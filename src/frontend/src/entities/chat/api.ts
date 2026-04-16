import { chatbiPath, deleteJson, postJson, requestJson } from "../../shared/api/http";
import type { ChatAction, ChatForkRequest, ChatForkResponse, ChatRequest, ChatResponse, ChatSessionDetail, ChatSessionSummary } from "./types";

type ContractInstruction = "generate_report" | "smart_query" | "fault_diagnosis";

type ContractChatRequest = {
  conversationId?: string;
  chatId: string;
  instruction?: ContractInstruction;
  question: string;
  reply?: {
    type: "fill_params" | "final_confirm";
    parameters: Record<string, unknown>;
  };
  command?: { name: string };
  selected_template_id?: string;
  target_param_id?: string;
  outline_override?: unknown[];
};

type ContractChatResponse = {
  conversationId: string;
  chatId: string;
  status: "running" | "waiting_user" | "finished" | "failed" | "aborted";
  steps: unknown[];
  delta: unknown[];
  ask: null | {
    mode: "form" | "chat";
    type: "fill_params" | "confirm" | "confirm_outline" | "select_template" | "confirm_task_switch";
    title?: string;
    question?: string;
    parameters?: Array<{
      id: string;
      label?: string;
      inputType?: string;
      required?: boolean;
      multi?: boolean;
      value?: unknown;
      options?: Array<string | { label?: string; value?: string }>;
    }>;
    outline?: unknown[];
    warnings?: string[];
    paramsSnapshot?: Array<{ id: string; label?: string; value?: unknown }>;
    candidates?: unknown[];
    reason?: string;
    fromCapability?: string;
    toCapability?: string;
  };
  answer: null | {
    answerType: "report_ready" | "report_updated";
    reportId?: string;
    templateInstanceId?: string;
    summary?: string;
    document?: {
      document_id?: string;
      file_name?: string;
      download_url?: string;
      [key: string]: unknown;
    };
  };
};

export function sendChatMessage(payload: ChatRequest) {
  return postJson<ChatResponse | ContractChatResponse>(chatbiPath("/chat"), toContractRequest(payload)).then((response) =>
    isLegacyChatResponse(response) ? response : fromContractResponse(response, payload),
  );
}

export function fetchChatSessions() {
  return requestJson<ChatSessionSummary[]>(chatbiPath("/chat"));
}

export function fetchChatSession(sessionId: string) {
  return requestJson<ChatSessionDetail>(chatbiPath(`/chat/${sessionId}`));
}

export function deleteChatSession(sessionId: string) {
  return deleteJson(chatbiPath(`/chat/${sessionId}`));
}

export function forkChatSession(payload: ChatForkRequest) {
  return postJson<ChatForkResponse>(chatbiPath("/chat/forks"), payload);
}

function toContractRequest(payload: ChatRequest): ContractChatRequest {
  const parameters = buildReplyParameters(payload);
  const commandName = mapLegacyCommand(payload.command);
  const instruction = mapInstruction(payload);
  return {
    conversationId: payload.session_id || undefined,
    chatId: buildChatId(),
    instruction,
    question: String(payload.message || ""),
    reply: parameters ? { type: "fill_params", parameters } : undefined,
    command: commandName ? { name: commandName } : undefined,
    selected_template_id: payload.selected_template_id,
    target_param_id: payload.target_param_id,
    outline_override: payload.outline_override,
  };
}

function buildReplyParameters(payload: ChatRequest): Record<string, unknown> | null {
  if (!payload.param_id) {
    return null;
  }
  if (payload.param_values && payload.param_values.length) {
    return { [payload.param_id]: payload.param_values };
  }
  return { [payload.param_id]: payload.param_value ?? "" };
}

function mapInstruction(payload: ChatRequest): ContractInstruction | undefined {
  if (payload.preferred_capability === "smart_query") {
    return "smart_query";
  }
  if (payload.preferred_capability === "fault_diagnosis") {
    return "fault_diagnosis";
  }
  if (
    payload.preferred_capability === "report_generation"
    || payload.param_id
    || payload.selected_template_id
    || payload.outline_override
    || payload.command
  ) {
    return "generate_report";
  }
  return undefined;
}

function mapLegacyCommand(command: ChatRequest["command"]): string {
  if (!command) {
    return "";
  }
  if (command === "confirm_outline_generation") {
    return "confirm_generate_report";
  }
  return command;
}

function buildChatId(): string {
  return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function isLegacyChatResponse(response: ChatResponse | ContractChatResponse): response is ChatResponse {
  return typeof (response as ChatResponse).session_id === "string";
}

function fromContractResponse(response: ContractChatResponse, source: ChatRequest): ChatResponse {
  const sessionId = String(response.conversationId || source.session_id || "");
  const askAction = mapAskToAction(response.ask);
  const answerAction = mapAnswerToAction(response.answer);
  const action: ChatAction | null = answerAction ?? askAction;
  return {
    session_id: sessionId,
    reply: pickReplyText(response),
    action,
    messages: [],
  };
}

function pickReplyText(response: ContractChatResponse): string {
  if (response.answer?.summary) {
    return response.answer.summary;
  }
  const ask = response.ask;
  if (!ask) {
    return "";
  }
  if (ask.mode === "chat" && ask.question) {
    return ask.question;
  }
  if (ask.type === "confirm_task_switch") {
    return String(ask.reason || "检测到任务切换请求，请确认。");
  }
  if (ask.type === "confirm") {
    return "参数已收集完成，请确认。";
  }
  if (ask.type === "confirm_outline") {
    return "参数已确认，请检查报告诉求。";
  }
  if (ask.type === "select_template") {
    return "请选择一个模板继续。";
  }
  return String(ask.title || "请继续补充信息。");
}

function mapAskToAction(ask: ContractChatResponse["ask"]): ChatAction | null {
  if (!ask) {
    return null;
  }
  if (ask.type === "fill_params" && ask.mode === "form") {
    const first = ask.parameters?.[0];
    if (!first?.id) {
      return null;
    }
    const options = (first.options || []).map((item) =>
      typeof item === "string" ? item : String(item.value || item.label || ""),
    ).filter(Boolean);
    const inputType = String(first.inputType || "free_text");
    return {
      type: "ask_param",
      param: {
        id: first.id,
        label: String(first.label || first.id),
        input_type: inputType,
        multi: Boolean(first.multi),
        options,
      },
      widget: {
        kind: resolveWidgetKind(inputType, Boolean(first.multi)),
      },
      selected_values: Array.isArray(first.value) ? (first.value as string[]) : (first.value ? [String(first.value)] : []),
    };
  }
  if (ask.type === "confirm") {
    return {
      type: "review_params",
      params: (ask.parameters || []).map((item) => ({
        id: String(item.id || ""),
        label: String(item.label || item.id || ""),
        value: Array.isArray(item.value) ? item.value.map((value) => String(value)) : String(item.value ?? ""),
        required: Boolean(item.required),
      })),
      missing_required: [],
    };
  }
  if (ask.type === "confirm_outline") {
    return {
      type: "review_outline",
      outline: Array.isArray(ask.outline) ? ask.outline as any[] : [],
      warnings: Array.isArray(ask.warnings) ? ask.warnings : [],
      params_snapshot: (ask.paramsSnapshot || []).map((item) => ({
        id: String(item.id || ""),
        label: String(item.label || item.id || ""),
        value: Array.isArray(item.value) ? item.value.map((value) => String(value)) : String(item.value ?? ""),
      })),
    };
  }
  if (ask.type === "select_template") {
    return {
      type: "show_template_candidates",
      candidates: Array.isArray(ask.candidates) ? ask.candidates as any[] : [],
    };
  }
  if (ask.type === "confirm_task_switch") {
    return {
      type: "confirm_task_switch",
      reason: String(ask.reason || ""),
      from_capability: normalizeCapability(ask.fromCapability),
      to_capability: normalizeCapability(ask.toCapability),
    };
  }
  return null;
}

function mapAnswerToAction(answer: ContractChatResponse["answer"]): ChatAction | null {
  if (!answer || answer.answerType !== "report_ready") {
    return null;
  }
  return {
    type: "download_document",
    report_id: answer.reportId ? String(answer.reportId) : undefined,
    template_instance_id: answer.templateInstanceId ? String(answer.templateInstanceId) : undefined,
    document: {
      document_id: String(answer.document?.document_id || ""),
      file_name: answer.document?.file_name ? String(answer.document.file_name) : undefined,
      download_url: answer.document?.download_url ? String(answer.document.download_url) : undefined,
    },
  };
}

function resolveWidgetKind(inputType: string, multi: boolean): "text" | "date" | "single_select" | "multi_select" {
  if (inputType === "date") {
    return "date";
  }
  if (multi) {
    return "multi_select";
  }
  if (inputType === "enum" || inputType === "dynamic") {
    return "single_select";
  }
  return "text";
}

function normalizeCapability(value: unknown): "report_generation" | "smart_query" | "fault_diagnosis" {
  if (value === "smart_query" || value === "fault_diagnosis") {
    return value;
  }
  return "report_generation";
}

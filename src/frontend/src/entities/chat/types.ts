export type ChatCandidate = {
  template_id: string;
  template_name: string;
  scenario?: string;
  description?: string;
  report_type?: string;
  template_type?: string;
  score?: number;
  score_label?: string;
  match_reasons?: string[];
};

export type AskParamAction = {
  type: "ask_param";
  template_name?: string;
  param: {
    id: string;
    label: string;
    input_type?: string;
    multi?: boolean;
    options?: string[];
  };
  widget: {
    kind: "text" | "date" | "single_select" | "multi_select";
  };
  selected_values?: string[];
  progress?: {
    collected: number;
    required: number;
  };
};

export type ReviewParamsAction = {
  type: "review_params";
  template_id?: string;
  template_name?: string;
  params: Array<{
    id: string;
    label: string;
    value: string | string[];
    required: boolean;
  }>;
  missing_required: string[];
};

export type OutlineNode = {
  node_id: string;
  title: string;
  description: string;
  level: number;
  children: OutlineNode[];
  outline_mode?: "structured" | "freeform";
  dynamic_meta?: Record<string, unknown>;
  display_text?: string;
  ai_generated?: boolean;
  node_kind?: "group" | "structured_leaf" | "freeform_leaf";
  requirement_instance?: {
    requirement_template?: string;
    rendered_requirement?: string;
    segments?: Array<
      | { kind: "text"; text: string }
      | { kind: "slot"; slot_id: string; slot_type?: string; value?: string }
    >;
    slots?: Array<{
      id: string;
      type?: string;
      hint?: string;
      value?: string;
      default?: string;
      param_id?: string;
      widget?: string;
      source?: string;
      options?: string[];
    }>;
  };
  execution_bindings?: Array<{
    slot_id: string;
    targets: string[];
  }>;
};

export type ReviewOutlineAction = {
  type: "review_outline";
  template_id?: string;
  template_name?: string;
  outline: OutlineNode[];
  warnings: string[];
  params_snapshot: Array<{
    id: string;
    label: string;
    value: string | string[];
  }>;
};

export type ShowTemplateCandidatesAction = {
  type: "show_template_candidates";
  selected_template_id?: string;
  candidates: ChatCandidate[];
};

export type DownloadDocumentAction = {
  type: "download_document";
  document: {
    document_id: string;
    file_name?: string;
    download_url?: string;
  };
};

export type ConfirmTaskSwitchAction = {
  type: "confirm_task_switch";
  from_capability: "report_generation" | "smart_query" | "fault_diagnosis";
  to_capability: "report_generation" | "smart_query" | "fault_diagnosis";
  reason: string;
};

export type ChatAction =
  | AskParamAction
  | ReviewParamsAction
  | ReviewOutlineAction
  | ShowTemplateCandidatesAction
  | DownloadDocumentAction
  | ConfirmTaskSwitchAction;

export type ChatForkMeta = {
  source_kind: "session_message" | "template_instance" | "update_from_instance";
  source_title: string;
  source_preview: string;
  source_session_id?: string;
  source_message_id?: string;
  source_template_instance_id?: string;
  source_report_instance_id?: string;
};

export type ChatSessionPayload = {
  session_id: string;
  title?: string;
  matched_template_id?: string | null;
  fork_meta?: ChatForkMeta | null;
  draft_message?: string;
  messages: Array<{
    role: "user" | "assistant";
    content: string;
    action?: ChatAction | null;
    created_at?: string;
    message_id?: string;
    meta?: unknown;
  }>;
};

export type ChatMessageItem = {
  role: "user" | "assistant";
  content: string;
  action?: ChatAction | null;
  created_at?: string;
  message_id?: string;
};

export type ChatSessionSummary = {
  session_id: string;
  title: string;
  created_at?: string | null;
  updated_at?: string | null;
  message_count: number;
  last_message_preview: string;
  matched_template_id?: string | null;
  fork_meta?: ChatForkMeta | null;
};

export type ChatSessionDetail = {
  session_id: string;
  title?: string;
  matched_template_id?: string | null;
  fork_meta?: ChatForkMeta | null;
  messages: ChatSessionPayload["messages"];
};
export type ChatResponse = {
  session_id: string;
  reply: string;
  title?: string;
  action?: ChatAction | null;
  matched_template_id?: string | null;
  fork_meta?: ChatForkMeta | null;
  messages?: ChatSessionPayload["messages"];
};

export type ChatForkResponse = {
  session_id: string;
  title: string;
  matched_template_id?: string | null;
  messages: ChatSessionPayload["messages"];
  draft_message?: string;
  fork_meta?: ChatForkMeta | null;
};

export type ChatRequest = {
  message?: string;
  session_id?: string;
  preferred_capability?: "report_generation" | "smart_query" | "fault_diagnosis";
  selected_template_id?: string;
  param_id?: string;
  param_value?: string;
  param_values?: string[];
  command?:
    | "prepare_outline_review"
    | "edit_outline"
    | "confirm_outline_generation"
    | "confirm_generation"
    | "reset_params"
    | "edit_param"
    | "confirm_task_switch"
    | "cancel_task_switch";
  target_param_id?: string;
  outline_override?: OutlineNode[];
};

export type ChatForkRequest = {
  source_kind: "session_message" | "template_instance";
  source_session_id?: string;
  source_message_id?: string;
  template_instance_id?: string;
};

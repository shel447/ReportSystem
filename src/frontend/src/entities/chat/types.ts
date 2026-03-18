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

export type ChatAction =
  | AskParamAction
  | ReviewParamsAction
  | ShowTemplateCandidatesAction
  | DownloadDocumentAction;

export type ChatMessageItem = {
  role: "user" | "assistant";
  content: string;
  action?: ChatAction | null;
};

export type ChatResponse = {
  session_id: string;
  reply: string;
  action?: ChatAction | null;
  matched_template_id?: string | null;
  messages?: Array<{
    role: "user" | "assistant";
    content: string;
    action?: ChatAction | null;
    meta?: unknown;
  }>;
};

export type ChatRequest = {
  message?: string;
  session_id?: string;
  selected_template_id?: string;
  param_id?: string;
  param_value?: string;
  param_values?: string[];
  command?: "confirm_generation" | "reset_params" | "edit_param";
  target_param_id?: string;
};

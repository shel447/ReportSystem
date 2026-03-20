export type InstanceSection = {
  title: string;
  description?: string;
  content?: string;
  status?: string;
  data_status?: string;
  generated_at?: string;
  debug?: {
    nl_request?: string;
    ibis_code?: string;
    compiled_sql?: string;
    attempts?: number;
    row_count?: number;
    sample_rows?: unknown[];
    error_message?: string;
    datasets?: unknown[];
    render_bindings?: unknown;
  };
};

export type InstanceBaselineNode = {
  node_id: string;
  title: string;
  description?: string;
  display_text?: string;
  level: number;
  children: InstanceBaselineNode[];
};

export type InstanceBaseline = {
  instance_id: string;
  template_id: string;
  template_name: string;
  params_snapshot: Record<string, unknown>;
  outline: InstanceBaselineNode[];
  warnings?: string[];
  created_at?: string;
};

export type InstanceForkSource = {
  message_id: string;
  role: string;
  preview: string;
  created_at?: string;
  action_type?: string | null;
};

export type ReportInstance = {
  instance_id: string;
  template_id: string;
  status: string;
  input_params: Record<string, unknown>;
  outline_content: InstanceSection[];
  created_at?: string;
  updated_at?: string;
  has_generation_baseline?: boolean;
  supports_update_chat?: boolean;
  supports_fork_chat?: boolean;
};

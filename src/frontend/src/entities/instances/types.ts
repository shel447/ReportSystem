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

export type ReportInstance = {
  instance_id: string;
  template_id: string;
  status: string;
  input_params: Record<string, unknown>;
  outline_content: InstanceSection[];
  created_at?: string;
  updated_at?: string;
};

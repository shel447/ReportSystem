export type ReportView = {
  reportId: string;
  status: string;
  template_instance: {
    id: string;
    schema_version?: string;
    instance_meta?: {
      status?: string;
      revision?: number;
      created_at?: string | null;
    };
    base_template?: {
      id?: string;
      name?: string;
      category?: string;
      description?: string;
    };
    runtime_state?: Record<string, unknown>;
    resolved_view?: {
      parameters?: Record<string, unknown>;
      outline?: unknown[];
      sections?: unknown[];
      [key: string]: unknown;
    };
    fragments?: Record<string, unknown>;
  };
  generated_content: {
    sections?: unknown[];
    documents?: Array<{ format?: string; download_url?: string; [key: string]: unknown }>;
    [key: string]: unknown;
  };
};

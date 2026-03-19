export type TemplateInstanceSummary = {
  template_instance_id: string;
  template_id: string;
  template_name: string;
  session_id: string;
  capture_stage: "outline_saved" | "outline_confirmed";
  report_instance_id?: string | null;
  param_count: number;
  outline_node_count: number;
  outline_preview: string[];
  created_at?: string;
};

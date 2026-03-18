export type ScheduledTask = {
  task_id: string;
  user_id: string;
  name: string;
  description: string;
  source_instance_id: string;
  template_id: string;
  schedule_type: string;
  cron_expression: string;
  enabled: boolean;
  auto_generate_doc: boolean;
  status: string;
  total_runs: number;
  success_runs: number;
  last_run_at?: string | null;
  created_at?: string;
};

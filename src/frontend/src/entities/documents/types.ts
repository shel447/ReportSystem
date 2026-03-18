export type ReportDocument = {
  document_id: string;
  instance_id: string;
  template_id: string;
  format: string;
  file_path: string;
  file_name: string;
  file_size: number;
  status: string;
  version: number;
  download_url: string;
  created_at?: string;
};

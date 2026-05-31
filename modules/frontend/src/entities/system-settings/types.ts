export type ProviderSettings = {
  base_url: string;
  model: string;
  timeout_sec: number;
  temperature?: number;
  has_api_key: boolean;
  masked_api_key: string;
  configured: boolean;
  use_completion_auth?: boolean;
};

export type SystemSettingsPayload = {
  completion: ProviderSettings;
  embedding: ProviderSettings;
  is_ready: boolean;
  index_status?: {
    ready_count?: number;
    stale_count?: number;
    error_count?: number;
    total_count?: number;
  };
};

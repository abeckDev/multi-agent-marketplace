/**
 * Service for interacting with the orchestrator API endpoints.
 * Provides methods for managing experiments, datasets, and settings.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export interface DatasetInfo {
  name: string;
  path: string;
  num_businesses: number;
  num_customers: number;
}

export interface ExperimentCreate {
  dataset: string;
  experiment_name?: string;
  search_algorithm?: string;
  search_bandwidth?: number;
  customer_max_steps?: number;
  postgres_host?: string;
  postgres_port?: number;
  postgres_password?: string;
  db_pool_min_size?: number;
  db_pool_max_size?: number;
  server_host?: string;
  server_port?: number;
  override?: boolean;
  export_sqlite?: boolean;
  export_dir?: string;
  export_filename?: string;
}

export interface ExperimentStatus {
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface ExperimentInfo {
  schema_name: string;
  first_activity: string | null;
  last_activity: string | null;
  agents_count: number;
  actions_count: number;
  logs_count: number;
  llm_providers: string[];
}

export interface SettingsResponse {
  default_search_algorithm: string;
  default_search_bandwidth: number;
  default_postgres_host: string;
  default_postgres_port: number;
  available_providers: string[];
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string | null;
  data: Record<string, unknown> | null;
  agent_id: string | null;
}

export interface LogsResponse {
  logs: LogEntry[];
  total: number;
  has_more: boolean;
}

class OrchestratorService {
  private async fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    return response.json();
  }

  /**
   * Get list of available datasets
   */
  async getDatasets(): Promise<DatasetInfo[]> {
    return this.fetchJson<DatasetInfo[]>(`${API_BASE_URL}/datasets`);
  }

  /**
   * Get current settings and available models
   */
  async getSettings(): Promise<SettingsResponse> {
    return this.fetchJson<SettingsResponse>(`${API_BASE_URL}/settings`);
  }

  /**
   * Create and launch a new experiment
   */
  async createExperiment(config: ExperimentCreate): Promise<ExperimentStatus> {
    return this.fetchJson<ExperimentStatus>(`${API_BASE_URL}/experiments`, {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  /**
   * Get status of a specific experiment
   */
  async getExperimentStatus(name: string): Promise<ExperimentStatus> {
    return this.fetchJson<ExperimentStatus>(
      `${API_BASE_URL}/experiments/${encodeURIComponent(name)}/status`,
    );
  }

  /**
   * Get list of all experiments
   */
  async getExperiments(params?: {
    limit?: number;
    host?: string;
    port?: number;
    database?: string;
    user?: string;
    password?: string;
  }): Promise<ExperimentInfo[]> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.host) queryParams.append("host", params.host);
    if (params?.port) queryParams.append("port", params.port.toString());
    if (params?.database) queryParams.append("database", params.database);
    if (params?.user) queryParams.append("user", params.user);
    if (params?.password) queryParams.append("password", params.password);

    const url = queryParams.toString()
      ? `${API_BASE_URL}/experiments?${queryParams}`
      : `${API_BASE_URL}/experiments`;

    return this.fetchJson<ExperimentInfo[]>(url);
  }

  /**
   * Get logs for a specific experiment (REST polling)
   */
  async getExperimentLogs(
    name: string,
    params?: {
      since?: string;
      limit?: number;
      host?: string;
      port?: number;
      database?: string;
      user?: string;
      password?: string;
    },
  ): Promise<LogsResponse> {
    const queryParams = new URLSearchParams();
    if (params?.since) queryParams.append("since", params.since);
    if (params?.limit) queryParams.append("limit", params.limit.toString());
    if (params?.host) queryParams.append("host", params.host);
    if (params?.port) queryParams.append("port", params.port.toString());
    if (params?.database) queryParams.append("database", params.database);
    if (params?.user) queryParams.append("user", params.user);
    if (params?.password) queryParams.append("password", params.password);

    const qs = queryParams.toString();
    const url = qs
      ? `${API_BASE_URL}/experiments/${encodeURIComponent(name)}/logs?${qs}`
      : `${API_BASE_URL}/experiments/${encodeURIComponent(name)}/logs`;

    return this.fetchJson<LogsResponse>(url);
  }
}

export const orchestratorService = new OrchestratorService();

const API_BASE = "/api/hooks";

async function fetchApi(endpoint: string, options?: RequestInit): Promise<any> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export interface Hook {
  id: string;
  name: string;
  trigger_type: string;
  hook_type: string;
  config: Record<string, any>;
  code: string | null;
  is_active: boolean;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface HookExecution {
  id: string;
  hook_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  result: string | null;
}

export const hooksApi = {
  async getHooks(): Promise<Hook[]> {
    return fetchApi("/");
  },

  async getHook(hookId: string): Promise<Hook> {
    return fetchApi(`/${hookId}`);
  },

  async createHook(data: Partial<Hook>): Promise<Hook> {
    return fetchApi("/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateHook(hookId: string, data: Partial<Hook>): Promise<Hook> {
    return fetchApi(`/${hookId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async deleteHook(hookId: string): Promise<void> {
    return fetchApi(`/${hookId}`, { method: "DELETE" });
  },

  async executeHook(hookId: string): Promise<HookExecution> {
    return fetchApi(`/${hookId}/execute`, { method: "POST" });
  },

  async getHookExecutions(hookId: string): Promise<HookExecution[]> {
    return fetchApi(`/${hookId}/executions`);
  },

  async getExecutions(): Promise<HookExecution[]> {
    return fetchApi("/executions");
  },
};
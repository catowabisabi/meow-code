const API_BASE = "/api/admin";

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

export const adminApi = {
  async getUsers(page: number = 1): Promise<{ items: any[]; total: number }> {
    return fetchApi(`/users?page=${page}&limit=10`);
  },

  async updateUser(userId: string, data: Record<string, any>): Promise<void> {
    return fetchApi(`/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteUser(userId: string): Promise<void> {
    return fetchApi(`/users/${userId}`, { method: "DELETE" });
  },

  async getRoles(): Promise<any[]> {
    return fetchApi("/roles");
  },

  async createRole(data: { name: string; description?: string; permissions?: string[] }): Promise<void> {
    return fetchApi("/roles", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateRole(roleId: string, data: Record<string, any>): Promise<void> {
    return fetchApi(`/roles/${roleId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteRole(roleId: string): Promise<void> {
    return fetchApi(`/roles/${roleId}`, { method: "DELETE" });
  },

  async getDepartments(): Promise<any[]> {
    return fetchApi("/departments");
  },

  async createDepartment(data: { name: string; description?: string; parent_id?: string }): Promise<void> {
    return fetchApi("/departments", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getTeams(): Promise<any[]> {
    return fetchApi("/teams");
  },

  async createTeam(data: { name: string; department_id: string }): Promise<void> {
    return fetchApi("/teams", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
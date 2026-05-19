const API_BASE = "/api/git";

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

export const gitService = {
  async getStatus() {
    return fetchApi("/status");
  },

  async stage(files: string[]) {
    return fetchApi("/stage", {
      method: "POST",
      body: JSON.stringify({ files }),
    });
  },

  async unstage(files: string[]) {
    return fetchApi("/unstage", {
      method: "POST",
      body: JSON.stringify({ files }),
    });
  },

  async commit(message: string) {
    return fetchApi("/commit", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
  },

  async getLog(maxCount: number = 50) {
    return fetchApi(`/log?max_count=${maxCount}`);
  },

  async getDiff(filePath?: string, staged: boolean = false) {
    const params = new URLSearchParams();
    if (filePath) params.set("file_path", filePath);
    if (staged) params.set("staged", "true");
    return fetchApi(`/diff?${params}`);
  },

  async getBranches() {
    return fetchApi("/branches");
  },

  async checkout(branch: string) {
    return fetchApi("/checkout", {
      method: "POST",
      body: JSON.stringify({ branch }),
    });
  },

  async createBranch(name: string, fromBranch?: string) {
    return fetchApi("/branch", {
      method: "POST",
      body: JSON.stringify({ name, from_branch: fromBranch }),
    });
  },
};
const API_BASE = "/api/debugger";

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

export const debuggerService = {
  async startDebugger(url: string = "http://localhost:9222") {
    return fetchApi("/start", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  },

  async attachToTab(tabId: string) {
    return fetchApi("/attach", {
      method: "POST",
      body: JSON.stringify({ tab_id: tabId }),
    });
  },

  async setBreakpoint(source: string, line: number, condition?: string) {
    return fetchApi("/breakpoint", {
      method: "POST",
      body: JSON.stringify({ source, line, condition }),
    });
  },

  async removeBreakpoint(breakpointId: string) {
    return fetchApi(`/breakpoint/${breakpointId}`, { method: "DELETE" });
  },

  async getBreakpoints() {
    return fetchApi("/breakpoints");
  },

  async resume() {
    return fetchApi("/resume", { method: "POST" });
  },

  async pause() {
    return fetchApi("/pause", { method: "POST" });
  },

  async stepOver() {
    return fetchApi("/step/over", { method: "POST" });
  },

  async stepInto() {
    return fetchApi("/step/into", { method: "POST" });
  },

  async stepOut() {
    return fetchApi("/step/out", { method: "POST" });
  },

  async evaluate(expression: string, frameId?: string) {
    return fetchApi("/evaluate", {
      method: "POST",
      body: JSON.stringify({ expression, frame_id: frameId }),
    });
  },

  async getStackTrace() {
    return fetchApi("/stack");
  },

  async getVariables(frameId?: string) {
    const params = frameId ? `?frame_id=${frameId}` : "";
    return fetchApi(`/variables${params}`);
  },

  async stop() {
    return fetchApi("/stop", { method: "POST" });
  },
};

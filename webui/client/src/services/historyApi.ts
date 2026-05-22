const API_BASE = "/api/history";

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

export interface HistoryMessageResponse {
  message: {
    id: number;
    session_id: string;
    role: string;
    content: string;
    token_count: number;
    created_at: string;
    edited: boolean;
    edit_history: string[];
    deleted_at: string | null;
  };
  annotations: Array<{
    id: number;
    message_id: number;
    type: string;
    content: string;
    metadata: Record<string, any>;
    created_at: string;
  }>;
}

export interface Annotation {
  id: number;
  message_id: number;
  type: string;
  content: string;
  metadata: Record<string, any>;
  created_at: string;
}

export const historyApi = {
  async getMessage(messageId: number): Promise<HistoryMessageResponse> {
    return fetchApi(`/messages/${messageId}`);
  },

  async updateMessage(messageId: number, content: string): Promise<{ message: any }> {
    return fetchApi(`/messages/${messageId}`, {
      method: "PATCH",
      body: JSON.stringify({ content }),
    });
  },

  async deleteMessage(messageId: number): Promise<{ ok: boolean }> {
    return fetchApi(`/messages/${messageId}`, { method: "DELETE" });
  },

  async createAnnotation(messageId: number, type: string, content: string, metadata?: Record<string, any>): Promise<Annotation> {
    return fetchApi(`/messages/${messageId}/annotations`, {
      method: "POST",
      body: JSON.stringify({ type, content, metadata }),
    });
  },

  async getAnnotations(messageId: number): Promise<Annotation[]> {
    return fetchApi(`/messages/${messageId}/annotations`);
  },

  async undoDelete(sessionId: string): Promise<{ message: any }> {
    return fetchApi(`/sessions/${sessionId}/undo`, { method: "POST" });
  },
};
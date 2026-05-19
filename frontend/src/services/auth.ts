const API_BASE = "/api";

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    username: string;
    full_name: string | null;
    avatar_url: string | null;
    is_active: boolean;
    is_superuser: boolean;
  };
}

async function fetchApi(endpoint: string, options?: RequestInit): Promise<any> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options?.headers,
  };
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export const authService = {
  async login(username: string, password: string): Promise<AuthResponse> {
    return fetchApi("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  async register(
    email: string,
    username: string,
    password: string,
    fullName?: string
  ): Promise<AuthResponse> {
    return fetchApi("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, username, password, full_name: fullName }),
    });
  },

  async refresh(refreshToken: string): Promise<AuthResponse> {
    return fetchApi("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async getMe(): Promise<AuthResponse["user"]> {
    const response = await fetchApi("/auth/me");
    return response;
  },

  async logout(): Promise<void> {
    return fetchApi("/auth/logout", { method: "POST" });
  },
};
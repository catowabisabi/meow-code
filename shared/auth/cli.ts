import { writeFile, readFile, unlink, mkdir } from "fs/promises";
import { existsSync } from "fs";
import path from "path";

const AUTH_DIR = path.join(process.env.HOME || "~", ".cato");
const AUTH_FILE = path.join(AUTH_DIR, "auth.json");
const API_BASE = "/api";

export interface AuthUser {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_superuser: boolean;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

async function ensureAuthDir(): Promise<void> {
  if (!existsSync(AUTH_DIR)) {
    await mkdir(AUTH_DIR, { recursive: true });
  }
}

async function saveTokens(tokens: TokenResponse): Promise<void> {
  await ensureAuthDir();
  await writeFile(AUTH_FILE, JSON.stringify(tokens, null, 2), "utf-8");
}

async function loadTokens(): Promise<TokenResponse | null> {
  try {
    const data = await readFile(AUTH_FILE, "utf-8");
    return JSON.parse(data) as TokenResponse;
  } catch {
    return null;
  }
}

async function clearTokens(): Promise<void> {
  try {
    await unlink(AUTH_FILE);
  } catch {
    // File doesn't exist, already cleared
  }
}

async function fetchApi(
  endpoint: string,
  options?: RequestInit
): Promise<any> {
  const tokens = await loadTokens();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(tokens?.access_token
      ? { Authorization: `Bearer ${tokens.access_token}` }
      : {}),
    ...options?.headers,
  };
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: "Request failed",
    }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

export async function authLogin(
  username: string,
  password: string
): Promise<AuthUser> {
  const response = await fetchApi("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  await saveTokens(response as TokenResponse);
  return (response as TokenResponse).user;
}

export async function performLogout(): Promise<void> {
  try {
    await fetchApi("/auth/logout", { method: "POST" });
  } finally {
    await clearTokens();
  }
}

export async function authStatus(): Promise<AuthUser | null> {
  try {
    const response = await fetchApi("/auth/me");
    return response as AuthUser;
  } catch (err) {
    if (err instanceof Error && err.message === "Unauthorized") {
      return null;
    }
    throw err;
  }
}
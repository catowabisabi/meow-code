import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";

const mockFetch = vi.fn();
const mockWriteFile = vi.fn();
const mockReadFile = vi.fn();
const mockUnlink = vi.fn();
const mockExistsSync = vi.fn();
const mockMkdir = vi.fn();

vi.mock("fs/promises", () => ({
  writeFile: mockWriteFile,
  readFile: mockReadFile,
  unlink: mockUnlink,
  mkdir: mockMkdir,
}));

vi.mock("fs", () => ({
  existsSync: mockExistsSync,
}));

global.fetch = mockFetch;

describe("authLogin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExistsSync.mockReturnValue(true);
    mockReadFile.mockRejectedValue(new Error("ENOENT"));
  });

  it("calls POST /auth/login and saves tokens on success", async () => {
    const { authLogin } = await import("./cli");
    const mockUser = {
      id: "user-123",
      email: "test@example.com",
      username: "testuser",
      full_name: "Test User",
      avatar_url: null,
      is_active: true,
      is_superuser: false,
    };
    const mockResponse = {
      access_token: "access-token-abc",
      refresh_token: "refresh-token-xyz",
      token_type: "bearer",
      user: mockUser,
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await authLogin("testuser", "password123");

    expect(mockFetch).toHaveBeenCalledWith("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: "testuser", password: "password123" }),
      headers: { "Content-Type": "application/json" },
    });
    expect(mockWriteFile).toHaveBeenCalled();
    expect(result).toEqual(mockUser);
  });

  it("throws error on failed login", async () => {
    const { authLogin } = await import("./cli");
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Invalid credentials" }),
    });

    await expect(authLogin("baduser", "badpass")).rejects.toThrow(
      "Invalid credentials"
    );
  });
});

describe("performLogout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExistsSync.mockReturnValue(true);
  });

  it("calls POST /auth/logout and clears tokens", async () => {
    const { performLogout } = await import("./cli");
    const storedTokens = {
      access_token: "access-token-abc",
      refresh_token: "refresh-token-xyz",
      token_type: "bearer",
      user: {
        id: "user-123",
        email: "test@example.com",
        username: "testuser",
        full_name: "Test User",
        avatar_url: null,
        is_active: true,
        is_superuser: false,
      },
    };
    mockReadFile.mockResolvedValue(JSON.stringify(storedTokens));
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ message: "Logged out" }),
    });

    await performLogout();

    expect(mockFetch).toHaveBeenCalledWith("/api/auth/logout", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer access-token-abc",
      },
    });
    expect(mockUnlink).toHaveBeenCalled();
  });
});

describe("authStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExistsSync.mockReturnValue(true);
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("returns AuthUser when authenticated", async () => {
    const { authStatus } = await import("./cli");
    const mockUser = {
      id: "user-123",
      email: "test@example.com",
      username: "testuser",
      full_name: "Test User",
      avatar_url: null,
      is_active: true,
      is_superuser: false,
    };
    const storedTokens = {
      access_token: "access-token-abc",
      refresh_token: "refresh-token-xyz",
      token_type: "bearer",
      user: mockUser,
    };
    mockReadFile.mockResolvedValue(JSON.stringify(storedTokens));
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockUser),
    });

    const result = await authStatus();

    expect(mockFetch).toHaveBeenCalledWith("/api/auth/me", {
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer access-token-abc",
      },
    });
    expect(result).toEqual(mockUser);
  });

  it("returns null on 401 response", async () => {
    const { authStatus } = await import("./cli");
    const storedTokens = {
      access_token: "access-token-abc",
      refresh_token: "refresh-token-xyz",
      token_type: "bearer",
      user: {
        id: "user-123",
        email: "test@example.com",
        username: "testuser",
        full_name: "Test User",
        avatar_url: null,
        is_active: true,
        is_superuser: false,
      },
    };
    mockReadFile.mockResolvedValue(JSON.stringify(storedTokens));
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Unauthorized" }),
    });

    const result = await authStatus();

    expect(result).toBeNull();
  });

  it("returns null when no token file exists", async () => {
    const { authStatus } = await import("./cli");
    mockExistsSync.mockReturnValue(false);
    mockReadFile.mockRejectedValue(new Error("ENOENT"));
    mockFetch.mockResolvedValue({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Unauthorized" }),
    });

    const result = await authStatus();

    expect(result).toBeNull();
  });

  it("throws error on non-401 errors", async () => {
    const { authStatus } = await import("./cli");
    const storedTokens = {
      access_token: "access-token-abc",
      refresh_token: "refresh-token-xyz",
      token_type: "bearer",
      user: {
        id: "user-123",
        email: "test@example.com",
        username: "testuser",
        full_name: "Test User",
        avatar_url: null,
        is_active: true,
        is_superuser: false,
      },
    };
    mockReadFile.mockResolvedValue(JSON.stringify(storedTokens));
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ detail: "Internal server error" }),
    });

    await expect(authStatus()).rejects.toThrow("Internal server error");
  });
});
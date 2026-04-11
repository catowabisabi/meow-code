import { api } from './client'

// ─── Types ───────────────────────────────────────────────────

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: ContentBlock[]
  model?: string
  provider?: string
  timestamp: number
  streaming?: boolean
  usage?: { inputTokens: number; outputTokens: number }
}

export interface ContentBlock {
  type: 'text' | 'thinking' | 'tool_use' | 'tool_result' | 'image'
  text?: string
  id?: string
  name?: string
  input?: Record<string, unknown>
  tool_use_id?: string
  content?: string
  is_error?: boolean
}

export interface SessionSummary {
  id: string
  title: string
  mode: string
  folder: string | null
  model: string
  updatedAt: number
}

export interface StoredSession {
  id: string
  title: string
  mode: string
  folder: string | null
  model: string
  provider: string
  messages: Array<{ role: string; content: unknown }>
  createdAt: number
  updatedAt: number
}

// ─── Sessions API ─────────────────────────────────────────────

export const sessionsAPI = {
  list(limit?: number): Promise<SessionSummary[]> {
    const params = limit ? `?limit=${limit}` : ''
    return api.get<SessionSummary[]>(`/api/sessions${params}`)
  },

  get(id: string): Promise<StoredSession> {
    return api.get<StoredSession>(`/api/sessions/${id}`)
  },

  delete(id: string): Promise<void> {
    return api.delete<void>(`/api/sessions/${id}`)
  },

  updateTitle(id: string, title: string): Promise<void> {
    return api.put<void>(`/api/sessions/${id}/title`, { title })
  },

  save(id: string, metadata?: Record<string, unknown>): Promise<{ ok: boolean; id: string }> {
    return api.post(`/api/sessions/${id}/save`, { metadata })
  },

  create(messages: Array<{ role: string; content: unknown }>, model?: string, provider?: string): Promise<{ id: string }> {
    return api.post(`/api/sessions`, { messages, model, provider })
  },

  listStored(limit?: number): Promise<{ sessions: SessionSummary[] }> {
    const params = limit ? `?limit=${limit}` : ''
    return api.get(`/api/sessions/stored/list${params}`)
  },

  getTags(id: string): Promise<{ session_id: string; tag: string | null; updated_at: number | null }> {
    return api.get(`/api/sessions/${id}/tag`)
  },

  addTag(id: string, tag: string): Promise<{ session_id: string; tag: string; updated_at: number }> {
    return api.post(`/api/sessions/${id}/tag`, { tag })
  },

  removeTag(id: string): Promise<{ ok: boolean }> {
    return api.delete(`/api/sessions/${id}/tag`)
  },
}

// ─── Models API ───────────────────────────────────────────────

export interface ProviderInfo {
  type: string
  displayName?: string
  baseUrl: string
  apiKey: string
  models: string[]
  enabled: boolean
  customHeaders?: Record<string, string>
}

export interface AvailableModel {
  providerId: string
  providerName: string
  model: string
  type: string
}

export const modelsAPI = {
  list(): Promise<{
    providers: Record<string, ProviderInfo>
    availableModels: AvailableModel[]
    hotkeys: Array<{ key: string; model: string; provider: string }>
    defaultModel: string
    defaultProvider: string
  }> {
    return api.get('/api/models')
  },

  add(id: string, config: Partial<ProviderInfo> & { type: string; baseUrl: string }): Promise<{ providers: Record<string, ProviderInfo> }> {
    return api.post('/api/models', { id, ...config })
  },

  update(id: string, updates: Partial<ProviderInfo>): Promise<{ provider: ProviderInfo }> {
    return api.put(`/api/models/${id}`, updates)
  },

  remove(id: string): Promise<{ providers: Record<string, ProviderInfo> }> {
    return api.delete(`/api/models/${id}`)
  },

  test(id: string): Promise<{ ok: boolean; error?: string; latencyMs?: number }> {
    return api.post(`/api/models/${id}/test`)
  },

  setDefault(model: string, provider: string): Promise<void> {
    return api.put('/api/models/default', { model, provider })
  },

  updateHotkeys(hotkeys: Array<{ key: string; model: string; provider: string }>): Promise<void> {
    return api.put('/api/models/hotkeys', { hotkeys })
  },
}

// ─── Settings API ─────────────────────────────────────────────

export interface Settings {
  theme?: string
  fontSize?: number
  permissionMode?: 'ask' | 'always-allow' | 'auto-approve'
  autoTitle?: boolean
  thinkingEnabled?: boolean
  [key: string]: unknown
}

export const settingsAPI = {
  get(): Promise<Settings> {
    return api.get<Settings>('/api/settings')
  },

  update(settings: Partial<Settings>): Promise<Settings> {
    return api.patch<Settings>('/api/settings', settings)
  },
}

// ─── Files API ────────────────────────────────────────────────

export interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
}

export const filesAPI = {
  list(path: string): Promise<FileNode[]> {
    const encoded = encodeURIComponent(path)
    return api.get<FileNode[]>(`/api/files?path=${encoded}`)
  },

  read(path: string): Promise<string> {
    const encoded = encodeURIComponent(path)
    return api.get<string>(`/api/files/read?path=${encoded}`)
  },

  write(path: string, content: string): Promise<{ ok: boolean; path: string }> {
    return api.post('/api/files/write', { path, content })
  },
}

// ─── Shell API ────────────────────────────────────────────────

export interface ShellResult {
  stdout: string
  stderr: string
  exitCode: number
}

export const shellAPI = {
  execute(command: string, cwd?: string): Promise<ShellResult> {
    return api.post<ShellResult>('/api/shell', { command, cwd })
  },

  getCwd(): Promise<{ cwd: string }> {
    return api.get('/api/shell/cwd')
  },
}

// ─── Skills API ───────────────────────────────────────────────

export interface Skill {
  name: string
  description: string
  enabled: boolean
  builtin: boolean
  config?: Record<string, unknown>
}

export const skillsAPI = {
  list(): Promise<Skill[]> {
    return api.get<Skill[]>('/api/skills')
  },

  add(skill: Omit<Skill, 'builtin'>): Promise<Skill> {
    return api.post<Skill>('/api/skills', skill)
  },

  update(name: string, updates: Partial<Skill>): Promise<Skill> {
    return api.put<Skill>(`/api/skills/${encodeURIComponent(name)}`, updates)
  },

  remove(name: string): Promise<void> {
    return api.delete<void>(`/api/skills/${encodeURIComponent(name)}`)
  },

  enable(name: string): Promise<void> {
    return api.patch<void>(`/api/skills/${encodeURIComponent(name)}/enable`)
  },

  disable(name: string): Promise<void> {
    return api.patch<void>(`/api/skills/${encodeURIComponent(name)}/disable`)
  },

  execute(name: string, args?: string, cwd?: string, context?: Record<string, unknown>): Promise<{
    skillName: string
    systemPrompt: string
    success: boolean
    error?: string
    output?: string
  }> {
    return api.post('/api/skills/execute', { name, args, cwd, context })
  },

  load(path?: string): Promise<{
    ok: boolean
    loaded_count: number
    skill_names: string[]
  }> {
    return api.post('/api/skills/load', { path })
  },
}

// ─── Memory API ───────────────────────────────────────────────

export interface MemoryEntry {
  id: string
  content: string
  type: string
  createdAt: number
  tags?: string[]
}

export const memoryAPI = {
  list(): Promise<MemoryEntry[]> {
    return api.get<MemoryEntry[]>('/api/memory')
  },

  add(entry: Omit<MemoryEntry, 'id' | 'createdAt'>): Promise<MemoryEntry> {
    return api.post<MemoryEntry>('/api/memory', entry)
  },

  search(query: string): Promise<MemoryEntry[]> {
    return api.post<MemoryEntry[]>('/api/memory/search', { query })
  },

  delete(id: string): Promise<void> {
    return api.delete<void>(`/api/memory/${id}`)
  },

  get(id: string): Promise<MemoryEntry> {
    return api.get<MemoryEntry>(`/api/memory/${id}`)
  },

  getIndex(): Promise<{ index: string }> {
    return api.get('/api/memory/index')
  },
}

// ─── Tools API ────────────────────────────────────────────────

export interface ToolDef {
  name: string
  description: string
  inputSchema: Record<string, unknown>
  category?: string
}

export const toolsAPI = {
  list(): Promise<{ tools: ToolDef[]; count: number }> {
    return api.get('/api/tools')
  },
}

// ─── MCP API ──────────────────────────────────────────────────

export interface MCPServerConfig {
  id: string
  name: string
  type: 'stdio' | 'http' | 'sse' | 'claude-ai'
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  authToken?: string
  enabled: boolean
}

export const mcpAPI = {
  list(): Promise<MCPServerConfig[]> {
    return api.get<MCPServerConfig[]>('/api/mcp/servers')
  },

  add(server: Omit<MCPServerConfig, 'id'>): Promise<MCPServerConfig> {
    return api.post<MCPServerConfig>('/api/mcp/servers', server)
  },

  update(id: string, updates: Partial<MCPServerConfig>): Promise<MCPServerConfig> {
    return api.put<MCPServerConfig>(`/api/mcp/servers/${id}`, updates)
  },

  remove(id: string): Promise<void> {
    return api.delete<void>(`/api/mcp/servers/${id}`)
  },

  toggle(id: string, enabled: boolean): Promise<void> {
    return api.patch<void>(`/api/mcp/servers/${id}`, { enabled })
  },

  templates(): Promise<Array<{ id: string; name: string; description: string; config: Partial<MCPServerConfig> }>> {
    return api.get('/api/mcp/templates')
  },
}

// ─── Agents API ────────────────────────────────────────────────

export interface Agent {
  id: string
  name: string
  type: 'explore' | 'plan' | 'general' | 'verify'
  status: 'running' | 'completed' | 'error'
  createdAt: number
  result?: string
}

export const agentsAPI = {
  list(): Promise<Agent[]> {
    return api.get<Agent[]>('/api/agents')
  },

  spawn(agent: { name: string; type: Agent['type']; task: string; model?: string; provider?: string }): Promise<Agent> {
    return api.post<Agent>('/api/agents', agent)
  },

  get(id: string): Promise<Agent> {
    return api.get<Agent>(`/api/agents/${id}`)
  },

  stop(id: string): Promise<void> {
    return api.delete<void>(`/api/agents/${id}`)
  },

  run(id: string): Promise<string> {
    return api.post<string>(`/api/agents/${id}/run`)
  },

  // Agent Summary API
  startSummary(agentId: string): Promise<{ ok: boolean; agentId: string; message: string }> {
    return api.post(`/api/agents/${agentId}/summary/start`)
  },

  stopSummary(agentId: string): Promise<{ ok: boolean; agentId: string; message: string }> {
    return api.delete(`/api/agents/${agentId}/summary/stop`)
  },

  getSummary(agentId: string): Promise<{ agentId: string; summary?: string; messageCount: number }> {
    return api.get(`/api/agents/${agentId}/summary`)
  },

  addMessage(agentId: string, message: { role: string; content: string | unknown[] }): Promise<{ ok: boolean; agentId: string; messageCount: number }> {
    return api.post(`/api/agents/${agentId}/messages`, message)
  },

  clearMessages(agentId: string): Promise<{ ok: boolean; agentId: string }> {
    return api.delete(`/api/agents/${agentId}/messages`)
  },
}

// ─── Agent Summary WebSocket Types ─────────────────────────────────

export interface AgentSummaryMessage {
  type: 'agent_summary'
  agentId: string
  summary: string
}

// ─── Permissions API ───────────────────────────────────────────

export interface PermissionRule {
  id: string
  tool_name: string
  action: string
  pattern?: string
  created_at: number
  description?: string
}

export interface PendingPermission {
  id: string
  tool_name: string
  arguments: Record<string, unknown>
  requested_at: number
  status: 'pending' | 'approved' | 'denied'
  approved_at?: number
  denied_at?: number
}

export const permissionsAPI = {
  list(): Promise<PermissionRule[]> {
    return api.get<PermissionRule[]>('/api/permissions')
  },

  create(rule: Omit<PermissionRule, 'id' | 'created_at'>): Promise<PermissionRule> {
    return api.post<PermissionRule>('/api/permissions', rule)
  },

  delete(ruleId: string): Promise<{ ok: boolean; id: string }> {
    return api.delete<{ ok: boolean; id: string }>(`/api/permissions/${ruleId}`)
  },

  getPending(): Promise<PendingPermission[]> {
    return api.get<PendingPermission[]>('/api/permissions/pending')
  },

  approve(permissionId: string): Promise<PendingPermission> {
    return api.post<PendingPermission>('/api/permissions/approve', { permissionId })
  },

  deny(permissionId: string): Promise<PendingPermission> {
    return api.post<PendingPermission>('/api/permissions/deny', { permissionId })
  },

  retry(commands: string[]): Promise<{ retried_commands: string[]; message: string }> {
    return api.get<{ retried_commands: string[]; message: string }>(`/api/permissions/retry?commands=${encodeURIComponent(commands.join(','))}`)
  },
}

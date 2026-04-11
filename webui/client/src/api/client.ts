import { getActiveProfile, resolveUrl, resolveWsUrl } from './config'

export type { ConnectionProfile, APIConfig } from './config'

// ─── HTTP Client ────────────────────────────────────────────────

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  signal?: AbortSignal
}

class APIClient {
  private baseHeaders(): Record<string, string> {
    const profile = getActiveProfile()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (profile.apiKey) {
      headers['Authorization'] = `Bearer ${profile.apiKey}`
    }
    return headers
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const profile = getActiveProfile()
    const url = resolveUrl(profile.httpUrl, path)
    
    const response = await fetch(url, {
      method: options.method || 'GET',
      headers: { ...this.baseHeaders(), ...options.headers },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: response.statusText }))
      throw new Error(error.error || `HTTP ${response.status}`)
    }

    return response.json() as Promise<T>
  }

  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'GET' })
  }

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'POST', body })
  }

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PUT', body })
  }

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'PATCH', body })
  }

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return this.request<T>(path, { ...options, method: 'DELETE' })
  }
}

export const api = new APIClient()

// ─── WebSocket Client ───────────────────────────────────────────

type WsHandler = (msg: Record<string, unknown>) => void

interface WsConnection {
  ws: WebSocket | null
  status: 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
  handler: WsHandler | null
  retryCount: number
  retryTimer: ReturnType<typeof setTimeout> | null
  path: string
}

class WSManager {
  private connections: Map<string, WsConnection> = new Map()
  private pingTimers: Map<string, ReturnType<typeof setInterval>> = new Map()

  get(path: string): WsConnection | undefined {
    return this.connections.get(path)
  }

  connect(id: string, path: string, handler: WsHandler): void {
    const profile = getActiveProfile()
    const wsUrl = resolveWsUrl(profile.wsUrl, path)

    const existing = this.connections.get(id)
    if (existing?.ws) {
      existing.handler = handler
      return
    }

    const connection: WsConnection = {
      ws: null,
      status: 'connecting',
      handler,
      retryCount: 0,
      retryTimer: null,
      path,
    }
    this.connections.set(id, connection)

    this.doConnect(id, wsUrl)
  }

  private doConnect(id: string, url: string): void {
    const conn = this.connections.get(id)
    if (!conn) return

    if (conn.ws) {
      try { conn.ws.close() } catch {}
    }

    conn.status = conn.retryCount > 0 ? 'reconnecting' : 'connecting'
    const socket = new WebSocket(url)
    conn.ws = socket

    socket.onopen = () => {
      conn.status = 'connected'
      conn.retryCount = 0
      this.startPing(id)
    }

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string)
        if (msg.type === 'pong') return
        conn.handler?.(msg)
      } catch {}
    }

    socket.onclose = (event) => {
      conn.ws = null
      conn.status = 'disconnected'
      this.stopPing(id)

      if (event.code !== 1000 && conn.retryCount < 10) {
        const delay = Math.min(1000 * Math.pow(2, conn.retryCount), 15000)
        conn.retryCount++
        conn.retryTimer = setTimeout(() => {
          const profile = getActiveProfile()
          this.doConnect(id, resolveWsUrl(profile.wsUrl, conn.path))
        }, delay)
      }
    }

    socket.onerror = () => {}
  }

  private startPing(id: string): void {
    this.stopPing(id)
    const interval = setInterval(() => {
      const conn = this.connections.get(id)
      if (conn?.ws?.readyState === WebSocket.OPEN) {
        conn.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)
    this.pingTimers.set(id, interval)
  }

  private stopPing(id: string): void {
    const timer = this.pingTimers.get(id)
    if (timer) {
      clearInterval(timer)
      this.pingTimers.delete(id)
    }
  }

  disconnect(id: string): void {
    const conn = this.connections.get(id)
    if (conn) {
      if (conn.retryTimer) clearTimeout(conn.retryTimer)
      this.stopPing(id)
      if (conn.ws) {
        try { conn.ws.close(1000) } catch {}
      }
      this.connections.delete(id)
    }
  }

  send(id: string, data: unknown): boolean {
    const conn = this.connections.get(id)
    if (conn?.ws?.readyState === WebSocket.OPEN) {
      conn.ws.send(JSON.stringify(data))
      return true
    }
    return false
  }

  reconnect(id: string): void {
    const conn = this.connections.get(id)
    if (conn && conn.handler) {
      conn.retryCount = 0
      if (conn.retryTimer) clearTimeout(conn.retryTimer)
      const profile = getActiveProfile()
      this.doConnect(id, resolveWsUrl(profile.wsUrl, conn.path))
    }
  }

  getStatus(id: string): 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'unknown' {
    return this.connections.get(id)?.status ?? 'unknown'
  }

  connectAgentSummary(agentId: string, handler: WsHandler): void {
    this.connect(`agent-summary-${agentId}`, `/ws/agent-summary/${agentId}`, handler)
  }

  disconnectAgentSummary(agentId: string): void {
    this.disconnect(`agent-summary-${agentId}`)
  }

  sendAgentSummaryMessage(agentId: string, data: unknown): boolean {
    return this.send(`agent-summary-${agentId}`, data)
  }

  getAgentSummaryStatus(agentId: string): 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'unknown' {
    return this.getStatus(`agent-summary-${agentId}`)
  }
}

export const wsManager = new WSManager()

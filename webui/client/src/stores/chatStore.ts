import { create } from 'zustand'

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

/** Permission mode for high-risk tools */
export type PermissionMode = 'ask' | 'always-allow' | 'auto-approve'

// ─── WebSocket Manager ────────────────────────────────────────────────────────

type WsHandler = (msg: Record<string, unknown>) => void

interface WsEntry {
  ws: WebSocket | null
  status: 'connecting' | 'connected' | 'disconnected' | 'reconnecting'
  handler: WsHandler | null
  retryCount: number
  retryTimer: ReturnType<typeof setTimeout> | null
}

const wsManager: Record<string, WsEntry> = {
  chat: { ws: null, status: 'disconnected', handler: null, retryCount: 0, retryTimer: null },
  cowork: { ws: null, status: 'disconnected', handler: null, retryCount: 0, retryTimer: null },
  code: { ws: null, status: 'disconnected', handler: null, retryCount: 0, retryTimer: null },
}

const WS_TARGET = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/chat'

function clearWsTimers(entry: WsEntry) {
  if (entry.retryTimer) { clearTimeout(entry.retryTimer); entry.retryTimer = null }
}

function connectWs(mode: string, handler: WsHandler) {
  const entry = wsManager[mode]
  if (!entry) return

  entry.handler = handler

  if (entry.ws) {
    try { entry.ws.close() } catch {}
    entry.ws = null
  }

  entry.status = entry.retryCount > 0 ? 'reconnecting' : 'connecting'
  useChatStore.getState().notifyWsStatusChange(mode)

  const socket = new WebSocket(WS_TARGET)
  entry.ws = socket

  socket.onopen = () => {
    entry.status = 'connected'
    entry.retryCount = 0
    useChatStore.getState().notifyWsStatusChange(mode)
  }

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data as string)
      if (msg.type === 'pong') return
      entry.handler?.(msg)
    } catch {}
  }

  socket.onclose = (event) => {
    entry.ws = null
    entry.status = 'disconnected'
    useChatStore.getState().notifyWsStatusChange(mode)
    clearWsTimers(entry)

    if (event.code !== 1000 && entry.retryCount < 10) {
      const backoff = [3000, 6000, 12000, 18000, 36000]
      const delay = backoff[entry.retryCount] ?? 36000
      entry.retryCount++
      entry.retryTimer = setTimeout(() => connectWs(mode, entry.handler!), delay)
    }
  }

  socket.onerror = () => {
    entry.status = 'disconnected'
    useChatStore.getState().notifyWsStatusChange(mode)
  }
}

function getWs(mode: string) {
  return wsManager[mode]?.ws ?? null
}

function reconnectWs(mode: string) {
  const entry = wsManager[mode]
  if (!entry || !entry.handler) return
  entry.retryCount = 0
  clearWsTimers(entry)
  connectWs(mode, entry.handler)
}

// ─── Store Interface ───────────────────────────────────────────────────────────

interface ChatState {
  sessionId: string | null
  messages: ChatMessage[]
  isStreaming: boolean
  currentModel: string
  currentProvider: string
  ws: WebSocket | null
  /** Permission mode: 'ask' = always ask, 'always-allow' = skip permission, 'auto-approve' = auto-approve after timeout */
  permissionMode: PermissionMode
  /** Tools that have been individually always-allowed, keyed by sessionId for session independence */
  alwaysAllowedTools: Record<string, Set<string>>

  /** Per-mode messages, session IDs, streaming states */
  modeMessages: Record<string, ChatMessage[]>
  modeSessionId: Record<string, string | null>
  modeStreaming: Record<string, boolean>
  /** Per-mode WebSocket connection status */
  wsStatus: Record<string, 'connecting' | 'connected' | 'disconnected' | 'reconnecting'>

  setSession: (id: string) => void
  setModel: (model: string, provider: string) => void
  setModelLocal: (model: string, provider: string) => void
  addMessage: (msg: ChatMessage) => void
  updateLastAssistant: (updater: (msg: ChatMessage) => ChatMessage) => void
  appendTextDelta: (text: string) => void
  appendThinkingDelta: (text: string) => void
  setStreaming: (v: boolean) => void
  clearMessages: () => void
  setWs: (ws: WebSocket | null) => void
  sendMessage: (content: string) => void
  abort: () => void
  setPermissionMode: (mode: PermissionMode) => void
  alwaysAllowTool: (toolName: string, sessionId: string) => void
  isToolAllowed: (toolName: string, sessionId: string) => boolean

  setModeMessages: (mode: string, messages: ChatMessage[]) => void
  getModeMessages: (mode: string) => ChatMessage[]
  setModeSession: (mode: string, id: string) => void
  getModeSession: (mode: string) => string | null
  setModeStreaming: (mode: string, streaming: boolean) => void
  addModeMessage: (mode: string, msg: ChatMessage) => void
  appendModeTextDelta: (mode: string, text: string) => void
  appendModeThinkingDelta: (mode: string, text: string) => void
  updateLastModeAssistant: (mode: string, updates: Partial<ChatMessage> | ((msg: ChatMessage) => ChatMessage)) => void
  clearModeMessages: (mode: string) => void
  /** Connect WebSocket for a mode and register its message handler */
  connectModeWs: (mode: string, handler: (msg: Record<string, unknown>) => void) => void
  /** Disconnect WebSocket for a mode (does NOT close — keeps connection alive) */
  disconnectModeWs: (mode: string) => void
  /** Get the active WebSocket for a mode */
  getModeWs: (mode: string) => WebSocket | null
  /** Notify store that ws status changed */
  notifyWsStatusChange: (mode: string) => void
  /** Manually reconnect a mode's WebSocket */
  reconnectModeWs: (mode: string) => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessionId: null,
  messages: [],
  isStreaming: false,
  currentModel: '',
  currentProvider: '',
  ws: null,
  permissionMode: 'ask' as PermissionMode,
  alwaysAllowedTools: {},

  modeMessages: { chat: [], cowork: [], code: [] },
  modeSessionId: { chat: null, cowork: null, code: null },
  modeStreaming: { chat: false, cowork: false, code: false },
  wsStatus: { chat: 'disconnected', cowork: 'disconnected', code: 'disconnected' },

  setSession: (id) => set({ sessionId: id }),
  setModelLocal: (model, provider) => {
    set({ currentModel: model, currentProvider: provider })
  },
  setModel: (model, provider) => {
    set({ currentModel: model, currentProvider: provider })
    const ws = get().ws
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'switch_model', model, provider }))
    }
  },

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  updateLastAssistant: (updater) =>
    set((s) => {
      const msgs = [...s.messages]
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i]!.role === 'assistant') {
          msgs[i] = updater(msgs[i]!)
          break
        }
      }
      return { messages: msgs }
    }),

  appendTextDelta: (text) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant') {
        const blocks = [...last.content]
        const lastBlock = blocks[blocks.length - 1]
        if (lastBlock?.type === 'text') {
          blocks[blocks.length - 1] = { ...lastBlock, text: (lastBlock.text || '') + text }
        } else {
          blocks.push({ type: 'text', text })
        }
        msgs[msgs.length - 1] = { ...last, content: blocks }
      }
      return { messages: msgs }
    }),

  appendThinkingDelta: (text) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant') {
        const blocks = [...last.content]
        const lastBlock = blocks[blocks.length - 1]
        if (lastBlock?.type === 'thinking') {
          blocks[blocks.length - 1] = { ...lastBlock, text: (lastBlock.text || '') + text }
        } else {
          blocks.push({ type: 'thinking', text })
        }
        msgs[msgs.length - 1] = { ...last, content: blocks }
      }
      return { messages: msgs }
    }),

  setStreaming: (v) => set({ isStreaming: v }),
  clearMessages: () => set({ messages: [], sessionId: null }),
  setWs: (ws) => set({ ws }),

  sendMessage: (content) => {
    const { ws, currentModel, currentProvider, sessionId } = get()
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    // Add user message to local state
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: [{ type: 'text', text: content }],
      timestamp: Date.now(),
    }
    set((s) => ({ messages: [...s.messages, userMsg] }))

    // Send to server
    ws.send(
      JSON.stringify({
        type: 'user_message',
        content,
        sessionId,
        model: currentModel,
        provider: currentProvider,
      })
    )
  },

  abort: () => {
    const ws = get().ws
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'abort' }))
    }
    set({ isStreaming: false })
  },

  setPermissionMode: (mode) => set({ permissionMode: mode }),

  alwaysAllowTool: (toolName, sessionId) =>
    set((s) => {
      const sessionTools = s.alwaysAllowedTools[sessionId] || new Set<string>()
      const next = new Set(sessionTools)
      next.add(toolName)
      return { alwaysAllowedTools: { ...s.alwaysAllowedTools, [sessionId]: next } }
    }),

  isToolAllowed: (toolName, sessionId) => {
    const { permissionMode, alwaysAllowedTools } = get()
    if (permissionMode === 'always-allow') return true
    const sessionTools = alwaysAllowedTools[sessionId || '']
    return sessionTools ? sessionTools.has(toolName) : false
  },

  setModeMessages: (mode, messages) =>
    set((s) => ({ modeMessages: { ...s.modeMessages, [mode]: messages } })),

  getModeMessages: (mode) => get().modeMessages[mode] ?? [],

  setModeSession: (mode, id) =>
    set((s) => ({ modeSessionId: { ...s.modeSessionId, [mode]: id } })),

  getModeSession: (mode) => get().modeSessionId[mode] ?? null,

  setModeStreaming: (mode, streaming) =>
    set((s) => ({ modeStreaming: { ...s.modeStreaming, [mode]: streaming } })),

  addModeMessage: (mode, msg) =>
    set((s) => ({
      modeMessages: {
        ...s.modeMessages,
        [mode]: [...(s.modeMessages[mode] ?? []), msg],
      },
    })),

  appendModeTextDelta: (mode, text) =>
    set((s) => {
      const msgs = [...(s.modeMessages[mode] ?? [])]
      // Find the last streaming assistant message
      let targetIdx = -1
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i]!.role === 'assistant' && msgs[i]!.streaming) {
          targetIdx = i
          break
        }
      }
      if (targetIdx === -1) return {}
      const last = msgs[targetIdx]!
      const blocks = [...last.content]
      const lastBlock = blocks[blocks.length - 1]
      if (lastBlock?.type === 'text') {
        blocks[blocks.length - 1] = { ...lastBlock, text: (lastBlock.text || '') + text }
      } else {
        blocks.push({ type: 'text', text })
      }
      msgs[targetIdx] = { ...last, content: blocks }
      return { modeMessages: { ...s.modeMessages, [mode]: msgs } }
    }),

  appendModeThinkingDelta: (mode, text) =>
    set((s) => {
      const msgs = [...(s.modeMessages[mode] ?? [])]
      // Find the last streaming assistant message
      let targetIdx = -1
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i]!.role === 'assistant' && msgs[i]!.streaming) {
          targetIdx = i
          break
        }
      }
      if (targetIdx === -1) return {}
      const last = msgs[targetIdx]!
      const blocks = [...last.content]
      const lastBlock = blocks[blocks.length - 1]
      if (lastBlock?.type === 'thinking') {
        blocks[blocks.length - 1] = { ...lastBlock, text: (lastBlock.text || '') + text }
      } else {
        blocks.push({ type: 'thinking', text })
      }
      msgs[targetIdx] = { ...last, content: blocks }
      return { modeMessages: { ...s.modeMessages, [mode]: msgs } }
    }),

  updateLastModeAssistant: (mode, updates) =>
    set((s) => {
      const msgs = [...(s.modeMessages[mode] ?? [])]
      for (let i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i]!.role === 'assistant') {
          msgs[i] = typeof updates === 'function' ? updates(msgs[i]!) : { ...msgs[i]!, ...updates }
          break
        }
      }
      return { modeMessages: { ...s.modeMessages, [mode]: msgs } }
    }),

  clearModeMessages: (mode) =>
    set((s) => ({
      modeMessages: { ...s.modeMessages, [mode]: [] },
      modeSessionId: { ...s.modeSessionId, [mode]: null },
    })),

  connectModeWs: (mode, handler) => {
    connectWs(mode, handler)
  },

  disconnectModeWs: (_mode) => {
    // no-op — connection stays alive
  },

  getModeWs: (mode) => getWs(mode),

  notifyWsStatusChange: (mode) => {
    const entry = wsManager[mode]
    if (!entry) return
    set((s) => ({ wsStatus: { ...s.wsStatus, [mode]: entry.status } }))
  },

  reconnectModeWs: (mode) => {
    reconnectWs(mode)
  },
}))

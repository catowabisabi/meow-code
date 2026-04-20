import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useChatStore, type ChatMessage } from '../stores/chatStore.ts'
import MessageBubble from '../components/chat/MessageBubble.tsx'
import PermissionDialog from '../components/chat/PermissionDialog.tsx'

const MODE = 'chat'

const quickPrompts = [
  { icon: '⚡', text: '寫一個 Python 快速排序' },
  { icon: '🔍', text: '解釋 React hooks 原理' },
  { icon: '🛠', text: '幫我 debug 這段代碼' },
  { icon: '📐', text: '設計一個 REST API 架構' },
]

// ── Empty state ───────────────────────────────────────────────────

function EmptyState({ onPrompt }: { onPrompt: (text: string) => void }) {
  const currentModel = useChatStore((s) => s.currentModel)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      height: '100%', padding: '40px 24px',
      animation: 'fadeIn 0.2s ease',
    }}>
      {/* Logo mark */}
      <div style={{
        width: 52, height: 52, borderRadius: '14px',
        background: 'linear-gradient(135deg, #cc785c 0%, #a0522d 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 24, fontWeight: 700, color: '#fff',
        marginBottom: 20,
        boxShadow: '0 8px 24px rgba(204,120,92,0.25)',
        letterSpacing: '-1px',
      }}>
        C
      </div>

      <h1 style={{
        fontSize: 22, fontWeight: 600,
        color: 'var(--text-primary)',
        marginBottom: 8, textAlign: 'center',
      }}>
        How can I help you today?
      </h1>

      {currentModel && (
        <p style={{
          fontSize: 13, color: 'var(--text-muted)',
          marginBottom: 32, textAlign: 'center',
        }}>
          {currentModel}
        </p>
      )}

      {/* Suggestion chips */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 10,
        width: '100%',
        maxWidth: 480,
      }}>
        {quickPrompts.map((p, i) => (
          <button
            key={i}
            onClick={() => onPrompt(p.text)}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '12px 16px',
              background: hoveredIdx === i ? 'var(--bg-hover)' : 'var(--bg-tertiary)',
              border: `1px solid ${hoveredIdx === i ? 'var(--border-focus)' : 'var(--border-default)'}`,
              borderRadius: 10, cursor: 'pointer',
              fontSize: 13, color: 'var(--text-secondary)',
              textAlign: 'left', transition: 'all 0.12s',
              fontFamily: 'inherit', lineHeight: 1.4,
            }}
          >
            <span style={{ fontSize: 16, flexShrink: 0 }}>{p.icon}</span>
            <span>{p.text}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Connection status bar ─────────────────────────────────────────

function ConnectionBanner({ status, onReconnect }: { status: string; onReconnect: () => void }) {
  if (status === 'connected') return null

  const isReconnecting = status === 'reconnecting' || status === 'connecting'
  const color = isReconnecting ? 'var(--accent-yellow)' : 'var(--accent-red)'
  const bg = isReconnecting ? 'rgba(251,191,36,0.08)' : 'rgba(248,113,113,0.08)'
  const border = isReconnecting ? 'rgba(251,191,36,0.25)' : 'rgba(248,113,113,0.25)'

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
      padding: '7px 16px', margin: '0 0 8px',
      background: bg, border: `1px solid ${border}`,
      borderRadius: 8, fontSize: 12, color,
    }}>
      {isReconnecting && (
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: color, animation: 'pulse-dot 1.2s infinite',
        }} />
      )}
      <span>{isReconnecting ? '正在重連後端...' : '連接已中斷'}</span>
      {!isReconnecting && (
        <button
          onClick={onReconnect}
          style={{
            padding: '2px 10px', borderRadius: 5,
            border: `1px solid ${color}`, background: 'transparent',
            color, fontSize: 11, cursor: 'pointer', fontFamily: 'inherit',
          }}
        >
          重連
        </button>
      )}
    </div>
  )
}

// ── Input area ────────────────────────────────────────────────────

interface InputAreaProps {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  onAbort: () => void
  isStreaming: boolean
  wsStatus: string
  textareaRef: React.RefObject<HTMLTextAreaElement>
}

function InputArea({ value, onChange, onSend, onAbort, isStreaming, wsStatus, textareaRef }: InputAreaProps) {
  const currentModel = useChatStore((s) => s.currentModel)
  const currentProvider = useChatStore((s) => s.currentProvider)
  const canSend = value.trim().length > 0 && wsStatus === 'connected' && !isStreaming

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (canSend) onSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value)
    const el = e.target
    el.style.height = '44px'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }

  return (
    <div style={{
      borderTop: '1px solid var(--border-muted)',
      padding: '12px 16px 16px',
      background: 'var(--bg-primary)',
    }}>
      <div style={{ maxWidth: 'var(--chat-max-width)', margin: '0 auto' }}>
        <ConnectionBanner status={wsStatus} onReconnect={() => useChatStore.getState().reconnectModeWs(MODE)} />

        <div style={{
          background: 'var(--bg-tertiary)',
          border: `1px solid var(--border-default)`,
          borderRadius: 14,
          overflow: 'hidden',
          transition: 'border-color 0.15s',
        }}
          onFocusCapture={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-focus)' }}
          onBlurCapture={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-default)' }}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Ask Cato anything… (Enter to send, Shift+Enter for newline)"
            style={{
              width: '100%', padding: '14px 16px 6px',
              background: 'transparent', border: 'none',
              color: 'var(--text-primary)', fontSize: 14,
              lineHeight: 1.6, resize: 'none',
              outline: 'none', fontFamily: 'inherit',
              minHeight: 44, maxHeight: 200,
              display: 'block',
            }}
          />

          {/* Footer row inside input */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 12px 10px',
          }}>
            {/* Model badge */}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: 11, color: 'var(--text-muted)',
            }}>
              {currentProvider && (
                <span style={{
                  padding: '2px 7px', borderRadius: 4,
                  background: 'var(--bg-hover)',
                  border: '1px solid var(--border-muted)',
                  textTransform: 'capitalize',
                }}>
                  {currentProvider}
                </span>
              )}
              {currentModel && (
                <span style={{ color: 'var(--text-muted)' }}>
                  {currentModel.length > 30 ? currentModel.slice(0, 28) + '…' : currentModel}
                </span>
              )}
            </div>

            {/* Send / Stop button */}
            {isStreaming ? (
              <button
                onClick={onAbort}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  padding: '5px 14px', borderRadius: 8,
                  border: '1px solid var(--accent-red)',
                  background: 'transparent', color: 'var(--accent-red)',
                  fontSize: 13, fontWeight: 500, cursor: 'pointer',
                  fontFamily: 'inherit', transition: 'all 0.12s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(248,113,113,0.08)' }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
              >
                <span style={{ fontSize: 10 }}>■</span> Stop
              </button>
            ) : (
              <button
                onClick={onSend}
                disabled={!canSend}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  padding: '5px 14px', borderRadius: 8,
                  border: 'none',
                  background: canSend
                    ? 'linear-gradient(135deg, #cc785c 0%, #a85c3e 100%)'
                    : 'var(--bg-hover)',
                  color: canSend ? '#fff' : 'var(--text-muted)',
                  fontSize: 13, fontWeight: 500,
                  cursor: canSend ? 'pointer' : 'default',
                  fontFamily: 'inherit', transition: 'all 0.12s',
                  boxShadow: canSend ? '0 2px 8px rgba(204,120,92,0.3)' : 'none',
                }}
              >
                Send
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            )}
          </div>
        </div>

        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text-muted)', marginTop: 8 }}>
          Ctrl+K 切換模型 · Agent 模式可執行命令、讀寫文件、搜索代碼
        </p>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────

export default function ChatPage() {
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const store = useChatStore()

  const messages = store.modeMessages[MODE] ?? []
  const isStreaming = store.modeStreaming[MODE] ?? false
  const wsStatus = useChatStore((s) => s.wsStatus[MODE] ?? 'disconnected')

  const [input, setInput] = useState('')
  const [permissionRequest, setPermissionRequest] = useState<{
    toolName: string; toolId: string; input: Record<string, unknown>; description: string
  } | null>(null)

  const messageEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const pendingMessagesRef = useRef<string[]>([])

  // Load session history from URL
  useEffect(() => {
    if (!urlSessionId) return
    const currentSessionId = useChatStore.getState().getModeSession(MODE)
    if (currentSessionId === urlSessionId && messages.length > 0) return

    fetch(`/api/sessions/${urlSessionId}`)
      .then((r) => {
        if (!r.ok) throw new Error('Session not found')
        return r.json()
      })
      .then((data) => {
        const s = useChatStore.getState()
        s.setModeSession(MODE, urlSessionId)
        const chatMessages: ChatMessage[] = (data.messages || [])
          .filter((m: any) => m.role === 'user' || m.role === 'assistant')
          .map((m: any) => ({
            id: crypto.randomUUID(),
            role: m.role,
            content: typeof m.content === 'string'
              ? [{ type: 'text', text: m.content }]
              : Array.isArray(m.content) ? m.content : [],
            timestamp: data.createdAt || Date.now(),
          }))
        s.setModeMessages(MODE, chatMessages)
      })
      .catch(() => {
        useChatStore.getState().setModeSession(MODE, urlSessionId)
      })
  }, [urlSessionId])

  // Auto-scroll
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // WS message handler
  const handleServerMessage = useCallback((msg: Record<string, unknown>) => {
    const s = useChatStore.getState()

    switch (msg.type) {
      case 'session_info': {
        const sessionId = (msg.sessionId as string) || (msg.session_id as string)
        if (sessionId) {
          s.setModeSession(MODE, sessionId)
          window.dispatchEvent(new CustomEvent('sessions-updated'))
        }
        if (msg.model && msg.provider) {
          s.setModelLocal(msg.model as string, msg.provider as string)
        }
        break
      }
      case 'stream_start': {
        s.setModeStreaming(MODE, true)
        const { currentModel, currentProvider } = useChatStore.getState()
        s.addModeMessage(MODE, {
          id: (msg.messageId as string) || crypto.randomUUID(),
          role: 'assistant', content: [],
          model: currentModel, provider: currentProvider,
          timestamp: Date.now(), streaming: true,
        })
        break
      }
      case 'stream_delta':
        if (msg.contentType === 'text') s.appendModeTextDelta(MODE, msg.text as string)
        else if (msg.contentType === 'thinking') s.appendModeThinkingDelta(MODE, msg.text as string)
        break
      case 'stream_text_delta':
        s.appendModeTextDelta(MODE, msg.text as string)
        break
      case 'stream_thinking_delta':
        s.appendModeThinkingDelta(MODE, msg.text as string)
        break
      case 'tool_use_start':
        s.updateLastModeAssistant(MODE, (m) => ({
          ...m,
          content: [...m.content, { type: 'tool_use', id: msg.toolId as string, name: msg.toolName as string, input: msg.input as Record<string, unknown> }],
        }))
        break
      case 'tool_result':
        s.updateLastModeAssistant(MODE, (m) => ({
          ...m,
          content: [...m.content, { type: 'tool_result', tool_use_id: msg.toolId as string, content: msg.output as string, is_error: msg.isError as boolean }],
        }))
        break
      case 'message_complete':
      case 'stream_end':
        s.setModeStreaming(MODE, false)
        s.updateLastModeAssistant(MODE, { streaming: false, usage: msg.usage as any })
        window.dispatchEvent(new CustomEvent('sessions-updated'))
        break
      case 'error':
        s.setModeStreaming(MODE, false)
        s.addModeMessage(MODE, {
          id: crypto.randomUUID(), role: 'system',
          content: [{ type: 'text', text: `Error: ${msg.message}` }],
          timestamp: Date.now(),
        })
        break
      case 'permission_request': {
        const toolName = msg.toolName as string
        const toolId = msg.toolId as string
        const sessionId = s.getModeSession(MODE)
        if (s.isToolAllowed(toolName, sessionId || '')) {
          const ws = wsRef.current
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'permission_response', toolUseId: toolId, allowed: true }))
          }
        } else {
          setPermissionRequest({ toolName, toolId, input: msg.input as Record<string, unknown>, description: msg.description as string })
        }
        break
      }
      case 'title_updated': {
        const sessionId = (msg as any).sessionId as string
        const newTitle = (msg as any).title as string
        if (sessionId && newTitle) {
          s.setSessionTitle(sessionId, newTitle)
          window.dispatchEvent(new CustomEvent('sessions-updated'))
        }
        break
      }
    }
  }, [])

  // Connect WS on mount
  useEffect(() => {
    useChatStore.getState().connectModeWs(MODE, handleServerMessage)
  }, [])

  // Sync wsRef and flush pending messages
  useEffect(() => {
    wsRef.current = useChatStore.getState().getModeWs(MODE)
    if (wsStatus === 'connected') {
      pendingMessagesRef.current.forEach((msg) => sendWsMessage(msg))
      pendingMessagesRef.current = []
    }
  }, [wsStatus])

  const sendWsMessage = (content: string) => {
    const s = useChatStore.getState()
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({
      type: 'user_message', content,
      sessionId: s.getModeSession(MODE),
      mode: MODE,
      model: s.currentModel,
      provider: s.currentProvider,
    }))
  }

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return

    const s = useChatStore.getState()
    s.addModeMessage(MODE, {
      id: crypto.randomUUID(), role: 'user',
      content: [{ type: 'text', text: trimmed }],
      timestamp: Date.now(),
    })

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      pendingMessagesRef.current.push(trimmed)
      s.reconnectModeWs(MODE)
    } else {
      sendWsMessage(trimmed)
    }

    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = '44px'
  }

  const handleAbort = () => {
    wsRef.current?.send(JSON.stringify({ type: 'abort' }))
    useChatStore.getState().setModeStreaming(MODE, false)
  }

  const handlePermissionDecision = useCallback((toolId: string, allowed: boolean) => {
    wsRef.current?.send(JSON.stringify({ type: 'permission_response', toolUseId: toolId, allowed }))
    setPermissionRequest(null)
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)' }}>
      {/* Message area */}
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {messages.length === 0 ? (
          <EmptyState onPrompt={(text) => { setInput(text); textareaRef.current?.focus() }} />
        ) : (
          <div style={{
            maxWidth: 'var(--chat-max-width)',
            margin: '0 auto',
            padding: '24px 24px 8px',
          }}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messageEndRef} style={{ height: 16 }} />
          </div>
        )}
      </div>

      {/* Input */}
      <InputArea
        value={input}
        onChange={setInput}
        onSend={handleSend}
        onAbort={handleAbort}
        isStreaming={isStreaming}
        wsStatus={wsStatus}
        textareaRef={textareaRef}
      />

      {/* Permission dialog */}
      {permissionRequest && (
        <PermissionDialog
          toolName={permissionRequest.toolName}
          toolId={permissionRequest.toolId}
          input={permissionRequest.input}
          description={permissionRequest.description}
          onDecision={handlePermissionDecision}
          onAlwaysAllow={(toolName) => {
            const sessionId = useChatStore.getState().getModeSession(MODE)
            if (sessionId) useChatStore.getState().alwaysAllowTool(toolName, sessionId)
          }}
        />
      )}
    </div>
  )
}

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useChatStore, type ChatMessage } from '../stores/chatStore.ts'
import MessageBubble from '../components/chat/MessageBubble.tsx'
import PermissionDialog from '../components/chat/PermissionDialog.tsx'

const MODE = 'chat'
// Subtle chat mode indicator (UI only)
const ChatModeIndicator: React.FC = () => (
  <div style={{ position: 'absolute', top: 8, right: 12, zIndex: 2 }}>
    <span style={{ padding: '4px 10px', borderRadius: '999px', background: 'rgba(0,0,0,0.25)', color: '#d9d9d9', fontSize: 12, border: '1px solid rgba(255,255,255,0.25)' }}>
      Chat mode
    </span>
  </div>
);

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
  },
  messageArea: {
    flex: 1,
    overflow: 'auto',
    padding: '16px 0',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--text-muted)',
    gap: '16px',
  },
  emptyIcon: {
    fontSize: '48px',
    opacity: 0.5,
  },
  emptyTitle: {
    fontSize: '20px',
    color: 'var(--text-secondary)',
    fontWeight: 600,
  },
  emptyHints: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap' as const,
    justifyContent: 'center',
    maxWidth: '600px',
  },
  hintChip: {
    padding: '8px 16px',
    borderRadius: '20px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-secondary)',
    fontSize: '13px',
    cursor: 'pointer',
  },
  inputArea: {
    borderTop: '1px solid var(--border-default)',
    padding: '12px 20px',
    background: 'var(--bg-secondary)',
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '8px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  textarea: {
    flex: 1,
    padding: '10px 14px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '12px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    lineHeight: 1.5,
    resize: 'none' as const,
    outline: 'none',
    minHeight: '44px',
    maxHeight: '200px',
    fontFamily: 'inherit',
  },
  sendBtn: (active: boolean) => ({
    padding: '10px 18px',
    borderRadius: '12px',
    border: 'none',
    background: active ? 'var(--accent-blue)' : 'var(--bg-tertiary)',
    color: active ? '#fff' : 'var(--text-muted)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: active ? 'pointer' : 'default',
    transition: 'all 0.15s',
  }),
  stopBtn: {
    padding: '10px 18px',
    borderRadius: '12px',
    border: '1px solid var(--accent-red)',
    background: 'transparent',
    color: 'var(--accent-red)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  hint: {
    textAlign: 'center' as const,
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '6px',
  },
}

const quickPrompts = [
  '寫一個 Python 快速排序',
  '解釋 React hooks 原理',
  '幫我寫一個 REST API',
  '分析這段代碼的性能',
  '生成 TypeScript 類型定義',
]

export default function ChatPage() {
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const store = useChatStore()

  const messages = store.modeMessages[MODE] ?? []
  const isStreaming = store.modeStreaming[MODE] ?? false

  const [input, setInput] = useState('')
  const [permissionRequest, setPermissionRequest] = useState<{
    toolName: string; toolId: string; input: Record<string, unknown>; description: string
  } | null>(null)
  const messageEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // Load session history from URL param
  useEffect(() => {
    if (!urlSessionId) return
    const currentSessionId = useChatStore.getState().getModeSession(MODE)
    if (currentSessionId === urlSessionId && messages.length > 0) return

    // Fetch session from backend and populate messages
    fetch(`/api/sessions/${urlSessionId}`)
      .then((r) => {
        if (!r.ok) throw new Error('Session not found')
        return r.json()
      })
      .then((data) => {
        const s = useChatStore.getState()
        s.setModeSession(MODE, urlSessionId)

        // Convert stored messages to ChatMessage format
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
        // Session not found — just set the ID so new messages go to this session
        useChatStore.getState().setModeSession(MODE, urlSessionId)
      })
  }, [urlSessionId])

  // Auto-scroll to bottom
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // WebSocket message handler
  const handleServerMessage = useCallback(
    (msg: Record<string, unknown>) => {
      const store = useChatStore.getState()

      switch (msg.type) {
        case 'session_info': {
          const sessionId = (msg.sessionId as string) || (msg.session_id as string)
          if (sessionId) {
            store.setModeSession(MODE, sessionId)
            window.dispatchEvent(new CustomEvent('sessions-updated'))
          }
          if (msg.model && msg.provider) {
            store.setModelLocal(msg.model as string, msg.provider as string)
          }
          break
        }

        case 'stream_start': {
          store.setModeStreaming(MODE, true)
          const { currentModel, currentProvider } = useChatStore.getState()
          const assistantMsg: ChatMessage = {
            id: (msg.messageId as string) || crypto.randomUUID(),
            role: 'assistant',
            content: [],
            model: currentModel,
            provider: currentProvider,
            timestamp: Date.now(),
            streaming: true,
          }
          store.addModeMessage(MODE, assistantMsg)
          break
        }

        case 'stream_delta':
          if (msg.contentType === 'text') {
            store.appendModeTextDelta(MODE, msg.text as string)
          } else if (msg.contentType === 'thinking') {
            store.appendModeThinkingDelta(MODE, msg.text as string)
          }
          break

        case 'stream_text_delta':
          store.appendModeTextDelta(MODE, msg.text as string)
          break

        case 'stream_thinking_delta':
          store.appendModeThinkingDelta(MODE, msg.text as string)
          break

        case 'tool_use_start':
          store.updateLastModeAssistant(MODE, (m) => ({
            ...m,
            content: [
              ...m.content,
              { type: 'tool_use', id: msg.toolId as string, name: msg.toolName as string, input: msg.input as Record<string, unknown> },
            ],
          }))
          break

        case 'tool_result':
          store.updateLastModeAssistant(MODE, (m) => ({
            ...m,
            content: [
              ...m.content,
              { type: 'tool_result', tool_use_id: msg.toolId as string, content: msg.output as string, is_error: msg.isError as boolean },
            ],
          }))
          break

        case 'message_complete':
        case 'stream_end':
          store.setModeStreaming(MODE, false)
          store.updateLastModeAssistant(MODE, {
            streaming: false,
            usage: msg.usage as { inputTokens: number; outputTokens: number } | undefined,
          })
          window.dispatchEvent(new CustomEvent('sessions-updated'))
          break

        case 'error':
          store.setModeStreaming(MODE, false)
          store.addModeMessage(MODE, {
            id: crypto.randomUUID(),
            role: 'system',
            content: [{ type: 'text', text: `Error: ${msg.message}` }],
            timestamp: Date.now(),
          })
          break

        case 'permission_request': {
          const toolName = msg.toolName as string
          const toolId = msg.toolId as string
          const sessionId = store.getModeSession(MODE)
          if (store.isToolAllowed(toolName, sessionId || '')) {
            const ws = wsRef.current
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'permission_response', toolUseId: toolId, allowed: true }))
            }
          } else {
            setPermissionRequest({
              toolName,
              toolId,
              input: msg.input as Record<string, unknown>,
              description: msg.description as string,
            })
          }
          break
        }

        case 'title_updated':
          // AI generated a new title — refresh sidebar
          window.dispatchEvent(new CustomEvent('sessions-updated'))
          break

        case 'model_switched':
          break
      }
    },
    []
  )

  // Get persistent WebSocket from store manager — no reconnect on tab switch
  const wsStatus = useChatStore((s) => s.wsStatus[MODE] ?? 'disconnected')

  // Connect handler on mount, keep connection alive on unmount
  useEffect(() => {
    useChatStore.getState().connectModeWs(MODE, handleServerMessage)
  }, [])

  // Sync wsRef for send
  useEffect(() => {
    wsRef.current = useChatStore.getState().getModeWs(MODE)
  }, [wsStatus])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return
    if (isStreaming) return

    const store = useChatStore.getState()
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not ready, attempting reconnect...')
      store.reconnectModeWs(MODE)
      return
    }

    const sessionId = store.getModeSession(MODE)
    const { currentModel, currentProvider } = store

    // Add user message to mode-specific state
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: [{ type: 'text', text: trimmed }],
      timestamp: Date.now(),
    }
    store.addModeMessage(MODE, userMsg)

    // Send to server
    ws.send(
      JSON.stringify({
        type: 'user_message',
        content: trimmed,
        sessionId,
        mode: MODE,
        model: currentModel,
        provider: currentProvider,
      })
    )

    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px'
    }
  }

  const handleAbort = () => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'abort' }))
    }
    useChatStore.getState().setModeStreaming(MODE, false)
  }

  const newChat = () => {
    useChatStore.getState().clearModeMessages(MODE)
  }

  const handlePermissionDecision = useCallback((toolId: string, allowed: boolean) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'permission_response', toolUseId: toolId, allowed }))
    }
    setPermissionRequest(null)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize
    const el = e.target
    el.style.height = '44px'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }

  return (
    <div style={{ ...styles.container, position: 'relative' }}>
      <ChatModeIndicator />
      <div style={styles.messageArea}>
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>⚡</div>
            <div style={styles.emptyTitle}>開始對話</div>
            <div style={{ fontSize: '13px' }}>
              選擇模型後，輸入你的問題或嘗試以下快捷提示
            </div>
            <div style={styles.emptyHints}>
              {quickPrompts.map((prompt) => (
                <div
                  key={prompt}
                  style={styles.hintChip}
                  onClick={() => {
                    setInput(prompt)
                    textareaRef.current?.focus()
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-blue)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-default)'
                  }}
                >
                  {prompt}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div style={{ maxWidth: '900px', margin: '0 auto' }}>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messageEndRef} />
          </div>
        )}
      </div>

      <div style={styles.inputArea}>
        {wsStatus !== 'connected' && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            padding: '6px 12px', marginBottom: '8px', borderRadius: '8px',
            background: wsStatus === 'reconnecting' ? 'rgba(210,153,34,0.15)' : 'rgba(248,81,73,0.15)',
            color: wsStatus === 'reconnecting' ? '#d29922' : '#f85149',
            fontSize: '13px', maxWidth: '900px', margin: '0 auto 8px',
          }}>
            <span>{wsStatus === 'reconnecting' ? '正在重連後端...' : wsStatus === 'connecting' ? '正在連接...' : '連接已斷開'}</span>
            {wsStatus === 'disconnected' && (
              <button onClick={() => useChatStore.getState().reconnectModeWs(MODE)} style={{
                padding: '2px 10px', borderRadius: '6px', border: '1px solid #f85149',
                background: 'transparent', color: '#f85149', fontSize: '12px', cursor: 'pointer',
              }}>重連</button>
            )}
          </div>
        )}
        <div style={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            style={styles.textarea}
            placeholder="輸入消息... (Enter 發送, Shift+Enter 換行, Ctrl+K 切換模型)"
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          {isStreaming ? (
            <button style={styles.stopBtn} onClick={handleAbort}>
              停止
            </button>
          ) : (
            <button
              style={styles.sendBtn(input.trim().length > 0 && wsStatus === 'connected')}
              onClick={handleSend}
              disabled={!input.trim() || wsStatus !== 'connected'}
            >
              發送
            </button>
          )}
        </div>
        <div style={styles.hint}>
          Ctrl+K 快速切換模型 · Ctrl+1/2/3 快捷切換 · Agent 模式：AI 可執行命令、讀寫文件、搜索代碼
        </div>
      </div>

      {/* Permission Dialog */}
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

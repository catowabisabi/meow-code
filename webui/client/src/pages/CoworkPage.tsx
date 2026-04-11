import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useChatStore, type ChatMessage, type ContentBlock } from '../stores/chatStore.ts'
import { useLayoutStore } from '../stores/layoutStore.ts'

const MODE = 'cowork'

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const colors = {
  cardBg: '#1b1b1f',
  cardBorder: '#2a2a2e',
  errorBannerBg: 'rgba(250, 204, 21, 0.1)',
  errorBannerBorder: 'rgba(250, 204, 21, 0.3)',
  errorText: '#facc15',
  fileCardHover: '#222226',
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
  },

  // -- Header / breadcrumb --
  header: {
    padding: '12px 20px',
    borderBottom: `1px solid ${colors.cardBorder}`,
    background: colors.cardBg,
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexShrink: 0,
  },
  breadcrumb: {
    fontSize: '13px',
    color: 'var(--text-muted)',
    fontFamily: 'monospace',
  },
  taskTitle: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  editBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '2px 6px',
    borderRadius: '4px',
  },

  // -- Scrollable body --
  messageArea: {
    flex: 1,
    overflow: 'auto',
    padding: '16px 20px',
  },
  messagesInner: {
    maxWidth: '900px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  },

  // -- Empty state --
  emptyState: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: '16px',
    color: 'var(--text-muted)',
  },
  emptyIcon: { fontSize: '48px', opacity: 0.5 },
  emptyTitle: { fontSize: '20px', fontWeight: 600, color: 'var(--text-secondary)' },
  folderInput: {
    padding: '10px 14px',
    background: colors.cardBg,
    border: `1px solid ${colors.cardBorder}`,
    borderRadius: '8px',
    color: 'var(--text-primary)',
    fontSize: '13px',
    fontFamily: 'monospace',
    width: '420px',
    outline: 'none',
  },
  browseBtn: {
    padding: '10px 16px',
    borderRadius: '8px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
    fontSize: '13px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  startBtn: {
    padding: '10px 24px',
    borderRadius: '8px',
    border: 'none',
    background: 'var(--accent-blue)',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },

  // -- File card --
  fileCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 14px',
    background: colors.cardBg,
    border: `1px solid ${colors.cardBorder}`,
    borderRadius: '8px',
    cursor: 'default',
    transition: 'background 0.15s',
  },
  fileIcon: { fontSize: '18px', flexShrink: 0 },
  filePath: {
    flex: 1,
    fontSize: '13px',
    fontFamily: 'monospace',
    color: 'var(--text-secondary)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  fileTypeLabel: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '2px',
  },
  openBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '6px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'transparent',
    color: '#4ade80',
    fontSize: '12px',
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
  },

  // -- Message cards --
  assistantCard: {
    padding: '14px 16px',
    background: colors.cardBg,
    border: `1px solid ${colors.cardBorder}`,
    borderRadius: '10px',
    fontSize: '14px',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap' as const,
    color: 'var(--text-primary)',
  },
  userCard: {
    padding: '12px 16px',
    background: 'var(--accent-blue)',
    borderRadius: '10px 10px 4px 10px',
    fontSize: '14px',
    lineHeight: 1.5,
    color: '#fff',
    alignSelf: 'flex-end' as const,
    maxWidth: '75%',
    whiteSpace: 'pre-wrap' as const,
  },
  systemCard: {
    padding: '10px 14px',
    background: 'rgba(239,68,68,0.1)',
    border: '1px solid rgba(239,68,68,0.3)',
    borderRadius: '8px',
    fontSize: '13px',
    color: '#f87171',
    whiteSpace: 'pre-wrap' as const,
  },

  // -- Tool execution card --
  toolCard: {
    padding: '10px 14px',
    background: colors.cardBg,
    border: `1px solid ${colors.cardBorder}`,
    borderRadius: '8px',
    fontSize: '13px',
    fontFamily: 'monospace',
  },
  toolHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    cursor: 'pointer',
    userSelect: 'none' as const,
  },
  toolName: { fontWeight: 600, color: 'var(--text-secondary)' },
  toolToggle: { fontSize: '12px', color: 'var(--text-muted)' },
  toolBody: {
    marginTop: '8px',
    padding: '8px',
    background: 'var(--bg-primary)',
    borderRadius: '6px',
    overflow: 'auto',
    maxHeight: '300px',
    whiteSpace: 'pre-wrap' as const,
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },

  // -- Error banner --
  errorBanner: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '12px 14px',
    background: colors.errorBannerBg,
    border: `1px solid ${colors.errorBannerBorder}`,
    borderRadius: '8px',
  },
  errorIcon: { fontSize: '18px', color: colors.errorText, flexShrink: 0 },
  errorBody: { flex: 1, fontSize: '13px', fontFamily: 'monospace', color: colors.errorText, whiteSpace: 'pre-wrap' as const },
  copyBtn: {
    padding: '4px 8px',
    borderRadius: '4px',
    border: `1px solid ${colors.errorBannerBorder}`,
    background: 'transparent',
    color: colors.errorText,
    fontSize: '11px',
    cursor: 'pointer',
    flexShrink: 0,
  },

  // -- Bottom input --
  inputArea: {
    borderTop: `1px solid ${colors.cardBorder}`,
    padding: '12px 20px',
    background: colors.cardBg,
    flexShrink: 0,
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '8px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  attachBtn: {
    padding: '8px',
    borderRadius: '8px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'transparent',
    color: 'var(--text-muted)',
    fontSize: '18px',
    cursor: 'pointer',
    lineHeight: 1,
  },
  textarea: {
    flex: 1,
    padding: '10px 14px',
    background: 'var(--bg-primary)',
    border: `1px solid ${colors.cardBorder}`,
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
  modelSelector: {
    padding: '8px 12px',
    borderRadius: '8px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'transparent',
    color: 'var(--text-secondary)',
    fontSize: '12px',
    cursor: 'pointer',
  },
  micBtn: {
    padding: '8px',
    borderRadius: '8px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'transparent',
    color: 'var(--text-muted)',
    fontSize: '16px',
    cursor: 'pointer',
    lineHeight: 1,
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
  newTaskBtn: {
    padding: '6px 14px',
    borderRadius: '8px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'transparent',
    color: 'var(--text-muted)',
    fontSize: '12px',
    cursor: 'pointer',
    flexShrink: 0,
  },
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function FileReferenceCard({ filePath }: { filePath: string }) {
  const [hovered, setHovered] = useState(false)
  const ext = filePath.split('.').pop() || ''
  const typeLabel = ext.toUpperCase() + ' file'
  return (
    <div
      style={{ ...styles.fileCard, background: hovered ? colors.fileCardHover : colors.cardBg }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span style={styles.fileIcon}>&#128196;</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={styles.filePath}>{filePath}</div>
        <div style={styles.fileTypeLabel}>{typeLabel}</div>
      </div>
      <button style={styles.openBtn} title="Open in Visual Studio Code">
        <span style={{ color: '#4ade80' }}>&#9679;</span> Visual Studio Code
      </button>
    </div>
  )
}

function ToolExecutionCard({ block }: { block: ContentBlock }) {
  const [expanded, setExpanded] = useState(false)
  const name = block.name || 'tool'
  const input = block.input ? JSON.stringify(block.input, null, 2) : ''
  const output = block.content || ''
  const isError = block.is_error

  return (
    <div style={styles.toolCard}>
      <div style={styles.toolHeader} onClick={() => setExpanded(!expanded)}>
        <span style={styles.toolName}>{block.type === 'tool_result' ? `Result: ${block.tool_use_id}` : name}</span>
        <span style={styles.toolToggle}>{expanded ? '▲ collapse' : '▼ expand'}</span>
      </div>
      {expanded && (
        <div style={{ ...styles.toolBody, borderLeft: isError ? '3px solid #f87171' : '3px solid #3b82f6' }}>
          {block.type === 'tool_use' && input && <div>{input}</div>}
          {block.type === 'tool_result' && <div>{output}</div>}
        </div>
      )}
    </div>
  )
}

function ErrorBanner({ message }: { message: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(message).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <div style={styles.errorBanner}>
      <span style={styles.errorIcon}>&#9888;&#65039;</span>
      <div style={styles.errorBody}>{message}</div>
      <button style={styles.copyBtn} onClick={handleCopy}>{copied ? 'Copied' : 'Copy'}</button>
    </div>
  )
}

function MessageBlock({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    const text = message.content.map((b) => b.text || '').join('')
    return <div style={styles.userCard}>{text}</div>
  }

  if (message.role === 'system') {
    const text = message.content.map((b) => b.text || '').join('')
    return <ErrorBanner message={text} />
  }

  // assistant
  const blocks = message.content
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {blocks.map((block, idx) => {
        if (block.type === 'text') {
          // Detect file paths in the text to render file cards
          const filePaths = extractFilePaths(block.text || '')
          return (
            <div key={idx}>
              {filePaths.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '8px' }}>
                  {filePaths.map((fp, i) => <FileReferenceCard key={i} filePath={fp} />)}
                </div>
              )}
              <div style={styles.assistantCard}>
                {block.text}
                {message.streaming && idx === blocks.length - 1 && (
                  <span style={{ opacity: 0.5, animation: 'blink 1s infinite' }}> &#9646;</span>
                )}
              </div>
            </div>
          )
        }
        if (block.type === 'tool_use' || block.type === 'tool_result') {
          return <ToolExecutionCard key={idx} block={block} />
        }
        if (block.type === 'thinking') {
          return (
            <div key={idx} style={{ ...styles.assistantCard, opacity: 0.6, borderLeft: '3px solid var(--accent-blue)', fontSize: '13px' }}>
              <span style={{ fontWeight: 600, marginRight: '6px' }}>Thinking:</span>
              {block.text}
            </div>
          )
        }
        return null
      })}
    </div>
  )
}

/** Simple heuristic: extract Windows/Unix absolute paths from text. */
function extractFilePaths(text: string): string[] {
  const regex = /(?:[A-Z]:\\[^\s<>"]+|\/(?:home|usr|var|tmp|etc|opt|mnt)[^\s<>"]+)/g
  const matches = text.match(regex)
  if (!matches) return []
  // Deduplicate
  return [...new Set(matches)]
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CoworkPage() {
  const [taskSidebarOpen, setTaskSidebarOpen] = useState(true)
  const [skillsPanelOpen, setSkillsPanelOpen] = useState(true)
  // Fix reconnect undefined: use proper function from store
  const reconnect = () => useChatStore.getState().reconnectModeWs(MODE)
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const {
    modeMessages,
    modeStreaming,
    modeSessionId,
    abort,
    ws,
    setWs,
    setModeStreaming,
    addModeMessage,
    appendModeTextDelta,
    appendModeThinkingDelta,
    updateLastModeAssistant,
    setModeSession,
    clearModeMessages,
    currentModel,
    currentProvider,
    setModelLocal,
    isToolAllowed,
  } = useChatStore()

  const messages = modeMessages[MODE] || []
  const isStreaming = modeStreaming[MODE] || false
  const sessionId = modeSessionId[MODE] || null

  const { currentFolder, setCurrentFolder } = useLayoutStore()

  const [input, setInput] = useState('')
  const [taskName, setTaskName] = useState('New Task')
  const [editingTitle, setEditingTitle] = useState(false)
  const [folderDraft, setFolderDraft] = useState('')
  const [directories, setDirectories] = useState<{ path: string; label: string }[]>([])
  const [showFolderDropdown, setShowFolderDropdown] = useState(false)
  const messageEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  // Keep a ref to the page-local WebSocket so the handler can access it without
  // touching the shared store ws (which may belong to another page).
  const localWsRef = useRef<WebSocket | null>(null)

  // Load session history from URL param
  useEffect(() => {
    if (!urlSessionId) return
    const currentSessionId = useChatStore.getState().getModeSession(MODE)
    if (currentSessionId === urlSessionId && messages.length > 0) return

    fetch(`/api/sessions/${urlSessionId}`)
      .then((r) => {
        if (!r.ok) throw new Error('Session not found')
        return r.json()
      })
      .then((data: any) => {
        const s = useChatStore.getState()
        s.setModeSession(MODE, urlSessionId)

        // Restore folder context from session
        if (data.folder) {
          useLayoutStore.getState().setCurrentFolder(data.folder)
        }

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
        useChatStore.getState().setModeSession(MODE, urlSessionId)
      })
  }, [urlSessionId])

  // Auto-scroll
  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // WebSocket message handler
  const handleServerMessage = useCallback(
    (msg: Record<string, unknown>) => {
      const store = useChatStore.getState()
      switch (msg.type) {
        case 'session_info':
          store.setModeSession(MODE, msg.sessionId as string)
          if (msg.model && msg.provider) {
            store.setModelLocal(msg.model as string, msg.provider as string)
          }
          window.dispatchEvent(new CustomEvent('sessions-updated'))
          break

        case 'stream_start': {
          store.setModeStreaming(MODE, true)
          const { currentModel: model, currentProvider: provider } = useChatStore.getState()
          const assistantMsg: ChatMessage = {
            id: (msg.messageId as string) || crypto.randomUUID(),
            role: 'assistant',
            content: [],
            model,
            provider,
            timestamp: Date.now(),
            streaming: true,
          }
          store.addModeMessage(MODE, assistantMsg)
          break
        }

        case 'stream_delta':
          if (msg.contentType === 'text') store.appendModeTextDelta(MODE, msg.text as string)
          else if (msg.contentType === 'thinking') store.appendModeThinkingDelta(MODE, msg.text as string)
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

        case 'stream_end':
          store.setModeStreaming(MODE, false)
          store.updateLastModeAssistant(MODE, (m) => ({
            ...m,
            streaming: false,
            usage: msg.usage as { inputTokens: number; outputTokens: number } | undefined,
          }))
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
          if (store.isToolAllowed(toolName, sessionId || '')) {
            const sock = localWsRef.current
            if (sock && sock.readyState === WebSocket.OPEN) {
              sock.send(JSON.stringify({ type: 'permission_response', toolUseId: toolId, allowed: true }))
            }
          }
          break
        }

        case 'title_updated':
          window.dispatchEvent(new CustomEvent('sessions-updated'))
          break

        case 'model_switched':
          break
      }
    },
    []
  )

  // Get persistent WebSocket from store manager
  const wsStatus = useChatStore((s) => s.wsStatus[MODE] ?? 'disconnected')

  useEffect(() => {
    useChatStore.getState().connectModeWs(MODE, handleServerMessage)
  }, [])

  useEffect(() => {
    localWsRef.current = useChatStore.getState().getModeWs(MODE)
  }, [wsStatus])

  useEffect(() => {
    fetch('/api/files/directories')
      .then(r => r.json())
      .then(d => setDirectories(d.directories || []))
      .catch(() => {})
  }, [])

  // -- Handlers --

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return

    const sock = localWsRef.current
    if (!sock || sock.readyState !== WebSocket.OPEN) return

    const { currentModel: model, currentProvider: provider } = useChatStore.getState()
    const currentSessionId = useChatStore.getState().modeSessionId[MODE] || null

    // Add user message to mode state
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: [{ type: 'text', text: trimmed }],
      timestamp: Date.now(),
    }
    useChatStore.getState().addModeMessage(MODE, userMsg)

    // Send to server (include folder for session sandbox)
    sock.send(
      JSON.stringify({
        type: 'user_message',
        content: trimmed,
        sessionId: currentSessionId,
        mode: MODE,
        folder: currentFolder || undefined,
        model,
        provider,
      })
    )

    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = '44px'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = '44px'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }

  const handleSelectFolder = () => {
    const folder = folderDraft.trim()
    if (folder) setCurrentFolder(folder)
  }

  const handleNewTask = () => {
    useChatStore.getState().clearModeMessages(MODE)
    useChatStore.getState().setModeSession(MODE, null as unknown as string)
    setTaskName('New Task')
  }

  const handleAbort = () => {
    const sock = localWsRef.current
    if (sock?.readyState === WebSocket.OPEN) {
      sock.send(JSON.stringify({ type: 'abort' }))
    }
    useChatStore.getState().setModeStreaming(MODE, false)
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  // Empty state — no folder selected or no messages
  if (!currentFolder && messages.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>&#128194;</div>
          <div style={styles.emptyTitle}>Start a new task</div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>
            Select a project folder to begin working with AI
          </div>
          <div style={{ position: 'relative', width: '100%', maxWidth: '400px' }}>
            <select
              style={{ ...styles.folderInput, cursor: 'pointer' }}
              value={folderDraft}
              onChange={(e) => {
                const val = e.target.value
                if (val === '__custom__') {
                  setShowFolderDropdown(false)
                } else {
                  setFolderDraft(val)
                  setCurrentFolder(val)
                }
              }}
            >
              <option value="">選擇資料夾...</option>
              {directories.map(d => (
                <option key={d.path} value={d.path}>{d.label} ({d.path})</option>
              ))}
              <option value="__custom__">自訂路徑...</option>
            </select>
          </div>
          <div style={{ display: 'flex', gap: '8px', marginTop: '8px', width: '100%', maxWidth: '400px' }}>
            <input
              type="file"
              id="folder-browse"
              // @ts-ignore - webkitdirectory is a non-standard but widely supported attribute
              webkitdirectory=""
              style={{ display: 'none' }}
              onChange={(e) => {
                const files = e.target.files
                if (files && files.length > 0) {
                  const folderPath = files[0].webkitRelativePath.split('/')[0]
                  setFolderDraft(folderPath)
                  setCurrentFolder(folderPath)
                }
              }}
            />
            <label htmlFor="folder-browse" style={{ ...styles.browseBtn, cursor: 'pointer' }}>
              <span>&#128193;</span> Browse Folders
            </label>
            {showFolderDropdown && (
              <input
                style={{ ...styles.folderInput, flex: 1 }}
                placeholder="C:\Users\Chris\Desktop\project"
                value={folderDraft}
                onChange={(e) => setFolderDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSelectFolder() }}
                autoFocus
              />
            )}
          </div>
          <button style={styles.startBtn} onClick={handleSelectFolder}>Open Folder</button>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {/* Overlay: left Task Sidebar */}
      {taskSidebarOpen && (
        <aside style={{ position: 'absolute', left: 12, top: 72, width: 260, bottom: 12, overflow: 'auto', padding: 12, background: colors.cardBg, border: `1px solid ${colors.cardBorder}`, borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>Tasks</strong>
            <button onClick={() => setTaskSidebarOpen(false)} style={{ fontSize: 12 }}>Hide</button>
          </div>
          <div style={{ height: 8 }} />
          {[
            { id: 1, title: 'Task 1', progress: 40 },
            { id: 2, title: 'Task 2', progress: 70 },
            { id: 3, title: 'Task 3', progress: 25 },
          ].map(t => (
            <div key={t.id} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#ddd' }}>{t.title}</span>
                <span style={{ color: '#aaa' }}>{t.progress}%</span>
              </div>
              <div style={{ height: 6, borderRadius: 6, background: colors.cardBorder, marginTop: 6, overflow: 'hidden' }}>
                <div style={{ width: `${t.progress}%`, height: '100%', background: '#4ade80' }} />
              </div>
            </div>
          ))}
        </aside>
      )}
      {/* Overlay: right Skills panel */}
      {skillsPanelOpen && (
        <aside style={{ position: 'absolute', right: 12, top: 72, width: 260, bottom: 12, overflow: 'auto', padding: 12, background: colors.cardBg, border: `1px solid ${colors.cardBorder}`, borderRadius: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>Skills</strong>
            <button onClick={() => setSkillsPanelOpen(false)} style={{ fontSize: 12 }}>Hide</button>
          </div>
          <div style={{ height: 8 }} />
          {['TypeScript','React','Design'].map((s) => (
            <div key={s} style={{ padding: '6px 10px', border: `1px solid ${colors.cardBorder}`, borderRadius: 6, marginBottom: 8 }}>
              {s}
            </div>
          ))}
        </aside>
      )}
      {/* Header */}
      <div style={styles.header}>
        <div style={{ flex: 1 }}>
          <div style={styles.breadcrumb}>{currentFolder || 'No folder'} / {taskName}</div>
          <div style={styles.taskTitle}>
            {editingTitle ? (
              <input
                autoFocus
                style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', fontSize: '15px', fontWeight: 600, outline: 'none', padding: 0 }}
                value={taskName}
                onChange={(e) => setTaskName(e.target.value)}
                onBlur={() => setEditingTitle(false)}
                onKeyDown={(e) => { if (e.key === 'Enter') setEditingTitle(false) }}
              />
            ) : (
              <>
                {taskName}
                <button style={styles.editBtn} onClick={() => setEditingTitle(true)} title="Edit task name">&#9998;</button>
              </>
            )}
          </div>
        </div>
        <button style={styles.newTaskBtn} onClick={handleNewTask} title="Start a new task">
          + New Task
        </button>
      </div>

      {/* Messages */}
      <div style={styles.messageArea}>
        {messages.length === 0 ? (
          <div style={{ ...styles.emptyState, height: '100%' }}>
            <div style={{ fontSize: '36px', opacity: 0.4 }}>&#9997;&#65039;</div>
            <div style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>Describe your task to get started</div>
          </div>
        ) : (
          <div style={styles.messagesInner}>
            {messages.map((msg) => (
              <MessageBlock key={msg.id} message={msg} />
            ))}
            <div ref={messageEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div style={styles.inputArea}>
        {wsStatus !== 'connected' && (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
            padding: '6px 12px', marginBottom: '8px', borderRadius: '8px',
            background: wsStatus === 'reconnecting' ? 'rgba(210,153,34,0.15)' : 'rgba(248,81,73,0.15)',
            color: wsStatus === 'reconnecting' ? '#d29922' : '#f85149',
            fontSize: '13px',
          }}>
            <span>{wsStatus === 'reconnecting' ? 'Reconnecting...' : wsStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}</span>
            {wsStatus === 'disconnected' && (
              <button onClick={() => reconnect()} style={{
                padding: '2px 10px', borderRadius: '6px', border: '1px solid #f85149',
                background: 'transparent', color: '#f85149', fontSize: '12px', cursor: 'pointer',
              }}>Reconnect</button>
            )}
          </div>
        )}
        <div style={styles.inputWrapper}>
          <button style={styles.attachBtn} title="Attach files">&#65291;</button>
          <textarea
            ref={textareaRef}
            style={styles.textarea}
            placeholder="Reply..."
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button style={styles.modelSelector}>
            {currentModel || 'Model'} &#9662;
          </button>
          <button style={styles.micBtn} title="Voice input">&#127908;</button>
          {isStreaming ? (
            <button style={styles.stopBtn} onClick={handleAbort}>Stop</button>
          ) : (
            <button
              style={styles.sendBtn(input.trim().length > 0 && wsStatus === 'connected')}
              onClick={handleSend}
              disabled={!input.trim() || wsStatus !== 'connected'}
            >
              Send
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useChatStore, type ChatMessage, type ContentBlock } from '../stores/chatStore.ts'
import { useLayoutStore } from '../stores/layoutStore.ts'

const MODE = 'code'

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const colors = {
  cardBg: '#1b1b1f',
  cardBorder: '#2a2a2e',
  warningBg: 'rgba(250, 163, 50, 0.12)',
  warningBorder: 'rgba(250, 163, 50, 0.35)',
  warningText: '#faa332',
  accentOrange: '#f97316',
  tableBorder: '#3a3a3e',
  codeBg: '#16161a',
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
  },

  // -- Header --
  header: {
    padding: '12px 20px',
    borderBottom: `1px solid ${colors.cardBorder}`,
    background: colors.cardBg,
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexShrink: 0,
  },
  headerTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    flex: 1,
  },

  // -- Warning banner --
  warningBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 16px',
    margin: '0',
    background: colors.warningBg,
    borderBottom: `1px solid ${colors.warningBorder}`,
    fontSize: '13px',
    color: colors.warningText,
    flexShrink: 0,
  },
  warningLink: {
    color: colors.warningText,
    textDecoration: 'underline',
    cursor: 'pointer',
    marginLeft: '4px',
    fontSize: '13px',
    background: 'none',
    border: 'none',
    padding: 0,
  },
  dismissBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    color: colors.warningText,
    cursor: 'pointer',
    fontSize: '16px',
    padding: '0 4px',
    lineHeight: 1,
  },

  // -- Scrollable body --
  messageArea: {
    flex: 1,
    overflow: 'auto',
    padding: '20px',
  },
  messagesInner: {
    maxWidth: '960px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
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
    background: colors.accentOrange,
    color: '#fff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },

  // -- Markdown content --
  markdownBlock: {
    fontSize: '14px',
    lineHeight: 1.7,
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap' as const,
  },
  heading: (level: number) => ({
    fontSize: `${22 - level * 2}px`,
    fontWeight: 700 as const,
    color: 'var(--text-primary)',
    margin: `${20 - level * 2}px 0 8px 0`,
    borderBottom: level <= 2 ? `1px solid ${colors.cardBorder}` : 'none',
    paddingBottom: level <= 2 ? '6px' : '0',
  }),
  codeBlock: {
    display: 'block',
    padding: '14px 16px',
    background: colors.codeBg,
    border: `1px solid ${colors.cardBorder}`,
    borderRadius: '8px',
    fontFamily: "'Fira Code', 'Cascadia Code', Consolas, monospace",
    fontSize: '13px',
    lineHeight: 1.6,
    color: '#e2e8f0',
    overflow: 'auto',
    whiteSpace: 'pre' as const,
    margin: '8px 0',
  },
  inlineCode: {
    padding: '2px 6px',
    background: colors.codeBg,
    border: `1px solid ${colors.cardBorder}`,
    borderRadius: '4px',
    fontFamily: "'Fira Code', Consolas, monospace",
    fontSize: '12px',
    color: '#f0abfc',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    margin: '8px 0',
    fontSize: '13px',
  },
  th: {
    padding: '8px 12px',
    background: colors.cardBg,
    border: `1px solid ${colors.tableBorder}`,
    fontWeight: 600,
    textAlign: 'left' as const,
    color: 'var(--text-secondary)',
  },
  td: {
    padding: '8px 12px',
    border: `1px solid ${colors.tableBorder}`,
    color: 'var(--text-secondary)',
  },
  blockquote: {
    borderLeft: `3px solid ${colors.accentOrange}`,
    padding: '8px 14px',
    margin: '8px 0',
    background: 'rgba(249,115,22,0.06)',
    color: 'var(--text-secondary)',
    fontSize: '14px',
  },
  list: {
    margin: '6px 0',
    paddingLeft: '24px',
    lineHeight: 1.7,
    color: 'var(--text-secondary)',
    fontSize: '14px',
  },

  // -- Tool card (collapsed by default) --
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

  // -- Input area --
  inputArea: {
    borderTop: `1px solid ${colors.cardBorder}`,
    padding: '12px 20px',
    background: colors.cardBg,
    flexShrink: 0,
  },
  inputRow: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: '8px',
    maxWidth: '960px',
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
    flexShrink: 0,
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
  bypassToggle: (active: boolean) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 10px',
    borderRadius: '8px',
    border: `1px solid ${active ? colors.warningBorder : colors.cardBorder}`,
    background: active ? colors.warningBg : 'transparent',
    color: active ? colors.warningText : 'var(--text-muted)',
    fontSize: '11px',
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
    flexShrink: 0,
  }),
  modelSelector: {
    padding: '6px 10px',
    borderRadius: '8px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'transparent',
    color: 'var(--text-secondary)',
    fontSize: '12px',
    cursor: 'pointer',
    whiteSpace: 'nowrap' as const,
    flexShrink: 0,
  },
  sendBtn: (active: boolean) => ({
    padding: '8px 14px',
    borderRadius: '10px',
    border: 'none',
    background: active ? colors.accentOrange : 'var(--bg-tertiary)',
    color: active ? '#fff' : 'var(--text-muted)',
    fontSize: '16px',
    fontWeight: 600,
    cursor: active ? 'pointer' : 'default',
    transition: 'all 0.15s',
    lineHeight: 1,
    flexShrink: 0,
  }),
  stopBtn: {
    padding: '8px 14px',
    borderRadius: '10px',
    border: '1px solid var(--accent-red)',
    background: 'transparent',
    color: 'var(--accent-red)',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
    flexShrink: 0,
  },
  belowInput: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    maxWidth: '960px',
    margin: '6px auto 0',
    fontSize: '11px',
    color: 'var(--text-muted)',
  },
  folderIndicator: {
    fontFamily: 'monospace',
    fontSize: '11px',
    color: 'var(--text-muted)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  planToggle: {
    padding: '2px 8px',
    borderRadius: '4px',
    border: `1px solid ${colors.cardBorder}`,
    background: 'transparent',
    color: 'var(--text-muted)',
    fontSize: '11px',
    cursor: 'pointer',
  },
  newChatBtn: {
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
// Simple Markdown Renderer
// ---------------------------------------------------------------------------

function SimpleMarkdown({ text }: { text: string }) {
  const lines = text.split('\n')
  const elements: JSX.Element[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]!

    // Code block
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim()
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i]!.startsWith('```')) {
        codeLines.push(lines[i]!)
        i++
      }
      i++ // skip closing ```
      elements.push(
        <pre key={elements.length} style={styles.codeBlock}>
          {lang && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>{lang}</div>}
          <code>{codeLines.join('\n')}</code>
        </pre>
      )
      continue
    }

    // Heading
    const headingMatch = line.match(/^(#{1,6})\s+(.*)/)
    if (headingMatch) {
      const level = headingMatch[1]!.length
      elements.push(
        <div key={elements.length} style={styles.heading(level)}>{headingMatch[2]}</div>
      )
      i++
      continue
    }

    // Table — collect rows starting with |
    if (line.trimStart().startsWith('|')) {
      const tableLines: string[] = []
      while (i < lines.length && lines[i]!.trimStart().startsWith('|')) {
        tableLines.push(lines[i]!)
        i++
      }
      elements.push(<MarkdownTable key={elements.length} lines={tableLines} />)
      continue
    }

    // Blockquote
    if (line.startsWith('>')) {
      elements.push(
        <div key={elements.length} style={styles.blockquote}>{line.replace(/^>\s?/, '')}</div>
      )
      i++
      continue
    }

    // Unordered list
    if (/^\s*[-*]\s/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*[-*]\s/.test(lines[i]!)) {
        items.push(lines[i]!.replace(/^\s*[-*]\s/, ''))
        i++
      }
      elements.push(
        <ul key={elements.length} style={styles.list}>
          {items.map((item, idx) => <li key={idx}>{renderInline(item)}</li>)}
        </ul>
      )
      continue
    }

    // Ordered list
    if (/^\s*\d+\.\s/.test(line)) {
      const items: string[] = []
      while (i < lines.length && /^\s*\d+\.\s/.test(lines[i]!)) {
        items.push(lines[i]!.replace(/^\s*\d+\.\s/, ''))
        i++
      }
      elements.push(
        <ol key={elements.length} style={styles.list}>
          {items.map((item, idx) => <li key={idx}>{renderInline(item)}</li>)}
        </ol>
      )
      continue
    }

    // Empty line
    if (line.trim() === '') {
      i++
      continue
    }

    // Paragraph
    elements.push(
      <p key={elements.length} style={{ margin: '4px 0', color: 'var(--text-secondary)' }}>{renderInline(line)}</p>
    )
    i++
  }

  return <div style={styles.markdownBlock}>{elements}</div>
}

function renderInline(text: string): (string | JSX.Element)[] {
  const parts: (string | JSX.Element)[] = []
  // Simple: bold, inline code
  const regex = /(`[^`]+`|\*\*[^*]+\*\*)/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index))
    const seg = match[0]!
    if (seg.startsWith('`')) {
      parts.push(<code key={key++} style={styles.inlineCode}>{seg.slice(1, -1)}</code>)
    } else if (seg.startsWith('**')) {
      parts.push(<strong key={key++}>{seg.slice(2, -2)}</strong>)
    }
    lastIndex = match.index + seg.length
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex))
  return parts
}

function MarkdownTable({ lines }: { lines: string[] }) {
  const parseRow = (line: string) =>
    line.split('|').map((c) => c.trim()).filter((c) => c.length > 0)

  if (lines.length < 2) return null
  const headerCells = parseRow(lines[0]!)
  // Skip separator row (index 1)
  const bodyRows = lines.slice(2).map(parseRow)

  return (
    <table style={styles.table}>
      <thead>
        <tr>
          {headerCells.map((cell, idx) => <th key={idx} style={styles.th}>{cell}</th>)}
        </tr>
      </thead>
      <tbody>
        {bodyRows.map((row, rIdx) => (
          <tr key={rIdx}>
            {row.map((cell, cIdx) => <td key={cIdx} style={styles.td}>{cell}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ToolExecutionCard({ block }: { block: ContentBlock }) {
  const [expanded, setExpanded] = useState(false)
  const input = block.input ? JSON.stringify(block.input, null, 2) : ''
  const output = block.content || ''
  const isError = block.is_error

  return (
    <div style={styles.toolCard}>
      <div style={styles.toolHeader} onClick={() => setExpanded(!expanded)}>
        <span style={styles.toolName}>
          {block.type === 'tool_use' ? block.name || 'tool' : `Result: ${block.tool_use_id}`}
        </span>
        <span style={styles.toolToggle}>{expanded ? '-- collapse' : '+ expand'}</span>
      </div>
      {expanded && (
        <div style={{ ...styles.toolBody, borderLeft: isError ? '3px solid #f87171' : `3px solid ${colors.accentOrange}` }}>
          {block.type === 'tool_use' && input && <div>{input}</div>}
          {block.type === 'tool_result' && <div>{output}</div>}
        </div>
      )}
    </div>
  )
}

function FileTreeItem({ name, isFolder, children, defaultExpanded }: { name: string; isFolder?: boolean; children?: React.ReactNode; defaultExpanded?: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded ?? false)
  const icon = isFolder ? (expanded ? '📂' : '📁') : '📄'
  return (
    <div>
      <div
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 6px', cursor: isFolder ? 'pointer' : 'default', borderRadius: 4, fontSize: 13, color: 'var(--text-secondary)' }}
        onClick={() => isFolder && setExpanded(!expanded)}
      >
        <span style={{ fontSize: 14 }}>{icon}</span>
        <span style={{ flex: 1 }}>{name}</span>
      </div>
      {isFolder && expanded && <div style={{ paddingLeft: 16 }}>{children}</div>}
    </div>
  )
}

function MessageBlock({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    const text = message.content.map((b) => b.text || '').join('')
    return (
      <div style={{ padding: '10px 14px', background: 'rgba(249,115,22,0.08)', border: `1px solid rgba(249,115,22,0.2)`, borderRadius: '8px', fontSize: '14px', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
        <span style={{ fontSize: '12px', color: colors.accentOrange, fontWeight: 600, marginRight: '8px' }}>You:</span>
        {text}
      </div>
    )
  }

  if (message.role === 'system') {
    const text = message.content.map((b) => b.text || '').join('')
    return (
      <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '8px', fontSize: '13px', color: '#f87171', whiteSpace: 'pre-wrap' }}>
        {text}
      </div>
    )
  }

  // assistant — render as markdown
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {message.content.map((block, idx) => {
        if (block.type === 'text') {
          return (
            <div key={idx}>
              <SimpleMarkdown text={block.text || ''} />
              {message.streaming && idx === message.content.length - 1 && (
                <span style={{ opacity: 0.5 }}> &#9646;</span>
              )}
            </div>
          )
        }
        if (block.type === 'tool_use' || block.type === 'tool_result') {
          return <ToolExecutionCard key={idx} block={block} />
        }
        if (block.type === 'thinking') {
          return (
            <div key={idx} style={{ padding: '8px 12px', borderLeft: `3px solid ${colors.accentOrange}`, opacity: 0.6, fontSize: '13px', color: 'var(--text-muted)', whiteSpace: 'pre-wrap' }}>
              <span style={{ fontWeight: 600, marginRight: '6px' }}>Thinking:</span>{block.text}
            </div>
          )
        }
        return null
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CodeModePage() {
  // Overlay panels for IDE-like UI
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [leftWidth, setLeftWidth] = useState<number>(260)
  const [rightWidth, setRightWidth] = useState<number>(320)
  const [terminalOpen, setTerminalOpen] = useState<boolean>(true)
  const reconnect = () => useChatStore.getState().reconnectModeWs(MODE)
  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>()
  const {
    modeMessages,
    modeStreaming,
    modeSessionId,
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
    permissionMode,
    setPermissionMode,
    isToolAllowed,
  } = useChatStore()

  const messages = modeMessages[MODE] || []
  const isStreaming = modeStreaming[MODE] || false
  const sessionId = modeSessionId[MODE] || null

  const { currentFolder, setCurrentFolder } = useLayoutStore()

  const [files, setFiles] = useState<{ name: string; path: string; isDirectory: boolean; isFile: boolean }[]>([])
  const [filesLoading, setFilesLoading] = useState(false)

  const [terminalOutput, setTerminalOutput] = useState<{ cmd: string; output: string; isError: boolean }[]>([])
  const [terminalInput, setTerminalInput] = useState('')
  const [terminalLoading, setTerminalLoading] = useState(false)

  const [input, setInput] = useState('')
  const [showWarning, setShowWarning] = useState(true)
  const [bypassPermissions, setBypassPermissions] = useState(false)
  const [folderDraft, setFolderDraft] = useState('')
  const [directories, setDirectories] = useState<{ path: string; label: string }[]>([])
  const [showFolderDropdown, setShowFolderDropdown] = useState(false)
  const [planEnabled, setPlanEnabled] = useState(false)
  const messageEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  // Page-local WebSocket ref
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

  useEffect(() => {
    if (!currentFolder) {
      setFiles([])
      return
    }
    setFilesLoading(true)
    fetch(`/api/files?path=${encodeURIComponent(currentFolder)}`)
      .then((r) => r.json())
      .then((d) => setFiles(d.files || []))
      .catch(() => setFiles([]))
      .finally(() => setFilesLoading(false))
  }, [currentFolder])

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
          const shouldAutoApprove = store.isToolAllowed(toolName, sessionId || '') || permissionMode === 'always-allow'
          if (shouldAutoApprove) {
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

  const wsStatus = useChatStore((s) => s.wsStatus[MODE] ?? 'disconnected')

  useEffect(() => {
    useChatStore.getState().connectModeWs(MODE, handleServerMessage)
  }, [])

  useEffect(() => {
    localWsRef.current = useChatStore.getState().getModeWs(MODE)
  }, [wsStatus])

  // Sync bypass toggle with store permission mode
  useEffect(() => {
    if (bypassPermissions) {
      setPermissionMode('always-allow')
      setShowWarning(true)
    } else {
      setPermissionMode('ask')
    }
  }, [bypassPermissions, setPermissionMode])

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

  const handleNewChat = () => {
    useChatStore.getState().clearModeMessages(MODE)
    useChatStore.getState().setModeSession(MODE, null as unknown as string)
  }

  const handleAbort = () => {
    const sock = localWsRef.current
    if (sock?.readyState === WebSocket.OPEN) {
      sock.send(JSON.stringify({ type: 'abort' }))
    }
    useChatStore.getState().setModeStreaming(MODE, false)
  }

  const executeTerminalCommand = async (cmd: string) => {
    setTerminalLoading(true)
    setTerminalOutput((prev) => [...prev, { cmd, output: 'Executing...', isError: false }])
    try {
      const res = await fetch('/api/shell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, cwd: currentFolder || undefined }),
      })
      const data = await res.json()
      setTerminalOutput((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { cmd, output: data.output || data.error || 'Done', isError: data.isError || !!data.error }
        return updated
      })
    } catch {
      setTerminalOutput((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { cmd, output: 'Command failed', isError: true }
        return updated
      })
    } finally {
      setTerminalLoading(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  // Empty state
  if (!currentFolder && messages.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.emptyState}>
          <div style={styles.emptyIcon}>&#128269;</div>
          <div style={styles.emptyTitle}>Select a project to analyze</div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>
            Enter a project folder path to begin code analysis
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
          <button style={styles.startBtn} onClick={handleSelectFolder}>Analyze Project</button>
        </div>
      </div>
    )
  }

  return (
    <div style={{ ...styles.container, position: 'relative' }}>
      {/* Header */}
      <div style={{ ...styles.header, gap: 8 }}>
        <div style={styles.headerTitle}>Code Analysis</div>
        <button onClick={() => setLeftOpen(!leftOpen)} style={{ ...styles.newChatBtn, opacity: leftOpen ? 1 : 0.6 }} title="Toggle file tree">
          {leftOpen ? '📂' : '📁'}
        </button>
        <button onClick={() => setTerminalOpen(!terminalOpen)} style={{ ...styles.newChatBtn, opacity: terminalOpen ? 1 : 0.6 }} title="Toggle terminal">
          {terminalOpen ? '🖥' : '⌨️'}
        </button>
        <button onClick={() => setRightOpen(!rightOpen)} style={{ ...styles.newChatBtn, opacity: rightOpen ? 1 : 0.6 }} title="Toggle problems">
          {rightOpen ? '⚠️' : '✓'}
        </button>
        <button style={styles.newChatBtn} onClick={handleNewChat} title="Start a new chat">
          + New Chat
        </button>
      </div>

      {/* Warning banner */}
      {bypassPermissions && showWarning && (
        <div style={styles.warningBanner}>
          <span>&#9888;</span>
          <span>
            Bypass permissions mode: Claude can take actions without asking for confirmation.
            <button style={styles.warningLink}>See safe use tips</button>
          </span>
          <button style={styles.dismissBtn} onClick={() => setShowWarning(false)}>&times;</button>
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {leftOpen && (
          <div style={{ width: leftWidth, borderRight: `1px solid ${colors.cardBorder}`, background: colors.cardBg, overflow: 'auto', flexShrink: 0 }}>
            <div style={{ padding: '8px 12px', borderBottom: `1px solid ${colors.cardBorder}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>EXPLORER</span>
              <button onClick={() => setLeftOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>✕</button>
            </div>
            <div style={{ padding: 8 }}>
              {filesLoading ? (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: 8 }}>Loading...</div>
              ) : !currentFolder ? (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: 8 }}>Select a folder first</div>
              ) : files.length === 0 ? (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: 8 }}>Empty folder</div>
              ) : (
                files.map((file) => (
                  <FileTreeItem key={file.path} name={file.name} isFolder={file.isDirectory} />
                ))
              )}
            </div>
          </div>
        )}

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ ...styles.messageArea, flex: terminalOpen ? 1 : undefined }}>
        {messages.length === 0 ? (
          <div style={{ ...styles.emptyState, height: '100%' }}>
            <div style={{ fontSize: '36px', opacity: 0.4 }}>&#128187;</div>
            <div style={{ fontSize: '16px', color: 'var(--text-secondary)' }}>Enter a query to analyze your project</div>
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
        <div style={styles.inputRow}>
          <button style={styles.attachBtn} title="Attach files">&#65291;</button>
          <textarea
            ref={textareaRef}
            style={styles.textarea}
            placeholder="Enter a query..."
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button
            style={styles.bypassToggle(bypassPermissions)}
            onClick={() => setBypassPermissions(!bypassPermissions)}
            title="Toggle bypass permissions"
          >
            &#9888; Bypass
          </button>
          <button style={styles.modelSelector}>
            {currentModel || 'Opus 4.6'} &#9662;
          </button>
          {isStreaming ? (
            <button style={styles.stopBtn} onClick={handleAbort}>Stop</button>
          ) : (
            <button
              style={styles.sendBtn(input.trim().length > 0 && wsStatus === 'connected')}
              onClick={handleSend}
              disabled={!input.trim() || wsStatus !== 'connected'}
              title="Send"
            >
              &#10148;
            </button>
          )}
        </div>

        {/* Below input controls */}
        <div style={styles.belowInput}>
          <span style={styles.folderIndicator}>{currentFolder || 'No folder selected'}</span>
          <button
            style={{ ...styles.planToggle, borderColor: planEnabled ? colors.accentOrange : colors.cardBorder, color: planEnabled ? colors.accentOrange : 'var(--text-muted)' }}
            onClick={() => setPlanEnabled(!planEnabled)}
          >
            Plan {planEnabled ? 'ON' : 'OFF'}
          </button>
          <span style={styles.folderIndicator}>{currentFolder || 'No folder selected'}</span>
          <button
            style={{ ...styles.planToggle, borderColor: planEnabled ? colors.accentOrange : colors.cardBorder, color: planEnabled ? colors.accentOrange : 'var(--text-muted)' }}
            onClick={() => setPlanEnabled(!planEnabled)}
          >
            Plan {planEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
        </div>
        {terminalOpen && (
          <div style={{ height: 200, borderTop: `1px solid ${colors.cardBorder}`, background: colors.cardBg, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
            <div style={{ padding: '6px 12px', borderBottom: `1px solid ${colors.cardBorder}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>TERMINAL</span>
              <button onClick={() => setTerminalOutput([])} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 11 }}>Clear</button>
            </div>
            <div style={{ flex: 1, overflow: 'auto', padding: '8px 12px', fontFamily: 'monospace', fontSize: 12, color: '#9ca3af' }}>
              {terminalOutput.length === 0 && (
                <div style={{ color: '#6b7280' }}>Type a command and press Enter</div>
              )}
              {terminalOutput.map((line, i) => (
                <div key={i} style={{ marginBottom: 4 }}>
                  <span style={{ color: '#4ade80' }}>$</span> {line.cmd}
                  {line.output && <div style={{ color: line.isError ? '#f87171' : '#d1d5db', whiteSpace: 'pre-wrap' }}>{line.output}</div>}
                </div>
              ))}
            </div>
            <div style={{ padding: '6px 12px', borderTop: `1px solid ${colors.cardBorder}`, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: '#4ade80', fontFamily: 'monospace', fontSize: 12 }}>$</span>
              <input
                style={{ flex: 1, background: 'transparent', border: 'none', color: '#e6e6e6', fontSize: 12, fontFamily: 'monospace', outline: 'none' }}
                value={terminalInput}
                onChange={(e) => setTerminalInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && terminalInput.trim()) {
                    executeTerminalCommand(terminalInput)
                    setTerminalInput('')
                  }
                }}
                placeholder="Enter command..."
                disabled={terminalLoading}
              />
            </div>
          </div>
        )}
        </div>
        {rightOpen && (
          <div style={{ width: rightWidth, borderLeft: `1px solid ${colors.cardBorder}`, background: colors.cardBg, overflow: 'auto', flexShrink: 0 }}>
            <div style={{ padding: '8px 12px', borderBottom: `1px solid ${colors.cardBorder}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>PROBLEMS</span>
              <button onClick={() => setRightOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 12 }}>✕</button>
            </div>
            <div style={{ padding: 8, fontSize: 12 }}>
              <div style={{ color: '#f87171', marginBottom: 8 }}>3 errors</div>
              <div style={{ padding: '4px 8px', color: '#9ca3af', marginBottom: 4, borderLeft: '2px solid #f87171' }}>
                <div>src/utils/api.ts:12</div>
                <div style={{ color: '#ef4444' }}>Cannot find name 'fetch'</div>
              </div>
              <div style={{ padding: '4px 8px', color: '#9ca3af', marginBottom: 4, borderLeft: '2px solid #f87171' }}>
                <div>src/components/App.tsx:45</div>
                <div style={{ color: '#ef4444' }}>Property 'map' does not exist</div>
              </div>
              <div style={{ color: '#facc15', marginBottom: 8, marginTop: 16 }}>2 warnings</div>
              <div style={{ padding: '4px 8px', color: '#9ca3af', marginBottom: 4, borderLeft: '2px solid #facc15' }}>
                <div>src/index.ts:5</div>
                <div style={{ color: '#eab308' }}>Unused variable 'x'</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

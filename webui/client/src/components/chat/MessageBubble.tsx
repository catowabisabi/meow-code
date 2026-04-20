import { useState } from 'react'
import type { ChatMessage, ContentBlock } from '../../stores/chatStore.ts'
import CodeBlock from '../shared/CodeBlock.tsx'

// ── Avatars ──────────────────────────────────────────────────────

function CatoAvatar() {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: '50%',
      background: 'linear-gradient(135deg, #cc785c 0%, #a0522d 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, fontSize: 13, fontWeight: 700, color: '#fff',
      letterSpacing: '-0.5px', userSelect: 'none',
    }}>
      C
    </div>
  )
}

function UserAvatar() {
  return (
    <div style={{
      width: 28, height: 28, borderRadius: '50%',
      background: '#2e2e35',
      border: '1px solid #3a3a42',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, fontSize: 13, color: '#9e9e9e',
      userSelect: 'none',
    }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/>
      </svg>
    </div>
  )
}

// ── Markdown renderer ─────────────────────────────────────────────

function renderMarkdown(text: string): JSX.Element[] {
  const elements: JSX.Element[] = []
  const lines = text.split('\n')
  let i = 0

  while (i < lines.length) {
    const line = lines[i]!

    if (line.startsWith('```')) {
      const lang = line.slice(3).trim()
      const codeLines: string[] = []
      i++
      while (i < lines.length && !lines[i]!.startsWith('```')) {
        codeLines.push(lines[i]!)
        i++
      }
      i++
      elements.push(
        <CodeBlock key={elements.length} code={codeLines.join('\n')} language={lang || 'text'} />
      )
      continue
    }

    if (line.startsWith('### ')) {
      elements.push(<h3 key={elements.length} style={{ fontSize: '14px', margin: '14px 0 6px', fontWeight: 600, color: 'var(--text-primary)' }}>{renderInline(line.slice(4))}</h3>)
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={elements.length} style={{ fontSize: '15px', margin: '16px 0 6px', fontWeight: 600, color: 'var(--text-primary)' }}>{renderInline(line.slice(3))}</h2>)
    } else if (line.startsWith('# ')) {
      elements.push(<h1 key={elements.length} style={{ fontSize: '17px', margin: '18px 0 8px', fontWeight: 700, color: 'var(--text-primary)' }}>{renderInline(line.slice(2))}</h1>)
    } else if (/^\d+\.\s/.test(line)) {
      elements.push(<div key={elements.length} style={{ paddingLeft: '20px', marginBottom: '2px' }}>
        <span style={{ color: 'var(--text-muted)', marginRight: '6px' }}>{line.match(/^\d+/)![0]}.</span>
        {renderInline(line.replace(/^\d+\.\s/, ''))}
      </div>)
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(<div key={elements.length} style={{ paddingLeft: '16px', marginBottom: '2px', display: 'flex', gap: '8px' }}>
        <span style={{ color: 'var(--text-muted)', flexShrink: 0, marginTop: '1px' }}>•</span>
        <span>{renderInline(line.slice(2))}</span>
      </div>)
    } else if (line.startsWith('> ')) {
      elements.push(<div key={elements.length} style={{
        borderLeft: '3px solid var(--border-focus)', paddingLeft: '12px',
        margin: '6px 0', color: 'var(--text-secondary)', fontStyle: 'italic',
      }}>{renderInline(line.slice(2))}</div>)
    } else if (line.trim() === '') {
      elements.push(<div key={elements.length} style={{ height: '10px' }} />)
    } else {
      elements.push(<div key={elements.length} style={{ marginBottom: '2px' }}>{renderInline(line)}</div>)
    }
    i++
  }

  return elements
}

function renderInline(text: string): JSX.Element {
  const parts: (string | JSX.Element)[] = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/)
    if (codeMatch) {
      if (codeMatch[1]) parts.push(codeMatch[1])
      parts.push(
        <code key={key++} style={{
          background: 'var(--bg-hover)', padding: '1px 6px', borderRadius: '4px',
          fontSize: '13px', fontFamily: "'SF Mono', 'Fira Code', 'Cascadia Code', monospace",
          color: '#cc785c', border: '1px solid var(--border-muted)',
        }}>
          {codeMatch[2]}
        </code>
      )
      remaining = codeMatch[3] || ''
      continue
    }

    const boldMatch = remaining.match(/^(.*?)\*\*([^*]+)\*\*(.*)$/)
    if (boldMatch) {
      if (boldMatch[1]) parts.push(boldMatch[1])
      parts.push(<strong key={key++} style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{boldMatch[2]}</strong>)
      remaining = boldMatch[3] || ''
      continue
    }

    const italicMatch = remaining.match(/^(.*?)_([^_]+)_(.*)$/)
    if (italicMatch) {
      if (italicMatch[1]) parts.push(italicMatch[1])
      parts.push(<em key={key++} style={{ color: 'var(--text-secondary)' }}>{italicMatch[2]}</em>)
      remaining = italicMatch[3] || ''
      continue
    }

    parts.push(remaining)
    break
  }

  return <span>{parts}</span>
}

// ── Think tags ────────────────────────────────────────────────────

function parseThinkTags(text: string): Array<{ kind: 'text' | 'think'; content: string }> {
  const result: Array<{ kind: 'text' | 'think'; content: string }> = []
  const regex = /<think>([\s\S]*?)<\/think>/g
  let lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      result.push({ kind: 'text', content: text.slice(lastIndex, match.index) })
    }
    result.push({ kind: 'think', content: match[1]! })
    lastIndex = regex.lastIndex
  }
  if (lastIndex < text.length) {
    result.push({ kind: 'text', content: text.slice(lastIndex) })
  }
  return result
}

// ── ThinkingBlock ─────────────────────────────────────────────────

function ThinkingBlock({ text, show, onToggle }: { text: string; show: boolean; onToggle: () => void }) {
  return (
    <div style={{ margin: '8px 0' }}>
      <button
        onClick={onToggle}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          background: 'none', border: '1px solid var(--border-default)',
          borderRadius: '6px', padding: '4px 10px', cursor: 'pointer',
          color: 'var(--text-muted)', fontSize: '12px', fontFamily: 'inherit',
          transition: 'all 0.12s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--border-focus)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-default)'; e.currentTarget.style.color = 'var(--text-muted)' }}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
        </svg>
        思考過程
        <span style={{ fontSize: '10px', transform: show ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s', display: 'inline-block' }}>▼</span>
      </button>
      {show && (
        <div style={{
          marginTop: '8px', padding: '12px 16px',
          background: 'var(--bg-tertiary)', borderRadius: '8px',
          borderLeft: '3px solid var(--accent-purple)',
          color: 'var(--text-secondary)', fontSize: '13px',
          fontStyle: 'italic', lineHeight: 1.6,
          whiteSpace: 'pre-wrap',
          animation: 'fadeIn 0.15s ease',
        }}>
          {text}
        </div>
      )}
    </div>
  )
}

// ── Tool summary ──────────────────────────────────────────────────

function toolSummary(name: string, input: Record<string, unknown> | undefined): string {
  const friendly: Record<string, string> = {
    web_search: 'Search', web_fetch: 'Fetch', file_read: 'Read',
    file_write: 'Write', file_edit: 'Edit', bash: 'Run', grep: 'Grep',
    glob: 'Glob', todo_write: 'Todo',
  }
  const label = friendly[name] || name
  if (!input) return label
  const val = input.query || input.command || input.url || input.path || input.pattern
  if (val && typeof val === 'string') {
    const short = val.length > 55 ? val.slice(0, 52) + '…' : val
    return `${label}: ${short}`
  }
  return label
}

function ToolUseCard({ name, input }: { name: string; input?: Record<string, unknown> }) {
  const [expanded, setExpanded] = useState(false)
  const summary = toolSummary(name, input)

  return (
    <div style={{
      margin: '6px 0', borderRadius: '8px',
      border: '1px solid var(--border-default)',
      background: 'var(--bg-tertiary)',
      overflow: 'hidden',
    }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 12px', cursor: input ? 'pointer' : 'default',
          userSelect: 'none',
        }}
        onClick={() => input && setExpanded(v => !v)}
      >
        <span style={{ fontSize: '13px' }}>⚙</span>
        <span style={{ flex: 1, fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>{summary}</span>
        {input && (
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', transform: expanded ? 'rotate(180deg)' : 'none', display: 'inline-block', transition: 'transform 0.15s' }}>▼</span>
        )}
      </div>
      {expanded && input && (
        <div style={{
          padding: '8px 12px', borderTop: '1px solid var(--border-muted)',
          fontSize: '12px', color: 'var(--text-secondary)',
          fontFamily: "'SF Mono', 'Fira Code', monospace",
          whiteSpace: 'pre-wrap', maxHeight: '160px', overflow: 'auto',
          background: 'var(--bg-secondary)',
        }}>
          {JSON.stringify(input, null, 2)}
        </div>
      )}
    </div>
  )
}

function ToolResultCard({ block }: { block: ContentBlock }) {
  const [expanded, setExpanded] = useState(false)
  const content = block.content || block.text || '(empty)'
  const isLong = content.length > 200

  return (
    <div style={{
      margin: '4px 0', borderRadius: '8px',
      border: `1px solid ${block.is_error ? 'rgba(248,113,113,0.3)' : 'var(--border-muted)'}`,
      background: block.is_error ? 'rgba(248,113,113,0.05)' : 'var(--bg-secondary)',
      overflow: 'hidden',
    }}>
      <div
        style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', cursor: isLong ? 'pointer' : 'default', userSelect: 'none' }}
        onClick={() => isLong && setExpanded(v => !v)}
      >
        <span style={{ fontSize: '12px' }}>{block.is_error ? '✗' : '✓'}</span>
        <span style={{ fontSize: '12px', color: block.is_error ? 'var(--accent-red)' : 'var(--text-muted)' }}>
          {block.is_error ? 'Error' : 'Result'}
        </span>
        {isLong && (
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: 'auto', transform: expanded ? 'rotate(180deg)' : 'none', display: 'inline-block', transition: 'transform 0.15s' }}>▼</span>
        )}
      </div>
      <div style={{
        padding: '0 12px 8px',
        fontSize: '12px', color: 'var(--text-secondary)',
        fontFamily: "'SF Mono', 'Fira Code', monospace",
        whiteSpace: 'pre-wrap',
        maxHeight: expanded || !isLong ? '320px' : '60px',
        overflow: 'hidden',
        transition: 'max-height 0.2s ease',
      }}>
        {content}
      </div>
    </div>
  )
}

// ── Cursor blink ──────────────────────────────────────────────────

function StreamCursor() {
  return (
    <span style={{
      display: 'inline-block', width: '2px', height: '16px',
      background: 'var(--accent-primary)', marginLeft: '2px',
      verticalAlign: 'text-bottom',
      animation: 'blink 1s ease-in-out infinite',
    }} />
  )
}

// ── Main export ───────────────────────────────────────────────────

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const [openThinking, setOpenThinking] = useState<Set<string>>(new Set())
  const toggleThinking = (key: string) => {
    setOpenThinking(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key); else next.add(key)
      return next
    })
  }

  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div style={{
        padding: '8px 16px', margin: '8px 0',
        background: 'rgba(248,113,113,0.08)',
        border: '1px solid rgba(248,113,113,0.2)',
        borderRadius: '8px', fontSize: '13px',
        color: 'var(--accent-red)',
        maxWidth: 'var(--chat-max-width)',
        marginLeft: 'auto', marginRight: 'auto',
      }}>
        {message.content.map((b, i) => b.type === 'text' ? <span key={i}>{b.text}</span> : null)}
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: '12px',
      padding: '10px 0',
      alignItems: 'flex-start',
      animation: 'fadeIn 0.15s ease',
    }}>
      {/* Avatar */}
      <div style={{ paddingTop: '2px', flexShrink: 0 }}>
        {isUser ? <UserAvatar /> : <CatoAvatar />}
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        minWidth: 0,
        maxWidth: isUser ? '75%' : '100%',
      }}>
        {/* Role label */}
        <div style={{
          fontSize: '12px', fontWeight: 600,
          color: 'var(--text-muted)',
          marginBottom: '6px',
          textAlign: isUser ? 'right' : 'left',
          letterSpacing: '0.3px',
          textTransform: 'uppercase',
        }}>
          {isUser ? 'You' : 'Cato'}
        </div>

        {/* Message content */}
        <div style={{
          background: isUser ? 'var(--bg-tertiary)' : 'transparent',
          borderRadius: isUser ? '12px 2px 12px 12px' : '0',
          padding: isUser ? '12px 16px' : '0',
          border: isUser ? '1px solid var(--border-default)' : 'none',
          fontSize: '14px',
          lineHeight: 1.7,
          color: 'var(--text-primary)',
          wordBreak: 'break-word',
        }}>
          {message.content.map((block, i) => {
            switch (block.type) {
              case 'text': {
                const segments = parseThinkTags(block.text || '')
                if (segments.length === 1 && segments[0]!.kind === 'text') {
                  return <div key={i}>{renderMarkdown(segments[0]!.content)}</div>
                }
                return (
                  <div key={i}>
                    {segments.map((seg, j) => {
                      const k = `${i}-${j}`
                      return seg.kind === 'think' ? (
                        <ThinkingBlock
                          key={k} text={seg.content}
                          show={openThinking.has(k)}
                          onToggle={() => toggleThinking(k)}
                        />
                      ) : (
                        <div key={k}>{renderMarkdown(seg.content)}</div>
                      )
                    })}
                  </div>
                )
              }

              case 'thinking': {
                const k = `think-${i}`
                return (
                  <ThinkingBlock
                    key={i} text={block.text || ''}
                    show={openThinking.has(k)}
                    onToggle={() => toggleThinking(k)}
                  />
                )
              }

              case 'tool_use':
                return <ToolUseCard key={i} name={block.name || block.id || ''} input={block.input as Record<string, unknown>} />

              case 'tool_result':
                return <ToolResultCard key={i} block={block} />

              default:
                return null
            }
          })}

          {message.streaming && <StreamCursor />}
        </div>

        {/* Meta */}
        {(message.model || message.usage) && (
          <div style={{
            display: 'flex', gap: '10px', marginTop: '6px',
            fontSize: '11px', color: 'var(--text-muted)',
            alignItems: 'center',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
          }}>
            {message.model && <span>{message.model}</span>}
            {message.usage && (
              <span>{(message.usage.inputTokens + message.usage.outputTokens).toLocaleString()} tokens</span>
            )}
            <span>{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        )}
      </div>
    </div>
  )
}

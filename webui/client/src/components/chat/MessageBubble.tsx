import { useState } from 'react'
import type { ChatMessage, ContentBlock } from '../../stores/chatStore.ts'
import CodeBlock from '../shared/CodeBlock.tsx'

const styles = {
  wrapper: (isUser: boolean) => ({
    display: 'flex',
    justifyContent: isUser ? 'flex-end' : 'flex-start',
    padding: '4px 20px',
    width: '100%',
  }),
  bubble: (isUser: boolean) => ({
    padding: '12px 16px',
    borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
    background: isUser ? '#1f6feb' : 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '14px',
    lineHeight: 1.6,
    wordBreak: 'break-word' as const,
    maxWidth: '100%',
    minWidth: isUser ? '80px' : '60px',
    width: 'fit-content',
  }),
  meta: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '4px',
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  thinkingToggle: {
    cursor: 'pointer',
    color: 'var(--accent-purple)',
    fontSize: '12px',
    padding: '4px 8px',
    borderRadius: '4px',
    background: 'rgba(188,140,255,0.1)',
    border: 'none',
    marginBottom: '8px',
  },
  thinkingContent: {
    padding: '8px 12px',
    margin: '4px 0 8px',
    borderLeft: '3px solid var(--accent-purple)',
    color: 'var(--text-secondary)',
    fontSize: '13px',
    fontStyle: 'italic' as const,
    lineHeight: 1.5,
    whiteSpace: 'pre-wrap' as const,
  },
  toolCard: {
    margin: '8px 0',
    padding: '10px 12px',
    borderRadius: '8px',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
  },
  toolName: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--accent-blue)',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  toolInput: {
    marginTop: '6px',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
    whiteSpace: 'pre-wrap' as const,
    maxHeight: '120px',
    overflow: 'auto',
  },
}

function renderMarkdown(text: string): JSX.Element[] {
  const elements: JSX.Element[] = []
  const lines = text.split('\n')
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
        <CodeBlock key={elements.length} code={codeLines.join('\n')} language={lang || 'text'} />
      )
      continue
    }

    // Headers
    if (line.startsWith('### ')) {
      elements.push(<h3 key={elements.length} style={{ fontSize: '15px', margin: '12px 0 6px', fontWeight: 600 }}>{line.slice(4)}</h3>)
    } else if (line.startsWith('## ')) {
      elements.push(<h2 key={elements.length} style={{ fontSize: '16px', margin: '12px 0 6px', fontWeight: 600 }}>{line.slice(3)}</h2>)
    } else if (line.startsWith('# ')) {
      elements.push(<h1 key={elements.length} style={{ fontSize: '18px', margin: '12px 0 6px', fontWeight: 700 }}>{line.slice(2)}</h1>)
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(<div key={elements.length} style={{ paddingLeft: '16px' }}>• {renderInline(line.slice(2))}</div>)
    } else if (line.trim() === '') {
      elements.push(<div key={elements.length} style={{ height: '8px' }} />)
    } else {
      elements.push(<div key={elements.length}>{renderInline(line)}</div>)
    }
    i++
  }

  return elements
}

function renderInline(text: string): JSX.Element {
  // Simple inline code and bold rendering
  const parts: (string | JSX.Element)[] = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // Inline code
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)$/)
    if (codeMatch) {
      if (codeMatch[1]) parts.push(codeMatch[1])
      parts.push(
        <code
          key={key++}
          style={{
            background: 'var(--bg-hover)',
            padding: '1px 5px',
            borderRadius: '3px',
            fontSize: '13px',
            fontFamily: 'monospace',
          }}
        >
          {codeMatch[2]}
        </code>
      )
      remaining = codeMatch[3] || ''
      continue
    }

    // Bold
    const boldMatch = remaining.match(/^(.*?)\*\*([^*]+)\*\*(.*)$/)
    if (boldMatch) {
      if (boldMatch[1]) parts.push(boldMatch[1])
      parts.push(<strong key={key++}>{boldMatch[2]}</strong>)
      remaining = boldMatch[3] || ''
      continue
    }

    parts.push(remaining)
    break
  }

  return <span>{parts}</span>
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const [showThinking, setShowThinking] = useState(false)
  const isUser = message.role === 'user'

  return (
    <div style={styles.wrapper(isUser)}>
      <div style={{ maxWidth: '80%', minWidth: isUser ? '80px' : undefined }}>
        <div style={styles.bubble(isUser)}>
          {message.content.map((block, i) => {
            switch (block.type) {
              case 'text':
                return <div key={i}>{renderMarkdown(block.text || '')}</div>

              case 'thinking':
                return (
                  <div key={i}>
                    <button
                      style={styles.thinkingToggle}
                      onClick={() => setShowThinking(!showThinking)}
                    >
                      {showThinking ? '▼' : '▶'} 思考過程
                    </button>
                    {showThinking && (
                      <div style={styles.thinkingContent}>{block.text}</div>
                    )}
                  </div>
                )

              case 'tool_use':
                return (
                  <div key={i} style={styles.toolCard}>
                    <div style={styles.toolName}>
                      <span>🔧</span>
                      <span>調用工具: {block.name || block.id}</span>
                    </div>
                    {block.input && (
                      <div style={styles.toolInput}>
                        {JSON.stringify(block.input, null, 2)}
                      </div>
                    )}
                  </div>
                )

              case 'tool_result':
                return (
                  <div key={i} style={styles.toolCard}>
                    <div style={styles.toolName}>
                      <span>{block.is_error ? '❌' : '✅'}</span>
                      <span>工具結果</span>
                    </div>
                    <div style={styles.toolInput}>
                      {block.content || block.text || '(empty)'}
                    </div>
                  </div>
                )

              default:
                return null
            }
          })}
          {message.streaming && (
            <span
              style={{
                display: 'inline-block',
                width: '8px',
                height: '16px',
                background: 'var(--accent-blue)',
                marginLeft: '2px',
                animation: 'blink 1s infinite',
              }}
            />
          )}
        </div>
        <div style={styles.meta}>
          {message.model && <span>{message.model}</span>}
          <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
          {message.usage && (
            <span>
              {message.usage.inputTokens + message.usage.outputTokens} tokens
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

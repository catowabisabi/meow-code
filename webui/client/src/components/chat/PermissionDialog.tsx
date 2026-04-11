/**
 * Permission dialog — shown when the AI tries to execute a high-risk tool.
 * Supports: Allow once, Always allow this tool, Allow all (skip future prompts).
 */
import { useState, useEffect } from 'react'

const styles = {
  overlay: {
    position: 'fixed' as const,
    bottom: '80px',
    right: '20px',
    zIndex: 9999,
  },
  card: {
    background: 'var(--bg-secondary)',
    border: '2px solid var(--accent-orange)',
    borderRadius: '12px',
    padding: '16px 20px',
    width: '440px',
    boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '12px',
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--accent-orange)',
  },
  description: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: 1.5,
    marginBottom: '12px',
  },
  inputPreview: {
    padding: '8px 12px',
    background: '#0d1117',
    borderRadius: '6px',
    fontSize: '12px',
    fontFamily: 'monospace',
    color: 'var(--text-primary)',
    maxHeight: '100px',
    overflow: 'auto',
    marginBottom: '12px',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-all' as const,
  },
  actions: {
    display: 'flex',
    gap: '6px',
    justifyContent: 'flex-end',
    flexWrap: 'wrap' as const,
  },
  btn: (variant: 'allow' | 'deny' | 'always' | 'all') => ({
    padding: '6px 14px',
    borderRadius: '6px',
    border: variant === 'deny' ? '1px solid var(--border-default)' : 'none',
    background:
      variant === 'allow' ? 'var(--accent-green)'
      : variant === 'always' ? 'var(--accent-blue)'
      : variant === 'all' ? 'var(--accent-purple)'
      : 'transparent',
    color:
      variant === 'deny' ? 'var(--accent-red)'
      : variant === 'all' ? '#fff'
      : variant === 'always' ? '#fff'
      : '#000',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
  }),
  timer: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '8px',
    textAlign: 'right' as const,
  },
}

interface Props {
  toolName: string
  toolId: string
  input: Record<string, unknown>
  description: string
  onDecision: (toolId: string, allowed: boolean) => void
  onAlwaysAllow: (toolName: string) => void
}

export default function PermissionDialog({
  toolName, toolId, input, description,
  onDecision, onAlwaysAllow,
}: Props) {
  const [countdown, setCountdown] = useState(60)

  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          onDecision(toolId, true)
          return 0
        }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [toolId, onDecision])

  const displayInput = JSON.stringify(input, null, 2).slice(0, 500)

  return (
    <div style={styles.overlay}>
      <div style={styles.card}>
        <div style={styles.header}>
          <span>⚠️</span>
          <span>權限請求: {toolName}</span>
        </div>
        <div style={styles.description}>{description}</div>
        <div style={styles.inputPreview}>{displayInput}</div>
        <div style={styles.actions}>
          <button style={styles.btn('deny')} onClick={() => onDecision(toolId, false)}>
            拒絕
          </button>
          <button style={styles.btn('allow')} onClick={() => onDecision(toolId, true)}>
            允許一次
          </button>
          <button
            style={styles.btn('always')}
            onClick={() => {
              onAlwaysAllow(toolName)
              onDecision(toolId, true)
            }}
          >
            始終允許 {toolName}
          </button>
        </div>
        <div style={styles.timer}>
          {countdown > 0 ? `${countdown}s 後自動允許` : '已自動允許'}
        </div>
      </div>
    </div>
  )
}

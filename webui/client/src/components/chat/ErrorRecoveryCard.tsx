import type { ToolErrorInfo } from '../../stores/chatStore.ts'
import { useChatStore } from '../../stores/chatStore.ts'

interface Props {
  toolName: string
  error: ToolErrorInfo
  toolUseId?: string
  onRetry: () => void
  onSkip: () => void
}

export default function ErrorRecoveryCard({ toolName, error, onRetry, onSkip }: Props) {
  return (
    <div style={{
      margin: '6px 0',
      borderRadius: '8px',
      border: '1px solid rgba(248,113,113,0.4)',
      background: 'rgba(248,113,113,0.06)',
      padding: '10px 12px',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
        <span style={{ fontSize: '14px', flexShrink: 0, marginTop: '1px' }}>⚠</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: error.suggestion ? '6px' : '0' }}>
            {error.suggestion || `The "${toolName}" tool failed. This may be a temporary issue.`}
          </div>
          {error.suggestion && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
              {error.suggestion}
            </div>
          )}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {error.retryable && (
              <button
                onClick={onRetry}
                style={{
                  padding: '4px 10px',
                  fontSize: '11px',
                  border: '1px solid rgba(248,113,113,0.5)',
                  borderRadius: '5px',
                  background: 'rgba(248,113,113,0.12)',
                  color: 'var(--accent-red)',
                  cursor: 'pointer',
                  transition: 'all 0.12s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.22)'; e.currentTarget.style.borderColor = 'rgba(248,113,113,0.7)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.12)'; e.currentTarget.style.borderColor = 'rgba(248,113,113,0.5)' }}
              >
                ↻ Retry
              </button>
            )}
            {error.canSkip && (
              <button
                onClick={onSkip}
                style={{
                  padding: '4px 10px',
                  fontSize: '11px',
                  border: '1px solid var(--border-muted)',
                  borderRadius: '5px',
                  background: 'transparent',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  transition: 'all 0.12s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-focus)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-muted)'; e.currentTarget.style.color = 'var(--text-muted)' }}
              >
                Skip
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
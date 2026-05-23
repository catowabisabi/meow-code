import { useState, useEffect, useRef } from 'react'
import { useIntrospectionStore } from '../stores/introspectionStore'

const IDLE_TIMEOUT_MS = 5000

export default function IntrospectionPanel() {
  const { tokenBudgetUsed, tokenBudgetTotal, recursionDepth, selfReflectionCount, thinkingContent, contextPressure, status, lastActivity } = useIntrospectionStore()
  const [expanded, setExpanded] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (status === 'idle') {
      idleTimerRef.current = setTimeout(() => { setCollapsed(true); setExpanded(false) }, IDLE_TIMEOUT_MS)
    } else {
      setCollapsed(false)
      if (idleTimerRef.current) { clearTimeout(idleTimerRef.current); idleTimerRef.current = null }
    }
    return () => { if (idleTimerRef.current) clearTimeout(idleTimerRef.current) }
  }, [status, lastActivity])

  if (collapsed && status === 'idle') return null

  const tokenPercent = Math.min(100, Math.round((tokenBudgetUsed / tokenBudgetTotal) * 100))
  const isHighPressure = contextPressure > 80
  const statusColor = { idle: '#6b7280', thinking: '#3b82f6', 'tool-use': '#f59e0b', error: '#ef4444' }[status]
  const statusLabel = { idle: 'Idle', thinking: 'Thinking', 'tool-use': 'Using Tools', error: 'Error' }[status]

  if (collapsed) {
    return (
      <div onClick={() => setCollapsed(false)} style={{
        position: 'fixed', bottom: 16, right: 16, display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 12px', background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
        borderRadius: 20, cursor: 'pointer', fontSize: 11, color: 'var(--text-secondary)', zIndex: 1000,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      }}>
        <span style={{ fontSize: 6, fontWeight: 700, color: statusColor }}>●</span>
        <span>{statusLabel}</span>
        {recursionDepth > 0 && <span style={{ color: '#f59e0b' }}>↻{recursionDepth}</span>}
        {tokenPercent > 0 && <span style={{ color: isHighPressure ? '#ef4444' : '#6b7280' }}>{tokenPercent}%</span>}
      </div>
    )
  }

  return (
    <div style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, background: 'var(--bg-secondary)',
      borderTop: '1px solid var(--border-default)', padding: '8px 16px', fontSize: 11, zIndex: 1000,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 6, fontWeight: 700, color: statusColor }}>●</span>
          <span style={{ color: 'var(--text-secondary)', minWidth: 50 }}>{statusLabel}</span>
        </div>

        <div style={{ flex: '0 0 120px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
            <span>Tokens</span>
            <span style={{ color: isHighPressure ? '#ef4444' : 'var(--text-secondary)' }}>{tokenPercent}%</span>
          </div>
          <div style={{ height: 4, background: 'var(--bg-tertiary)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{
              width: `${tokenPercent}%`, height: '100%',
              background: isHighPressure ? 'linear-gradient(90deg, #ef4444, #f97316)' : 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
              transition: 'width 0.3s ease',
            }} />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: 'var(--text-muted)' }}>↻</span>
          <span style={{ color: recursionDepth > 3 ? '#ef4444' : recursionDepth > 0 ? '#f59e0b' : 'var(--text-secondary)', fontWeight: recursionDepth > 0 ? 600 : 400 }}>{recursionDepth}</span>
        </div>

        {selfReflectionCount > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ color: 'var(--text-muted)' }}>◐</span>
            <span style={{ color: 'var(--text-secondary)' }}>{selfReflectionCount}</span>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: 'var(--text-muted)' }}>▤</span>
          <span style={{ color: isHighPressure ? '#ef4444' : 'var(--text-secondary)' }}>{contextPressure}%</span>
        </div>

        <div style={{ flex: 1, display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8 }}>
          <button onClick={() => setExpanded(!expanded)} style={{
            padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border-default)',
            background: 'transparent', color: 'var(--text-muted)', fontSize: 10, cursor: 'pointer',
          }}>{expanded ? 'Collapse' : 'Thinking'}</button>
        </div>
      </div>

      {expanded && thinkingContent && (
        <div style={{
          maxHeight: 80, overflow: 'hidden', marginTop: 8, padding: '8px 12px',
          background: 'var(--bg-tertiary)', borderRadius: 6, fontSize: 11, color: 'var(--text-secondary)',
          fontFamily: 'monospace', lineHeight: 1.4,
        }}>
          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>{thinkingContent}</div>
        </div>
      )}
    </div>
  )
}
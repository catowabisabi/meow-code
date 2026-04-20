import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useLayoutStore, type AppMode } from '../../stores/layoutStore.ts'
import { useChatStore } from '../../stores/chatStore.ts'

const modes: { key: AppMode; label: string; path: string }[] = [
  { key: 'chat', label: 'Chat', path: '/chat' },
  { key: 'cowork', label: 'Cowork', path: '/cowork' },
  { key: 'code', label: 'Code', path: '/code' },
]

export default function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode, setMode, currentFolder, rightPanelOpen, toggleRightPanel } = useLayoutStore()
  const currentModel = useChatStore((s) => s.currentModel)
  const currentProvider = useChatStore((s) => s.currentProvider)
  const wsStatus = useChatStore((s) => s.wsStatus[mode] ?? 'disconnected')

  // Sync mode from URL
  useEffect(() => {
    const segment = location.pathname.split('/').filter(Boolean)[0] as AppMode | undefined
    if (segment && ['chat', 'cowork', 'code'].includes(segment) && segment !== mode) {
      setMode(segment)
    }
  }, [location.pathname, mode, setMode])

  const handleTabClick = (m: AppMode, path: string) => {
    setMode(m)
    navigate(path)
  }

  // WS status dot
  const statusColor = wsStatus === 'connected' ? '#4ade80' : wsStatus === 'connecting' || wsStatus === 'reconnecting' ? '#fbbf24' : '#5e5e5e'

  return (
    <div style={{
      height: 48, minHeight: 48,
      background: 'var(--bg-primary)',
      borderBottom: '1px solid var(--border-muted)',
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 16px',
      userSelect: 'none',
      gap: 12,
    }}>
      {/* ── Left: nav + breadcrumb ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0, flex: '0 0 auto' }}>
        <button
          title="Back"
          onClick={() => navigate(-1)}
          style={navBtnStyle}
          onMouseEnter={hoverIn}
          onMouseLeave={hoverOut}
        >
          ←
        </button>
        <button
          title="Forward"
          onClick={() => navigate(1)}
          style={navBtnStyle}
          onMouseEnter={hoverIn}
          onMouseLeave={hoverOut}
        >
          →
        </button>
        {currentFolder && mode !== 'chat' && (
          <span style={{
            fontSize: 12, color: 'var(--text-muted)',
            marginLeft: 6, maxWidth: 200,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }} title={currentFolder}>
            {currentFolder}
          </span>
        )}
      </div>

      {/* ── Center: mode tabs ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}>
        <div style={{
          display: 'flex', alignItems: 'center',
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-default)',
          borderRadius: 10, padding: 3, gap: 2,
        }}>
          {modes.map((m) => {
            const active = m.key === mode
            return (
              <button
                key={m.key}
                onClick={() => handleTabClick(m.key, m.path)}
                style={{
                  padding: '5px 20px',
                  fontSize: 13, fontWeight: active ? 600 : 400,
                  borderRadius: 7, border: 'none',
                  background: active ? 'var(--bg-hover)' : 'transparent',
                  color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  transition: 'all 0.12s',
                  fontFamily: 'inherit',
                  letterSpacing: active ? '-0.2px' : '0',
                }}
                onMouseEnter={(e) => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)' }}
                onMouseLeave={(e) => { if (!active) (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-muted)' }}
              >
                {m.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Right: model + status + panel toggle ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: '0 0 auto' }}>
        {/* Model info */}
        {currentModel && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 10px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-default)',
            borderRadius: 7, fontSize: 11,
          }}>
            {/* WS status dot */}
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: statusColor,
              flexShrink: 0,
              ...(wsStatus === 'reconnecting' ? { animation: 'pulse-dot 1s infinite' } : {}),
            }} />
            {currentProvider && (
              <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{currentProvider}</span>
            )}
            <span style={{
              color: 'var(--text-secondary)',
              maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {currentModel}
            </span>
          </div>
        )}

        {/* Right panel toggle */}
        <button
          title="Toggle right panel"
          onClick={toggleRightPanel}
          style={{
            ...navBtnStyle,
            background: rightPanelOpen ? 'var(--bg-hover)' : 'transparent',
            color: rightPanelOpen ? 'var(--text-primary)' : 'var(--text-muted)',
            borderColor: rightPanelOpen ? 'var(--border-focus)' : 'var(--border-default)',
          }}
          onMouseEnter={hoverIn}
          onMouseLeave={(e) => { if (!rightPanelOpen) hoverOut(e) }}
        >
          ☰
        </button>
      </div>
    </div>
  )
}

const navBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid var(--border-default)',
  borderRadius: 6,
  color: 'var(--text-muted)',
  fontSize: 15,
  width: 30, height: 30,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  cursor: 'pointer',
  transition: 'color 0.12s, border-color 0.12s',
  padding: 0, lineHeight: 1, fontFamily: 'inherit',
}

function hoverIn(e: React.MouseEvent<HTMLButtonElement>) {
  e.currentTarget.style.color = 'var(--text-primary)'
  e.currentTarget.style.borderColor = 'var(--border-focus)'
}
function hoverOut(e: React.MouseEvent<HTMLButtonElement>) {
  e.currentTarget.style.color = 'var(--text-muted)'
  e.currentTarget.style.borderColor = 'var(--border-default)'
}

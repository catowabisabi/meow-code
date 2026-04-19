import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useLayoutStore, type AppMode } from '../../stores/layoutStore.ts'

const modes: { key: AppMode; label: string; path: string }[] = [
  { key: 'chat', label: 'Chat', path: '/chat' },
  { key: 'cowork', label: 'Cowork', path: '/cowork' },
  { key: 'code', label: 'Code', path: '/code' },
]

const styles = {
  bar: {
    height: '48px',
    minHeight: '48px',
    background: '#0f0f10',
    borderBottom: '1px solid #2a2a2e',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    userSelect: 'none' as const,
  },

  /* ---- left ---- */
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    minWidth: '200px',
  },
  navBtn: {
    background: 'none',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#71717a',
    fontSize: '16px',
    width: '30px',
    height: '30px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'color 0.15s, border-color 0.15s',
    padding: 0,
    lineHeight: 1,
  },
  breadcrumb: {
    fontSize: '13px',
    color: '#71717a',
    marginLeft: '10px',
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: '260px',
  },

  /* ---- center ---- */
  center: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  tabGroup: {
    display: 'flex',
    alignItems: 'center',
    background: '#151517',
    border: '1px solid #2a2a2e',
    borderRadius: '10px',
    padding: '3px',
    gap: '2px',
  },
  tab: {
    padding: '5px 18px',
    fontSize: '13px',
    fontWeight: 500,
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    transition: 'background 0.15s, color 0.15s',
    lineHeight: 1.4,
  },
  tabActive: {
    background: '#2a2a2e',
    color: '#e6e6e6',
  },
  tabInactive: {
    background: 'transparent',
    color: '#71717a',
  },

  /* ---- right ---- */
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    minWidth: '200px',
    justifyContent: 'flex-end',
  },
  previewBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    background: '#151517',
    border: '1px solid #2a2a2e',
    borderRadius: '8px',
    color: '#a1a1aa',
    fontSize: '13px',
    padding: '5px 12px',
    cursor: 'pointer',
    transition: 'color 0.15s, border-color 0.15s',
  },
  previewCheck: {
    fontSize: '12px',
    color: '#22c55e',
  },
  panelToggle: {
    background: 'none',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#71717a',
    fontSize: '16px',
    width: '30px',
    height: '30px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'color 0.15s, border-color 0.15s',
    padding: 0,
    lineHeight: 1,
  },
}

function hoverColor(e: React.MouseEvent<HTMLButtonElement>) {
  ;(e.currentTarget as HTMLButtonElement).style.color = '#e6e6e6'
  ;(e.currentTarget as HTMLButtonElement).style.borderColor = '#3f3f46'
}
function unhoverColor(e: React.MouseEvent<HTMLButtonElement>) {
  ;(e.currentTarget as HTMLButtonElement).style.color = '#71717a'
  ;(e.currentTarget as HTMLButtonElement).style.borderColor = '#2a2a2e'
}

export default function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { mode, setMode, currentFolder, rightPanelOpen, toggleRightPanel } =
    useLayoutStore()

  // Sync mode from URL
  useEffect(() => {
    const segment = location.pathname.split('/').filter(Boolean)[0] as
      | AppMode
      | undefined
    if (segment && ['chat', 'cowork', 'code'].includes(segment) && segment !== mode) {
      setMode(segment)
    }
  }, [location.pathname, mode, setMode])

  const handleTabClick = (m: AppMode, path: string) => {
    setMode(m)
    navigate(path)
  }

  const showBreadcrumb = mode !== 'chat' && currentFolder

  return (
    <div style={styles.bar}>
      {/* ---- Left ---- */}
      <div style={styles.left}>
        <button
          style={styles.navBtn}
          title="Back"
          onClick={() => navigate(-1)}
          onMouseEnter={hoverColor}
          onMouseLeave={unhoverColor}
        >
          &#8592;
        </button>
        <button
          style={styles.navBtn}
          title="Forward"
          onClick={() => navigate(1)}
          onMouseEnter={hoverColor}
          onMouseLeave={unhoverColor}
        >
          &#8594;
        </button>
        {showBreadcrumb && (
          <span style={styles.breadcrumb} title={currentFolder ?? undefined}>
            {currentFolder}
          </span>
        )}
      </div>

      {/* ---- Center: mode tabs ---- */}
      <div style={styles.center}>
        <div style={styles.tabGroup}>
          {modes.map((m) => {
            const active = m.key === mode
            return (
              <button
                key={m.key}
                style={{
                  ...styles.tab,
                  ...(active ? styles.tabActive : styles.tabInactive),
                }}
                onClick={() => handleTabClick(m.key, m.path)}
                onMouseEnter={(e) => {
                  if (!active) {
                    ;(e.currentTarget as HTMLButtonElement).style.color = '#a1a1aa'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!active) {
                    ;(e.currentTarget as HTMLButtonElement).style.color = '#71717a'
                  }
                }}
              >
                {m.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* ---- Right ---- */}
      <div style={styles.right}>
        <button
          style={{
            ...styles.panelToggle,
            ...(rightPanelOpen
              ? { color: '#e6e6e6', borderColor: '#3f3f46' }
              : {}),
          }}
          title="Toggle right panel"
          onClick={toggleRightPanel}
          onMouseEnter={hoverColor}
          onMouseLeave={(e) => {
            if (!rightPanelOpen) unhoverColor(e)
          }}
        >
          {'☰'}
        </button>
      </div>
    </div>
  )
}

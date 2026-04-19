import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useLayoutStore } from '../../stores/layoutStore.ts'
import { useChatStore } from '../../stores/chatStore.ts'
import SettingsPage from '../../pages/SettingsPage.tsx'

// ---------- Types ----------

interface Session {
  id: string
  title?: string
  preview?: string
  created_at?: string
  createdAt?: number
  mode?: string
  folder?: string | null
}

// ---------- Color tokens (Claude.ai dark mode) ----------

const C = {
  bg: '#151517',
  bgHover: '#1b1b1f',
  bgActive: '#1b1b1f',
  text: '#e6e6e6',
  textSecondary: '#a1a1aa',
  textMuted: '#71717a',
  border: '#2a2a2e',
  accent: '#f97316',
} as const

// ---------- Sidebar dimensions ----------

const SIDEBAR_WIDTH = 260
const SIDEBAR_COLLAPSED_WIDTH = 48

// ---------- Action buttons ----------


// ---------- Agent Dashboard indicator ----------

interface AgentInfo {
  id: string
  status: 'running' | 'completed' | 'error'
}

function AgentDashboardIndicator({ agents }: { agents: AgentInfo[] }) {
  const navigate = useNavigate()
  const runningAgents = agents.filter((a) => a.status === 'running')
  
  if (runningAgents.length === 0) return null
  
  return (
    <div
      onClick={() => navigate('/agent-dashboard')}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 12px',
        background: 'rgba(34, 197, 94, 0.1)',
        border: '1px solid rgba(34, 197, 94, 0.3)',
        borderRadius: '8px',
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'rgba(34, 197, 94, 0.15)'
        e.currentTarget.style.borderColor = 'rgba(34, 197, 94, 0.5)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'rgba(34, 197, 94, 0.1)'
        e.currentTarget.style.borderColor = 'rgba(34, 197, 94, 0.3)'
      }}
    >
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: '#22c55e',
          animation: 'pulse 1.5s ease-in-out infinite',
        }}
      />
      <span style={{ fontSize: '12px', color: '#22c55e', fontWeight: 500 }}>
        {runningAgents.length} 個代理運行中
      </span>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.9); }
        }
      `}</style>
    </div>
  )
}

// ---------- Component ----------

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const sidebarCollapsed = useLayoutStore((s) => s.sidebarCollapsed)
  const toggleSidebar = useLayoutStore((s) => s.toggleSidebar)

  // Sessions
  const [sessions, setSessions] = useState<Session[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(true)

  // Collapsible sections
  const [sectionsOpen, setSectionsOpen] = useState<Record<string, boolean>>({
    today: true,
    starred: true,
    recents: true,
  })

  // User dropdown
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Settings modal
  const [settingsOpen, setSettingsOpen] = useState(false)

  // Hovered item tracking
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)
  const [hoveredSession, setHoveredSession] = useState<string | null>(null)
  const [hoveredBottomNav, setHoveredBottomNav] = useState<string | null>(null)

  // Agents
  const [agents, setAgents] = useState<AgentInfo[]>([])

  // ---------- Fetch sessions ----------

  useEffect(() => {
    setSessionsLoading(true)
    fetch('/api/sessions')
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []))
      .catch(() => setSessions([]))
      .finally(() => setSessionsLoading(false))
  }, [])

  // Refresh sessions on event, polling, and navigation
  useEffect(() => {
    const refresh = () => {
      fetch('/api/sessions')
        .then((r) => r.json())
        .then((d) => setSessions(d.sessions || []))
        .catch(() => {})
    }
    window.addEventListener('sessions-updated', refresh)
    const interval = setInterval(refresh, 10000)
    return () => {
      window.removeEventListener('sessions-updated', refresh)
      clearInterval(interval)
    }
  }, [])

  // Refresh when location changes
  useEffect(() => {
    fetch('/api/sessions')
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []))
      .catch(() => {})
  }, [location.pathname])

  // Fetch agents periodically
  useEffect(() => {
    const fetchAgents = () => {
      fetch('/api/agents')
        .then((r) => r.json())
        .then((d) => setAgents(d.agents || []))
        .catch(() => {})
    }
    fetchAgents()
    const interval = setInterval(fetchAgents, 3000)
    return () => clearInterval(interval)
  }, [])

  // ---------- Close user menu on outside click ----------

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClick)
    }
    return () => document.removeEventListener('mousedown', handleClick)
  }, [userMenuOpen])

  // ---------- Helpers ----------

  const toggleSection = useCallback((key: string) => {
    setSectionsOpen((prev) => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const currentSessionId = location.pathname.startsWith('/chat/')
    ? location.pathname.replace('/chat/', '')
    : location.pathname.startsWith('/cowork/')
    ? location.pathname.replace('/cowork/', '')
    : location.pathname.startsWith('/code/')
    ? location.pathname.replace('/code/', '')
    : null

  // Derive the current mode from the URL path — show sessions for this mode
  const currentMode = location.pathname.startsWith('/cowork')
    ? 'cowork'
    : location.pathname.startsWith('/code')
    ? 'code'
    : location.pathname.startsWith('/chat') || location.pathname === '/'
    ? 'chat'
    : null

  const isPathActive = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/')

  // Categorize sessions by actual created_at date
  const todayStr = new Date().toDateString()
  const getSessionDate = (s: Session) => {
    if (s.created_at) return new Date(s.created_at)
    if (s.createdAt) return new Date(s.createdAt)
    return null
  }
  const todaySessions = sessions.filter((s) => {
    if (currentMode && s.mode !== currentMode) return false
    const d = getSessionDate(s)
    return d && d.toDateString() === todayStr
  })
  const recentSessions = sessions.filter((s) => {
    if (currentMode && s.mode !== currentMode) return false
    const d = getSessionDate(s)
    return !d || d.toDateString() !== todayStr
  })

  const handleDeleteSession = useCallback((id: string) => {
    fetch(`/api/sessions/${id}`, { method: 'DELETE' })
      .then(() => {
        setSessions((prev) => prev.filter((s) => s.id !== id))
        // If we just deleted the active session, navigate away
        if (id === currentSessionId) {
          navigate('/chat')
        }
      })
      .catch((err) => console.error('Failed to delete session:', err))
  }, [currentSessionId, navigate])

  const handleUpdateSessionTitle = useCallback((id: string, newTitle: string) => {
    fetch(`/api/sessions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: newTitle }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) {
          setSessions((prev) =>
            prev.map((s) => (s.id === id ? { ...s, title: newTitle } : s))
          )
        }
      })
      .catch((err) => console.error('Failed to update session title:', err))
  }, [])

  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingTitle, setEditingTitle] = useState('')

  const collapsed = sidebarCollapsed
  const width = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH

  // ---------- Render ----------

  return (
    <div
      style={{
        width,
        minWidth: width,
        height: '100vh',
        background: C.bg,
        borderRight: `1px solid ${C.border}`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        transition: 'width 0.2s ease, min-width 0.2s ease',
        userSelect: 'none',
      }}
    >
      {/* ============ TOP: New Chat ============ */}
      <div style={{ padding: collapsed ? '8px 4px' : '8px', flexShrink: 0 }}>
        <button
          title={collapsed ? 'New chat' : undefined}
          onClick={() => {
            const currentPath = location.pathname
            let targetPath = '/chat'
            let mode = 'chat'
            if (currentPath.startsWith('/cowork')) { targetPath = '/cowork'; mode = 'cowork' }
            else if (currentPath.startsWith('/code')) { targetPath = '/code'; mode = 'code' }
            useChatStore.getState().clearModeMessages(mode)
            useChatStore.getState().setModeSession(mode, null as unknown as string)
            navigate(targetPath)
          }}
          onMouseEnter={() => setHoveredItem('new-chat')}
          onMouseLeave={() => setHoveredItem(null)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: collapsed ? '8px 0' : '8px 12px',
            justifyContent: collapsed ? 'center' : 'flex-start',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 600,
            color: location.pathname === '/chat' ? C.text : hoveredItem === 'new-chat' ? C.text : C.textSecondary,
            background: location.pathname === '/chat' ? C.bgActive : hoveredItem === 'new-chat' ? C.bgHover : 'transparent',
            border: 'none',
            width: '100%',
            textAlign: 'left',
            transition: 'all 0.12s ease',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        >
          <span style={{ fontSize: '16px', lineHeight: 1, flexShrink: 0 }}>＋</span>
          {!collapsed && <span>New chat</span>}
        </button>

        {/* Search */}
        <button
          title={collapsed ? 'Search' : undefined}
          onClick={() => navigate('/search')}
          onMouseEnter={() => setHoveredItem('search')}
          onMouseLeave={() => setHoveredItem(null)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: collapsed ? '8px 0' : '8px 12px',
            justifyContent: collapsed ? 'center' : 'flex-start',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 400,
            color: isPathActive('/search') ? C.text : hoveredItem === 'search' ? C.text : C.textSecondary,
            background: isPathActive('/search') ? C.bgActive : hoveredItem === 'search' ? C.bgHover : 'transparent',
            border: 'none',
            width: '100%',
            textAlign: 'left',
            transition: 'all 0.12s ease',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        >
          <span style={{ fontSize: '16px', lineHeight: 1, flexShrink: 0 }}>🔍</span>
          {!collapsed && <span>Search</span>}
        </button>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: C.border, margin: collapsed ? '0 4px' : '0 12px', flexShrink: 0 }} />

      {/* ============ MIDDLE: History (scrollable) ============ */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: collapsed ? '8px 4px' : '8px',
        }}
      >
        {collapsed ? (
          // Collapsed: show small chat icon
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              padding: '8px 0',
              color: C.textMuted,
              fontSize: '14px',
            }}
            title="Chat history"
          >
            {'💬'}
          </div>
        ) : sessionsLoading ? (
          <div style={{ padding: '16px 12px', color: C.textMuted, fontSize: '13px' }}>
            Loading...
          </div>
        ) : sessions.length === 0 ? (
          <div style={{ padding: '16px 12px', color: C.textMuted, fontSize: '13px', lineHeight: 1.5 }}>
            No conversations yet. Start a new chat to begin.
          </div>
        ) : (
          <>
            {/* Today section */}
            {todaySessions.length > 0 && (
              <HistorySection
                title="Today"
                open={sectionsOpen.today}
                onToggle={() => toggleSection('today')}
                sessions={todaySessions}
                currentSessionId={currentSessionId}
                hoveredSession={hoveredSession}
                onHoverSession={setHoveredSession}
                onNavigate={navigate}
                onDelete={handleDeleteSession}
                onUpdateTitle={handleUpdateSessionTitle}
                editingSessionId={editingSessionId}
                editingTitle={editingTitle}
                setEditingSessionId={setEditingSessionId}
                setEditingTitle={setEditingTitle}
              />
            )}

            {/* Recents section */}
            {recentSessions.length > 0 && (
              <HistorySection
                title="Recents"
                open={sectionsOpen.recents}
                onToggle={() => toggleSection('recents')}
                sessions={recentSessions}
                currentSessionId={currentSessionId}
                hoveredSession={hoveredSession}
                onHoverSession={setHoveredSession}
                onNavigate={navigate}
                onDelete={handleDeleteSession}
                onUpdateTitle={handleUpdateSessionTitle}
                editingSessionId={editingSessionId}
                editingTitle={editingTitle}
                setEditingSessionId={setEditingSessionId}
                setEditingTitle={setEditingTitle}
              />
            )}
          </>
        )}
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: C.border, margin: collapsed ? '0 4px' : '0 12px', flexShrink: 0 }} />

      {/* Agent Dashboard Indicator */}
      {!collapsed && <div style={{ padding: '8px 12px' }}><AgentDashboardIndicator agents={agents} /></div>}

      {/* ============ BOTTOM: User Panel ============ */}
      <div style={{ flexShrink: 0 }}>

        {/* User panel */}
        <div ref={userMenuRef} style={{ position: 'relative' }}>
          <button
            onClick={() => setUserMenuOpen((v) => !v)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              width: '100%',
              padding: collapsed ? '10px 0' : '10px 12px',
              justifyContent: collapsed ? 'center' : 'flex-start',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              outline: 'none',
              fontFamily: 'inherit',
              transition: 'background 0.12s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = C.bgHover }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
          >
            {/* Avatar */}
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: '50%',
                background: '#6366f1',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '13px',
                fontWeight: 600,
                color: '#fff',
                flexShrink: 0,
              }}
            >
              C
            </div>
            {!collapsed && (
              <>
                <div style={{ flex: 1, textAlign: 'left', minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 500,
                      color: C.text,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    Chris
                  </div>
                  <div style={{ fontSize: '11px', color: C.textMuted }}>Pro plan</div>
                </div>
                <span
                  style={{
                    fontSize: '12px',
                    color: C.textMuted,
                    transform: userMenuOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.15s ease',
                  }}
                >
                  {'▲'}
                </span>
              </>
            )}
          </button>

          {/* User dropdown menu */}
          {userMenuOpen && (
            <div
              style={{
                position: 'absolute',
                bottom: '100%',
                left: collapsed ? 0 : 8,
                right: collapsed ? undefined : 8,
                width: collapsed ? 200 : undefined,
                marginBottom: 4,
                background: '#1e1e22',
                border: `1px solid ${C.border}`,
                borderRadius: '10px',
                padding: '4px',
                zIndex: 1000,
                boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              }}
            >
              {[
                { label: '⚙️  Settings', action: () => setSettingsOpen(true) },
                { label: '👥  Teams', action: () => navigate('/teams') },
                { label: 'Log out', action: () => { console.warn('Logout not implemented') } },
              ].map((item, i) => (
                <UserMenuItem
                  key={i}
                  label={item.label}
                  onClick={() => {
                    item.action()
                    setUserMenuOpen(false)
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Collapse toggle button (thin strip on right edge) */}
      <button
        onClick={toggleSidebar}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        style={{
          position: 'absolute',
          top: '50%',
          left: width - 6,
          transform: 'translateY(-50%)',
          width: 12,
          height: 40,
          borderRadius: '0 4px 4px 0',
          border: `1px solid ${C.border}`,
          borderLeft: 'none',
          background: C.bg,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
          color: C.textMuted,
          opacity: 0.6,
          transition: 'opacity 0.15s ease, left 0.2s ease',
          zIndex: 10,
          outline: 'none',
          padding: 0,
        }}
        onMouseEnter={(e) => { e.currentTarget.style.opacity = '1' }}
        onMouseLeave={(e) => { e.currentTarget.style.opacity = '0.6' }}
      >
        {collapsed ? '\u203A' : '\u2039'}
      </button>

      {/* Settings Modal */}
      {settingsOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            zIndex: 9000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setSettingsOpen(false) }}
        >
          <div
            style={{
              width: '90vw',
              maxWidth: '860px',
              maxHeight: '85vh',
              background: '#151517',
              border: `1px solid ${C.border}`,
              borderRadius: '14px',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
              boxShadow: '0 24px 64px rgba(0,0,0,0.7)',
            }}
          >
            {/* Modal header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px 24px',
              borderBottom: `1px solid ${C.border}`,
              flexShrink: 0,
            }}>
              <span style={{ fontSize: '16px', fontWeight: 600, color: C.text }}>Settings</span>
              <button
                onClick={() => setSettingsOpen(false)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: C.textMuted, fontSize: '20px', lineHeight: 1,
                  padding: '4px 8px', borderRadius: '6px',
                  outline: 'none', fontFamily: 'inherit',
                  transition: 'color 0.12s',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = C.text }}
                onMouseLeave={(e) => { e.currentTarget.style.color = C.textMuted }}
              >
                ✕
              </button>
            </div>
            {/* Modal body */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              <SettingsPage />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------- Sub-components ----------

interface HistorySectionProps {
  title: string
  open: boolean
  onToggle: () => void
  sessions: Session[]
  currentSessionId: string | null
  hoveredSession: string | null
  onHoverSession: (id: string | null) => void
  onNavigate: (path: string) => void
  onDelete: (id: string) => void
  onUpdateTitle: (id: string, newTitle: string) => void
  editingSessionId: string | null
  editingTitle: string
  setEditingSessionId: (id: string | null) => void
  setEditingTitle: (title: string) => void
  emptyText?: string
}

function HistorySection({
  title,
  open,
  onToggle,
  sessions,
  currentSessionId,
  hoveredSession,
  onHoverSession,
  onNavigate,
  onDelete,
  onUpdateTitle,
  editingSessionId,
  editingTitle,
  setEditingSessionId,
  setEditingTitle,
  emptyText,
}: HistorySectionProps) {
  const [hoveredHeader, setHoveredHeader] = useState(false)

  return (
    <div style={{ marginBottom: '4px' }}>
      {/* Section header */}
      <button
        onClick={onToggle}
        onMouseEnter={() => setHoveredHeader(true)}
        onMouseLeave={() => setHoveredHeader(false)}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
          padding: '6px 12px',
          border: 'none',
          background: hoveredHeader ? C.bgHover : 'transparent',
          cursor: 'pointer',
          borderRadius: '6px',
          outline: 'none',
          fontFamily: 'inherit',
          transition: 'background 0.12s ease',
        }}
      >
        <span style={{ fontSize: '12px', fontWeight: 600, color: C.textMuted, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {title}
        </span>
        <span
          style={{
            fontSize: '10px',
            color: C.textMuted,
            transform: open ? 'rotate(0deg)' : 'rotate(-90deg)',
            transition: 'transform 0.15s ease',
          }}
        >
          {'▼'}
        </span>
      </button>

      {/* Section content */}
      {open && (
        <div>
          {sessions.length === 0 ? (
            <div style={{ padding: '6px 12px', fontSize: '12px', color: C.textMuted }}>
              {emptyText || 'No items'}
            </div>
          ) : (
            sessions.map((session) => {
              const active = session.id === currentSessionId
              const hovered = hoveredSession === session.id
              const isEditing = editingSessionId === session.id
              const displayTitle = session.title && session.title !== 'Untitled Session'
                ? session.title
                : session.preview && session.preview !== '(empty)' && session.preview !== '(new session)'
                  ? session.preview.slice(0, 50)
                  : `Chat ${session.id.slice(0, 8)}...`

              return (
                <div
                  key={session.id}
                  onClick={() => {
                    if (isEditing) return
                    const base = session.mode === 'cowork' ? '/cowork' : session.mode === 'code' ? '/code' : '/chat'
                    if (session.folder) {
                      useLayoutStore.getState().setCurrentFolder(session.folder)
                    }
                    onNavigate(`${base}/${session.id}`)
                  }}
                  onMouseEnter={() => onHoverSession(session.id)}
                  onMouseLeave={() => onHoverSession(null)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '7px 12px',
                    borderRadius: '8px',
                    cursor: isEditing ? 'default' : 'pointer',
                    fontSize: '13px',
                    color: active ? C.text : C.textSecondary,
                    background: active ? C.bgActive : hovered ? C.bgHover : 'transparent',
                    borderLeft: active ? `2px solid ${C.accent}` : '2px solid transparent',
                    transition: 'all 0.12s ease',
                    position: 'relative',
                  }}
                >
                  {session.mode && (
                    <span
                      style={{
                        display: 'inline-block',
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background:
                          session.mode === 'chat' ? '#3b82f6' :
                          session.mode === 'cowork' ? '#22c55e' :
                          session.mode === 'code' ? '#a855f7' : C.textMuted,
                        marginRight: '6px',
                        flexShrink: 0,
                      }}
                      title={session.mode}
                    />
                  )}

                  {isEditing ? (
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          onUpdateTitle(session.id, editingTitle)
                          setEditingSessionId(null)
                        } else if (e.key === 'Escape') {
                          setEditingSessionId(null)
                        }
                      }}
                      onBlur={() => {
                        onUpdateTitle(session.id, editingTitle)
                        setEditingSessionId(null)
                      }}
                      autoFocus
                      style={{
                        flex: 1,
                        background: '#2a2a2e',
                        border: '1px solid #3b82f6',
                        borderRadius: '4px',
                        padding: '2px 6px',
                        fontSize: '13px',
                        color: C.text,
                        outline: 'none',
                        fontFamily: 'inherit',
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <span
                      style={{
                        flex: 1,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {displayTitle}
                    </span>
                  )}

                  {hovered && !isEditing && (
                    <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                      <span
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingSessionId(session.id)
                          setEditingTitle(displayTitle)
                        }}
                        style={{
                          fontSize: '14px',
                          color: C.textMuted,
                          lineHeight: 1,
                          padding: '2px 4px',
                          cursor: 'pointer',
                          borderRadius: '4px',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.color = '#3b82f6' }}
                        onMouseLeave={(e) => { e.currentTarget.style.color = C.textMuted }}
                        title="編輯標題"
                      >
                        ✎
                      </span>
                      <span
                        onClick={(e) => {
                          e.stopPropagation()
                          if (confirm('確定要刪除此對話？')) {
                            onDelete(session.id)
                          }
                        }}
                        style={{
                          fontSize: '14px',
                          color: C.textMuted,
                          lineHeight: 1,
                          padding: '2px 4px',
                          cursor: 'pointer',
                          borderRadius: '4px',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.color = '#f85149' }}
                        onMouseLeave={(e) => { e.currentTarget.style.color = C.textMuted }}
                        title="刪除對話"
                      >
                        ✕
                      </span>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

function UserMenuItem({ label, onClick }: { label: string; onClick: () => void }) {
  const [hovered, setHovered] = useState(false)

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'block',
        width: '100%',
        padding: '8px 12px',
        border: 'none',
        background: hovered ? C.bgHover : 'transparent',
        color: label === 'Log out' ? '#ef4444' : C.text,
        fontSize: '13px',
        textAlign: 'left',
        cursor: 'pointer',
        borderRadius: '6px',
        outline: 'none',
        fontFamily: 'inherit',
        transition: 'background 0.12s ease',
      }}
    >
      {label}
    </button>
  )
}

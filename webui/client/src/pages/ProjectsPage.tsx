import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLayoutStore } from '../stores/layoutStore.ts'

interface Session {
  id: string
  title?: string
  created_at?: string
  mode?: string
}

const C = {
  bg: '#0f0f10',
  surface: '#151517',
  border: '#2a2a2e',
  text: '#e6e6e6',
  textSecondary: '#a1a1aa',
  textMuted: '#71717a',
  bgHover: '#1b1b1f',
  accent: '#f97316',
}

function groupByDate(sessions: Session[]): Record<string, Session[]> {
  const groups: Record<string, Session[]> = {}
  for (const s of sessions) {
    const key = s.created_at
      ? new Date(s.created_at).toDateString()
      : 'Unknown Date'
    if (!groups[key]) groups[key] = []
    groups[key]!.push(s)
  }
  return groups
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const setCurrentFolder = useLayoutStore((s) => (s as any).setCurrentFolder)
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [hoveredFolder, setHoveredFolder] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    fetch('/api/sessions')
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []))
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [])

  const groups = groupByDate(sessions)
  const groupKeys = Object.keys(groups).sort((a, b) => {
    if (a === 'Unknown Date') return 1
    if (b === 'Unknown Date') return -1
    return new Date(b).getTime() - new Date(a).getTime()
  })

  return (
    <div style={{ minHeight: '100vh', background: C.bg, color: C.text, padding: '40px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>項目</h1>
      <p style={{ color: C.textMuted, fontSize: '14px', marginBottom: '32px' }}>
        按日期分組的對話歷史
      </p>

      {loading ? (
        <div style={{ color: C.textMuted }}>載入中...</div>
      ) : groupKeys.length === 0 ? (
        <div style={{ color: C.textMuted }}>尚無對話記錄</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '700px' }}>
          {groupKeys.map((dateKey) => {
            const folderHovered = hoveredFolder === dateKey
            const sessionList = groups[dateKey] || []
            return (
              <div
                key={dateKey}
                style={{
                  border: `1px solid ${C.border}`,
                  borderRadius: '12px',
                  overflow: 'hidden',
                  background: C.surface,
                }}
              >
                {/* Folder header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    borderBottom: `1px solid ${C.border}`,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '16px' }}>📁</span>
                    <span style={{ fontSize: '14px', fontWeight: 600, color: C.text }}>
                      {dateKey}
                    </span>
                    <span
                      style={{
                        fontSize: '11px',
                        color: C.textMuted,
                        background: '#2a2a2e',
                        padding: '2px 6px',
                        borderRadius: '10px',
                      }}
                    >
                      {sessionList.length}
                    </span>
                  </div>
                  <button
                    onMouseEnter={() => setHoveredFolder(dateKey)}
                    onMouseLeave={() => setHoveredFolder(null)}
                    onClick={() => {
                      if (typeof setCurrentFolder === 'function') {
                        setCurrentFolder(dateKey)
                      }
                    }}
                    style={{
                      padding: '5px 10px',
                      borderRadius: '6px',
                      border: `1px solid ${C.border}`,
                      background: folderHovered ? C.bgHover : 'transparent',
                      color: C.textSecondary,
                      fontSize: '12px',
                      cursor: 'pointer',
                      outline: 'none',
                      fontFamily: 'inherit',
                      transition: 'background 0.12s ease',
                    }}
                  >
                    打開文件夾
                  </button>
                </div>

                {/* Session list */}
                <div>
                  {sessionList.map((s) => {
                    const hovered = hoveredId === s.id
                    return (
                      <div
                        key={s.id}
                        onClick={() => navigate(`/chat/${s.id}`)}
                        onMouseEnter={() => setHoveredId(s.id)}
                        onMouseLeave={() => setHoveredId(null)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '10px 16px',
                          cursor: 'pointer',
                          background: hovered ? C.bgHover : 'transparent',
                          borderBottom: `1px solid ${C.border}`,
                          transition: 'background 0.12s ease',
                          gap: '10px',
                        }}
                      >
                        <span style={{ fontSize: '14px' }}>💬</span>
                        <span
                          style={{
                            flex: 1,
                            fontSize: '13px',
                            color: C.text,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {s.title || `Chat ${s.id.slice(0, 8)}...`}
                        </span>
                        {s.created_at && (
                          <span style={{ fontSize: '11px', color: C.textMuted, flexShrink: 0 }}>
                            {new Date(s.created_at).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

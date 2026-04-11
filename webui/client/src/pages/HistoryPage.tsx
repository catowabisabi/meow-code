import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const styles = {
  container: {
    padding: '24px 32px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  header: {
    marginBottom: '24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
  },
  newChatBtn: {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    background: 'var(--accent-blue)',
    color: '#fff',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  searchBar: {
    width: '100%',
    padding: '10px 14px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '8px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
    marginBottom: '16px',
  },
  sessionList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
  },
  sessionCard: {
    padding: '16px 20px',
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: '10px',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  sessionTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  sessionModel: {
    fontSize: '12px',
    padding: '2px 8px',
    borderRadius: '4px',
    background: 'var(--bg-tertiary)',
    color: 'var(--accent-blue)',
    fontWeight: 500,
  },
  sessionTime: {
    fontSize: '12px',
    color: 'var(--text-muted)',
  },
  sessionPreview: {
    fontSize: '14px',
    color: 'var(--text-secondary)',
    lineHeight: 1.4,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  sessionMeta: {
    marginTop: '8px',
    fontSize: '12px',
    color: 'var(--text-muted)',
    display: 'flex',
    gap: '12px',
  },
  emptyState: {
    textAlign: 'center' as const,
    padding: '60px 0',
    color: 'var(--text-muted)',
  },
}

interface SessionSummary {
  id: string
  model: string
  provider: string
  messageCount: number
  createdAt: number
  preview: string
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchSessions()
  }, [])

  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/sessions')
      const data = await res.json()
      setSessions(data.sessions || [])
    } catch (e) {
      console.error('Failed to fetch sessions:', e)
    } finally {
      setLoading(false)
    }
  }

  const createNewSession = async () => {
    try {
      const res = await fetch('/api/sessions', { method: 'POST' })
      const data = await res.json()
      navigate(`/chat/${data.id}`)
    } catch (e) {
      console.error('Failed to create session:', e)
    }
  }

  const filtered = sessions.filter(
    (s) =>
      s.preview.toLowerCase().includes(search.toLowerCase()) ||
      s.model.toLowerCase().includes(search.toLowerCase())
  )

  const formatDate = (ts: number) => {
    const d = new Date(ts)
    const now = new Date()
    const diff = now.getTime() - d.getTime()

    if (diff < 60000) return '剛剛'
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分鐘前`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小時前`
    if (diff < 604800000) return `${Math.floor(diff / 86400000)} 天前`
    return d.toLocaleDateString('zh-CN')
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>歷史記錄</div>
        <button style={styles.newChatBtn} onClick={createNewSession}>
          + 新對話
        </button>
      </div>

      <input
        style={styles.searchBar}
        placeholder="搜索對話歷史..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div style={styles.sessionList}>
        {loading ? (
          <div style={styles.emptyState}>加載中...</div>
        ) : filtered.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '36px', marginBottom: '12px' }}>📋</div>
            <div style={{ fontSize: '16px', marginBottom: '4px' }}>
              {search ? '未找到匹配的對話' : '暫無歷史記錄'}
            </div>
            <div style={{ fontSize: '13px' }}>
              {search ? '嘗試其他搜索詞' : '開始一段新對話，記錄會顯示在這裡'}
            </div>
          </div>
        ) : (
          filtered.map((session) => (
            <div
              key={session.id}
              style={styles.sessionCard}
              onClick={() => navigate(`/chat/${session.id}`)}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-blue)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-default)'
              }}
            >
              <div style={styles.sessionTop}>
                <span style={styles.sessionModel}>{session.model}</span>
                <span style={styles.sessionTime}>{formatDate(session.createdAt)}</span>
              </div>
              <div style={styles.sessionPreview}>
                {session.preview || '(空對話)'}
              </div>
              <div style={styles.sessionMeta}>
                <span>{session.messageCount} 條消息</span>
                <span>{session.provider}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

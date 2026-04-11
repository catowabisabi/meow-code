import { useState, useEffect } from 'react'

type MemoryType = 'user' | 'feedback' | 'project' | 'reference'

interface Memory {
  id: string
  type: MemoryType
  name: string
  description: string
  content: string
  createdAt: string
}

const TYPE_COLORS: Record<MemoryType, string> = {
  user: '#3b82f6',
  feedback: '#f59e0b',
  project: '#22c55e',
  reference: '#a855f7',
}

const TYPE_LABELS: Record<MemoryType, string> = {
  user: 'User',
  feedback: 'Feedback',
  project: 'Project',
  reference: 'Reference',
}

const FILTER_OPTIONS: { value: MemoryType | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'user', label: 'User' },
  { value: 'feedback', label: 'Feedback' },
  { value: 'project', label: 'Project' },
  { value: 'reference', label: 'Reference' },
]

const styles = {
  container: {
    padding: '24px 32px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    marginBottom: '8px',
    color: '#e6e6e6',
  },
  subtitle: {
    fontSize: '13px',
    color: '#a1a1aa',
    marginBottom: '20px',
  },
  statsRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '20px',
    flexWrap: 'wrap' as const,
  },
  statCard: (color: string) => ({
    background: '#1b1b1f',
    border: '1px solid #2a2a2e',
    borderRadius: '10px',
    padding: '14px 18px',
    minWidth: '120px',
    flex: 1,
    borderTop: `3px solid ${color}`,
  }),
  statValue: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#e6e6e6',
  },
  statLabel: {
    fontSize: '12px',
    color: '#a1a1aa',
    marginTop: '2px',
  },
  toolbar: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap' as const,
    alignItems: 'center',
  },
  searchInput: {
    flex: 1,
    minWidth: '200px',
    padding: '10px 12px',
    background: '#0f0f10',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#e6e6e6',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box' as const,
  },
  filterBtn: (active: boolean) => ({
    padding: '7px 14px',
    borderRadius: '6px',
    border: active ? '1px solid #58a6ff' : '1px solid #2a2a2e',
    background: active ? 'rgba(88,166,255,0.1)' : '#1b1b1f',
    color: active ? '#58a6ff' : '#a1a1aa',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: active ? 600 : 400,
  }),
  btn: (variant: 'primary' | 'secondary' | 'danger') => ({
    padding: '8px 18px',
    borderRadius: '6px',
    border: variant === 'primary' ? 'none' : '1px solid #2a2a2e',
    background: variant === 'primary' ? '#58a6ff' : variant === 'danger' ? 'transparent' : '#1b1b1f',
    color: variant === 'primary' ? '#fff' : variant === 'danger' ? '#f87171' : '#a1a1aa',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: 500,
  }),
  card: {
    background: '#1b1b1f',
    border: '1px solid #2a2a2e',
    borderRadius: '10px',
    padding: '16px',
    marginBottom: '10px',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    justifyContent: 'space-between',
  },
  badge: (color: string) => ({
    display: 'inline-block',
    padding: '3px 10px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: 600,
    background: `${color}20`,
    color: color,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  }),
  cardName: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#e6e6e6',
  },
  cardDesc: {
    fontSize: '13px',
    color: '#a1a1aa',
    marginTop: '6px',
    lineHeight: 1.5,
  },
  cardDate: {
    fontSize: '12px',
    color: '#71717a',
    marginTop: '6px',
  },
  cardContent: {
    marginTop: '12px',
    padding: '12px',
    background: '#0f0f10',
    borderRadius: '6px',
    fontSize: '13px',
    color: '#e6e6e6',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap' as const,
    border: '1px solid #2a2a2e',
  },
  modal: {
    background: '#1b1b1f',
    border: '1px solid #2a2a2e',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '16px',
  },
  modalTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#e6e6e6',
    marginBottom: '16px',
  },
  field: {
    marginBottom: '12px',
  },
  label: {
    fontSize: '13px',
    color: '#a1a1aa',
    marginBottom: '6px',
    fontWeight: 500,
    display: 'block',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    background: '#0f0f10',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#e6e6e6',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box' as const,
  },
  textarea: {
    width: '100%',
    padding: '10px 12px',
    background: '#0f0f10',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#e6e6e6',
    fontSize: '14px',
    outline: 'none',
    minHeight: '100px',
    resize: 'vertical' as const,
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
  },
  select: {
    width: '100%',
    padding: '10px 12px',
    background: '#0f0f10',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#e6e6e6',
    fontSize: '14px',
    outline: 'none',
    cursor: 'pointer',
    boxSizing: 'border-box' as const,
  },
  loading: {
    textAlign: 'center' as const,
    padding: '40px',
    color: '#a1a1aa',
    fontSize: '14px',
  },
  error: {
    padding: '12px 16px',
    background: 'rgba(248,113,113,0.08)',
    border: '1px solid rgba(248,113,113,0.2)',
    borderRadius: '8px',
    color: '#f87171',
    fontSize: '13px',
    marginBottom: '12px',
  },
  empty: {
    textAlign: 'center' as const,
    padding: '40px',
    color: '#a1a1aa',
    fontSize: '14px',
  },
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<MemoryType | 'all'>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [newMemory, setNewMemory] = useState({
    type: 'user' as MemoryType,
    name: '',
    description: '',
    content: '',
  })

  const fetchMemories = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/memory')
      if (!res.ok) throw new Error('Failed to fetch memories')
      const data = await res.json()
      setMemories(data.memories || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load memories')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMemories()
  }, [])

  const handleCreate = async () => {
    if (!newMemory.name.trim()) return
    setCreating(true)
    setError(null)
    try {
      const res = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newMemory),
      })
      if (!res.ok) throw new Error('Failed to create memory')
      setNewMemory({ type: 'user', name: '', description: '', content: '' })
      setShowCreate(false)
      await fetchMemories()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    setError(null)
    try {
      const res = await fetch(`/api/memory/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Failed to delete memory')
      setDeleteConfirm(null)
      await fetchMemories()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Delete failed')
    }
  }

  // Client-side filtering
  const filtered = memories.filter((m) => {
    if (typeFilter !== 'all' && m.type !== typeFilter) return false
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      return (
        m.name.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q) ||
        m.content.toLowerCase().includes(q)
      )
    }
    return true
  })

  // Stats
  const totalCount = memories.length
  const typeCounts = {
    user: memories.filter((m) => m.type === 'user').length,
    feedback: memories.filter((m) => m.type === 'feedback').length,
    project: memories.filter((m) => m.type === 'project').length,
    reference: memories.filter((m) => m.type === 'reference').length,
  }

  return (
    <div style={styles.container}>
      <div style={styles.title}>Memory Management</div>
      <div style={styles.subtitle}>Manage stored memories and knowledge for AI context</div>

      {/* Stats */}
      <div style={styles.statsRow}>
        <div style={styles.statCard('#58a6ff')}>
          <div style={styles.statValue}>{totalCount}</div>
          <div style={styles.statLabel}>Total</div>
        </div>
        {(Object.keys(TYPE_COLORS) as MemoryType[]).map((type) => (
          <div key={type} style={styles.statCard(TYPE_COLORS[type])}>
            <div style={styles.statValue}>{typeCounts[type]}</div>
            <div style={styles.statLabel}>{TYPE_LABELS[type]}</div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div style={styles.toolbar}>
        <input
          style={styles.searchInput}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search memories..."
        />
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            style={styles.filterBtn(typeFilter === opt.value)}
            onClick={() => setTypeFilter(opt.value)}
          >
            {opt.label}
          </button>
        ))}
        <button style={styles.btn('primary')} onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ Create'}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* Create Form */}
      {showCreate && (
        <div style={styles.modal}>
          <div style={styles.modalTitle}>Create New Memory</div>
          <div style={styles.field}>
            <label style={styles.label}>Type</label>
            <select
              style={styles.select}
              value={newMemory.type}
              onChange={(e) => setNewMemory({ ...newMemory, type: e.target.value as MemoryType })}
            >
              {(Object.keys(TYPE_LABELS) as MemoryType[]).map((t) => (
                <option key={t} value={t}>{TYPE_LABELS[t]}</option>
              ))}
            </select>
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Name</label>
            <input
              style={styles.input}
              value={newMemory.name}
              onChange={(e) => setNewMemory({ ...newMemory, name: e.target.value })}
              placeholder="Memory name"
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Description</label>
            <input
              style={styles.input}
              value={newMemory.description}
              onChange={(e) => setNewMemory({ ...newMemory, description: e.target.value })}
              placeholder="Brief description"
            />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Content</label>
            <textarea
              style={styles.textarea}
              value={newMemory.content}
              onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
              placeholder="Full content of the memory..."
            />
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button style={styles.btn('primary')} onClick={handleCreate} disabled={creating || !newMemory.name.trim()}>
              {creating ? 'Creating...' : 'Create Memory'}
            </button>
            <button style={styles.btn('secondary')} onClick={() => setShowCreate(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Memory List */}
      {loading ? (
        <div style={styles.loading}>Loading memories...</div>
      ) : filtered.length === 0 ? (
        <div style={styles.empty}>
          {searchQuery || typeFilter !== 'all' ? 'No memories match your filter' : 'No memories yet. Create one to get started.'}
        </div>
      ) : (
        <div>
          {filtered.map((mem) => (
            <div
              key={mem.id}
              style={styles.card}
              onClick={() => setExpandedId(expandedId === mem.id ? null : mem.id)}
              onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#58a6ff' }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#2a2a2e' }}
            >
              <div style={styles.cardHeader}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={styles.badge(TYPE_COLORS[mem.type])}>{TYPE_LABELS[mem.type]}</span>
                  <span style={styles.cardName}>{mem.name}</span>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {deleteConfirm === mem.id ? (
                    <>
                      <button
                        style={styles.btn('danger')}
                        onClick={(e) => { e.stopPropagation(); handleDelete(mem.id) }}
                      >
                        Confirm Delete
                      </button>
                      <button
                        style={styles.btn('secondary')}
                        onClick={(e) => { e.stopPropagation(); setDeleteConfirm(null) }}
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <button
                      style={styles.btn('danger')}
                      onClick={(e) => { e.stopPropagation(); setDeleteConfirm(mem.id) }}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
              {mem.description && <div style={styles.cardDesc}>{mem.description}</div>}
              <div style={styles.cardDate}>
                {mem.createdAt ? new Date(mem.createdAt).toLocaleDateString() : ''}
              </div>
              {expandedId === mem.id && (
                <div style={styles.cardContent}>{mem.content || 'No content'}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

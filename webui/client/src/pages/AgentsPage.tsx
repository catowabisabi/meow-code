import { useState, useEffect } from 'react'
import { toast } from '../components/shared/Toast'

interface Agent {
  id: string
  name: string
  type: 'explore' | 'plan' | 'general' | 'verify'
  status: 'running' | 'completed' | 'error'
  createdAt: number
  result?: string
  error?: string
}

const styles = {
  container: { padding: '24px 32px', maxWidth: '900px', margin: '0 auto' },
  title: { fontSize: '22px', fontWeight: 700, color: '#e6e6e6', marginBottom: '8px' },
  subtitle: { fontSize: '13px', color: '#a1a1aa', marginBottom: '24px' },
  section: { background: '#1b1b1f', border: '1px solid #2a2a2e', borderRadius: '12px', padding: '20px', marginBottom: '16px' },
  sectionTitle: { fontSize: '16px', fontWeight: 600, marginBottom: '14px', color: '#e6e6e6' },
  card: { background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '8px', padding: '14px', marginBottom: '10px' },
  cardTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  cardName: { fontSize: '14px', fontWeight: 600, color: '#e6e6e6' },
  cardMeta: { fontSize: '12px', color: '#71717a', marginTop: '4px' },
  statusBadge: (status: string) => ({
    padding: '4px 10px',
    borderRadius: '14px',
    border: `1px solid ${status === 'running' ? '#22c55e' : status === 'completed' ? '#3b82f6' : '#f85149'}`,
    background: status === 'running' ? 'rgba(34,197,94,0.12)' : status === 'completed' ? 'rgba(59,130,246,0.12)' : 'rgba(248,81,73,0.12)',
    color: status === 'running' ? '#22c55e' : status === 'completed' ? '#3b82f6' : '#f85149',
    fontSize: '11px',
    fontWeight: 500,
  }),
  typeBadge: { padding: '2px 8px', borderRadius: '6px', fontSize: '10px', background: 'rgba(249,115,22,0.1)', color: '#f97316', border: '1px solid rgba(249,115,22,0.2)' },
  result: { marginTop: '10px', padding: '10px', background: '#151517', borderRadius: '6px', fontSize: '12px', color: '#9ca3af', whiteSpace: 'pre-wrap' as const, maxHeight: '200px', overflowY: 'auto' as const },
  spawnBtn: { padding: '8px 16px', borderRadius: '8px', border: 'none', background: '#f97316', color: '#fff', fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' },
  runBtn: { padding: '4px 10px', borderRadius: '6px', border: '1px solid #2a2a2e', background: 'transparent', color: '#22c55e', fontSize: '12px', cursor: 'pointer' },
  delBtn: { padding: '4px 10px', borderRadius: '6px', border: 'none', background: 'transparent', color: '#f85149', fontSize: '12px', cursor: 'pointer' },
  modal: { position: 'fixed' as const, inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modalContent: { background: '#1b1b1f', border: '1px solid #2a2a2e', borderRadius: '12px', padding: '24px', width: '450px', maxWidth: '90vw' },
  field: { marginBottom: '14px' },
  label: { fontSize: '13px', color: '#a1a1aa', marginBottom: '6px', display: 'block' },
  input: { width: '100%', padding: '8px 12px', background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '6px', color: '#e6e6e6', fontSize: '14px', outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' as const },
  select: { width: '100%', padding: '8px 12px', background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '6px', color: '#e6e6e6', fontSize: '14px', outline: 'none' },
  loading: { textAlign: 'center' as const, padding: '40px', color: '#a1a1aa', fontSize: '14px' },
  empty: { textAlign: 'center' as const, padding: '30px', color: '#71717a', fontSize: '13px' },
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div style={styles.modal} onClick={onClose}>
      <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#e6e6e6', margin: 0 }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#71717a', fontSize: '20px', cursor: 'pointer' }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [spawning, setSpawning] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [newAgent, setNewAgent] = useState({ name: '', type: 'general' as const, task: '' })

  const fetchAgents = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/agents')
      const data = await res.json()
      setAgents(data.agents || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAgents() }, [])

  const handleSpawn = async () => {
    if (!newAgent.name || !newAgent.task) return
    setSpawning(true)
    const loadingId = toast.loading('正在創建代理...')
    try {
      await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAgent),
      })
      toast.dismiss(loadingId)
      toast.success('代理創建成功', newAgent.name)
      await fetchAgents()
      setModalOpen(false)
      setNewAgent({ name: '', type: 'general', task: '' })
    } catch (err) {
      toast.dismiss(loadingId)
      toast.error('創建代理失敗', err instanceof Error ? err.message : undefined)
    } finally {
      setSpawning(false)
    }
  }

  const handleRun = async (id: string) => {
    const loadingId = toast.loading('正在運行代理...')
    try {
      await fetch(`/api/agents/${id}/run?id=${id}`, { method: 'POST' })
      toast.dismiss(loadingId)
      toast.success('代理運行完成')
      await fetchAgents()
    } catch (err) {
      toast.dismiss(loadingId)
      toast.error('運行代理失敗', err instanceof Error ? err.message : undefined)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this agent?')) return
    const loadingId = toast.loading('正在刪除...')
    try {
      await fetch(`/api/agents/${id}?id=${id}`, { method: 'DELETE' })
      toast.dismiss(loadingId)
      toast.success('代理已刪除')
      await fetchAgents()
    } catch (err) {
      toast.dismiss(loadingId)
      toast.error('刪除代理失敗', err instanceof Error ? err.message : undefined)
    }
  }

  const typeLabels = { explore: 'Explorer', plan: 'Planner', general: 'General', verify: 'Verifier' }

  return (
    <div style={styles.container}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={styles.title}>Subagents</div>
        <button onClick={() => setModalOpen(true)} style={styles.spawnBtn}>+ Spawn Agent</button>
      </div>
      <div style={styles.subtitle}>Spawn and manage sub-agents for parallel task execution.</div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Active Agents ({agents.length})</div>
        {loading ? <div style={styles.loading}>Loading...</div> : agents.length === 0 ? (
          <div style={styles.empty}>No agents spawned. Click "Spawn Agent" to create one.</div>
        ) : agents.map((agent) => (
          <div key={agent.id} style={styles.card}>
            <div style={styles.cardTop}>
              <div>
                <div style={styles.cardName}>{agent.name}</div>
                <div style={styles.cardMeta}>
                  <span style={styles.typeBadge}>{typeLabels[agent.type]}</span>
                  <span style={{ marginLeft: '8px' }}>Created {new Date(agent.createdAt).toLocaleTimeString()}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={styles.statusBadge(agent.status)}>{agent.status}</span>
                {agent.status !== 'running' && (
                  <>
                    <button onClick={() => handleRun(agent.id)} style={styles.runBtn}>Run</button>
                    <button onClick={() => handleDelete(agent.id)} style={styles.delBtn}>Delete</button>
                  </>
                )}
              </div>
            </div>
            {(agent.result || agent.error) && (
              <div style={styles.result}>{agent.error || agent.result}</div>
            )}
          </div>
        ))}
      </div>

      <div style={styles.section}>
        <div style={styles.sectionTitle}>Agent Types</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
          {Object.entries(typeLabels).map(([key, label]) => (
            <div key={key} style={{ padding: '12px', background: '#0f0f10', borderRadius: '8px', border: '1px solid #2a2a2e' }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>{label}</div>
              <div style={{ fontSize: '12px', color: '#71717a' }}>
                {key === 'explore' && 'Read-only exploration. Use for gathering info.'}
                {key === 'plan' && 'Create step-by-step plans. No file changes.'}
                {key === 'general' && 'Full access. Can read, write, and execute.'}
                {key === 'verify' && 'Verify correctness. Run tests and report.'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {modalOpen && (
        <Modal title="Spawn New Agent" onClose={() => setModalOpen(false)}>
          <div style={styles.field}>
            <label style={styles.label}>Agent Name</label>
            <input style={styles.input} value={newAgent.name} onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })} placeholder="e.g. file-explorer" />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Type</label>
            <select style={styles.select} value={newAgent.type} onChange={(e) => setNewAgent({ ...newAgent, type: e.target.value as any })}>
              <option value="explore">Explorer - Read-only</option>
              <option value="plan">Plan - Create plans</option>
              <option value="general">General - Full access</option>
              <option value="verify">Verify - Run tests</option>
            </select>
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Task</label>
            <textarea style={{ ...styles.input, minHeight: '100px', resize: 'vertical' }} value={newAgent.task} onChange={(e) => setNewAgent({ ...newAgent, task: e.target.value })} placeholder="What should this agent do?" />
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
            <button onClick={() => setModalOpen(false)} style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #2a2a2e', background: 'transparent', color: '#a1a1aa', fontSize: '13px', cursor: 'pointer' }}>Cancel</button>
            <button onClick={handleSpawn} disabled={spawning || !newAgent.name || !newAgent.task} style={{ ...styles.spawnBtn, opacity: spawning || !newAgent.name || !newAgent.task ? 0.6 : 1 }}>Spawn</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

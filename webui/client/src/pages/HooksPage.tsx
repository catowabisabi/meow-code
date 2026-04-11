import { useState, useEffect } from 'react'

interface Hook {
  name: string
  type: 'pre-command' | 'post-command' | 'pre-task' | 'post-task'
  enabled: boolean
  script: string
  description: string
}

const styles = {
  container: { padding: '24px 32px', maxWidth: '900px', margin: '0 auto' },
  title: { fontSize: '22px', fontWeight: 700, color: '#e6e6e6', marginBottom: '8px' },
  subtitle: { fontSize: '13px', color: '#a1a1aa', marginBottom: '24px' },
  section: { background: '#1b1b1f', border: '1px solid #2a2a2e', borderRadius: '12px', padding: '20px', marginBottom: '16px' },
  sectionTitle: { fontSize: '16px', fontWeight: 600, marginBottom: '14px', color: '#e6e6e6' },
  hookCard: { background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '8px', padding: '14px', marginBottom: '10px' },
  hookTop: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  hookName: { fontSize: '14px', fontWeight: 600, color: '#e6e6e6' },
  hookDesc: { fontSize: '12px', color: '#71717a', marginTop: '4px' },
  hookScript: { marginTop: '10px', padding: '10px', background: '#151517', borderRadius: '6px', fontSize: '12px', fontFamily: 'monospace', color: '#9ca3af', whiteSpace: 'pre-wrap' as const, maxHeight: '100px', overflowY: 'auto' as const },
  typeBadge: (type: string) => ({
    padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 500,
    background: type.includes('pre') ? 'rgba(59,130,246,0.1)' : 'rgba(34,197,94,0.1)',
    color: type.includes('pre') ? '#3b82f6' : '#22c55e',
    border: `1px solid ${type.includes('pre') ? 'rgba(59,130,246,0.3)' : 'rgba(34,197,94,0.3)'}`,
  }),
  toggle: (enabled: boolean) => ({
    padding: '4px 10px', borderRadius: '14px', border: `1px solid ${enabled ? '#22c55e' : '#71717a'}`,
    background: enabled ? 'rgba(34,197,94,0.12)' : 'rgba(113,113,122,0.1)',
    color: enabled ? '#22c55e' : '#71717a', fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit',
  }),
  addBtn: { padding: '8px 16px', borderRadius: '8px', border: 'none', background: '#f97316', color: '#fff', fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' },
  editBtn: { padding: '4px 10px', borderRadius: '6px', border: '1px solid #2a2a2e', background: 'transparent', color: '#a1a1aa', fontSize: '12px', cursor: 'pointer' },
  deleteBtn: { padding: '4px 10px', borderRadius: '6px', border: 'none', background: 'transparent', color: '#f85149', fontSize: '12px', cursor: 'pointer' },
  empty: { textAlign: 'center' as const, padding: '30px', color: '#71717a', fontSize: '13px' },
  infoBox: { background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '8px', padding: '14px', fontSize: '13px', color: '#a1a1aa', lineHeight: 1.6 },
  modal: { position: 'fixed' as const, inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 },
  modalContent: { background: '#1b1b1f', border: '1px solid #2a2a2e', borderRadius: '12px', padding: '24px', width: '500px', maxWidth: '90vw' },
  field: { marginBottom: '14px' },
  label: { fontSize: '13px', color: '#a1a1aa', marginBottom: '6px', display: 'block' },
  input: { width: '100%', padding: '8px 12px', background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '6px', color: '#e6e6e6', fontSize: '14px', outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' as const },
  select: { width: '100%', padding: '8px 12px', background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '6px', color: '#e6e6e6', fontSize: '14px', outline: 'none' },
}

const TYPE_LABELS: Record<string, string> = {
  'pre-command': 'Pre-Command',
  'post-command': 'Post-Command',
  'pre-task': 'Pre-Task',
  'post-task': 'Post-Task',
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

export default function HooksPage() {
  const [hooks, setHooks] = useState<Hook[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingHook, setEditingHook] = useState<Hook | undefined>()
  const [newHook, setNewHook] = useState<Hook>({ name: '', type: 'post-command', enabled: true, script: '#!/bin/bash\necho "Hook running..."', description: '' })

  useEffect(() => {
    const mockHooks: Hook[] = [
      { name: 'lint-check', type: 'pre-command', enabled: true, description: 'Run linter before git commits', script: '#!/bin/bash\nexit 0' },
      { name: 'format-code', type: 'post-command', enabled: false, description: 'Auto-format code after changes', script: '#!/bin/bash\nnpm run format' },
      { name: 'test-runner', type: 'post-task', enabled: true, description: 'Run tests after task completion', script: '#!/bin/bash\nnpm test' },
    ]
    setHooks(mockHooks)
    setLoading(false)
  }, [])

  const handleSave = () => {
    if (editingHook) {
      setHooks(hooks.map((h) => (h.name === editingHook.name ? { ...newHook, name: editingHook.name } : h)))
    } else {
      setHooks([...hooks, newHook])
    }
    setModalOpen(false)
    setEditingHook(undefined)
    setNewHook({ name: '', type: 'post-command', enabled: true, script: '#!/bin/bash\necho "Hook running..."', description: '' })
  }

  const handleEdit = (hook: Hook) => {
    setEditingHook(hook)
    setNewHook(hook)
    setModalOpen(true)
  }

  const handleDelete = (name: string) => {
    if (!confirm(`Delete hook "${name}"?`)) return
    setHooks(hooks.filter((h) => h.name !== name))
  }

  const handleToggle = (name: string) => {
    setHooks(hooks.map((h) => (h.name === name ? { ...h, enabled: !h.enabled } : h)))
  }

  return (
    <div style={styles.container}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={styles.title}>Hooks</div>
        <button onClick={() => { setEditingHook(undefined); setNewHook({ name: '', type: 'post-command', enabled: true, script: '#!/bin/bash\necho "Hook running..."', description: '' }); setModalOpen(true) }} style={styles.addBtn}>+ Add Hook</button>
      </div>
      <div style={styles.subtitle}>Configure pre/post command and task hooks for automation.</div>

      {loading ? <div style={styles.empty}>Loading hooks...</div> : (
        <>
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Active Hooks ({hooks.filter((h) => h.enabled).length})</div>
            {hooks.length === 0 ? (
              <div style={styles.empty}>No hooks configured. Add one to get started.</div>
            ) : hooks.map((hook) => (
              <div key={hook.name} style={styles.hookCard}>
                <div style={styles.hookTop}>
                  <div>
                    <div style={styles.hookName}>{hook.name}</div>
                    <div style={styles.hookDesc}>{hook.description || 'No description'}</div>
                    <div style={{ marginTop: '6px' }}><span style={styles.typeBadge(hook.type)}>{TYPE_LABELS[hook.type]}</span></div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button onClick={() => handleToggle(hook.name)} style={styles.toggle(hook.enabled)}>{hook.enabled ? 'ON' : 'OFF'}</button>
                    <button onClick={() => handleEdit(hook)} style={styles.editBtn}>Edit</button>
                    <button onClick={() => handleDelete(hook.name)} style={styles.deleteBtn}>Delete</button>
                  </div>
                </div>
                <div style={styles.hookScript}>{hook.script}</div>
              </div>
            ))}
          </div>

          <div style={styles.section}>
            <div style={styles.sectionTitle}>Hook Types</div>
            <div style={styles.infoBox}>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>Pre-Command</div>
                <div>Runs before a command is executed. Can modify or reject the command.</div>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>Post-Command</div>
                <div>Runs after a command completes. Useful for notifications or cleanup.</div>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>Pre-Task</div>
                <div>Runs before a task starts. Can validate task parameters.</div>
              </div>
              <div>
                <div style={{ fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>Post-Task</div>
                <div>Runs after a task completes. Useful for testing or deployment.</div>
              </div>
            </div>
          </div>
        </>
      )}

      {modalOpen && (
        <Modal title={editingHook ? `Edit Hook: ${editingHook.name}` : 'Add New Hook'} onClose={() => { setModalOpen(false); setEditingHook(undefined) }}>
          <div style={styles.field}>
            <label style={styles.label}>Hook Name</label>
            <input style={styles.input} value={newHook.name} onChange={(e) => setNewHook({ ...newHook, name: e.target.value })} placeholder="e.g. lint-before-commit" disabled={!!editingHook} />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Type</label>
            <select style={styles.select} value={newHook.type} onChange={(e) => setNewHook({ ...newHook, type: e.target.value as Hook['type'] })}>
              <option value="pre-command">Pre-Command</option>
              <option value="post-command">Post-Command</option>
              <option value="pre-task">Pre-Task</option>
              <option value="post-task">Post-Task</option>
            </select>
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Description</label>
            <input style={styles.input} value={newHook.description} onChange={(e) => setNewHook({ ...newHook, description: e.target.value })} placeholder="What does this hook do?" />
          </div>
          <div style={styles.field}>
            <label style={styles.label}>Script</label>
            <textarea style={{ ...styles.input, minHeight: '150px', fontFamily: 'monospace', resize: 'vertical' }} value={newHook.script} onChange={(e) => setNewHook({ ...newHook, script: e.target.value })} placeholder="#!/bin/bash&#10;echo 'Running hook...'" />
          </div>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
            <button onClick={() => { setModalOpen(false); setEditingHook(undefined) }} style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid #2a2a2e', background: 'transparent', color: '#a1a1aa', fontSize: '13px', cursor: 'pointer' }}>Cancel</button>
            <button onClick={handleSave} style={styles.addBtn}>Save</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

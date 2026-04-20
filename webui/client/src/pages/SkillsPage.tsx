import { useState, useEffect } from 'react'

interface Skill {
  name: string
  description: string
  prompt: string
  triggers: string[]
  enabled: boolean
  isDefault?: boolean
}

const C = {
  bg: 'var(--bg-primary)',
  surface: 'var(--bg-secondary)',
  border: 'var(--border-default)',
  text: 'var(--text-primary)',
  textSecondary: 'var(--text-secondary)',
  textMuted: 'var(--text-muted)',
  bgHover: 'var(--bg-secondary)',
  accent: 'var(--accent-primary)',
  green: 'var(--accent-green)',
  red: 'var(--accent-red)',
  blue: 'var(--accent-blue)',
}

const styles = {
  container: {
    padding: '24px 32px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '8px',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
  subtitle: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    marginBottom: '24px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))',
    gap: '12px',
    marginBottom: '24px',
  },
  card: (enabled: boolean) => ({
    background: 'var(--bg-secondary)',
    border: '1px solid #2a2a2e',
    borderRadius: '10px',
    padding: '16px',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
    opacity: enabled ? 1 : 0.5,
  }),
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '8px',
  },
  cardName: {
    fontSize: '15px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  enabledDot: (enabled: boolean) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: enabled ? 'var(--accent-green)' : 'var(--text-muted)',
    flexShrink: 0,
  }),
  cardDesc: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: 1.5,
    marginBottom: '10px',
  },
  tagsRow: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap' as const,
  },
  tag: {
    display: 'inline-block',
    padding: '3px 10px',
    borderRadius: '12px',
    fontSize: '11px',
    fontWeight: 500,
    background: 'rgba(88,166,255,0.1)',
    color: 'var(--accent-blue)',
    border: '1px solid rgba(88,166,255,0.2)',
  },
  defaultBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '8px',
    fontSize: '10px',
    fontWeight: 600,
    background: 'rgba(249,115,22,0.12)',
    color: 'var(--accent-primary)',
    border: '1px solid rgba(249,115,22,0.25)',
  },
  expandedContent: {
    marginTop: '12px',
    padding: '12px',
    background: 'var(--bg-primary)',
    borderRadius: '6px',
    fontSize: '13px',
    color: 'var(--text-primary)',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap' as const,
    border: '1px solid #2a2a2e',
    maxHeight: '300px',
    overflowY: 'auto' as const,
  },
  section: {
    background: 'var(--bg-secondary)',
    border: '1px solid #2a2a2e',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: 600,
    marginBottom: '14px',
    color: 'var(--text-primary)',
  },
  cardActions: {
    display: 'flex',
    gap: '8px',
    marginTop: '12px',
    paddingTop: '12px',
    borderTop: '1px solid #2a2a2e',
  },
  actionBtn: (color?: string) => ({
    padding: '5px 12px',
    borderRadius: '6px',
    border: '1px solid #2a2a2e',
    background: 'transparent',
    color: color || 'var(--text-secondary)',
    fontSize: '12px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  }),
  loading: {
    textAlign: 'center' as const,
    padding: '40px',
    color: 'var(--text-secondary)',
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
    color: 'var(--text-secondary)',
    fontSize: '14px',
  },
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-secondary)',
          border: '1px solid #2a2a2e',
          borderRadius: '12px',
          padding: '24px',
          width: '500px',
          maxWidth: '90vw',
          maxHeight: '90vh',
          overflow: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>{title}</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '20px', cursor: 'pointer', padding: '4px 8px' }}
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

function SkillForm({ skill, onSave, onCancel, saving }: { skill: Partial<Skill>; onSave: (s: Partial<Skill>) => void; onCancel: () => void; saving: boolean }) {
  const [name, setName] = useState(skill.name || '')
  const [description, setDescription] = useState(skill.description || '')
  const [prompt, setPrompt] = useState(skill.prompt || '')
  const [triggers, setTriggers] = useState((skill.triggers || []).join(', '))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      name: name.trim(),
      description: description.trim(),
      prompt: prompt.trim(),
      triggers: triggers.split(',').map((t) => t.trim()).filter(Boolean),
      enabled: skill.enabled ?? true,
    })
  }

  const fieldStyle = {
    width: '100%' as const,
    padding: '8px 12px',
    background: 'var(--bg-primary)',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
  }

  return (
    <form onSubmit={handleSubmit}>
      <div style={{ marginBottom: '14px' }}>
        <label style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', display: 'block' }}>Name</label>
        <input style={fieldStyle} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. my-custom-skill" required />
      </div>
      <div style={{ marginBottom: '14px' }}>
        <label style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', display: 'block' }}>Description</label>
        <input style={fieldStyle} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this skill does" />
      </div>
      <div style={{ marginBottom: '14px' }}>
        <label style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', display: 'block' }}>Triggers (comma-separated)</label>
        <input style={fieldStyle} value={triggers} onChange={(e) => setTriggers(e.target.value)} placeholder="/trigger, trigger phrase" />
      </div>
      <div style={{ marginBottom: '20px' }}>
        <label style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', display: 'block' }}>Prompt</label>
        <textarea
          style={{ ...fieldStyle, minHeight: '200px', resize: 'vertical' }}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Instructions for the AI when this skill is activated..."
          required
        />
      </div>
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
        <button type="button" onClick={onCancel} style={{ ...styles.actionBtn(), padding: '8px 16px' }}>Cancel</button>
        <button type="submit" disabled={saving} style={{ ...styles.actionBtn(), padding: '8px 16px', background: 'var(--accent-primary)', borderColor: 'var(--accent-primary)', color: '#fff' }}>
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </form>
  )
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedName, setExpandedName] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [modalMode, setModalMode] = useState<'create' | 'edit' | null>(null)
  const [editingSkill, setEditingSkill] = useState<Partial<Skill> | null>(null)

  const fetchSkills = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/skills')
      if (!res.ok) throw new Error('Failed to fetch skills')
      const data = await res.json()
      setSkills(data.skills || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load skills')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSkills()
  }, [])

  const handleCreate = () => {
    setEditingSkill({ name: '', description: '', prompt: '', triggers: [] })
    setModalMode('create')
  }

  const handleEdit = (skill: Skill, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingSkill(skill)
    setModalMode('edit')
  }

  const handleDuplicate = async (skill: Skill, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await fetch(`/api/skills/${encodeURIComponent(skill.name)}/duplicate?` + new URLSearchParams({ name: skill.name }), { method: 'POST' })
      if (!res.ok) throw new Error('Failed to duplicate')
      await fetchSkills()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to duplicate skill')
    }
  }

  const handleDelete = async (skill: Skill, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!confirm(`Delete skill "${skill.name}"?`)) return
    try {
      const res = await fetch(`/api/skills/${encodeURIComponent(skill.name)}?` + new URLSearchParams({ name: skill.name }), { method: 'DELETE' })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Failed to delete')
      }
      await fetchSkills()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete skill')
    }
  }

  const handleSaveSkill = async (skillData: Partial<Skill>) => {
    setSaving(true)
    try {
      if (modalMode === 'create') {
        await fetch('/api/skills', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(skillData),
        })
      } else if (modalMode === 'edit' && editingSkill?.name) {
        await fetch(`/api/skills/${encodeURIComponent(editingSkill.name)}?` + new URLSearchParams({ name: editingSkill.name }), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(skillData),
        })
      }
      setModalMode(null)
      setEditingSkill(null)
      await fetchSkills()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save skill')
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (skill: Skill, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await fetch(
        `/api/skills/${encodeURIComponent(skill.name)}/enable?` + new URLSearchParams({ name: skill.name, enabled: String(!skill.enabled) }),
        { method: 'PATCH' }
      )
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'Failed to toggle')
      }
      await fetchSkills()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle skill')
    }
  }

  const truncate = (text: string, maxLen: number) =>
    text.length > maxLen ? text.slice(0, maxLen) + '...' : text

  return (
    <div style={styles.container}>
      <div style={styles.titleRow}>
        <div style={styles.title}>Skills Management</div>
        <button
          onClick={handleCreate}
          style={{ padding: '8px 16px', borderRadius: '8px', border: 'none', background: 'var(--accent-primary)', color: '#fff', fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' }}
        >
          + New Skill
        </button>
      </div>
      <div style={styles.subtitle}>View available skills and their trigger keywords. Click a card to expand details.</div>

      {error && <div style={styles.error}>{error} <span style={{ float: 'right', cursor: 'pointer' }} onClick={() => setError(null)}>✕</span></div>}

      {loading ? (
        <div style={styles.loading}>Loading skills...</div>
      ) : skills.length === 0 ? (
        <div style={styles.empty}>No skills available. Click "+ New Skill" to create one.</div>
      ) : (
        <div style={styles.grid}>
          {skills.map((skill) => (
            <div
              key={skill.name}
              style={styles.card(skill.enabled)}
              onClick={() => setExpandedName(expandedName === skill.name ? null : skill.name)}
              onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--accent-blue)' }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-default)' }}
            >
              <div style={styles.cardHeader}>
                <div style={styles.cardName}>
                  <span style={styles.enabledDot(skill.enabled)} />
                  <span>{skill.name}</span>
                  {skill.isDefault && <span style={styles.defaultBadge}>Default</span>}
                </div>
                <button
                  onClick={(e) => handleToggle(skill, e)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '14px',
                    border: `1px solid ${skill.enabled ? 'var(--accent-green)' : 'var(--text-muted)'}`,
                    background: skill.enabled ? 'rgba(34,197,94,0.12)' : 'rgba(113,113,122,0.1)',
                    color: skill.enabled ? 'var(--accent-green)' : 'var(--text-muted)',
                    fontSize: '11px',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  {skill.enabled ? 'ON' : 'OFF'}
                </button>
              </div>
              <div style={styles.cardDesc}>
                {truncate(skill.description || skill.prompt || 'No description', 120)}
              </div>
              {skill.triggers.length > 0 && (
                <div style={styles.tagsRow}>
                  {skill.triggers.slice(0, 4).map((trigger, i) => (
                    <span key={i} style={styles.tag}>{trigger}</span>
                  ))}
                  {skill.triggers.length > 4 && (
                    <span style={{ ...styles.tag, background: 'rgba(113,113,122,0.1)', color: 'var(--text-muted)', borderColor: 'rgba(113,113,122,0.2)' }}>
                      +{skill.triggers.length - 4}
                    </span>
                  )}
                </div>
              )}
              {expandedName === skill.name && (
                <>
                  <div style={styles.expandedContent}>
                    {skill.prompt || 'No prompt content'}
                  </div>
                  <div style={styles.cardActions}>
                    {!skill.isDefault && (
                      <>
                        <button style={styles.actionBtn()} onClick={(e) => handleEdit(skill, e)}>Edit</button>
                        <button style={styles.actionBtn()} onClick={(e) => handleDuplicate(skill, e)}>Duplicate</button>
                        <button style={styles.actionBtn(C.red)} onClick={(e) => handleDelete(skill, e)}>Delete</button>
                      </>
                    )}
                    {skill.isDefault && (
                      <button style={styles.actionBtn()} onClick={(e) => handleDuplicate(skill, e)}>Duplicate</button>
                    )}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}

      {modalMode && editingSkill && (
        <Modal
          title={modalMode === 'create' ? 'Create New Skill' : `Edit Skill: ${editingSkill.name}`}
          onClose={() => { setModalMode(null); setEditingSkill(null) }}
        >
          <SkillForm
            skill={editingSkill}
            onSave={handleSaveSkill}
            onCancel={() => { setModalMode(null); setEditingSkill(null) }}
            saving={saving}
          />
        </Modal>
      )}
    </div>
  )
}
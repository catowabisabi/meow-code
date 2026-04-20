import { useState, useEffect } from 'react'
import { toast } from '../components/shared/Toast'

interface MCPServer {
  name: string
  command: string
  args?: string[]
  enabled: boolean
}

interface MCPTemplate {
  name: string
  label: string
  description: string
  command: string
  args: string[]
}

const styles = {
  container: {
    padding: '24px 32px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    color: 'var(--text-primary)',
    marginBottom: '8px',
  },
  subtitle: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    marginBottom: '24px',
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
  card: {
    background: 'var(--bg-primary)',
    border: '1px solid #2a2a2e',
    borderRadius: '8px',
    padding: '14px',
    marginBottom: '10px',
  },
  cardTop: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  cardDesc: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    marginTop: '4px',
  },
  cardCmd: {
    fontSize: '11px',
    color: 'var(--text-muted)',
    marginTop: '6px',
    fontFamily: 'monospace' as const,
  },
  toggle: (enabled: boolean) => ({
    padding: '4px 10px',
    borderRadius: '14px',
    border: `1px solid ${enabled ? 'var(--accent-green)' : 'var(--text-muted)'}`,
    background: enabled ? 'rgba(34,197,94,0.12)' : 'rgba(113,113,122,0.1)',
    color: enabled ? 'var(--accent-green)' : 'var(--text-muted)',
    fontSize: '11px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  }),
  btn: (primary?: boolean) => ({
    padding: '6px 14px',
    borderRadius: '6px',
    border: primary ? 'none' : '1px solid #2a2a2e',
    background: primary ? 'var(--accent-primary)' : 'transparent',
    color: primary ? '#fff' : 'var(--text-secondary)',
    fontSize: '12px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  }),
  deleteBtn: {
    padding: '4px 8px',
    borderRadius: '4px',
    border: 'none',
    background: 'transparent',
    color: 'var(--accent-red)',
    fontSize: '12px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  addBtn: {
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    background: 'var(--accent-primary)',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
    fontFamily: 'inherit',
  },
  templateGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
    gap: '12px',
  },
  templateCard: {
    background: 'var(--bg-primary)',
    border: '1px solid #2a2a2e',
    borderRadius: '8px',
    padding: '14px',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  templateName: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    marginBottom: '4px',
  },
  templateDesc: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    lineHeight: 1.4,
  },
  modal: {
    position: 'fixed' as const,
    inset: 0,
    background: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modalContent: {
    background: 'var(--bg-secondary)',
    border: '1px solid #2a2a2e',
    borderRadius: '12px',
    padding: '24px',
    width: '450px',
    maxWidth: '90vw',
  },
  field: {
    marginBottom: '14px',
  },
  label: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    marginBottom: '6px',
    display: 'block',
  },
  input: {
    width: '100%',
    padding: '8px 12px',
    background: 'var(--bg-primary)',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
    fontFamily: 'inherit',
    boxSizing: 'border-box' as const,
  },
  loading: {
    textAlign: 'center' as const,
    padding: '40px',
    color: 'var(--text-secondary)',
    fontSize: '14px',
  },
  empty: {
    textAlign: 'center' as const,
    padding: '30px',
    color: 'var(--text-muted)',
    fontSize: '13px',
  },
}

function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div style={styles.modal} onClick={onClose}>
      <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '20px', cursor: 'pointer' }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

function ServerForm({ server, onSave, onCancel, saving }: { server?: Partial<MCPServer>; onSave: (s: Partial<MCPServer>) => void; onCancel: () => void; saving: boolean }) {
  const [name, setName] = useState(server?.name || '')
  const [command, setCommand] = useState(server?.command || '')
  const [args, setArgs] = useState((server?.args || []).join(' '))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      name: name.trim(),
      command: command.trim(),
      args: args.trim().split(/\s+/).filter(Boolean),
      enabled: true,
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <div style={styles.field}>
        <label style={styles.label}>Server Name</label>
        <input style={styles.input} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. filesystem" required disabled={!!server?.name} />
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Command</label>
        <input style={styles.input} value={command} onChange={(e) => setCommand(e.target.value)} placeholder="e.g. npx, node, python" required />
      </div>
      <div style={styles.field}>
        <label style={styles.label}>Arguments (space-separated)</label>
        <input style={styles.input} value={args} onChange={(e) => setArgs(e.target.value)} placeholder="e.g. -y @modelcontextprotocol/server-filesystem ." />
      </div>
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
        <button type="button" onClick={onCancel} style={styles.btn()}>Cancel</button>
        <button type="submit" disabled={saving} style={{ ...styles.btn(true), opacity: saving ? 0.7 : 1 }}>{saving ? 'Saving...' : 'Save'}</button>
      </div>
    </form>
  )
}

export default function MCPPage() {
  const [servers, setServers] = useState<MCPServer[]>([])
  const [templates, setTemplates] = useState<MCPTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingServer, setEditingServer] = useState<Partial<MCPServer> | undefined>()

  const fetchServers = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/mcp/servers')
      const data = await res.json()
      setServers(data.servers || [])
    } catch {
      setServers([])
    } finally {
      setLoading(false)
    }
  }

  const fetchTemplates = async () => {
    try {
      const res = await fetch('/api/mcp/templates')
      const data = await res.json()
      setTemplates(data.templates || [])
    } catch {
      setTemplates([])
    }
  }

  useEffect(() => {
    fetchServers()
    fetchTemplates()
  }, [])

  const handleAddTemplate = async (template: MCPTemplate) => {
    if (servers.some((s) => s.name === template.name)) return
    setSaving(true)
    const loadingId = toast.loading('正在添加服務器...')
    try {
      await fetch('/api/mcp/servers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: template.name, command: template.command, args: template.args, enabled: true }),
      })
      toast.dismiss(loadingId)
      toast.success('MCP 服務器已添加', template.name)
      await fetchServers()
    } catch (err) {
      toast.dismiss(loadingId)
      toast.error('添加失敗', err instanceof Error ? err.message : undefined)
    } finally {
      setSaving(false)
    }
  }

  const handleAddCustom = () => {
    setEditingServer({})
    setModalOpen(true)
  }

  const handleSaveServer = async (serverData: Partial<MCPServer>) => {
    setSaving(true)
    const loadingId = toast.loading(editingServer?.name ? '正在更新...' : '正在創建...')
    try {
      if (editingServer?.name) {
        await fetch(`/api/mcp/servers/${encodeURIComponent(editingServer.name)}?name=${encodeURIComponent(editingServer.name)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(serverData),
        })
        toast.dismiss(loadingId)
        toast.success('MCP 服務器已更新')
      } else {
        await fetch('/api/mcp/servers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(serverData),
        })
        toast.dismiss(loadingId)
        toast.success('MCP 服務器已創建')
      }
      setModalOpen(false)
      setEditingServer(undefined)
      await fetchServers()
    } catch (err) {
      toast.dismiss(loadingId)
      toast.error('操作失敗', err instanceof Error ? err.message : undefined)
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (server: MCPServer) => {
    const newState = !server.enabled
    const loadingId = toast.loading(newState ? '正在啟用...' : '正在停用...')
    try {
      await fetch(`/api/mcp/servers/${encodeURIComponent(server.name)}/enable?name=${encodeURIComponent(server.name)}&enabled=${newState}`, { method: 'PATCH' })
      toast.dismiss(loadingId)
      toast.success(newState ? '已啟用' : '已停用', server.name)
      await fetchServers()
    } catch (err) {
      toast.dismiss(loadingId)
      toast.error('操作失敗', err instanceof Error ? err.message : undefined)
    }
  }

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete MCP server "${name}"?`)) return
    const loadingId = toast.loading('正在刪除...')
    try {
      await fetch(`/api/mcp/servers/${encodeURIComponent(name)}?name=${encodeURIComponent(name)}`, { method: 'DELETE' })
      toast.dismiss(loadingId)
      toast.success('MCP 服務器已刪除', name)
      await fetchServers()
    } catch (err) {
      toast.dismiss(loadingId)
      toast.error('刪除失敗', err instanceof Error ? err.message : undefined)
    }
  }

  const availableTemplates = templates.filter((t) => !servers.some((s) => s.name === t.name))

  return (
    <div style={styles.container}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={styles.title}>MCP Servers</div>
        <button onClick={handleAddCustom} style={styles.addBtn}>+ Add Server</button>
      </div>
      <div style={styles.subtitle}>Configure Model Context Protocol servers to extend AI capabilities.</div>

      {loading ? (
        <div style={styles.loading}>Loading MCP servers...</div>
      ) : (
        <>
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Configured Servers ({servers.length})</div>
            {servers.length === 0 ? (
              <div style={styles.empty}>No MCP servers configured. Add one from templates or create a custom server.</div>
            ) : (
              servers.map((server) => (
                <div key={server.name} style={styles.card}>
                  <div style={styles.cardTop}>
                    <div>
                      <div style={styles.cardName}>{server.name}</div>
                      <div style={styles.cardCmd}>{server.command} {(server.args || []).join(' ')}</div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                      <button onClick={() => handleToggle(server)} style={styles.toggle(server.enabled)}>
                        {server.enabled ? 'ON' : 'OFF'}
                      </button>
                      <button onClick={() => handleDelete(server.name)} style={styles.deleteBtn}>Delete</button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {availableTemplates.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>Quick Add Templates</div>
              <div style={styles.templateGrid}>
                {availableTemplates.map((template) => (
                  <div
                    key={template.name}
                    style={styles.templateCard}
                    onClick={() => handleAddTemplate(template)}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--accent-blue)' }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border-default)' }}
                  >
                    <div style={styles.templateName}>{template.label}</div>
                    <div style={styles.templateDesc}>{template.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {modalOpen && (
        <Modal title={editingServer?.name ? 'Edit Server' : 'Add Custom Server'} onClose={() => { setModalOpen(false); setEditingServer(undefined) }}>
          <ServerForm server={editingServer} onSave={handleSaveServer} onCancel={() => { setModalOpen(false); setEditingServer(undefined) }} saving={saving} />
        </Modal>
      )}
    </div>
  )
}

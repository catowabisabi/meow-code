import { useState, useEffect } from 'react'
import { useConnectionStore } from '../api/store'
import type { ConnectionProfile } from '../api'

const DEFAULT_PROFILE: Omit<ConnectionProfile, 'id' | 'name'> = {
  type: 'remote',
  httpUrl: '',
  wsUrl: '',
  apiKey: '',
  description: '',
}

export default function ConnectionsPage() {
  const store = useConnectionStore()
  const { activeProfile, profiles } = store

  const [editingId, setEditingId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [form, setForm] = useState<Partial<ConnectionProfile>>(DEFAULT_PROFILE)
  const [testResult, setTestResult] = useState<{ ok: boolean; latencyMs?: number; error?: string } | null>(null)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    store.loadConfig()
  }, [])

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    const result = await store.testConnection({
      id: 'test',
      name: 'Test',
      ...form,
    } as ConnectionProfile)
    setTestResult(result)
    setTesting(false)
  }

  const handleSave = () => {
    if (editingId) {
      store.updateProfile(editingId, form)
    } else if (isCreating) {
      const id = `profile-${Date.now()}`
      store.addProfile({ id, name: form.name || '新連接', ...form } as ConnectionProfile)
      setIsCreating(false)
    }
    setEditingId(null)
    setForm(DEFAULT_PROFILE)
    setTestResult(null)
  }

  const handleEdit = (id: string) => {
    const profile = profiles[id]
    if (profile) {
      setForm(profile)
      setEditingId(id)
      setIsCreating(false)
      setTestResult(null)
    }
  }

  const handleDelete = (id: string) => {
    if (id !== 'local' && confirm('確定要刪除這個連接設定？')) {
      store.removeProfile(id)
    }
  }

  const startCreate = () => {
    setForm(DEFAULT_PROFILE)
    setEditingId(null)
    setIsCreating(true)
    setTestResult(null)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setIsCreating(false)
    setForm(DEFAULT_PROFILE)
    setTestResult(null)
  }

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '24px' }}>連接設定</h1>

      <p style={{ color: 'var(--text-secondary)', marginBottom: '24px', fontSize: '14px' }}>
        設定不同的後端連接。切換連接後，UI 將使用該後端的 API 和 WebSocket 端點。
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
        {Object.entries(profiles).map(([id, profile]) => (
          <div
            key={id}
            onClick={() => !editingId && !isCreating && store.setActiveProfile(id)}
            style={{
              padding: '16px',
              borderRadius: '8px',
              border: `1px solid ${activeProfile.id === id ? 'var(--accent-blue)' : 'var(--border-default)'}`,
              background: activeProfile.id === id ? 'rgba(88, 166, 255, 0.1)' : 'var(--bg-tertiary)',
              cursor: editingId || isCreating ? 'default' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '8px' }}>
                {activeProfile.id === id && (
                  <span style={{ color: 'var(--accent-blue)', fontSize: '12px' }}>✓</span>
                )}
                {profile.name}
                {id === 'local' && (
                  <span style={{
                    fontSize: '11px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'var(--bg-secondary)',
                    color: 'var(--text-muted)',
                  }}>
                    內建
                  </span>
                )}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                {profile.type === 'local' ? '本地服務器' : profile.httpUrl || '未設定'}
              </div>
            </div>
            {id !== 'local' && !editingId && !isCreating && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={(e) => { e.stopPropagation(); handleEdit(id) }}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-default)',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    fontSize: '12px',
                    cursor: 'pointer',
                  }}
                >
                  編輯
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(id) }}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--accent-red)',
                    background: 'transparent',
                    color: 'var(--accent-red)',
                    fontSize: '12px',
                    cursor: 'pointer',
                  }}
                >
                  刪除
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {(editingId || isCreating) && (
        <div style={{
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid var(--border-default)',
          background: 'var(--bg-tertiary)',
          marginBottom: '24px',
        }}>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px' }}>
            {editingId ? '編輯連接' : '新增連接'}
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px', color: 'var(--text-secondary)' }}>
                名稱
              </label>
              <input
                type="text"
                value={form.name || ''}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="我的服務器"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px', color: 'var(--text-secondary)' }}>
                HTTP 端點
              </label>
              <input
                type="text"
                value={form.httpUrl || ''}
                onChange={(e) => setForm({ ...form, httpUrl: e.target.value })}
                placeholder="https://api.example.com (留空使用本地)"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px', color: 'var(--text-secondary)' }}>
                WebSocket 端點
              </label>
              <input
                type="text"
                value={form.wsUrl || ''}
                onChange={(e) => setForm({ ...form, wsUrl: e.target.value })}
                placeholder="wss://api.example.com (留空使用本地)"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px', color: 'var(--text-secondary)' }}>
                API Key (可選)
              </label>
              <input
                type="password"
                value={form.apiKey || ''}
                onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
                placeholder="Bearer Token"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px', color: 'var(--text-secondary)' }}>
                描述 (可選)
              </label>
              <input
                type="text"
                value={form.description || ''}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="連接到遠程伺服器"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <button
                onClick={handleTest}
                disabled={testing}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  background: 'transparent',
                  color: 'var(--text-primary)',
                  fontSize: '13px',
                  cursor: testing ? 'default' : 'pointer',
                  opacity: testing ? 0.6 : 1,
                }}
              >
                {testing ? '測試中...' : '測試連接'}
              </button>
              <button
                onClick={handleSave}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  background: 'var(--accent-blue)',
                  color: '#fff',
                  fontSize: '13px',
                  cursor: 'pointer',
                }}
              >
                儲存
              </button>
              <button
                onClick={cancelEdit}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-default)',
                  background: 'transparent',
                  color: 'var(--text-secondary)',
                  fontSize: '13px',
                  cursor: 'pointer',
                }}
              >
                取消
              </button>
            </div>

            {testResult && (
              <div style={{
                padding: '12px',
                borderRadius: '6px',
                background: testResult.ok ? 'rgba(63, 185, 80, 0.15)' : 'rgba(248, 81, 73, 0.15)',
                color: testResult.ok ? 'var(--accent-green)' : 'var(--accent-red)',
                fontSize: '13px',
              }}>
                {testResult.ok
                  ? `✓ 連接成功 (延遲: ${testResult.latencyMs}ms)`
                  : `✗ 連接失敗: ${testResult.error}`}
              </div>
            )}
          </div>
        </div>
      )}

      {!editingId && !isCreating && (
        <button
          onClick={startCreate}
          style={{
            padding: '10px 20px',
            borderRadius: '8px',
            border: '1px dashed var(--border-default)',
            background: 'transparent',
            color: 'var(--text-secondary)',
            fontSize: '14px',
            cursor: 'pointer',
          }}
        >
          + 新增連接
        </button>
      )}

      <div style={{
        marginTop: '32px',
        padding: '16px',
        borderRadius: '8px',
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--border-default)',
      }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>使用說明</h3>
        <ul style={{ fontSize: '13px', color: 'var(--text-secondary)', paddingLeft: '20px', margin: 0 }}>
          <li>選擇一個連接設定作為當前使用的後端</li>
          <li>遠程連接需要填寫完整的 HTTP 和 WebSocket 端點</li>
          <li>支援任何相容此 WebUI API 格式的後端服務</li>
          <li>API Key 會以 Bearer Token 方式傳遞</li>
        </ul>
      </div>
    </div>
  )
}

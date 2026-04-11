import { useState } from 'react'

interface ApiSetupModalProps {
  onClose?: () => void
}

const PROVIDERS = [
  { id: 'minimax', name: 'MiniMax', url: 'https://api.minimax.chat/v1' },
  { id: 'anthropic', name: 'Anthropic', url: 'https://api.anthropic.com' },
  { id: 'openai', name: 'OpenAI', url: 'https://api.openai.com/v1' },
  { id: 'deepseek', name: 'DeepSeek', url: 'https://api.deepseek.com' },
]

export default function ApiSetupModal({ onClose }: ApiSetupModalProps) {
  const [provider, setProvider] = useState('minimax')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const selectedProvider = PROVIDERS.find(p => p.id === provider)

  const handleSave = async () => {
    if (!apiKey.trim()) {
      setError('請輸入 API Key')
      return
    }

    setSaving(true)
    setError('')

    try {
      const response = await fetch('/api/settings/api-credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          api_key: apiKey,
          base_url: baseUrl || selectedProvider?.url,
        }),
      })

      if (response.ok) {
        window.location.reload()
      } else {
        const data = await response.json()
        setError(data.message || '保存失敗')
      }
    } catch (err) {
      setError('網絡錯誤，請稍後再試')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
    }}>
      <div style={{
        background: 'var(--bg-secondary)',
        borderRadius: '16px',
        padding: '32px',
        maxWidth: '500px',
        width: '90%',
        border: '1px solid var(--border-default)',
      }}>
        <h2 style={{ margin: '0 0 8px', fontSize: '20px', fontWeight: 600 }}>
          API 設置
        </h2>
        <p style={{ margin: '0 0 24px', color: 'var(--text-secondary)', fontSize: '14px' }}>
          請輸入您的 API Key 開始使用
        </p>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px', color: 'var(--text-secondary)' }}>
            Provider
          </label>
          <select
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value)
              const p = PROVIDERS.find(x => x.id === e.target.value)
              setBaseUrl(p?.url || '')
            }}
            style={{
              width: '100%',
              padding: '10px 12px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-default)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '14px',
            }}
          >
            {PROVIDERS.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px', color: 'var(--text-secondary)' }}>
            API Key
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="輸入您的 API Key"
            style={{
              width: '100%',
              padding: '10px 12px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-default)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '14px',
            }}
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px', color: 'var(--text-secondary)' }}>
            Base URL (可選)
          </label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={selectedProvider?.url || 'https://...'}
            style={{
              width: '100%',
              padding: '10px 12px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-default)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '14px',
            }}
          />
        </div>

        {error && (
          <div style={{
            padding: '12px',
            background: 'rgba(248, 81, 73, 0.15)',
            borderRadius: '8px',
            color: 'var(--accent-red)',
            fontSize: '13px',
            marginBottom: '16px',
          }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: '10px 24px',
              background: saving ? 'var(--bg-tertiary)' : 'var(--accent-blue)',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 500,
              cursor: saving ? 'default' : 'pointer',
              opacity: saving ? 0.6 : 1,
            }}
          >
            {saving ? '保存中...' : '保存並繼續'}
          </button>
        </div>
      </div>
    </div>
  )
}
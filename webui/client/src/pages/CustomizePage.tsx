import { useState, useEffect } from 'react'

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

export default function CustomizePage() {
  const [systemPrompt, setSystemPrompt] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Load from server API
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => {
        if (data.systemPrompt) setSystemPrompt(data.systemPrompt)
      })
      .catch(console.error)
  }, [])

  const handleSave = async () => {
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ systemPrompt }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || '保存失敗')
      } else {
        setSaved(true)
        setError(null)
        setTimeout(() => setSaved(false), 2000)
      }
    } catch (e) {
      setError('保存失敗，請檢查網絡連接')
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: C.bg, color: C.text, padding: '40px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>自定義</h1>
      <p style={{ color: C.textMuted, fontSize: '14px', marginBottom: '40px' }}>
        個性化您的 AI 助手體驗
      </p>

      <div style={{ maxWidth: '640px', display: 'flex', flexDirection: 'column', gap: '32px' }}>

        {/* Language preference */}
        <section>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px', color: C.textSecondary }}>
            語言偏好
          </h2>
          <div
            style={{
              padding: '16px 20px',
              borderRadius: '10px',
              border: `1px solid ${C.border}`,
              background: C.surface,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ fontSize: '14px', fontWeight: 500, color: C.text }}>
                繁體中文 (Traditional Chinese)
              </div>
              <div style={{ fontSize: '12px', color: C.textMuted, marginTop: '2px' }}>
                目前語言設定
              </div>
            </div>
            <div
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                background: 'rgba(249,115,22,0.12)',
                border: '1px solid rgba(249,115,22,0.3)',
                fontSize: '12px',
                color: C.accent,
              }}
            >
              已啟用
            </div>
          </div>
        </section>

        {/* Theme */}
        <section>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '12px', color: C.textSecondary }}>
            主題
          </h2>
          <div
            style={{
              padding: '16px 20px',
              borderRadius: '10px',
              border: `1px solid ${C.border}`,
              background: C.surface,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: '#151517',
                  border: `2px solid ${C.accent}`,
                }}
              />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500, color: C.text }}>深色模式</div>
                <div style={{ fontSize: '12px', color: C.textMuted, marginTop: '2px' }}>
                  目前僅支持深色模式
                </div>
              </div>
            </div>
            <div
              style={{
                padding: '5px 12px',
                borderRadius: '6px',
                background: 'rgba(249,115,22,0.12)',
                border: '1px solid rgba(249,115,22,0.3)',
                fontSize: '12px',
                color: C.accent,
              }}
            >
              已啟用
            </div>
          </div>
        </section>

        {/* System prompt */}
        <section>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '4px', color: C.textSecondary }}>
            自定義系統提示
          </h2>
          <p style={{ fontSize: '13px', color: C.textMuted, marginBottom: '12px', lineHeight: 1.5 }}>
            此提示將被加入到每次對話的開頭，用於設定 AI 的行為和角色。
          </p>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="例如：你是一個友善的助手，擅長繁體中文回覆..."
            rows={6}
            style={{
              width: '100%',
              padding: '12px 16px',
              borderRadius: '10px',
              border: `1px solid ${C.border}`,
              background: C.surface,
              color: C.text,
              fontSize: '14px',
              lineHeight: 1.6,
              resize: 'vertical',
              outline: 'none',
              fontFamily: 'inherit',
              boxSizing: 'border-box',
            }}
          />
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: '12px',
            }}
          >
            <span style={{ fontSize: '12px', color: C.textMuted }}>
              {systemPrompt.length} 個字符
            </span>
            {error && (
              <span style={{ fontSize: '12px', color: '#ef4444' }}>
                {error}
              </span>
            )}
            <button
              onClick={handleSave}
              style={{
                padding: '8px 20px',
                borderRadius: '8px',
                border: 'none',
                background: saved ? '#22c55e' : C.accent,
                color: '#fff',
                fontSize: '14px',
                fontWeight: 500,
                cursor: 'pointer',
                outline: 'none',
                fontFamily: 'inherit',
                transition: 'background 0.2s ease',
              }}
            >
              {saved ? '已保存 ✓' : '保存'}
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}

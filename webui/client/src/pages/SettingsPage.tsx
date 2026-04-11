import { useState, useEffect } from 'react'
import { useModelStore, type HotkeyBinding } from '../stores/modelStore.ts'
import { useChatStore } from '../stores/chatStore.ts'

const styles = {
  container: {
    padding: '24px 32px',
    maxWidth: '800px',
    margin: '0 auto',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    marginBottom: '24px',
  },
  section: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '15px',
    fontWeight: 600,
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  field: {
    marginBottom: '14px',
  },
  label: {
    fontSize: '13px',
    color: 'var(--text-secondary)',
    marginBottom: '6px',
    fontWeight: 500,
  },
  input: {
    width: '100%',
    padding: '8px 12px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
  },
  select: {
    padding: '8px 12px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    fontSize: '14px',
    outline: 'none',
    cursor: 'pointer',
  },
  hotkeyRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
    padding: '8px 12px',
    background: 'var(--bg-tertiary)',
    borderRadius: '6px',
  },
  hotkeyKey: {
    padding: '4px 10px',
    borderRadius: '4px',
    background: 'var(--bg-hover)',
    color: 'var(--accent-blue)',
    fontSize: '13px',
    fontFamily: 'monospace',
    fontWeight: 600,
    minWidth: '80px',
    textAlign: 'center' as const,
  },
  hotkeyModel: {
    flex: 1,
    fontSize: '13px',
    color: 'var(--text-secondary)',
  },
  btn: (variant: 'primary' | 'secondary' | 'danger') => ({
    padding: '8px 16px',
    borderRadius: '6px',
    border: variant === 'primary' ? 'none' : '1px solid var(--border-default)',
    background: variant === 'primary' ? 'var(--accent-blue)' : variant === 'danger' ? 'transparent' : 'var(--bg-tertiary)',
    color: variant === 'primary' ? '#fff' : variant === 'danger' ? 'var(--accent-red)' : 'var(--text-secondary)',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: 500,
  }),
  removeBtn: {
    padding: '4px 8px',
    borderRadius: '4px',
    border: 'none',
    background: 'transparent',
    color: 'var(--accent-red)',
    cursor: 'pointer',
    fontSize: '14px',
  },
  description: {
    fontSize: '12px',
    color: 'var(--text-muted)',
    marginTop: '4px',
    lineHeight: 1.4,
  },
  infoBox: {
    padding: '12px 16px',
    background: 'rgba(88,166,255,0.08)',
    border: '1px solid rgba(88,166,255,0.2)',
    borderRadius: '8px',
    fontSize: '13px',
    color: 'var(--text-secondary)',
    lineHeight: 1.5,
  },
  warningBox: {
    padding: '12px 16px',
    background: 'rgba(220,38,38,0.08)',
    border: '1px solid rgba(220,38,38,0.3)',
    borderRadius: '8px',
    fontSize: '13px',
    color: 'var(--accent-red)',
    lineHeight: 1.5,
  },
}

export default function SettingsPage() {
  const {
    providers,
    hotkeys,
    defaultModel,
    defaultProvider,
    fetchModels,
    setDefault,
    updateHotkeys,
  } = useModelStore()

  const { permissionMode, setPermissionMode } = useChatStore()

  const [localHotkeys, setLocalHotkeys] = useState<HotkeyBinding[]>([])
  const [port, setPort] = useState(3456)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [language, setLanguage] = useState('')
  const [languageSaved, setLanguageSaved] = useState(false)
  const [languageError, setLanguageError] = useState<string | null>(null)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [systemPromptSaved, setSystemPromptSaved] = useState(false)
  const [systemPromptError, setSystemPromptError] = useState<string | null>(null)

  useEffect(() => {
    fetchModels()
    // Load settings including language
    fetch('/api/settings')
      .then(r => r.json())
      .then(data => {
        if (data.port) setPort(data.port)
        if (data.language) setLanguage(data.language)
        if (data.systemPrompt) setSystemPrompt(data.systemPrompt)
      })
      .catch(console.error)
  }, [fetchModels])

  useEffect(() => {
    setLocalHotkeys(hotkeys)
  }, [hotkeys])

  // Build flat model list for selectors
  const allModels = Object.entries(providers)
    .filter(([, p]) => p.enabled)
    .flatMap(([id, p]) => p.models.map((m) => ({ provider: id, model: m, label: `${p.displayName || id} / ${m}` })))

  const handleSaveHotkeys = async () => {
    await updateHotkeys(localHotkeys)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const addHotkey = () => {
    const idx = localHotkeys.length + 1
    setLocalHotkeys([
      ...localHotkeys,
      { key: `ctrl+${idx}`, model: allModels[0]?.model || '', provider: allModels[0]?.provider || '' },
    ])
  }

  const removeHotkey = (index: number) => {
    setLocalHotkeys(localHotkeys.filter((_, i) => i !== index))
  }

  const updateHotkeyField = (index: number, field: keyof HotkeyBinding, value: string) => {
    const updated = [...localHotkeys]
    if (field === 'model') {
      // When model changes, also update provider
      const found = allModels.find((m) => `${m.provider}:${m.model}` === value)
      if (found) {
        updated[index] = { ...updated[index]!, model: found.model, provider: found.provider }
      }
    } else {
      updated[index] = { ...updated[index]!, [field]: value }
    }
    setLocalHotkeys(updated)
  }

  const handleSaveLanguage = async () => {
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language }),
      })
      const data = await res.json()
      if (!res.ok) {
        setLanguageError(data.error || '保存失敗')
      } else {
        setLanguageSaved(true)
        setLanguageError(null)
        setTimeout(() => setLanguageSaved(false), 2000)
      }
    } catch (e) {
      setLanguageError('保存失敗，請檢查網絡連接')
    }
  }

  const handleSaveSystemPrompt = async () => {
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ systemPrompt }),
      })
      const data = await res.json()
      if (!res.ok) {
        setSystemPromptError(data.error || '保存失敗')
      } else {
        setSystemPromptSaved(true)
        setSystemPromptError(null)
        setTimeout(() => setSystemPromptSaved(false), 2000)
      }
    } catch (e) {
      setSystemPromptError('保存失敗，請檢查網絡連接')
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.title}>設置</div>

      {/* Default Model */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <span>🎯</span>
          <span>默認模型</span>
        </div>
        <div style={styles.field}>
          <div style={styles.label}>啟動時使用的默認模型</div>
          <select
            style={styles.select}
            value={`${defaultProvider}:${defaultModel}`}
            onChange={(e) => {
              const [prov, mod] = e.target.value.split(':')
              if (prov && mod) setDefault(mod, prov)
            }}
          >
            {allModels.map((m) => (
              <option key={`${m.provider}:${m.model}`} value={`${m.provider}:${m.model}`}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Permission Settings */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <span>🔒</span>
          <span>工具執行授權</span>
        </div>
        <div style={styles.field}>
          <div style={styles.label}>全域授權模式</div>
          <select
            style={styles.select}
            value={permissionMode}
            onChange={(e) => setPermissionMode(e.target.value as 'ask' | 'always-allow')}
          >
            <option value="ask">每次詢問（推薦）</option>
            <option value="always-allow">始終允許所有工具</option>
          </select>
          <div style={styles.description}>
            「每次詢問」會在執行高風險工具前要求確認。「始終允許」會繞過所有確認提示。
          </div>
          {permissionMode === 'always-allow' && (
            <div style={{ ...styles.warningBox, marginTop: '12px' }}>
              ⚠️ 全域授權已啟用！所有工具（shell、file_write 等）將自動執行，無需任何確認。
              這是一個安全風險，請只在信任的環境中使用。
            </div>
          )}
        </div>
      </div>

      {/* Hotkey Bindings */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <span>⌨️</span>
          <span>快捷鍵綁定</span>
        </div>
        <div style={styles.description}>
          配置快捷鍵來快速切換模型。按 Ctrl+K 打開模型搜索面板。
        </div>
        <div style={{ marginTop: '12px' }}>
          {localHotkeys.map((hk, i) => (
            <div key={i} style={styles.hotkeyRow}>
              <input
                style={{ ...styles.input, width: '120px', textAlign: 'center', fontFamily: 'monospace' }}
                value={hk.key}
                onChange={(e) => updateHotkeyField(i, 'key', e.target.value)}
                placeholder="ctrl+1"
              />
              <span style={{ color: 'var(--text-muted)' }}>→</span>
              <select
                style={{ ...styles.select, flex: 1 }}
                value={`${hk.provider}:${hk.model}`}
                onChange={(e) => updateHotkeyField(i, 'model', e.target.value)}
              >
                {allModels.map((m) => (
                  <option key={`${m.provider}:${m.model}`} value={`${m.provider}:${m.model}`}>
                    {m.label}
                  </option>
                ))}
              </select>
              <button style={styles.removeBtn} onClick={() => removeHotkey(i)}>
                ✕
              </button>
            </div>
          ))}
          <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
            <button style={styles.btn('secondary')} onClick={addHotkey}>
              + 添加快捷鍵
            </button>
            <button style={styles.btn('primary')} onClick={handleSaveHotkeys}>
              {saved ? '✓ 已保存' : '保存快捷鍵'}
            </button>
          </div>
        </div>
      </div>

      {/* Server Settings */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <span>🌐</span>
          <span>服務器設置</span>
        </div>
        <div style={styles.field}>
          <div style={styles.label}>WebUI 端口</div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              style={{ ...styles.input, width: '120px' }}
              type="number"
              value={port}
              onChange={(e) => setPort(parseInt(e.target.value) || 7778)}
            />
            <button
              style={styles.btn('primary')}
              onClick={async () => {
                try {
                  const res = await fetch('/api/settings', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ port }),
                  })
                  const data = await res.json()
                  if (!res.ok) {
                    setSaveError(data.error || '保存失敗')
                  } else {
                    setSaved(true)
                    setSaveError(null)
                    setTimeout(() => setSaved(false), 2000)
                  }
                } catch (e) {
                  setSaveError('保存失敗，請檢查網絡連接')
                }
              }}
            >
              {saved ? '✓ 已保存' : '保存'}
            </button>
          </div>
          <div style={styles.description}>
            更改端口後需要重啟服務才能生效。
          </div>
          {saveError && (
            <div style={{ ...styles.description, color: 'var(--accent-red)', marginTop: '8px' }}>
              {saveError}
            </div>
          )}
        </div>
      </div>

      {/* Language Preference */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <span>🌍</span>
          <span>語言偏好</span>
        </div>
        <div style={styles.description}>
          設置 AI 回覆的語言。選擇語言後，AI 會使用該語言進行回覆。
        </div>
        <div style={{ ...styles.field, marginTop: '12px' }}>
          <div style={styles.label}>回覆語言</div>
          <select
            style={styles.select}
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="">默認（跟隨系統）</option>
            <option value="繁體中文">繁體中文</option>
            <option value="简体中文">简体中文</option>
            <option value="English">English</option>
            <option value="日本語">日本語</option>
            <option value="한국어">한국어</option>
          </select>
          <div style={{ marginTop: '8px' }}>
            <button
              style={styles.btn('primary')}
              onClick={handleSaveLanguage}
            >
              {languageSaved ? '✓ 已保存' : '保存語言設置'}
            </button>
          </div>
          {languageError && (
            <div style={{ ...styles.description, color: 'var(--accent-red)', marginTop: '8px' }}>
              {languageError}
            </div>
          )}
        </div>
      </div>

      {/* System Prompt */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <span>💬</span>
          <span>自定義系統提示</span>
        </div>
        <div style={styles.description}>
          此提示將被加入到每次對話的開頭，用於設定 AI 的行為和角色。
        </div>
        <div style={{ ...styles.field, marginTop: '12px' }}>
          <textarea
            style={{ ...styles.input, minHeight: '100px', resize: 'vertical' }}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="例如：你是一個友善的助手，擅長繁體中文回覆..."
          />
          <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {systemPrompt.length} 個字符
            </span>
            <button
              style={styles.btn('primary')}
              onClick={handleSaveSystemPrompt}
            >
              {systemPromptSaved ? '✓ 已保存' : '保存系統提示'}
            </button>
          </div>
          {systemPromptError && (
            <div style={{ ...styles.description, color: 'var(--accent-red)', marginTop: '8px' }}>
              {systemPromptError}
            </div>
          )}
        </div>
      </div>

      {/* Info */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <span>ℹ️</span>
          <span>關於</span>
        </div>
        <div style={styles.infoBox}>
          <strong>AI Code Assistant WebUI</strong>
          <br />
          基於 Claude Code 源碼魔改的多模型 AI 編程助手。
          <br />
          支持 DeepSeek、MiniMax、OpenAI、Anthropic、Ollama 等多種模型供應商。
          <br />
          <br />
          <strong>快捷操作：</strong>
          <br />
          • Ctrl+K — 打開模型切換面板
          <br />
          • Ctrl+1/2/3 — 快速切換預設模型
          <br />
          • Ctrl+S — 保存當前編輯的文件
          <br />
          • Enter — 發送消息
          <br />
          • Shift+Enter — 換行
        </div>
      </div>
    </div>
  )
}

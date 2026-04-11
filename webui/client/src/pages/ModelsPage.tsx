import { useState, useEffect } from 'react'
import { useModelStore, type ProviderInfo } from '../stores/modelStore.ts'

const styles = {
  container: {
    padding: '24px 32px',
    maxWidth: '1000px',
    margin: '0 auto',
  },
  header: {
    marginBottom: '24px',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    marginBottom: '8px',
  },
  subtitle: {
    color: 'var(--text-secondary)',
    fontSize: '14px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(440px, 1fr))',
    gap: '16px',
  },
  card: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: '12px',
    padding: '20px',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  providerName: {
    fontSize: '16px',
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusDot: (enabled: boolean) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: enabled ? 'var(--accent-green)' : 'var(--text-muted)',
  }),
  toggle: (on: boolean) => ({
    width: '40px',
    height: '22px',
    borderRadius: '11px',
    background: on ? 'var(--accent-green)' : 'var(--bg-hover)',
    border: 'none',
    cursor: 'pointer',
    position: 'relative' as const,
    transition: 'background 0.2s',
  }),
  toggleDot: (on: boolean) => ({
    width: '18px',
    height: '18px',
    borderRadius: '50%',
    background: '#fff',
    position: 'absolute' as const,
    top: '2px',
    left: on ? '20px' : '2px',
    transition: 'left 0.2s',
  }),
  field: {
    marginBottom: '12px',
  },
  label: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    marginBottom: '4px',
    fontWeight: 500,
  },
  input: {
    width: '100%',
    padding: '8px 10px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'monospace',
  },
  modelChips: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: '6px',
    marginTop: '4px',
  },
  chip: {
    padding: '3px 10px',
    borderRadius: '12px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
  actions: {
    display: 'flex',
    gap: '8px',
    marginTop: '16px',
  },
  btn: (variant: 'primary' | 'secondary' | 'danger') => ({
    padding: '6px 14px',
    borderRadius: '6px',
    border: variant === 'primary' ? 'none' : '1px solid var(--border-default)',
    background:
      variant === 'primary'
        ? 'var(--accent-blue)'
        : variant === 'danger'
          ? 'transparent'
          : 'var(--bg-tertiary)',
    color:
      variant === 'primary' ? '#fff' : variant === 'danger' ? 'var(--accent-red)' : 'var(--text-secondary)',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: 500,
  }),
  addCard: {
    background: 'var(--bg-secondary)',
    border: '2px dashed var(--border-default)',
    borderRadius: '12px',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '12px',
  },
  testResult: (ok: boolean) => ({
    fontSize: '12px',
    marginTop: '6px',
    color: ok ? 'var(--accent-green)' : 'var(--accent-red)',
  }),
}

const providerTemplates = [
  { id: 'deepseek', name: 'DeepSeek', type: 'deepseek', baseUrl: 'https://api.deepseek.com/v1', models: ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner'] },
  { id: 'minimax', name: 'MiniMax', type: 'minimax', baseUrl: 'https://api.minimax.chat/v1', models: ['MiniMax-Text-01', 'abab6.5s-chat'] },
  { id: 'openai', name: 'OpenAI', type: 'openai', baseUrl: 'https://api.openai.com/v1', models: ['gpt-4o', 'gpt-4o-mini', 'o1', 'o3-mini'] },
  { id: 'anthropic', name: 'Anthropic', type: 'anthropic', baseUrl: 'https://api.anthropic.com', models: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514'] },
  { id: 'ollama', name: 'Ollama (Local)', type: 'ollama', baseUrl: 'http://localhost:11434/v1', models: ['llama3', 'codellama', 'qwen2.5-coder'] },
]

export default function ModelsPage() {
  const { providers, fetchModels, updateProvider, removeProvider, testProvider, addProvider } = useModelStore()
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; error?: string; latencyMs?: number }>>({})
  const [editingKeys, setEditingKeys] = useState<Record<string, string>>({})

  useEffect(() => {
    fetchModels()
  }, [fetchModels])

  const handleTest = async (id: string) => {
    setTestResults((r) => ({ ...r, [id]: { ok: false, error: '測試中...' } }))
    const result = await testProvider(id)
    setTestResults((r) => ({ ...r, [id]: result }))
  }

  const handleSaveKey = async (id: string) => {
    const key = editingKeys[id]
    if (key !== undefined) {
      await updateProvider(id, { apiKey: key, enabled: true })
      setEditingKeys((k) => {
        const copy = { ...k }
        delete copy[id]
        return copy
      })
      fetchModels()
    }
  }

  const handleAddTemplate = async (tmpl: typeof providerTemplates[number]) => {
    await addProvider(tmpl.id, {
      type: tmpl.type,
      displayName: tmpl.name,
      baseUrl: tmpl.baseUrl,
      apiKey: '',
      models: tmpl.models,
      enabled: false,
    })
    fetchModels()
  }

  const existingIds = Object.keys(providers)
  const availableTemplates = providerTemplates.filter((t) => !existingIds.includes(t.id))

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>模型管理</div>
        <div style={styles.subtitle}>
          配置 AI 模型供應商，添加 API Key 即可在聊天中使用。支持 Ctrl+1/2/3 快捷切換。
        </div>
      </div>

      <div style={styles.grid}>
        {Object.entries(providers).map(([id, provider]) => (
          <div key={id} style={styles.card}>
            <div style={styles.cardHeader}>
              <div style={styles.providerName}>
                <div style={styles.statusDot(provider.enabled && !!provider.apiKey)} />
                <span>{provider.displayName || id}</span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>({provider.type})</span>
              </div>
              <button
                style={styles.toggle(provider.enabled)}
                onClick={() => {
                  updateProvider(id, { enabled: !provider.enabled })
                  fetchModels()
                }}
              >
                <div style={styles.toggleDot(provider.enabled)} />
              </button>
            </div>

            <div style={styles.field}>
              <div style={styles.label}>API Base URL</div>
              <input
                style={styles.input}
                value={provider.baseUrl}
                onChange={(e) => updateProvider(id, { baseUrl: e.target.value })}
              />
            </div>

            <div style={styles.field}>
              <div style={styles.label}>API Key</div>
              <div style={{ display: 'flex', gap: '6px' }}>
                <input
                  style={{ ...styles.input, flex: 1 }}
                  type="password"
                  placeholder="輸入 API Key..."
                  value={editingKeys[id] ?? (provider.apiKey ? '••••••••' : '')}
                  onChange={(e) => setEditingKeys((k) => ({ ...k, [id]: e.target.value }))}
                  onFocus={() => {
                    if (editingKeys[id] === undefined) {
                      setEditingKeys((k) => ({ ...k, [id]: provider.apiKey }))
                    }
                  }}
                />
                {editingKeys[id] !== undefined && (
                  <button style={styles.btn('primary')} onClick={() => handleSaveKey(id)}>
                    保存
                  </button>
                )}
              </div>
            </div>

            <div style={styles.field}>
              <div style={styles.label}>可用模型</div>
              <div style={styles.modelChips}>
                {provider.models.map((m) => (
                  <span key={m} style={styles.chip}>{m}</span>
                ))}
              </div>
            </div>

            <div style={styles.actions}>
              <button style={styles.btn('secondary')} onClick={() => handleTest(id)}>
                測試連接
              </button>
              <button style={styles.btn('danger')} onClick={() => { removeProvider(id); fetchModels() }}>
                刪除
              </button>
            </div>

            {testResults[id] && (
              <div style={styles.testResult(testResults[id]!.ok)}>
                {testResults[id]!.ok
                  ? `✓ 連接成功 (${testResults[id]!.latencyMs}ms)`
                  : `✗ ${testResults[id]!.error}`}
              </div>
            )}
          </div>
        ))}

        {/* Add new provider */}
        <div style={styles.addCard}>
          <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
            ➕ 添加供應商
          </div>
          
          {/* Provider templates */}
          {availableTemplates.length > 0 && (
            <>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                熱門供應商
              </div>
              {availableTemplates.map((tmpl) => (
                <button
                  key={tmpl.id}
                  style={{
                    ...styles.btn('secondary'),
                    width: '100%',
                    padding: '10px',
                    textAlign: 'left' as const,
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: '6px',
                  }}
                  onClick={() => handleAddTemplate(tmpl)}
                >
                  <span>{tmpl.name}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                    {tmpl.models.length} 模型
                  </span>
                </button>
              ))}
            </>
          )}

          {/* Custom provider form */}
          <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-default)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
              自訂供應商
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <input
                style={styles.input}
                placeholder="供應商 ID (如: custom-api)"
                id="custom-provider-id"
              />
              <input
                style={styles.input}
                placeholder="顯示名稱 (如: My API)"
                id="custom-provider-name"
              />
              <input
                style={styles.input}
                placeholder="API Base URL (如: https://api.example.com/v1)"
                id="custom-provider-url"
              />
              <input
                style={styles.input}
                placeholder="模型名稱 (如: my-model，多個用逗號分隔)"
                id="custom-provider-models"
              />
              <button
                style={styles.btn('primary')}
                onClick={() => {
                  const idInput = document.getElementById('custom-provider-id') as HTMLInputElement
                  const nameInput = document.getElementById('custom-provider-name') as HTMLInputElement
                  const urlInput = document.getElementById('custom-provider-url') as HTMLInputElement
                  const modelsInput = document.getElementById('custom-provider-models') as HTMLInputElement
                  
                  const id = idInput.value.trim()
                  const name = nameInput.value.trim()
                  const url = urlInput.value.trim()
                  const models = modelsInput.value.split(',').map(m => m.trim()).filter(Boolean)
                  
                  if (!id || !url || models.length === 0) {
                    alert('請填寫所有必填欄位')
                    return
                  }
                  
                  addProvider(id, {
                    type: 'custom',
                    displayName: name || id,
                    baseUrl: url,
                    apiKey: '',
                    models,
                    enabled: false,
                  })
                  fetchModels()
                  
                  idInput.value = ''
                  nameInput.value = ''
                  urlInput.value = ''
                  modelsInput.value = ''
                }}
              >
                添加自訂供應商
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

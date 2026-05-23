import { useState, useEffect } from 'react'
import { useModelStore, type HotkeyBinding } from '../stores/modelStore.ts'
import { useChatStore } from '../stores/chatStore.ts'
import { useProviderHeartbeatStore } from '../stores/providerHeartbeatStore.ts'

// ─── Styles ────────────────────────────────────────────────────

const S = {
  container: { display: 'flex', height: '100%', minHeight: '400px' },
  sidebar: {
    width: '180px', flexShrink: 0, borderRight: '1px solid var(--border-default)',
    padding: '12px 8px', display: 'flex', flexDirection: 'column' as const, gap: '2px',
  },
  tabBtn: (active: boolean) => ({
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '8px 12px', borderRadius: '6px', border: 'none',
    background: active ? 'var(--bg-hover)' : 'transparent',
    color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
    fontSize: '13px', fontWeight: active ? 600 : 400,
    cursor: 'pointer', textAlign: 'left' as const, width: '100%',
    outline: 'none', fontFamily: 'inherit', transition: 'all 0.12s',
  }),
  body: { flex: 1, padding: '24px 32px', overflowY: 'auto' as const },
  section: {
    background: 'var(--bg-secondary)', border: '1px solid var(--border-default)',
    borderRadius: '12px', padding: '20px', marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '15px', fontWeight: 600, marginBottom: '16px',
    display: 'flex', alignItems: 'center', gap: '8px',
  },
  field: { marginBottom: '14px' },
  label: { fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '6px', fontWeight: 500 },
  input: {
    width: '100%', padding: '8px 12px', background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)', borderRadius: '6px',
    color: 'var(--text-primary)', fontSize: '14px', outline: 'none',
  },
  select: {
    padding: '8px 12px', background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)', borderRadius: '6px',
    color: 'var(--text-primary)', fontSize: '14px', outline: 'none', cursor: 'pointer',
  },
  btn: (variant: 'primary' | 'secondary' | 'danger') => ({
    padding: '8px 16px', borderRadius: '6px',
    border: variant === 'primary' ? 'none' : '1px solid var(--border-default)',
    background: variant === 'primary' ? 'var(--accent-primary)' : variant === 'danger' ? 'transparent' : 'var(--bg-tertiary)',
    color: variant === 'primary' ? '#fff' : variant === 'danger' ? 'var(--accent-red)' : 'var(--text-secondary)',
    fontSize: '13px', cursor: 'pointer', fontWeight: 500,
  }),
  desc: { fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', lineHeight: 1.4 },
  hotkeyRow: {
    display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px',
    padding: '8px 12px', background: 'var(--bg-tertiary)', borderRadius: '6px',
  },
  warningBox: {
    padding: '12px 16px', background: 'rgba(220,38,38,0.08)',
    border: '1px solid rgba(220,38,38,0.3)', borderRadius: '8px',
    fontSize: '13px', color: 'var(--accent-red)', lineHeight: 1.5,
  },
  infoBox: {
    padding: '12px 16px', background: 'rgba(88,166,255,0.08)',
    border: '1px solid rgba(88,166,255,0.2)', borderRadius: '8px',
    fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5,
  },
  sparklineWrap: {
    display: 'flex', flexDirection: 'column', gap: '2px',
  },
  sparklineRow: {
    display: 'flex', alignItems: 'center', gap: '10px',
    padding: '10px 12px', borderRadius: '8px', background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
  },
  sparklineName: {
    fontSize: '13px', fontWeight: 500, minWidth: '80px',
  },
  sparklineChart: {
    flex: 1, height: '40px', position: 'relative' as const,
  },
  sparklineCircuitBand: {
    position: 'absolute' as const, left: 0, right: 0, height: '8px', bottom: 0,
    opacity: 0.3,
  },
  failureDot: {
    width: '6px', height: '6px', borderRadius: '50%',
    background: 'var(--accent-red)', margin: '0 1px',
  },
  stateDot: {
    width: '8px', height: '8px', borderRadius: '50%',
  },
}

// ─── Tabs ──────────────────────────────────────────────────────

type TabId = 'general' | 'appearance' | 'security' | 'hotkeys' | 'server' | 'about' | 'providers'

const TABS: { id: TabId; icon: string; label: string }[] = [
  { id: 'general', icon: '🎯', label: '一般' },
  { id: 'appearance', icon: '🎨', label: '外觀' },
  { id: 'security', icon: '🔒', label: '安全' },
  { id: 'hotkeys', icon: '⌨️', label: '快捷鍵' },
  { id: 'server', icon: '🌐', label: '伺服器' },
  { id: 'about', icon: 'ℹ️', label: '關於' },
  { id: 'providers', icon: '🔄', label: '提供商' },
]

// ─── Component ────────────────────────────────────────────────

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('general')

  const { providers, hotkeys, defaultModel, defaultProvider, fetchModels, setDefault, updateHotkeys } = useModelStore()
  const { permissionMode, setPermissionMode } = useChatStore()
  const { heartbeatData, serverTime: serverTimeValue, fetchHeartbeat } = useProviderHeartbeatStore()

  const [localHotkeys, setLocalHotkeys] = useState<HotkeyBinding[]>([])
  const [port, setPort] = useState(3456)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [language, setLanguage] = useState('')
  const [languageSaved, setLanguageSaved] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState('')
  const [systemPromptSaved, setSystemPromptSaved] = useState(false)
  const [systemPromptError, setSystemPromptError] = useState<string | null>(null)
  const [providerHealth, setProviderHealth] = useState<Record<string, { state: string; failure_count: number; last_failure_time?: number; last_failure_reason?: string }>>({})
  const [providerOrder, setProviderOrder] = useState<string[]>([])

  useEffect(() => {
    fetch('/api/providers/health').then(r => r.json()).then(data => {
      if (data.providers) setProviderHealth(data.providers)
    }).catch(() => {})
    fetch('/api/providers/order').then(r => r.json()).then(data => {
      if (data.order) setProviderOrder(data.order)
    }).catch(() => {})
    fetchHeartbeat()
    const interval = setInterval(() => {
      fetch('/api/providers/health').then(r => r.json()).then(data => {
        if (data.providers) setProviderHealth(data.providers)
      }).catch(() => {})
    }, 30000)
    const heartbeatInterval = setInterval(() => {
      fetchHeartbeat()
    }, 30000)
    return () => { clearInterval(interval); clearInterval(heartbeatInterval) }
  }, [fetchHeartbeat])

  useEffect(() => {
    fetchModels()
    fetch('/api/settings').then(r => r.json()).then(data => {
      if (data.port) setPort(data.port)
      if (data.language) setLanguage(data.language)
      if (data.systemPrompt) setSystemPrompt(data.systemPrompt)
    }).catch(console.error)
  }, [fetchModels])

  useEffect(() => { setLocalHotkeys(hotkeys) }, [hotkeys])

  const allModels = Object.entries(providers)
    .filter(([, p]) => p.enabled)
    .flatMap(([id, p]) => p.models.map((m) => ({ provider: id, model: m, label: `${p.displayName || id} / ${m}` })))

  // ─── Save helpers ───

  const saveSetting = async (body: object, onOk: () => void, onErr: (msg: string) => void) => {
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) onErr(data.error || '保存失敗')
      else onOk()
    } catch { onErr('保存失敗') }
  }

  const handleSaveHotkeys = async () => {
    await updateHotkeys(localHotkeys)
    setSaved(true); setTimeout(() => setSaved(false), 2000)
  }

  const addHotkey = () => {
    const idx = localHotkeys.length + 1
    setLocalHotkeys([...localHotkeys, { key: `ctrl+${idx}`, model: allModels[0]?.model || '', provider: allModels[0]?.provider || '' }])
  }

  const removeHotkey = (i: number) => setLocalHotkeys(localHotkeys.filter((_, j) => j !== i))

  const updateHotkeyField = (index: number, field: keyof HotkeyBinding, value: string) => {
    const updated = [...localHotkeys]
    if (field === 'model') {
      const found = allModels.find((m) => `${m.provider}:${m.model}` === value)
      if (found) updated[index] = { ...updated[index]!, model: found.model, provider: found.provider }
    } else {
      updated[index] = { ...updated[index]!, [field]: value }
    }
    setLocalHotkeys(updated)
  }

  // ─── Sparkline Chart ───────────────────────────────────────────

  const renderSparkline = (
    latencySamples: number[],
    threshold: number,
    circuitStateHistory: { timestamp: number; from_state: string; to_state: string }[],
    failureTimestamps: number[],
    serverTime: number,
    width: number,
    height: number,
    currentState: string
  ) => {
    if (latencySamples.length === 0) {
      latencySamples = [0]
    }

    const maxLatency = Math.max(...latencySamples, threshold * 1.2)
    const minLatency = 0
    const range = maxLatency - minLatency || 1

    // Calculate bar positions
    const barWidth = Math.max(1, (width - 2) / latencySamples.length)
    const chartHeight = height - 10 // leave room for circuit band

    // Determine colors: green -> yellow -> red based on threshold
    const getBarColor = (value: number): string => {
      const ratio = value / threshold
      if (ratio <= 0.7) return '#4ade80' // green
      if (ratio <= 1.0) return '#facc15' // yellow
      return '#f85149' // red
    }

    // Build SVG bars for latency
    const bars: React.ReactNode[] = latencySamples.map((val, i) => {
      const barHeight = ((val - minLatency) / range) * chartHeight
      const x = i * barWidth + 1
      const y = chartHeight - barHeight
      return (
        <rect
          key={i}
          x={x}
          y={y}
          width={Math.max(1, barWidth - 1)}
          height={barHeight}
          fill={getBarColor(val)}
          opacity={0.85}
        />
      )
    })

    // Threshold line
    const thresholdY = chartHeight - ((threshold - minLatency) / range) * chartHeight

    // Circuit state bands (approximate positions based on timestamps)
    const bandColor: Record<string, string> = {
      closed: '#4ade80',
      half_open: '#facc15',
      open: '#f85149',
    }
    const nowSecs = serverTime || Date.now() / 1000
    const sixtySecsAgo = nowSecs - 60

    // Group circuit history into time slices (last 60 seconds)
    const numBands = 6
    const bandSecs = 60 / numBands
    const circuitBands: React.ReactNode[] = []
    for (let b = 0; b < numBands; b++) {
      const bandStart = sixtySecsAgo + b * bandSecs
      const bandEnd = bandStart + bandSecs
      // Find most recent state in this window
      let stateColor = '#888'
      for (let j = circuitStateHistory.length - 1; j >= 0; j--) {
        const entry = circuitStateHistory[j]
        if (entry.timestamp >= bandStart && entry.timestamp < bandEnd) {
          stateColor = bandColor[entry.to_state] || '#888'
          break
        } else if (entry.timestamp < bandStart) {
          break
        }
      }
      const bandX = (b / numBands) * width
      const bandW = width / numBands
      circuitBands.push(
        <rect
          key={`band-${b}`}
          x={bandX}
          y={height - 10}
          width={bandW}
          height={10}
          fill={stateColor}
          opacity={0.4}
        />
      )
    }

    // Failure dots (last 5, showing as small dots on the right side)
    const recentFailures = (failureTimestamps || []).slice(-5)
    const failureX = width - 8
    const failureDots: React.ReactNode[] = recentFailures.map((ts, i) => (
      <circle
        key={`fail-${i}`}
        cx={failureX}
        cy={height - 12 - i * 9}
        r={3}
        fill="#f85149"
        opacity={0.7}
      />
    ))

    // Current state dot
    const stateDotColor: Record<string, string> = {
      closed: '#4ade80',
      half_open: '#facc15',
      open: '#f85149',
      unknown: '#888',
    }

    return (
      <svg width={width} height={height} style={{ display: 'block' }}>
        {/* Threshold dashed line */}
        <line
          x1={0}
          y1={thresholdY}
          x2={width}
          y2={thresholdY}
          stroke="#888"
          strokeWidth={1}
          strokeDasharray="3,3"
          opacity={0.5}
        />
        {/* Latency bars */}
        {bars}
        {/* Circuit state bands */}
        {circuitBands}
        {/* Failure dots */}
        {failureDots}
        {/* Current state dot */}
        <circle
          cx={width - (recentFailures.length > 0 ? 22 : 8)}
          cy={8}
          r={5}
          fill={stateDotColor[currentState] || '#888'}
        />
      </svg>
    )
  }

  // ─── Render ───

  return (
    <div style={S.container}>
      {/* Left tab sidebar */}
      <div style={S.sidebar}>
        {TABS.map(tab => (
          <button key={tab.id} style={S.tabBtn(activeTab === tab.id)} onClick={() => setActiveTab(tab.id)}>
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {/* Right content */}
      <div style={S.body}>
        {activeTab === 'general' && (
          <>
            {/* Default Model */}
            <div style={S.section}>
              <div style={S.sectionTitle}><span>🎯</span> 默認模型</div>
              <div style={S.field}>
                <div style={S.label}>啟動時使用的默認模型</div>
                <select style={S.select} value={`${defaultProvider}:${defaultModel}`}
                  onChange={(e) => { const [p, m] = e.target.value.split(':'); if (p && m) setDefault(m, p) }}>
                  {allModels.map((m) => (
                    <option key={`${m.provider}:${m.model}`} value={`${m.provider}:${m.model}`}>{m.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Language */}
            <div style={S.section}>
              <div style={S.sectionTitle}><span>🌍</span> 語言偏好</div>
              <div style={S.desc}>設置 AI 回覆的語言。</div>
              <div style={{ ...S.field, marginTop: '12px' }}>
                <select style={S.select} value={language} onChange={(e) => setLanguage(e.target.value)}>
                  <option value="">默認（跟隨系統）</option>
                  <option value="繁體中文">繁體中文</option>
                  <option value="简体中文">简体中文</option>
                  <option value="English">English</option>
                  <option value="日本語">日本語</option>
                  <option value="한국어">한국어</option>
                </select>
                <div style={{ marginTop: '8px' }}>
                  <button style={S.btn('primary')} onClick={() =>
                    saveSetting({ language }, () => { setLanguageSaved(true); setTimeout(() => setLanguageSaved(false), 2000) }, () => {})
                  }>
                    {languageSaved ? '✓ 已保存' : '保存語言設置'}
                  </button>
                </div>
              </div>
            </div>

            {/* System Prompt */}
            <div style={S.section}>
              <div style={S.sectionTitle}><span>💬</span> 自定義系統提示</div>
              <div style={S.desc}>此提示將被加入到每次對話的開頭，用於設定 AI 的行為和角色。</div>
              <div style={{ ...S.field, marginTop: '12px' }}>
                <textarea style={{ ...S.input, minHeight: '100px', resize: 'vertical' }}
                  value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="例如：你是一個友善的助手，擅長繁體中文回覆..." />
                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{systemPrompt.length} 個字符</span>
                  <button style={S.btn('primary')} onClick={() =>
                    saveSetting({ systemPrompt },
                      () => { setSystemPromptSaved(true); setTimeout(() => setSystemPromptSaved(false), 2000) },
                      (msg) => setSystemPromptError(msg))
                  }>
                    {systemPromptSaved ? '✓ 已保存' : '保存系統提示'}
                  </button>
                </div>
                {systemPromptError && <div style={{ ...S.desc, color: 'var(--accent-red)', marginTop: '8px' }}>{systemPromptError}</div>}
              </div>
            </div>
          </>
        )}

        {activeTab === 'appearance' && (
          <div style={S.section}>
            <div style={S.sectionTitle}><span>🎨</span> 主題</div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '12px', padding: '12px',
              borderRadius: '8px', background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-default)',
            }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--bg-primary)', border: '2px solid var(--accent-primary)' }} />
              <div>
                <div style={{ fontSize: '14px', fontWeight: 500 }}>深色模式</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>目前僅支持深色模式</div>
              </div>
              <div style={{ marginLeft: 'auto', padding: '4px 10px', borderRadius: '6px', background: 'rgba(204,120,92,0.12)', border: '1px solid rgba(204,120,92,0.3)', fontSize: '12px', color: 'var(--accent-primary)' }}>
                已啟用
              </div>
            </div>
          </div>
        )}

        {activeTab === 'security' && (
          <div style={S.section}>
            <div style={S.sectionTitle}><span>🔒</span> 工具執行授權</div>
            <div style={S.field}>
              <div style={S.label}>全域授權模式</div>
              <select style={S.select} value={permissionMode}
                onChange={(e) => setPermissionMode(e.target.value as 'ask' | 'always-allow')}>
                <option value="ask">每次詢問（推薦）</option>
                <option value="always-allow">始終允許所有工具</option>
              </select>
              <div style={S.desc}>「每次詢問」會在執行高風險工具前要求確認。「始終允許」會繞過所有確認提示。</div>
              {permissionMode === 'always-allow' && (
                <div style={{ ...S.warningBox, marginTop: '12px' }}>
                  ⚠️ 全域授權已啟用！所有工具將自動執行，無需任何確認。請只在信任的環境中使用。
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'hotkeys' && (
          <div style={S.section}>
            <div style={S.sectionTitle}><span>⌨️</span> 快捷鍵綁定</div>
            <div style={S.desc}>配置快捷鍵來快速切換模型。按 Ctrl+K 打開模型搜索面板。</div>
            <div style={{ marginTop: '12px' }}>
              {localHotkeys.map((hk, i) => (
                <div key={i} style={S.hotkeyRow}>
                  <input style={{ ...S.input, width: '120px', textAlign: 'center', fontFamily: 'monospace' }}
                    value={hk.key} onChange={(e) => updateHotkeyField(i, 'key', e.target.value)} placeholder="ctrl+1" />
                  <span style={{ color: 'var(--text-muted)' }}>→</span>
                  <select style={{ ...S.select, flex: 1 }} value={`${hk.provider}:${hk.model}`}
                    onChange={(e) => updateHotkeyField(i, 'model', e.target.value)}>
                    {allModels.map((m) => (
                      <option key={`${m.provider}:${m.model}`} value={`${m.provider}:${m.model}`}>{m.label}</option>
                    ))}
                  </select>
                  <button style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'transparent', color: 'var(--accent-red)', cursor: 'pointer', fontSize: '14px' }}
                    onClick={() => removeHotkey(i)}>✕</button>
                </div>
              ))}
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                <button style={S.btn('secondary')} onClick={addHotkey}>+ 添加快捷鍵</button>
                <button style={S.btn('primary')} onClick={handleSaveHotkeys}>{saved ? '✓ 已保存' : '保存快捷鍵'}</button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'server' && (
          <div style={S.section}>
            <div style={S.sectionTitle}><span>🌐</span> 服務器設置</div>
            <div style={S.field}>
              <div style={S.label}>WebUI 端口</div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <input style={{ ...S.input, width: '120px' }} type="number" value={port}
                  onChange={(e) => setPort(parseInt(e.target.value) || 7778)} />
                <button style={S.btn('primary')} onClick={() =>
                  saveSetting({ port },
                    () => { setSaved(true); setSaveError(null); setTimeout(() => setSaved(false), 2000) },
                    (msg) => setSaveError(msg))
                }>
                  {saved ? '✓ 已保存' : '保存'}
                </button>
              </div>
              <div style={S.desc}>更改端口後需要重啟服務才能生效。</div>
              {saveError && <div style={{ ...S.desc, color: 'var(--accent-red)', marginTop: '8px' }}>{saveError}</div>}
            </div>
          </div>
        )}

        {activeTab === 'about' && (
          <div style={S.section}>
            <div style={S.sectionTitle}><span>ℹ️</span> 關於</div>
            <div style={S.infoBox}>
              <strong>AI Code Assistant WebUI</strong><br />
              基於 Claude Code 源碼魔改的多模型 AI 編程助手。<br />
              支持 DeepSeek、MiniMax、OpenAI、Anthropic、Ollama 等多種模型供應商。<br /><br />
              <strong>快捷操作：</strong><br />
              • Ctrl+K — 打開模型切換面板<br />
              • Ctrl+1/2/3 — 快速切換預設模型<br />
              • Enter — 發送消息<br />
              • Shift+Enter — 換行
            </div>
          </div>
        )}

        {activeTab === 'providers' && (
          <div style={S.section}>
            <div style={S.sectionTitle}><span>🔄</span> 提供商狀態</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {providerOrder.map(provider => {
                const status = providerHealth[provider]
                const state = status?.state || 'unknown'
                const stateColors: Record<string, string> = {
                  closed: '#4ade80',
                  open: '#f85149',
                  half_open: '#facc15',
                  unknown: '#888',
                }
                const stateLabels: Record<string, string> = {
                  closed: '正常',
                  open: '斷路',
                  half_open: '測試中',
                  unknown: '未知',
                }

                // Get heartbeat data for this provider
                const hb = heartbeatData[provider]
                const threshold = hb?.custom_thresholds?.latency_ms || 2000
                const latencySamples = hb?.latency_samples || []
                const circuitHistory = hb?.circuit_state_history || []
                const failures = hb?.failure_timestamps || []
                const serverTime = serverTimeValue

                return (
                  <div key={provider} style={S.sparklineRow}>
                    <div style={S.sparklineName}>{provider}</div>
                    <div style={S.sparklineChart}>
                      {renderSparkline(
                        latencySamples,
                        threshold,
                        circuitHistory,
                        failures,
                        serverTime,
                        200,
                        40,
                        state
                      )}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px', minWidth: '100px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div style={{ ...S.stateDot, background: stateColors[state] || '#888' }} />
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {stateLabels[state] || state}
                        </span>
                      </div>
                      {failures.length > 0 && (
                        <div style={{ display: 'flex', gap: '2px' }}>
                          {failures.slice(-5).map((ts, i) => (
                            <div key={i} style={S.failureDot} />
                          ))}
                        </div>
                      )}
                    </div>
                    <button style={{ ...S.btn('secondary'), padding: '4px 8px', fontSize: '12px' }}
                      onClick={() => fetch(`/api/providers/${provider}/reset`, { method: 'POST' }).then(() => fetch('/api/providers/health').then(r => r.json()).then(d => setProviderHealth(d.providers || {}))).catch(() => {})}>
                      重置
                    </button>
                  </div>
                )
              })}
              {providerOrder.length === 0 && (
                <div style={{ ...S.desc, color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>暫無提供商數據</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

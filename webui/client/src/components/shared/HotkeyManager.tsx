import { useEffect, useState, useCallback } from 'react'
import { useModelStore } from '../../stores/modelStore.ts'
import { useChatStore } from '../../stores/chatStore.ts'

const overlayStyles = {
  backdrop: {
    position: 'fixed' as const,
    inset: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    paddingTop: '20vh',
    zIndex: 9999,
  },
  modal: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-default)',
    borderRadius: '12px',
    width: '480px',
    maxHeight: '400px',
    overflow: 'auto',
    boxShadow: '0 16px 48px rgba(0,0,0,0.4)',
  },
  input: {
    width: '100%',
    padding: '14px 16px',
    background: 'transparent',
    border: 'none',
    borderBottom: '1px solid var(--border-default)',
    color: 'var(--text-primary)',
    fontSize: '15px',
    outline: 'none',
  },
  item: (selected: boolean) => ({
    padding: '10px 16px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: selected ? 'var(--bg-tertiary)' : 'transparent',
    borderLeft: selected ? '2px solid var(--accent-blue)' : '2px solid transparent',
  }),
  hotkey: {
    fontSize: '11px',
    padding: '2px 6px',
    borderRadius: '4px',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
  },
}

export default function HotkeyManager() {
  const { providers, hotkeys, fetchModels } = useModelStore()
  const { setModel } = useChatStore()
  const [showSwitcher, setShowSwitcher] = useState(false)
  const [search, setSearch] = useState('')
  const [selectedIdx, setSelectedIdx] = useState(0)

  // Build flat model list
  const allModels = Object.entries(providers)
    .filter(([, p]) => p.enabled && p.apiKey)
    .flatMap(([id, p]) =>
      p.models.map((m) => ({
        provider: id,
        providerName: p.displayName || id,
        model: m,
      }))
    )

  const filtered = allModels.filter(
    (m) =>
      m.model.toLowerCase().includes(search.toLowerCase()) ||
      m.providerName.toLowerCase().includes(search.toLowerCase())
  )

  const getHotkeyForModel = (provider: string, model: string): string | null => {
    const binding = hotkeys.find((h) => h.provider === provider && h.model === model)
    return binding?.key || null
  }

  // Global keyboard handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ctrl+K: open model switcher
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setShowSwitcher((v) => !v)
        setSearch('')
        setSelectedIdx(0)
        return
      }

      // Escape: close switcher
      if (e.key === 'Escape' && showSwitcher) {
        setShowSwitcher(false)
        return
      }

      // Check hotkey bindings (ctrl+1, ctrl+2, etc.)
      for (const binding of hotkeys) {
        const parts = binding.key.split('+')
        const needsCtrl = parts.includes('ctrl')
        const needsShift = parts.includes('shift')
        const needsAlt = parts.includes('alt')
        const key = parts[parts.length - 1]

        if (
          (needsCtrl ? e.ctrlKey || e.metaKey : true) &&
          (needsShift ? e.shiftKey : true) &&
          (needsAlt ? e.altKey : true) &&
          e.key === key
        ) {
          e.preventDefault()
          setModel(binding.model, binding.provider)
          return
        }
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [hotkeys, showSwitcher, setModel])

  // Arrow key navigation in switcher
  useEffect(() => {
    if (!showSwitcher) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIdx((i) => Math.min(i + 1, filtered.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIdx((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const selected = filtered[selectedIdx]
        if (selected) {
          setModel(selected.model, selected.provider)
          setShowSwitcher(false)
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [showSwitcher, filtered, selectedIdx, setModel])

  if (!showSwitcher) return null

  return (
    <div style={overlayStyles.backdrop} onClick={() => setShowSwitcher(false)}>
      <div style={overlayStyles.modal} onClick={(e) => e.stopPropagation()}>
        <input
          style={overlayStyles.input}
          placeholder="搜索模型... (輸入名稱或供應商)"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setSelectedIdx(0)
          }}
          autoFocus
        />
        {filtered.map((m, i) => (
          <div
            key={`${m.provider}:${m.model}`}
            style={overlayStyles.item(i === selectedIdx)}
            onClick={() => {
              setModel(m.model, m.provider)
              setShowSwitcher(false)
            }}
            onMouseEnter={() => setSelectedIdx(i)}
          >
            <div>
              <span style={{ color: 'var(--text-primary)' }}>{m.model}</span>
              <span style={{ color: 'var(--text-muted)', marginLeft: '8px', fontSize: '12px' }}>
                {m.providerName}
              </span>
            </div>
            {getHotkeyForModel(m.provider, m.model) && (
              <span style={overlayStyles.hotkey}>{getHotkeyForModel(m.provider, m.model)}</span>
            )}
          </div>
        ))}
        {filtered.length === 0 && (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            {allModels.length === 0 ? '請先在模型管理中添加供應商' : '未找到匹配的模型'}
          </div>
        )}
      </div>
    </div>
  )
}

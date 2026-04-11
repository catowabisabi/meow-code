import { useState, useRef, useEffect } from 'react'

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: '100%',
    background: '#0d1117',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-default)',
    fontSize: '13px',
  },
  shellSelect: {
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    padding: '4px 8px',
    fontSize: '12px',
    outline: 'none',
  },
  cwdDisplay: {
    color: 'var(--text-muted)',
    fontSize: '12px',
    fontFamily: 'monospace',
    flex: 1,
  },
  clearBtn: {
    padding: '3px 10px',
    borderRadius: '4px',
    border: '1px solid var(--border-default)',
    background: 'transparent',
    color: 'var(--text-secondary)',
    fontSize: '12px',
    cursor: 'pointer',
  },
  output: {
    flex: 1,
    overflow: 'auto',
    padding: '12px 16px',
    fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace",
    fontSize: '13px',
    lineHeight: 1.6,
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-all' as const,
  },
  entryLine: {
    display: 'flex',
    gap: '0',
    marginBottom: '4px',
  },
  prompt: {
    color: '#3fb950',
    whiteSpace: 'nowrap' as const,
  },
  cmdText: {
    color: '#58a6ff',
    fontWeight: 500 as const,
  },
  stdout: {
    color: '#e6edf3',
  },
  stderr: {
    color: '#f85149',
  },
  inputArea: {
    display: 'flex',
    alignItems: 'center',
    padding: '8px 16px',
    background: '#0d1117',
    borderTop: '1px solid var(--border-default)',
  },
  promptChar: {
    color: '#3fb950',
    fontFamily: "'Cascadia Code', 'Fira Code', monospace",
    fontSize: '14px',
    marginRight: '8px',
    fontWeight: 700,
  },
  input: {
    flex: 1,
    padding: '6px 0',
    background: 'transparent',
    border: 'none',
    color: '#e6edf3',
    fontSize: '14px',
    fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace",
    outline: 'none',
  },
  running: {
    padding: '4px 10px',
    borderRadius: '4px',
    background: '#d2992233',
    color: 'var(--accent-orange)',
    fontSize: '12px',
    fontWeight: 600,
  },
}

interface TerminalEntry {
  id: string
  command: string
  output: string
  isError: boolean
  timestamp: number
  shell: string
}

export default function TerminalPage() {
  const [entries, setEntries] = useState<TerminalEntry[]>([])
  const [input, setInput] = useState('')
  const [cwd, setCwd] = useState('')
  const [shell, setShell] = useState<'auto' | 'powershell' | 'bash' | 'cmd'>('auto')
  const [running, setRunning] = useState(false)
  const [history, setHistory] = useState<string[]>([])
  const [historyIdx, setHistoryIdx] = useState(-1)
  const outputRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetch('/api/shell/cwd').then((r) => r.json()).then((d) => setCwd(d.cwd)).catch(() => {})
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    outputRef.current?.scrollTo(0, outputRef.current.scrollHeight)
  }, [entries])

  const executeCommand = async (command: string) => {
    if (!command.trim() || running) return

    setRunning(true)
    setHistory((h) => [command, ...h.slice(0, 100)])
    setHistoryIdx(-1)

    // Handle cd specially to track cwd
    const cdMatch = command.match(/^cd\s+(.+)/)

    try {
      const res = await fetch('/api/shell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command, cwd, shell, timeout: 120000 }),
      })
      const data = await res.json()

      setEntries((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          command,
          output: data.output || '',
          isError: data.isError || false,
          timestamp: Date.now(),
          shell,
        },
      ])

      // Track cwd changes
      if (cdMatch && !data.isError) {
        // Re-fetch cwd after cd
        const cwdCmd = shell === 'powershell' || shell === 'auto'
          ? 'Get-Location | Select-Object -ExpandProperty Path'
          : 'pwd'
        const cwdRes = await fetch('/api/shell', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cwdCmd, cwd, shell }),
        })
        const cwdData = await cwdRes.json()
        if (!cwdData.isError && cwdData.output) {
          setCwd(cwdData.output.trim())
        }
      }
    } catch (err: unknown) {
      setEntries((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          command,
          output: `Network error: ${err instanceof Error ? err.message : String(err)}`,
          isError: true,
          timestamp: Date.now(),
          shell,
        },
      ])
    }

    setRunning(false)
    setInput('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      executeCommand(input)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (history.length > 0) {
        const idx = Math.min(historyIdx + 1, history.length - 1)
        setHistoryIdx(idx)
        setInput(history[idx] || '')
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIdx > 0) {
        const idx = historyIdx - 1
        setHistoryIdx(idx)
        setInput(history[idx] || '')
      } else {
        setHistoryIdx(-1)
        setInput('')
      }
    } else if (e.key === 'c' && e.ctrlKey) {
      // Ctrl+C: cancel current or clear input
      setInput('')
    }
  }

  return (
    <div style={styles.container} onClick={() => inputRef.current?.focus()}>
      <div style={styles.toolbar}>
        <span style={{ fontWeight: 600 }}>Terminal</span>
        <select
          style={styles.shellSelect}
          value={shell}
          onChange={(e) => setShell(e.target.value as typeof shell)}
        >
          <option value="auto">Auto</option>
          <option value="powershell">PowerShell</option>
          <option value="bash">Bash</option>
          <option value="cmd">CMD</option>
        </select>
        <div style={styles.cwdDisplay}>{cwd}</div>
        {running && <span style={styles.running}>Running...</span>}
        <button style={styles.clearBtn} onClick={() => setEntries([])}>
          Clear
        </button>
      </div>

      <div style={styles.output} ref={outputRef}>
        {entries.map((entry) => (
          <div key={entry.id}>
            <div style={styles.entryLine}>
              <span style={styles.prompt}>{cwd.split(/[/\\]/).pop()}$&nbsp;</span>
              <span style={styles.cmdText}>{entry.command}</span>
            </div>
            {entry.output && (
              <div style={entry.isError ? styles.stderr : styles.stdout}>
                {entry.output}
              </div>
            )}
            <div style={{ height: '8px' }} />
          </div>
        ))}
        {entries.length === 0 && (
          <div style={{ color: 'var(--text-muted)', padding: '20px 0' }}>
            AI Code Assistant Terminal — 輸入命令開始操作
            {'\n'}支持 PowerShell / Bash / CMD
            {'\n'}Ctrl+C 取消 · ↑↓ 翻閱歷史
          </div>
        )}
      </div>

      <div style={styles.inputArea}>
        <span style={styles.promptChar}>$</span>
        <input
          ref={inputRef}
          style={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={running ? 'Waiting...' : '輸入命令...'}
          disabled={running}
          autoFocus
        />
      </div>
    </div>
  )
}

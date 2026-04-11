import { useState } from 'react'

const styles = {
  container: {
    margin: '8px 0',
    borderRadius: '8px',
    overflow: 'hidden',
    border: '1px solid var(--border-default)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 12px',
    background: 'var(--bg-hover)',
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
  copyBtn: {
    background: 'transparent',
    border: '1px solid var(--border-default)',
    color: 'var(--text-secondary)',
    borderRadius: '4px',
    padding: '2px 8px',
    fontSize: '11px',
    cursor: 'pointer',
  },
  code: {
    padding: '12px 16px',
    background: '#0d1117',
    color: '#e6edf3',
    fontSize: '13px',
    lineHeight: 1.5,
    fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace",
    overflow: 'auto',
    whiteSpace: 'pre' as const,
    tabSize: 2,
  },
}

export default function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span>{language}</span>
        <button style={styles.copyBtn} onClick={handleCopy}>
          {copied ? '已複製 ✓' : '複製'}
        </button>
      </div>
      <pre style={styles.code}>
        <code>{code}</code>
      </pre>
    </div>
  )
}

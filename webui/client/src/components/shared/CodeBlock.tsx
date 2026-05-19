import { useState, useEffect } from 'react'
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import css from 'highlight.js/lib/languages/css'
import xml from 'highlight.js/lib/languages/xml'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import sql from 'highlight.js/lib/languages/sql'
import markdown from 'highlight.js/lib/languages/markdown'
import plaintext from 'highlight.js/lib/languages/plaintext'

hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('css', css)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('json', json)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('text', plaintext)

const LANG_ALIASES: Record<string, string> = {
  'js': 'javascript',
  'ts': 'typescript',
  'py': 'python',
  'sh': 'bash',
  'shell': 'bash',
  'yml': 'plaintext',
  'yaml': 'plaintext',
  'md': 'markdown',
  'dockerfile': 'plaintext',
}

function highlightCode(code: string, language: string): string {
  const lang = LANG_ALIASES[language] || language
  try {
    if (hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value
    }
  } catch {
  }
  return code
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

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
  const [highlighted, setHighlighted] = useState('')

  useEffect(() => {
    if (language === 'html') {
      setHighlighted(
        code
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
      )
    } else {
      setHighlighted(highlightCode(code, language))
    }
  }, [code, language])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span>{language || 'text'}</span>
        <button style={styles.copyBtn} onClick={handleCopy}>
          {copied ? '已複製 ✓' : '複製'}
        </button>
      </div>
      <pre style={styles.code}>
        {language === 'html' ? (
          <code
            dangerouslySetInnerHTML={{ __html: code }}
          />
        ) : (
          <code dangerouslySetInnerHTML={{ __html: highlighted }} />
        )}
      </pre>
    </div>
  )
}
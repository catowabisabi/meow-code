import { useState, useEffect, useRef } from 'react'
import { useChatStore } from '../stores/chatStore.ts'

const styles = {
  container: {
    display: 'flex',
    height: '100%',
    overflow: 'hidden',
  },
  filePanel: {
    width: '240px',
    minWidth: '240px',
    background: 'var(--bg-secondary)',
    borderRight: '1px solid var(--border-default)',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  filePanelHeader: {
    padding: '12px 14px',
    fontSize: '13px',
    fontWeight: 600,
    borderBottom: '1px solid var(--border-default)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  pathInput: {
    width: '100%',
    padding: '6px 10px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    fontSize: '12px',
    outline: 'none',
    margin: '8px',
    fontFamily: 'monospace',
  },
  fileList: {
    flex: 1,
    overflow: 'auto',
    padding: '4px 0',
  },
  fileItem: (isDir: boolean, selected: boolean) => ({
    padding: '5px 14px',
    fontSize: '13px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    color: selected ? 'var(--text-primary)' : 'var(--text-secondary)',
    background: selected ? 'var(--bg-tertiary)' : 'transparent',
    fontWeight: isDir ? 500 : 400,
  }),
  editorArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  editorHeader: {
    padding: '8px 16px',
    fontSize: '13px',
    borderBottom: '1px solid var(--border-default)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: 'var(--bg-secondary)',
  },
  editorContent: {
    flex: 1,
    overflow: 'auto',
    position: 'relative' as const,
  },
  textarea: {
    width: '100%',
    height: '100%',
    padding: '16px',
    background: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    border: 'none',
    outline: 'none',
    resize: 'none' as const,
    fontSize: '14px',
    lineHeight: 1.6,
    fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace",
    tabSize: 2,
  },
  aiPanel: {
    width: '360px',
    minWidth: '360px',
    borderLeft: '1px solid var(--border-default)',
    display: 'flex',
    flexDirection: 'column' as const,
    background: 'var(--bg-secondary)',
  },
  aiHeader: {
    padding: '12px 14px',
    fontSize: '13px',
    fontWeight: 600,
    borderBottom: '1px solid var(--border-default)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  aiMessages: {
    flex: 1,
    overflow: 'auto',
    padding: '12px',
    fontSize: '13px',
    lineHeight: 1.6,
  },
  aiMsg: (isUser: boolean) => ({
    padding: '8px 12px',
    marginBottom: '8px',
    borderRadius: '8px',
    background: isUser ? '#1f6feb33' : 'var(--bg-tertiary)',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  }),
  aiInput: {
    display: 'flex',
    gap: '6px',
    padding: '10px 12px',
    borderTop: '1px solid var(--border-default)',
  },
  aiTextarea: {
    flex: 1,
    padding: '8px 10px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    fontSize: '13px',
    resize: 'none' as const,
    outline: 'none',
    fontFamily: 'inherit',
    minHeight: '36px',
    maxHeight: '100px',
  },
  aiSendBtn: {
    padding: '8px 12px',
    borderRadius: '6px',
    border: 'none',
    background: 'var(--accent-blue)',
    color: '#fff',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: 500,
    whiteSpace: 'nowrap' as const,
  },
  actionBtn: {
    padding: '4px 10px',
    borderRadius: '4px',
    border: '1px solid var(--border-default)',
    background: 'var(--bg-tertiary)',
    color: 'var(--text-secondary)',
    fontSize: '12px',
    cursor: 'pointer',
  },
  statusBar: {
    padding: '4px 16px',
    fontSize: '11px',
    color: 'var(--text-muted)',
    background: 'var(--bg-secondary)',
    borderTop: '1px solid var(--border-default)',
    display: 'flex',
    gap: '16px',
  },
}

interface FileEntry {
  name: string
  path: string
  isDirectory: boolean
  isFile: boolean
}

interface AIChatMsg {
  role: 'user' | 'assistant'
  text: string
}

export default function CodeEditorPage() {
  const [currentPath, setCurrentPath] = useState('C:\\')
  const [files, setFiles] = useState<FileEntry[]>([])
  const [openFile, setOpenFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState('')
  const [language, setLanguage] = useState('plaintext')
  const [modified, setModified] = useState(false)
  const [aiMessages, setAiMessages] = useState<AIChatMsg[]>([])
  const [aiInput, setAiInput] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const { ws, currentModel, currentProvider } = useChatStore()

  // Load file list
  const loadFiles = async (dirPath: string) => {
    try {
      const res = await fetch(`/api/files?path=${encodeURIComponent(dirPath)}`)
      const data = await res.json()
      if (data.files) {
        setFiles(data.files)
        setCurrentPath(data.path)
      }
    } catch (e) {
      console.error('Failed to load files:', e)
    }
  }

  // Load file content
  const loadFile = async (filePath: string) => {
    try {
      const res = await fetch(`/api/files/read?path=${encodeURIComponent(filePath)}`)
      const data = await res.json()
      if (data.content !== undefined) {
        setFileContent(data.content)
        setLanguage(data.language || 'plaintext')
        setOpenFile(filePath)
        setModified(false)
      }
    } catch (e) {
      console.error('Failed to load file:', e)
    }
  }

  // Save file
  const saveFile = async () => {
    if (!openFile) return
    try {
      await fetch('/api/files/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: openFile, content: fileContent }),
      })
      setModified(false)
    } catch (e) {
      console.error('Failed to save:', e)
    }
  }

  // AI chat for code assistance
  const sendAiMessage = async () => {
    const msg = aiInput.trim()
    if (!msg || aiLoading) return

    const context = openFile
      ? `\n\n[當前文件: ${openFile}]\n\`\`\`${language}\n${fileContent.slice(0, 2000)}\n\`\`\``
      : ''

    setAiMessages((prev) => [...prev, { role: 'user', text: msg }])
    setAiInput('')
    setAiLoading(true)

    // Use a separate fetch for code AI to avoid interfering with main chat WS
    try {
      const fullPrompt = msg + context
      // Simple approach: create a temporary WS or reuse
      // For now, just use a POST to trigger and collect response
      setAiMessages((prev) => [...prev, { role: 'assistant', text: '思考中...' }])

      // We'll connect to the same WS and just listen for the response
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: 'user_message',
            content: fullPrompt,
            model: currentModel,
            provider: currentProvider,
          })
        )
      }
      // Note: In a full implementation, we'd use a separate session for editor AI
      setAiLoading(false)
    } catch {
      setAiLoading(false)
    }
  }

  useEffect(() => {
    loadFiles(currentPath)
  }, [])

  // Keyboard shortcut: Ctrl+S to save
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        saveFile()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [openFile, fileContent])

  const fileName = openFile ? openFile.split(/[/\\]/).pop() : null
  const lineCount = fileContent.split('\n').length
  const charCount = fileContent.length

  return (
    <div style={styles.container}>
      {/* File Explorer */}
      <div style={styles.filePanel}>
        <div style={styles.filePanelHeader}>
          <span>📁</span>
          <span>文件瀏覽器</span>
        </div>
        <input
          style={styles.pathInput}
          value={currentPath}
          onChange={(e) => setCurrentPath(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') loadFiles(currentPath)
          }}
          placeholder="輸入路徑..."
        />
        <div style={styles.fileList}>
          {/* Parent directory */}
          <div
            style={styles.fileItem(true, false)}
            onClick={() => {
              const parent = currentPath.replace(/[/\\][^/\\]*$/, '') || '/'
              loadFiles(parent)
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <span>📂</span>
            <span>..</span>
          </div>
          {files.map((f) => (
            <div
              key={f.path}
              style={styles.fileItem(f.isDirectory, f.path === openFile)}
              onClick={() => {
                if (f.isDirectory) {
                  loadFiles(f.path)
                } else {
                  loadFile(f.path)
                }
              }}
              onMouseEnter={(e) => {
                if (f.path !== openFile) e.currentTarget.style.background = 'var(--bg-hover)'
              }}
              onMouseLeave={(e) => {
                if (f.path !== openFile) e.currentTarget.style.background = 'transparent'
              }}
            >
              <span>{f.isDirectory ? '📁' : '📄'}</span>
              <span>{f.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Editor */}
      <div style={styles.editorArea}>
        <div style={styles.editorHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>{fileName || '未打開文件'}</span>
            {modified && (
              <span style={{ color: 'var(--accent-orange)', fontSize: '11px' }}>● 已修改</span>
            )}
            {language !== 'plaintext' && (
              <span
                style={{
                  fontSize: '11px',
                  padding: '1px 6px',
                  borderRadius: '3px',
                  background: 'var(--bg-tertiary)',
                  color: 'var(--text-muted)',
                }}
              >
                {language}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              style={styles.actionBtn}
              onClick={saveFile}
              disabled={!modified}
            >
              💾 保存 (Ctrl+S)
            </button>
          </div>
        </div>
        <div style={styles.editorContent}>
          {openFile ? (
            <textarea
              style={styles.textarea}
              value={fileContent}
              onChange={(e) => {
                setFileContent(e.target.value)
                setModified(true)
              }}
              onKeyDown={(e) => {
                // Tab support
                if (e.key === 'Tab') {
                  e.preventDefault()
                  const target = e.target as HTMLTextAreaElement
                  const start = target.selectionStart
                  const end = target.selectionEnd
                  const newValue =
                    fileContent.substring(0, start) + '  ' + fileContent.substring(end)
                  setFileContent(newValue)
                  setModified(true)
                  requestAnimationFrame(() => {
                    target.selectionStart = target.selectionEnd = start + 2
                  })
                }
              }}
              spellCheck={false}
            />
          ) : (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--text-muted)',
                fontSize: '14px',
              }}
            >
              從左側選擇文件開始編輯
            </div>
          )}
        </div>
        {openFile && (
          <div style={styles.statusBar}>
            <span>行 {lineCount}</span>
            <span>字符 {charCount}</span>
            <span>{language}</span>
            <span>UTF-8</span>
          </div>
        )}
      </div>

      {/* AI Assistant Panel */}
      <div style={styles.aiPanel}>
        <div style={styles.aiHeader}>
          <span>🤖</span>
          <span>AI 代碼助手</span>
        </div>
        <div style={styles.aiMessages}>
          {aiMessages.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '40px' }}>
              <div style={{ fontSize: '24px', marginBottom: '8px' }}>💡</div>
              <div>選擇代碼後，向 AI 提問</div>
              <div style={{ marginTop: '12px', fontSize: '12px' }}>
                例如：
                <br />• "解釋這段代碼"
                <br />• "重構這個函數"
                <br />• "添加錯誤處理"
                <br />• "寫單元測試"
              </div>
            </div>
          ) : (
            aiMessages.map((msg, i) => (
              <div key={i} style={styles.aiMsg(msg.role === 'user')}>
                {msg.text}
              </div>
            ))
          )}
        </div>
        <div style={styles.aiInput}>
          <textarea
            style={styles.aiTextarea}
            placeholder="問 AI 關於代碼的問題..."
            value={aiInput}
            onChange={(e) => setAiInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendAiMessage()
              }
            }}
            rows={1}
          />
          <button style={styles.aiSendBtn} onClick={sendAiMessage} disabled={aiLoading}>
            發送
          </button>
        </div>
      </div>
    </div>
  )
}

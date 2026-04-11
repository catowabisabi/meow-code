import { useState, useEffect } from 'react'

type TabId = 'setup' | 'browser' | 'databases'

interface NotionSearchResult {
  id: string
  title: string
  icon?: string
  object: 'page' | 'database'
  lastEditedTime?: string
}

interface NotionBlock {
  id: string
  type: string
  text?: string
  children?: NotionBlock[]
}

interface PageDetail {
  id: string
  title: string
  blocks: NotionBlock[]
}

interface DatabaseColumn {
  name: string
  type: string
}

interface DatabaseResult {
  columns: DatabaseColumn[]
  rows: Record<string, string>[]
}

const styles = {
  container: {
    padding: '24px 32px',
    maxWidth: '900px',
    margin: '0 auto',
  },
  title: {
    fontSize: '22px',
    fontWeight: 700,
    marginBottom: '8px',
    color: '#e6e6e6',
  },
  subtitle: {
    fontSize: '13px',
    color: '#a1a1aa',
    marginBottom: '20px',
  },
  tabBar: {
    display: 'flex',
    gap: '4px',
    marginBottom: '24px',
    borderBottom: '1px solid #2a2a2e',
    paddingBottom: '0',
  },
  tab: (active: boolean) => ({
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: active ? 600 : 400,
    color: active ? '#e6e6e6' : '#a1a1aa',
    background: 'transparent',
    border: 'none',
    borderBottom: active ? '2px solid #58a6ff' : '2px solid transparent',
    cursor: 'pointer',
    transition: 'color 0.15s',
  }),
  section: {
    background: '#1b1b1f',
    border: '1px solid #2a2a2e',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '16px',
  },
  sectionTitle: {
    fontSize: '15px',
    fontWeight: 600,
    marginBottom: '16px',
    color: '#e6e6e6',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  stepList: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
  },
  step: {
    display: 'flex',
    gap: '12px',
    marginBottom: '14px',
    fontSize: '14px',
    color: '#e6e6e6',
    lineHeight: 1.6,
  },
  stepNumber: {
    flexShrink: 0,
    width: '28px',
    height: '28px',
    borderRadius: '50%',
    background: 'rgba(88,166,255,0.12)',
    color: '#58a6ff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '13px',
    fontWeight: 600,
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    background: '#0f0f10',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#e6e6e6',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box' as const,
  },
  inputRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    marginBottom: '12px',
  },
  btn: (variant: 'primary' | 'secondary' | 'danger') => ({
    padding: '8px 18px',
    borderRadius: '6px',
    border: variant === 'primary' ? 'none' : '1px solid #2a2a2e',
    background: variant === 'primary' ? '#58a6ff' : variant === 'danger' ? 'transparent' : '#1b1b1f',
    color: variant === 'primary' ? '#fff' : variant === 'danger' ? '#f87171' : '#a1a1aa',
    fontSize: '13px',
    cursor: 'pointer',
    fontWeight: 500,
  }),
  statusBadge: (connected: boolean) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 14px',
    borderRadius: '20px',
    fontSize: '13px',
    fontWeight: 500,
    background: connected ? 'rgba(34,197,94,0.1)' : 'rgba(248,113,113,0.1)',
    color: connected ? '#22c55e' : '#f87171',
    border: `1px solid ${connected ? 'rgba(34,197,94,0.2)' : 'rgba(248,113,113,0.2)'}`,
  }),
  searchBar: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
  },
  card: {
    background: '#1b1b1f',
    border: '1px solid #2a2a2e',
    borderRadius: '10px',
    padding: '14px 16px',
    marginBottom: '10px',
    cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  cardTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#e6e6e6',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  cardMeta: {
    fontSize: '12px',
    color: '#a1a1aa',
    marginTop: '4px',
  },
  pageContent: {
    background: '#0f0f10',
    border: '1px solid #2a2a2e',
    borderRadius: '8px',
    padding: '16px',
    marginTop: '12px',
    fontSize: '14px',
    color: '#e6e6e6',
    lineHeight: 1.7,
    whiteSpace: 'pre-wrap' as const,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '13px',
  },
  th: {
    textAlign: 'left' as const,
    padding: '10px 12px',
    borderBottom: '1px solid #2a2a2e',
    color: '#a1a1aa',
    fontWeight: 600,
    fontSize: '12px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #2a2a2e',
    color: '#e6e6e6',
  },
  loading: {
    textAlign: 'center' as const,
    padding: '40px',
    color: '#a1a1aa',
    fontSize: '14px',
  },
  error: {
    padding: '12px 16px',
    background: 'rgba(248,113,113,0.08)',
    border: '1px solid rgba(248,113,113,0.2)',
    borderRadius: '8px',
    color: '#f87171',
    fontSize: '13px',
    marginBottom: '12px',
  },
  empty: {
    textAlign: 'center' as const,
    padding: '40px',
    color: '#a1a1aa',
    fontSize: '14px',
  },
  backBtn: {
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #2a2a2e',
    background: 'transparent',
    color: '#a1a1aa',
    fontSize: '13px',
    cursor: 'pointer',
    marginBottom: '12px',
  },
  label: {
    fontSize: '13px',
    color: '#a1a1aa',
    marginBottom: '6px',
    fontWeight: 500,
  },
  toggleBtn: {
    padding: '8px 12px',
    background: '#0f0f10',
    border: '1px solid #2a2a2e',
    borderRadius: '0 6px 6px 0',
    color: '#a1a1aa',
    cursor: 'pointer',
    fontSize: '13px',
    flexShrink: 0,
  },
}

export default function NotionPage() {
  const [activeTab, setActiveTab] = useState<TabId>('setup')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [connected, setConnected] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [results, setResults] = useState<NotionSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedPage, setSelectedPage] = useState<PageDetail | null>(null)
  const [selectedDb, setSelectedDb] = useState<DatabaseResult | null>(null)
  const [selectedDbTitle, setSelectedDbTitle] = useState('')

  // Load settings on mount
  useEffect(() => {
    fetch('/api/settings')
      .then((r) => r.json())
      .then((d) => {
        if (d.notion?.apiKey) {
          setApiKey(d.notion.apiKey)
          setConnected(true)
        }
      })
      .catch(() => {})
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notion: { apiKey } }),
      })
      if (!res.ok) throw new Error('Failed to save settings')
      setConnected(!!apiKey)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await fetch('/api/notion/search?q=test')
      if (res.ok) {
        setTestResult('success')
        setConnected(true)
      } else {
        setTestResult('fail')
        setConnected(false)
      }
    } catch {
      setTestResult('fail')
      setConnected(false)
    } finally {
      setTesting(false)
    }
  }

  const handleSearch = async (query?: string) => {
    const q = query ?? searchQuery
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    setSelectedPage(null)
    setSelectedDb(null)
    try {
      const res = await fetch(`/api/notion/search?q=${encodeURIComponent(q)}`)
      if (!res.ok) throw new Error('Search failed')
      const data = await res.json()
      setResults(data.results || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleClickPage = async (item: NotionSearchResult) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/notion/pages/${item.id}`)
      if (!res.ok) throw new Error('Failed to load page')
      const data = await res.json()
      setSelectedPage(data)
      setSelectedDb(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Load failed')
    } finally {
      setLoading(false)
    }
  }

  const handleClickDatabase = async (item: NotionSearchResult) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/notion/databases/${item.id}/query`, { method: 'POST' })
      if (!res.ok) throw new Error('Failed to query database')
      const data = await res.json()
      setSelectedDb(data)
      setSelectedDbTitle(item.title)
      setSelectedPage(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const renderBlock = (block: NotionBlock) => {
    const text = block.text || ''
    switch (block.type) {
      case 'heading_1':
        return <div key={block.id} style={{ fontSize: '20px', fontWeight: 700, margin: '16px 0 8px' }}>{text}</div>
      case 'heading_2':
        return <div key={block.id} style={{ fontSize: '17px', fontWeight: 600, margin: '12px 0 6px' }}>{text}</div>
      case 'heading_3':
        return <div key={block.id} style={{ fontSize: '15px', fontWeight: 600, margin: '10px 0 4px' }}>{text}</div>
      case 'bulleted_list_item':
        return <div key={block.id} style={{ paddingLeft: '16px', margin: '4px 0' }}>{'- '}{text}</div>
      case 'numbered_list_item':
        return <div key={block.id} style={{ paddingLeft: '16px', margin: '4px 0' }}>{text}</div>
      case 'to_do':
        return <div key={block.id} style={{ paddingLeft: '16px', margin: '4px 0' }}>{'[ ] '}{text}</div>
      case 'code':
        return (
          <pre key={block.id} style={{ background: '#0f0f10', padding: '12px', borderRadius: '6px', fontSize: '13px', overflow: 'auto', margin: '8px 0' }}>
            {text}
          </pre>
        )
      case 'divider':
        return <hr key={block.id} style={{ border: 'none', borderTop: '1px solid #2a2a2e', margin: '12px 0' }} />
      default:
        return <div key={block.id} style={{ margin: '4px 0' }}>{text}</div>
    }
  }

  const renderDatabaseTable = (db: DatabaseResult) => (
    <div style={{ overflowX: 'auto', marginTop: '12px' }}>
      <table style={styles.table}>
        <thead>
          <tr>
            {db.columns.map((col, i) => (
              <th key={i} style={styles.th}>{col.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {db.rows.map((row, ri) => (
            <tr key={ri}>
              {db.columns.map((col, ci) => (
                <td key={ci} style={styles.td}>{row[col.name] || '-'}</td>
              ))}
            </tr>
          ))}
          {db.rows.length === 0 && (
            <tr>
              <td colSpan={db.columns.length} style={{ ...styles.td, textAlign: 'center', color: '#a1a1aa' }}>
                No data
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )

  const filteredResults = activeTab === 'databases'
    ? results.filter((r) => r.object === 'database')
    : results

  const tabs: { id: TabId; label: string }[] = [
    { id: 'setup', label: 'Setup' },
    { id: 'browser', label: 'Browser' },
    { id: 'databases', label: 'Databases' },
  ]

  return (
    <div style={styles.container}>
      <div style={styles.title}>Notion Integration</div>
      <div style={styles.subtitle}>Connect and browse your Notion workspace</div>

      {/* Tab Bar */}
      <div style={styles.tabBar}>
        {tabs.map((t) => (
          <button
            key={t.id}
            style={styles.tab(activeTab === t.id)}
            onClick={() => { setActiveTab(t.id); setSelectedPage(null); setSelectedDb(null) }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* Tab: Setup */}
      {activeTab === 'setup' && (
        <>
          <div style={styles.section}>
            <div style={styles.sectionTitle}>
              <span>Setup Tutorial</span>
            </div>
            <ol style={styles.stepList}>
              {[
                'Go to notion.so/my-integrations and create an integration',
                'Copy the Integration Token (starts with ntn_ or secret_)',
                'Enter the API Key below',
                'In Notion, go to your page, click "..." then "Add connections" and select your integration',
                'Click the Test button to verify the connection',
              ].map((text, i) => (
                <li key={i} style={styles.step}>
                  <div style={styles.stepNumber}>{i + 1}</div>
                  <div style={{ paddingTop: '3px' }}>{text}</div>
                </li>
              ))}
            </ol>
          </div>

          <div style={styles.section}>
            <div style={styles.sectionTitle}>API Key</div>
            <div style={styles.label}>Notion Integration Token</div>
            <div style={styles.inputRow}>
              <input
                style={{ ...styles.input, borderRadius: '6px 0 0 6px', flex: 1 }}
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="ntn_xxxxx or secret_xxxxx"
              />
              <button
                style={styles.toggleBtn}
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? 'Hide' : 'Show'}
              </button>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <button style={styles.btn('primary')} onClick={handleSave} disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button style={styles.btn('secondary')} onClick={handleTest} disabled={testing}>
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
              <span style={styles.statusBadge(connected)}>
                {connected ? 'Connected' : 'Not Connected'}
              </span>
              {testResult === 'success' && (
                <span style={{ color: '#22c55e', fontSize: '13px' }}>Test passed</span>
              )}
              {testResult === 'fail' && (
                <span style={{ color: '#f87171', fontSize: '13px' }}>Test failed</span>
              )}
            </div>
          </div>
        </>
      )}

      {/* Tab: Browser */}
      {activeTab === 'browser' && (
        <>
          <div style={styles.searchBar}>
            <input
              style={{ ...styles.input, flex: 1 }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search Notion pages and databases..."
            />
            <button style={styles.btn('primary')} onClick={() => handleSearch()} disabled={loading}>
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {selectedPage && (
            <>
              <button style={styles.backBtn} onClick={() => setSelectedPage(null)}>
                Back to results
              </button>
              <div style={styles.section}>
                <div style={styles.sectionTitle}>{selectedPage.title}</div>
                <div style={styles.pageContent}>
                  {selectedPage.blocks.map(renderBlock)}
                  {selectedPage.blocks.length === 0 && (
                    <div style={{ color: '#a1a1aa' }}>No content blocks found</div>
                  )}
                </div>
              </div>
            </>
          )}

          {selectedDb && (
            <>
              <button style={styles.backBtn} onClick={() => setSelectedDb(null)}>
                Back to results
              </button>
              <div style={styles.section}>
                <div style={styles.sectionTitle}>{selectedDbTitle}</div>
                {renderDatabaseTable(selectedDb)}
              </div>
            </>
          )}

          {!selectedPage && !selectedDb && !loading && filteredResults.length > 0 && (
            <div>
              {filteredResults.map((item) => (
                <div
                  key={item.id}
                  style={styles.card}
                  onClick={() =>
                    item.object === 'page' ? handleClickPage(item) : handleClickDatabase(item)
                  }
                  onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#58a6ff' }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#2a2a2e' }}
                >
                  <div style={styles.cardTitle}>
                    <span>{item.object === 'database' ? 'DB' : 'Page'}</span>
                    <span>{item.title || 'Untitled'}</span>
                  </div>
                  <div style={styles.cardMeta}>
                    {item.object} {item.lastEditedTime ? `| ${new Date(item.lastEditedTime).toLocaleDateString()}` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!selectedPage && !selectedDb && !loading && filteredResults.length === 0 && searchQuery && (
            <div style={styles.empty}>No results found. Try a different search term.</div>
          )}

          {loading && <div style={styles.loading}>Loading...</div>}
        </>
      )}

      {/* Tab: Databases */}
      {activeTab === 'databases' && (
        <>
          <div style={styles.searchBar}>
            <input
              style={{ ...styles.input, flex: 1 }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search databases..."
            />
            <button style={styles.btn('primary')} onClick={() => handleSearch()} disabled={loading}>
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {selectedDb && (
            <>
              <button style={styles.backBtn} onClick={() => setSelectedDb(null)}>
                Back to results
              </button>
              <div style={styles.section}>
                <div style={styles.sectionTitle}>{selectedDbTitle}</div>
                {renderDatabaseTable(selectedDb)}
              </div>
            </>
          )}

          {!selectedDb && !loading && filteredResults.length > 0 && (
            <div>
              {filteredResults.map((item) => (
                <div
                  key={item.id}
                  style={styles.card}
                  onClick={() => handleClickDatabase(item)}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#58a6ff' }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = '#2a2a2e' }}
                >
                  <div style={styles.cardTitle}>
                    <span>DB</span>
                    <span>{item.title || 'Untitled'}</span>
                  </div>
                  <div style={styles.cardMeta}>
                    database {item.lastEditedTime ? `| ${new Date(item.lastEditedTime).toLocaleDateString()}` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}

          {!selectedDb && !loading && filteredResults.length === 0 && searchQuery && (
            <div style={styles.empty}>No databases found. Try a different search term.</div>
          )}

          {!selectedDb && !loading && !searchQuery && (
            <div style={styles.empty}>Search for databases in your Notion workspace</div>
          )}

          {loading && <div style={styles.loading}>Loading...</div>}
        </>
      )}
    </div>
  )
}

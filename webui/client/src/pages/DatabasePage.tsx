import { useState, useEffect, useCallback } from 'react'

interface DatabaseInfo {
  name: string
  size: number
  modified: string
}

interface TableInfo {
  name: string
  rowCount: number
}

interface TableData {
  columns: string[]
  rows: Record<string, unknown>[]
}

interface QueryResult {
  results?: Record<string, unknown>[]
  columns?: string[]
  changes?: number
  lastInsertRowid?: number
}

const styles = {
  container: {
    display: 'flex',
    height: '100vh',
    background: '#0f0f10',
    color: '#e6e6e6',
    overflow: 'hidden',
  },
  leftPanel: {
    width: '250px',
    minWidth: '250px',
    background: '#151517',
    borderRight: '1px solid #2a2a2e',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  leftHeader: {
    padding: '16px',
    borderBottom: '1px solid #2a2a2e',
  },
  title: {
    fontSize: '16px',
    fontWeight: 700,
    marginBottom: '12px',
  },
  createRow: {
    display: 'flex',
    gap: '6px',
  },
  input: {
    flex: 1,
    padding: '6px 10px',
    background: '#0d0d0f',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#e6e6e6',
    fontSize: '13px',
    outline: 'none',
  },
  btnPrimary: {
    padding: '6px 12px',
    borderRadius: '6px',
    border: 'none',
    background: '#3b82f6',
    color: '#fff',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 500,
    whiteSpace: 'nowrap' as const,
  },
  btnSecondary: {
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #2a2a2e',
    background: '#1b1b1f',
    color: '#a1a1aa',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 500,
  },
  btnDanger: {
    padding: '4px 8px',
    borderRadius: '4px',
    border: 'none',
    background: 'transparent',
    color: '#ef4444',
    fontSize: '11px',
    cursor: 'pointer',
  },
  btnGreen: {
    padding: '6px 12px',
    borderRadius: '6px',
    border: 'none',
    background: '#22c55e',
    color: '#fff',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 500,
  },
  listSection: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '8px',
  },
  sectionLabel: {
    fontSize: '11px',
    fontWeight: 600,
    color: '#a1a1aa',
    textTransform: 'uppercase' as const,
    padding: '8px 8px 4px',
    letterSpacing: '0.5px',
  },
  dbItem: (selected: boolean) => ({
    padding: '8px 10px',
    borderRadius: '6px',
    background: selected ? '#222226' : 'transparent',
    cursor: 'pointer',
    marginBottom: '2px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    transition: 'background 0.15s',
  }),
  dbItemInfo: {
    flex: 1,
    minWidth: 0,
  },
  dbName: {
    fontSize: '13px',
    fontWeight: 500,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  dbMeta: {
    fontSize: '11px',
    color: '#a1a1aa',
    marginTop: '2px',
  },
  tableItem: (selected: boolean) => ({
    padding: '6px 10px 6px 18px',
    borderRadius: '6px',
    background: selected ? '#222226' : 'transparent',
    cursor: 'pointer',
    marginBottom: '1px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '13px',
    transition: 'background 0.15s',
  }),
  tableRowCount: {
    fontSize: '11px',
    color: '#a1a1aa',
  },
  rightPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  contentArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  },
  tableHeader: {
    padding: '16px 20px',
    borderBottom: '1px solid #2a2a2e',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  tableTitle: {
    fontSize: '16px',
    fontWeight: 600,
  },
  tableSubtitle: {
    fontSize: '12px',
    color: '#a1a1aa',
    marginTop: '2px',
  },
  actionBar: {
    display: 'flex',
    gap: '8px',
  },
  dataGrid: {
    flex: 1,
    overflow: 'auto',
    padding: '0 20px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '13px',
  },
  th: {
    background: '#1b1b1f',
    padding: '8px 12px',
    textAlign: 'left' as const,
    fontWeight: 600,
    fontSize: '12px',
    color: '#a1a1aa',
    borderBottom: '1px solid #2a2a2e',
    position: 'sticky' as const,
    top: 0,
    whiteSpace: 'nowrap' as const,
  },
  td: {
    padding: '6px 12px',
    borderBottom: '1px solid #1b1b1f',
    maxWidth: '300px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  },
  tr: {
    transition: 'background 0.1s',
  },
  sqlSection: {
    borderTop: '1px solid #2a2a2e',
    padding: '12px 20px',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '8px',
    minHeight: '180px',
  },
  sqlLabel: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#a1a1aa',
  },
  sqlTextarea: {
    width: '100%',
    minHeight: '80px',
    padding: '10px 12px',
    background: '#0d0d0f',
    border: '1px solid #2a2a2e',
    borderRadius: '6px',
    color: '#e6e6e6',
    fontSize: '13px',
    fontFamily: "'Fira Code', 'Consolas', monospace",
    outline: 'none',
    resize: 'vertical' as const,
    lineHeight: '1.5',
  },
  sqlActions: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
  },
  sqlError: {
    fontSize: '12px',
    color: '#ef4444',
    background: 'rgba(239,68,68,0.08)',
    padding: '8px 10px',
    borderRadius: '6px',
    fontFamily: "'Fira Code', 'Consolas', monospace",
  },
  sqlResultsWrapper: {
    maxHeight: '200px',
    overflow: 'auto',
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    color: '#a1a1aa',
    gap: '8px',
  },
  hint: {
    fontSize: '13px',
    color: '#a1a1aa',
    background: '#1b1b1f',
    padding: '12px 16px',
    borderRadius: '8px',
    margin: '20px',
    lineHeight: '1.6',
    fontFamily: "'Fira Code', 'Consolas', monospace",
  },
  loadingBar: {
    height: '2px',
    background: '#3b82f6',
    animation: 'pulse 1s infinite',
  },
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('zh-TW', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return dateStr
  }
}

function cellToString(value: unknown): string {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function DatabasePage() {
  const [databases, setDatabases] = useState<DatabaseInfo[]>([])
  const [selectedDb, setSelectedDb] = useState<string | null>(null)
  const [tables, setTables] = useState<TableInfo[]>([])
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [tableData, setTableData] = useState<TableData>({ columns: [], rows: [] })
  const [sqlInput, setSqlInput] = useState('')
  const [sqlResults, setSqlResults] = useState<Record<string, unknown>[] | null>(null)
  const [sqlColumns, setSqlColumns] = useState<string[]>([])
  const [sqlError, setSqlError] = useState<string | null>(null)
  const [sqlMessage, setSqlMessage] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingTables, setLoadingTables] = useState(false)
  const [loadingData, setLoadingData] = useState(false)
  const [newDbName, setNewDbName] = useState('')
  const [hoveredRow, setHoveredRow] = useState<number | null>(null)
  const [hoveredSqlRow, setHoveredSqlRow] = useState<number | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const fetchDatabases = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/databases')
      if (!res.ok) throw new Error('Failed to fetch databases')
      const data = await res.json()
      setDatabases(data.databases || [])
    } catch (err) {
      console.error('Failed to fetch databases:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchTables = useCallback(async (dbName: string) => {
    setLoadingTables(true)
    try {
      const res = await fetch(`/api/databases/${encodeURIComponent(dbName)}/tables`)
      if (!res.ok) throw new Error('Failed to fetch tables')
      const data = await res.json()
      setTables(data.tables || [])
    } catch (err) {
      console.error('Failed to fetch tables:', err)
      setTables([])
    } finally {
      setLoadingTables(false)
    }
  }, [])

  const fetchTableData = useCallback(async (dbName: string, tableName: string) => {
    setLoadingData(true)
    try {
      const res = await fetch(`/api/databases/${encodeURIComponent(dbName)}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql: `SELECT * FROM "${tableName}" LIMIT 100` }),
      })
      if (!res.ok) throw new Error('Failed to fetch table data')
      const data: QueryResult = await res.json()
      if (data.results && data.results.length > 0) {
        const cols = data.columns || Object.keys(data.results[0])
        setTableData({ columns: cols, rows: data.results })
      } else {
        const cols = data.columns || []
        setTableData({ columns: cols, rows: [] })
      }
    } catch (err) {
      console.error('Failed to fetch table data:', err)
      setTableData({ columns: [], rows: [] })
    } finally {
      setLoadingData(false)
    }
  }, [])

  useEffect(() => {
    fetchDatabases()
  }, [fetchDatabases])

  useEffect(() => {
    if (selectedDb) {
      fetchTables(selectedDb)
      setSelectedTable(null)
      setTableData({ columns: [], rows: [] })
      setSqlResults(null)
      setSqlError(null)
      setSqlMessage(null)
    }
  }, [selectedDb, fetchTables])

  useEffect(() => {
    if (selectedDb && selectedTable) {
      fetchTableData(selectedDb, selectedTable)
    }
  }, [selectedDb, selectedTable, fetchTableData])

  const handleCreateDb = async () => {
    const name = newDbName.trim()
    if (!name) return
    try {
      const res = await fetch('/api/databases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || 'Failed to create database')
      }
      setNewDbName('')
      await fetchDatabases()
      setSelectedDb(name.endsWith('.db') ? name : `${name}.db`)
    } catch (err) {
      console.error('Failed to create database:', err)
    }
  }

  const handleDeleteDb = async (dbName: string) => {
    if (deleteConfirm !== dbName) {
      setDeleteConfirm(dbName)
      return
    }
    try {
      const res = await fetch(`/api/databases/${encodeURIComponent(dbName)}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to delete database')
      if (selectedDb === dbName) {
        setSelectedDb(null)
        setTables([])
        setSelectedTable(null)
        setTableData({ columns: [], rows: [] })
      }
      setDeleteConfirm(null)
      await fetchDatabases()
    } catch (err) {
      console.error('Failed to delete database:', err)
    }
  }

  const handleExecuteSql = async () => {
    if (!selectedDb || !sqlInput.trim()) return
    setSqlError(null)
    setSqlResults(null)
    setSqlColumns([])
    setSqlMessage(null)
    setLoadingData(true)
    try {
      const res = await fetch(`/api/databases/${encodeURIComponent(selectedDb)}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql: sqlInput.trim() }),
      })
      const data: QueryResult = await res.json()
      if (!res.ok) {
        throw new Error((data as unknown as { error: string }).error || 'Query failed')
      }
      if (data.results) {
        const cols = data.columns || (data.results.length > 0 ? Object.keys(data.results[0]) : [])
        setSqlColumns(cols)
        setSqlResults(data.results)
      } else if (data.changes !== undefined) {
        setSqlMessage(`Query executed. ${data.changes} row(s) affected.${data.lastInsertRowid ? ` Last insert ID: ${data.lastInsertRowid}` : ''}`)
        // Refresh tables and data after mutation
        fetchTables(selectedDb)
        if (selectedTable) {
          fetchTableData(selectedDb, selectedTable)
        }
      } else {
        setSqlMessage('Query executed successfully.')
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setSqlError(message)
    } finally {
      setLoadingData(false)
    }
  }

  const handleExport = async (format: 'csv' | 'json') => {
    if (!selectedDb || !selectedTable) return
    try {
      const res = await fetch(`/api/databases/${encodeURIComponent(selectedDb)}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table: selectedTable, format }),
      })
      if (!res.ok) throw new Error('Export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedTable}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  const handleRefresh = () => {
    if (selectedDb && selectedTable) {
      fetchTableData(selectedDb, selectedTable)
    }
  }

  const renderDataTable = (
    columns: string[],
    rows: Record<string, unknown>[],
    hoveredIdx: number | null,
    setHovered: (idx: number | null) => void,
  ) => (
    <table style={styles.table}>
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={col} style={styles.th}>{col}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr
            key={i}
            style={{
              ...styles.tr,
              background: hoveredIdx === i ? '#222226' : 'transparent',
            }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
          >
            {columns.map((col) => (
              <td
                key={col}
                style={{
                  ...styles.td,
                  color: row[col] === null || row[col] === undefined ? '#a1a1aa' : '#e6e6e6',
                  fontStyle: row[col] === null || row[col] === undefined ? 'italic' : 'normal',
                }}
              >
                {cellToString(row[col])}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )

  return (
    <div style={styles.container}>
      {/* Left Panel */}
      <div style={styles.leftPanel}>
        <div style={styles.leftHeader}>
          <div style={styles.title}>資料庫管理</div>
          <div style={styles.createRow}>
            <input
              style={styles.input}
              placeholder="新建資料庫..."
              value={newDbName}
              onChange={(e) => setNewDbName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreateDb() }}
            />
            <button
              style={{
                ...styles.btnPrimary,
                opacity: newDbName.trim() ? 1 : 0.5,
              }}
              onClick={handleCreateDb}
              disabled={!newDbName.trim()}
            >
              建立
            </button>
          </div>
        </div>

        <div style={styles.listSection}>
          <div style={styles.sectionLabel}>資料庫</div>
          {loading && <div style={{ padding: '8px', fontSize: '12px', color: '#a1a1aa' }}>載入中...</div>}
          {!loading && databases.length === 0 && (
            <div style={{ padding: '8px', fontSize: '12px', color: '#a1a1aa' }}>尚無資料庫</div>
          )}
          {databases.map((db) => (
            <div
              key={db.name}
              style={styles.dbItem(selectedDb === db.name)}
              onClick={() => {
                setSelectedDb(db.name)
                setDeleteConfirm(null)
              }}
            >
              <div style={styles.dbItemInfo}>
                <div style={styles.dbName}>{db.name}</div>
                <div style={styles.dbMeta}>
                  {formatBytes(db.size)} &middot; {formatDate(db.modified)}
                </div>
              </div>
              <button
                style={{
                  ...styles.btnDanger,
                  fontWeight: deleteConfirm === db.name ? 700 : 400,
                }}
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteDb(db.name)
                }}
                title={deleteConfirm === db.name ? '再次點擊確認刪除' : '刪除'}
              >
                {deleteConfirm === db.name ? '確認?' : '刪除'}
              </button>
            </div>
          ))}

          {selectedDb && (
            <>
              <div style={{ ...styles.sectionLabel, marginTop: '12px' }}>表格</div>
              {loadingTables && (
                <div style={{ padding: '8px', fontSize: '12px', color: '#a1a1aa' }}>載入中...</div>
              )}
              {!loadingTables && tables.length === 0 && (
                <div style={{ padding: '8px', fontSize: '12px', color: '#a1a1aa' }}>無表格</div>
              )}
              {tables.map((t) => (
                <div
                  key={t.name}
                  style={styles.tableItem(selectedTable === t.name)}
                  onClick={() => setSelectedTable(t.name)}
                >
                  <span>{t.name}</span>
                  <span style={styles.tableRowCount}>{t.rowCount} 行</span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      {/* Right Panel */}
      <div style={styles.rightPanel}>
        {!selectedDb ? (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '36px', opacity: 0.3 }}>&#128451;</div>
            <div style={{ fontSize: '14px' }}>選擇或建立一個資料庫開始使用</div>
          </div>
        ) : (
          <div style={styles.contentArea}>
            {selectedTable ? (
              <>
                {/* Table Header */}
                <div style={styles.tableHeader}>
                  <div>
                    <div style={styles.tableTitle}>{selectedTable}</div>
                    <div style={styles.tableSubtitle}>
                      {tableData.rows.length} 行 &middot; {tableData.columns.length} 列
                      {tableData.rows.length >= 100 && ' (顯示前 100 筆)'}
                    </div>
                  </div>
                  <div style={styles.actionBar}>
                    <button style={styles.btnSecondary} onClick={() => handleExport('csv')}>
                      匯出 CSV
                    </button>
                    <button style={styles.btnSecondary} onClick={() => handleExport('json')}>
                      匯出 JSON
                    </button>
                    <button style={styles.btnSecondary} onClick={handleRefresh}>
                      重新整理
                    </button>
                  </div>
                </div>

                {/* Data Grid */}
                <div style={styles.dataGrid}>
                  {loadingData && !sqlResults ? (
                    <div style={{ padding: '20px', color: '#a1a1aa', fontSize: '13px' }}>載入中...</div>
                  ) : tableData.columns.length > 0 ? (
                    renderDataTable(tableData.columns, tableData.rows, hoveredRow, setHoveredRow)
                  ) : (
                    <div style={{ padding: '20px', color: '#a1a1aa', fontSize: '13px' }}>此表格無資料</div>
                  )}
                </div>
              </>
            ) : (
              <div style={styles.contentArea}>
                {tables.length === 0 && !loadingTables ? (
                  <div style={styles.hint}>
                    使用下方 SQL 控制台創建表格，例如：
                    <br />
                    CREATE TABLE expenses (id INTEGER PRIMARY KEY, date TEXT, amount REAL, category TEXT)
                  </div>
                ) : (
                  <div style={styles.emptyState}>
                    <div style={{ fontSize: '14px' }}>選擇一個表格查看資料</div>
                  </div>
                )}
              </div>
            )}

            {/* SQL Console */}
            <div style={styles.sqlSection}>
              <div style={styles.sqlLabel}>SQL 控制台</div>
              <textarea
                style={styles.sqlTextarea}
                placeholder="輸入 SQL 語句..."
                value={sqlInput}
                onChange={(e) => setSqlInput(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    handleExecuteSql()
                  }
                }}
              />
              <div style={styles.sqlActions}>
                <button
                  style={{
                    ...styles.btnPrimary,
                    opacity: sqlInput.trim() ? 1 : 0.5,
                  }}
                  onClick={handleExecuteSql}
                  disabled={!sqlInput.trim() || loadingData}
                >
                  {loadingData ? '執行中...' : '執行 (Ctrl+Enter)'}
                </button>
                {sqlMessage && (
                  <span style={{ fontSize: '12px', color: '#22c55e' }}>{sqlMessage}</span>
                )}
              </div>

              {sqlError && <div style={styles.sqlError}>{sqlError}</div>}

              {sqlResults && sqlResults.length > 0 && (
                <div style={styles.sqlResultsWrapper}>
                  {renderDataTable(sqlColumns, sqlResults, hoveredSqlRow, setHoveredSqlRow)}
                </div>
              )}

              {sqlResults && sqlResults.length === 0 && (
                <div style={{ fontSize: '12px', color: '#a1a1aa' }}>查詢完成，無結果返回。</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

interface SearchResult {
  session_id: string
  title: string
  snippet: string
  matched_at: string
}

const C = {
  bg: '#0f0f10',
  surface: '#151517',
  border: '#2a2a2e',
  text: '#e6e6e6',
  textSecondary: '#a1a1aa',
  textMuted: '#71717a',
  accent: '#f97316',
  bgHover: '#1b1b1f',
}

export default function SearchPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  const performSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([])
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`/api/history/search?q=${encodeURIComponent(q)}&limit=50`)
      const data = await res.json()
      setResults(data.results || [])
    } catch (err) {
      console.error('Search failed:', err)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const debounce = setTimeout(() => {
      performSearch(query)
    }, 300)
    return () => clearTimeout(debounce)
  }, [query, performSearch])

  return (
    <div style={{ minHeight: '100vh', background: C.bg, color: C.text, padding: '40px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '24px' }}>搜索歷史</h1>

      <div style={{ marginBottom: '24px' }}>
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="輸入關鍵詞搜索對話內容..."
          style={{
            width: '100%',
            maxWidth: '560px',
            padding: '10px 16px',
            borderRadius: '10px',
            border: `1px solid ${C.border}`,
            background: C.surface,
            color: C.text,
            fontSize: '15px',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {loading ? (
        <div style={{ color: C.textMuted }}>搜尋中...</div>
      ) : query.trim() && results.length === 0 ? (
        <div style={{ color: C.textMuted }}>沒有找到匹配的結果</div>
      ) : !query.trim() ? (
        <div style={{ color: C.textMuted }}>輸入關鍵詞開始搜索</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '560px' }}>
          {results.map((r) => {
            const hovered = hoveredId === r.session_id
            return (
              <div
                key={r.session_id}
                onClick={() => navigate(`/chat/${r.session_id}`)}
                onMouseEnter={() => setHoveredId(r.session_id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{
                  padding: '12px 16px',
                  borderRadius: '10px',
                  border: `1px solid ${C.border}`,
                  background: hovered ? C.bgHover : C.surface,
                  cursor: 'pointer',
                  transition: 'background 0.12s ease',
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 500, color: C.text, marginBottom: '4px' }}>
                  {r.title || `Chat ${r.session_id.slice(0, 8)}...`}
                </div>
                <div style={{ fontSize: '12px', color: C.textSecondary, marginBottom: '4px', lineHeight: 1.4 }}>
                  {r.snippet}
                </div>
                <div style={{ fontSize: '11px', color: C.textMuted }}>
                  {r.matched_at ? new Date(r.matched_at).toLocaleString() : r.session_id}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

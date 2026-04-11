import { useState, useEffect } from 'react'

interface FeatureItem {
  name: string
  description: string
  status: 'done' | 'pending'
  category: string
  tools?: string[]
  routes?: string[]
}

const features: FeatureItem[] = [
  // ── Completed ──
  { name: '多模型 AI 聊天', description: '支持 Anthropic / DeepSeek / MiniMax / OpenAI / Ollama 等多供應商', status: 'done', category: '核心功能', tools: ['所有 tool 均可用'] },
  { name: 'Agentic Loop (自主代理)', description: 'AI 自主規劃 → 執行工具 → 驗證 → 自我修正，最多 25 輪迭代', status: 'done', category: '核心功能' },
  { name: 'Shell 執行', description: '執行 PowerShell / Bash / CMD 命令，支持超時、abort、權限控制', status: 'done', category: '工具', tools: ['shell'] },
  { name: '文件操作', description: '讀取、寫入、編輯文件，支持行號、偏移、replace_all', status: 'done', category: '工具', tools: ['file_read', 'file_write', 'file_edit'] },
  { name: '代碼搜索', description: 'Glob 文件搜索 + Grep 內容搜索', status: 'done', category: '工具', tools: ['glob', 'grep'] },
  { name: '網頁獲取/搜索', description: 'Fetch URL 內容 + DuckDuckGo 搜索', status: 'done', category: '工具', tools: ['web_fetch', 'web_search'] },
  { name: '權限系統', description: '高風險工具需授權，支持「始終允許」和「允許所有」模式', status: 'done', category: '核心功能' },
  { name: 'TODO 任務追蹤', description: 'AI 可創建/更新/列出結構化任務清單，每個 session 獨立', status: 'done', category: '功能', tools: ['todo_write'], routes: ['/api/tools'] },
  { name: 'Skills 技能系統', description: '7 個內建技能 (commit, review-pr, debug, simplify, explain, refactor, test)，觸發式自動匹配', status: 'done', category: '功能', routes: ['/api/skills'] },
  { name: 'Plan 模式', description: '只讀探索模式 — AI 只能讀取和搜索，不能修改文件', status: 'done', category: '功能', tools: ['enter_plan_mode', 'exit_plan_mode'] },
  { name: 'Context 壓縮', description: '對話超過 40 條時自動壓縮，保留最近 10 條 + 摘要', status: 'done', category: '核心功能' },
  { name: 'Session 持久化', description: '對話自動保存至 ~/.claude/sessions/，支持列出/載入/刪除', status: 'done', category: '功能', routes: ['/api/sessions'] },
  { name: 'Memory 記憶系統', description: '跨 session 的持久記憶，支持分類(user/project/reference)、搜索', status: 'done', category: '功能', tools: ['memory_write', 'memory_read'], routes: ['/api/memory'] },
  { name: '多 Agent 子進程', description: '主 AI 可生成子 Agent (explore/plan/general/verify)，獨立或後台運行', status: 'done', category: '功能', tools: ['agent_spawn', 'agent_status'] },
  { name: 'Notion 完整整合', description: '搜索/讀寫頁面/查詢數據庫/管理 blocks/評論，完全控制 Notion', status: 'done', category: '整合', tools: ['notion_search', 'notion_read_page', 'notion_write_page', 'notion_database', 'notion_block'], routes: ['/api/notion/*'] },
  { name: '終端頁面', description: 'WebUI 內建終端，支持命令歷史、多 shell 切換', status: 'done', category: 'UI' },
  { name: '代碼編輯器', description: 'Monaco Editor 整合', status: 'done', category: 'UI' },
  { name: '<think> 標籤解析', description: 'MiniMax 等模型的思考過程自動解析為可展開的「思考過程」區塊', status: 'done', category: '核心功能' },

  // ── Pending ──
  { name: 'Hooks 系統', description: '工具執行前後的自訂鉤子 (pre/post tool hooks)', status: 'pending', category: '進階功能' },
  { name: 'Git Worktree', description: '隔離的 git 工作樹，安全地並行修改代碼', status: 'pending', category: '進階功能' },
  { name: 'Jupyter Notebook 支持', description: '讀取/編輯 .ipynb 文件的 cell', status: 'pending', category: '工具' },
  { name: 'LSP 語言伺服器', description: '代碼智能提示、符號查找、格式化', status: 'pending', category: '進階功能' },
  { name: 'Cron 排程任務', description: '定時執行任務 (cron 表達式)', status: 'pending', category: '進階功能' },
  { name: '語音輸入/輸出', description: 'Voice mode — 語音與 AI 對話', status: 'pending', category: '進階功能' },
  { name: 'Plugin 插件系統', description: '第三方插件載入和管理', status: 'pending', category: '進階功能' },
  { name: 'MCP 協議', description: '連接外部 MCP 伺服器擴展工具能力', status: 'pending', category: '進階功能' },
  { name: '團隊記憶同步', description: '跨團隊共享知識庫', status: 'pending', category: '進階功能' },
  { name: 'Teleport 遠端執行', description: '跳轉到遠端機器執行任務', status: 'pending', category: '進階功能' },
  { name: 'Memory / Skills / Notion UI', description: '記憶管理頁面、技能管理頁面、Notion 瀏覽器', status: 'pending', category: 'UI' },
]

const styles = {
  container: { padding: '24px 32px', maxWidth: '1000px', margin: '0 auto' },
  header: { marginBottom: '24px' },
  title: { fontSize: '22px', fontWeight: 700, marginBottom: '8px' },
  subtitle: { fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 },
  stats: {
    display: 'flex', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' as const,
  },
  statCard: (color: string) => ({
    padding: '12px 20px', borderRadius: '10px', background: 'var(--bg-tertiary)',
    border: `1px solid ${color}33`, minWidth: '140px',
  }),
  statNumber: (color: string) => ({ fontSize: '28px', fontWeight: 700, color }),
  statLabel: { fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' },
  filterBar: {
    display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' as const,
  },
  filterChip: (active: boolean) => ({
    padding: '5px 14px', borderRadius: '16px', fontSize: '12px', fontWeight: 600,
    cursor: 'pointer', border: '1px solid var(--border-default)',
    background: active ? 'var(--accent-blue)' : 'var(--bg-tertiary)',
    color: active ? '#fff' : 'var(--text-secondary)',
    transition: 'all 0.15s',
  }),
  section: { marginBottom: '28px' },
  sectionTitle: { fontSize: '16px', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' },
  card: {
    padding: '14px 16px', borderRadius: '8px', background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)', marginBottom: '8px',
    display: 'flex', gap: '12px', alignItems: 'flex-start',
  },
  statusDot: (done: boolean) => ({
    width: '10px', height: '10px', borderRadius: '50%', marginTop: '5px', flexShrink: 0,
    background: done ? 'var(--accent-green)' : 'var(--text-muted)',
  }),
  cardContent: { flex: 1 },
  cardName: { fontSize: '14px', fontWeight: 600, marginBottom: '4px' },
  cardDesc: { fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 },
  tags: { display: 'flex', gap: '4px', flexWrap: 'wrap' as const, marginTop: '6px' },
  tag: (color: string) => ({
    padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 500,
    background: `${color}20`, color, fontFamily: 'monospace',
  }),
  categoryBadge: {
    padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
    background: 'var(--bg-hover)', color: 'var(--text-muted)',
  },
}

export default function RoadmapPage() {
  const [filter, setFilter] = useState<'all' | 'done' | 'pending'>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [toolCount, setToolCount] = useState(0)

  useEffect(() => {
    fetch('/api/tools').then(r => r.json()).then(d => setToolCount(d.tools?.length || 0)).catch(() => {})
  }, [])

  const done = features.filter(f => f.status === 'done')
  const pending = features.filter(f => f.status === 'pending')
  const categories = ['all', ...new Set(features.map(f => f.category))]

  const filtered = features.filter(f => {
    if (filter === 'done' && f.status !== 'done') return false
    if (filter === 'pending' && f.status !== 'pending') return false
    if (categoryFilter !== 'all' && f.category !== categoryFilter) return false
    return true
  })

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.title}>開發路線圖</div>
        <div style={styles.subtitle}>
          AI Code Assistant 功能追蹤 — 已完成和計劃中的功能一覽
        </div>
      </div>

      <div style={styles.stats}>
        <div style={styles.statCard('var(--accent-green)')}>
          <div style={styles.statNumber('var(--accent-green)')}>{done.length}</div>
          <div style={styles.statLabel}>已完成功能</div>
        </div>
        <div style={styles.statCard('var(--accent-orange)')}>
          <div style={styles.statNumber('var(--accent-orange)')}>{pending.length}</div>
          <div style={styles.statLabel}>計劃中功能</div>
        </div>
        <div style={styles.statCard('var(--accent-blue)')}>
          <div style={styles.statNumber('var(--accent-blue)')}>{toolCount}</div>
          <div style={styles.statLabel}>可用 Tools</div>
        </div>
        <div style={styles.statCard('var(--accent-purple)')}>
          <div style={styles.statNumber('var(--accent-purple)')}>7</div>
          <div style={styles.statLabel}>內建 Skills</div>
        </div>
      </div>

      <div style={styles.filterBar}>
        {(['all', 'done', 'pending'] as const).map(f => (
          <span key={f} style={styles.filterChip(filter === f)} onClick={() => setFilter(f)}>
            {f === 'all' ? '全部' : f === 'done' ? '已完成' : '計劃中'}
          </span>
        ))}
        <span style={{ width: '1px', background: 'var(--border-default)', margin: '0 4px' }} />
        {categories.map(c => (
          <span key={c} style={styles.filterChip(categoryFilter === c)} onClick={() => setCategoryFilter(c)}>
            {c === 'all' ? '所有分類' : c}
          </span>
        ))}
      </div>

      {filtered.filter(f => f.status === 'done').length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <span style={{ color: 'var(--accent-green)' }}>✅</span>
            <span>已完成 ({filtered.filter(f => f.status === 'done').length})</span>
          </div>
          {filtered.filter(f => f.status === 'done').map((f, i) => (
            <div key={i} style={styles.card}>
              <div style={styles.statusDot(true)} />
              <div style={styles.cardContent}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={styles.cardName}>{f.name}</div>
                  <span style={styles.categoryBadge}>{f.category}</span>
                </div>
                <div style={styles.cardDesc}>{f.description}</div>
                <div style={styles.tags}>
                  {f.tools?.map(t => (
                    <span key={t} style={styles.tag('var(--accent-blue)')}>{t}</span>
                  ))}
                  {f.routes?.map(r => (
                    <span key={r} style={styles.tag('var(--accent-purple)')}>{r}</span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {filtered.filter(f => f.status === 'pending').length > 0 && (
        <div style={styles.section}>
          <div style={styles.sectionTitle}>
            <span style={{ color: 'var(--accent-orange)' }}>🔜</span>
            <span>計劃中 ({filtered.filter(f => f.status === 'pending').length})</span>
          </div>
          {filtered.filter(f => f.status === 'pending').map((f, i) => (
            <div key={i} style={styles.card}>
              <div style={styles.statusDot(false)} />
              <div style={styles.cardContent}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={styles.cardName}>{f.name}</div>
                  <span style={styles.categoryBadge}>{f.category}</span>
                </div>
                <div style={styles.cardDesc}>{f.description}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

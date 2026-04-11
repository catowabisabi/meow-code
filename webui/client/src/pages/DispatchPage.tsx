const C = {
  bg: '#0f0f10',
  surface: '#151517',
  border: '#2a2a2e',
  text: '#e6e6e6',
  textSecondary: '#a1a1aa',
  textMuted: '#71717a',
}

export default function DispatchPage() {
  return (
    <div style={{ minHeight: '100vh', background: C.bg, color: C.text, padding: '40px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>任務派發</h1>
      <p style={{ color: C.textMuted, fontSize: '14px', marginBottom: '32px' }}>
        派發任務給多個 AI Agent
      </p>

      {/* Placeholder card */}
      <div
        style={{
          maxWidth: '600px',
          padding: '32px',
          borderRadius: '16px',
          border: `1px solid ${C.border}`,
          background: C.surface,
        }}
      >
        <div style={{ fontSize: '40px', marginBottom: '16px' }}>📤</div>
        <div style={{ fontSize: '18px', fontWeight: 600, marginBottom: '12px', color: C.text }}>
          多 Agent 任務派發
        </div>
        <div style={{ fontSize: '14px', color: C.textSecondary, lineHeight: 1.7, marginBottom: '24px' }}>
          此功能允許您同時向多個 AI Agent 派發任務，協調複雜的工作流程。
          每個 Agent 可以並行處理不同的子任務，最終匯總結果。
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '12px',
          }}
        >
          {[
            { icon: '🤖', label: 'Chat Agent', desc: '對話式任務處理' },
            { icon: '🛠️', label: 'Code Agent', desc: '代碼生成與審查' },
            { icon: '🔍', label: 'Search Agent', desc: '信息搜索與整合' },
            { icon: '📊', label: 'Analysis Agent', desc: '數據分析與報告' },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                padding: '16px',
                borderRadius: '10px',
                border: `1px solid ${C.border}`,
                background: '#1b1b1f',
                opacity: 0.6,
              }}
            >
              <div style={{ fontSize: '20px', marginBottom: '6px' }}>{item.icon}</div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: C.text }}>{item.label}</div>
              <div style={{ fontSize: '12px', color: C.textMuted, marginTop: '2px' }}>{item.desc}</div>
            </div>
          ))}
        </div>

        <div
          style={{
            marginTop: '24px',
            padding: '12px 16px',
            borderRadius: '8px',
            background: 'rgba(249,115,22,0.08)',
            border: '1px solid rgba(249,115,22,0.2)',
            fontSize: '13px',
            color: '#f97316',
          }}
        >
          即將推出 — 敬請期待
        </div>
      </div>
    </div>
  )
}

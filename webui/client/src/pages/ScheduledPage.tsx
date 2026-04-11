import { useState, useEffect } from 'react'

interface ScheduledTask {
  id: string
  name: string
  cron?: string
  prompt?: string
  createdAt?: string
}

const C = {
  bg: '#0f0f10',
  surface: '#151517',
  border: '#2a2a2e',
  text: '#e6e6e6',
  textSecondary: '#a1a1aa',
  textMuted: '#71717a',
}

export default function ScheduledPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])

  useEffect(() => {
    try {
      const raw = localStorage.getItem('scheduled_tasks')
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed)) setTasks(parsed)
      }
    } catch {
      setTasks([])
    }
  }, [])

  return (
    <div style={{ minHeight: '100vh', background: C.bg, color: C.text, padding: '40px' }}>
      <h1 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '8px' }}>排程任務</h1>
      <p style={{ color: C.textMuted, fontSize: '14px', marginBottom: '32px' }}>
        排程任務功能即將推出
      </p>

      {/* Placeholder banner */}
      <div
        style={{
          maxWidth: '560px',
          padding: '20px 24px',
          borderRadius: '12px',
          border: `1px solid ${C.border}`,
          background: C.surface,
          marginBottom: '32px',
        }}
      >
        <div style={{ fontSize: '32px', marginBottom: '12px' }}>📅</div>
        <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: C.text }}>
          排程任務即將推出
        </div>
        <div style={{ fontSize: '14px', color: C.textSecondary, lineHeight: 1.6 }}>
          您將能夠設置定期執行的 AI 任務，例如每日摘要、自動報告生成等。
        </div>
      </div>

      {/* Saved tasks from localStorage */}
      {tasks.length > 0 && (
        <>
          <h2 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: C.textSecondary }}>
            已保存的任務
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '560px' }}>
            {tasks.map((task) => (
              <div
                key={task.id}
                style={{
                  padding: '12px 16px',
                  borderRadius: '10px',
                  border: `1px solid ${C.border}`,
                  background: C.surface,
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: 500, color: C.text, marginBottom: '4px' }}>
                  {task.name || task.id}
                </div>
                {task.cron && (
                  <div style={{ fontSize: '12px', color: C.textMuted }}>
                    Cron: <code style={{ color: C.textSecondary }}>{task.cron}</code>
                  </div>
                )}
                {task.prompt && (
                  <div
                    style={{
                      fontSize: '12px',
                      color: C.textMuted,
                      marginTop: '4px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {task.prompt}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

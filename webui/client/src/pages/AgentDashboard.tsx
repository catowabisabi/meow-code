import { useState, useEffect, useCallback } from 'react'
import { EmptyState, Card, LoadingSpinner } from '../components/shared/UI'
import { toast } from '../components/shared/Toast'

interface Agent {
  id: string
  name: string
  type: 'explore' | 'plan' | 'general' | 'verify'
  status: 'running' | 'completed' | 'error'
  createdAt: number
  result?: string
  error?: string
  parentSessionId?: string
}

const typeConfig = {
  explore: { label: '探索者', icon: '🔍', color: '#3b82f6' },
  plan: { label: '規劃者', icon: '📋', color: '#f97316' },
  general: { label: '通用', icon: '⚡', color: '#22c55e' },
  verify: { label: '驗證者', icon: '✓', color: '#a855f7' },
}

const statusConfig = {
  running: { label: '運行中', color: '#22c55e', bg: 'rgba(34, 197, 94, 0.15)' },
  completed: { label: '已完成', color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.15)' },
  error: { label: '錯誤', color: '#f85149', bg: 'rgba(248, 81, 73, 0.15)' },
}

function AgentCard({ agent, onView }: { agent: Agent; onView: () => void }) {
  const type = typeConfig[agent.type]
  const status = statusConfig[agent.status]

  return (
    <Card hoverable onClick={onView}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: `${type.color}20`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
            }}
          >
            {type.icon}
          </div>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: '#e6e6e6' }}>
              {agent.name}
            </div>
            <div style={{ fontSize: '12px', color: '#71717a' }}>
              {type.label} · {new Date(agent.createdAt).toLocaleTimeString()}
            </div>
          </div>
        </div>
        <div
          style={{
            padding: '4px 10px',
            borderRadius: '12px',
            background: status.bg,
            border: `1px solid ${status.color}40`,
            color: status.color,
            fontSize: '11px',
            fontWeight: 500,
          }}
        >
          {agent.status === 'running' && <LoadingSpinner size={10} />} {status.label}
        </div>
      </div>

      {agent.status === 'running' && (
        <div style={{ marginTop: '12px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12px',
              color: '#a1a1aa',
            }}
          >
            <LoadingSpinner size={12} />
            <span>正在處理任務...</span>
          </div>
          <div
            style={{
              marginTop: '8px',
              height: '4px',
              background: '#2a2a2e',
              borderRadius: '2px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: '60%',
                height: '100%',
                background: `linear-gradient(90deg, ${type.color}, ${type.color}80)`,
                borderRadius: '2px',
                animation: 'pulse 1.5s ease-in-out infinite',
              }}
            />
          </div>
        </div>
      )}

      {(agent.result || agent.error) && (
        <div
          style={{
            marginTop: '12px',
            padding: '10px',
            background: '#151517',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#9ca3af',
            maxHeight: '100px',
            overflow: 'auto',
            whiteSpace: 'pre-wrap' as const,
          }}
        >
          {agent.error ? (
            <span style={{ color: '#f85149' }}>{agent.error}</span>
          ) : (
            agent.result
          )}
        </div>
      )}
    </Card>
  )
}

function AgentDetailModal({ agent, onClose }: { agent: Agent; onClose: () => void }) {
  const type = typeConfig[agent.type]
  const status = statusConfig[agent.status]

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#1b1b1f',
          border: '1px solid #2a2a2e',
          borderRadius: '12px',
          padding: '24px',
          width: '600px',
          maxWidth: '90vw',
          maxHeight: '80vh',
          overflow: 'auto',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '12px',
                background: `${type.color}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px',
              }}
            >
              {type.icon}
            </div>
            <div>
              <h2 style={{ fontSize: '20px', fontWeight: 600, color: '#e6e6e6', margin: 0 }}>
                {agent.name}
              </h2>
              <div style={{ fontSize: '13px', color: '#71717a' }}>
                {type.label} · {new Date(agent.createdAt).toLocaleString()}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#71717a',
              fontSize: '20px',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>

        <div
          style={{
            padding: '12px',
            borderRadius: '8px',
            background: status.bg,
            border: `1px solid ${status.color}40`,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '16px',
          }}
        >
          {agent.status === 'running' && <LoadingSpinner size={14} />}
          <span style={{ color: status.color, fontWeight: 500 }}>
            {status.label}
          </span>
        </div>

        {agent.status === 'running' && (
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '13px', color: '#a1a1aa', marginBottom: '8px' }}>
              任務進度
            </div>
            <div
              style={{
                height: '8px',
                background: '#2a2a2e',
                borderRadius: '4px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: '60%',
                  height: '100%',
                  background: `linear-gradient(90deg, ${type.color}, ${type.color}80)`,
                  borderRadius: '4px',
                  animation: 'pulse 1.5s ease-in-out infinite',
                }}
              />
            </div>
          </div>
        )}

        {(agent.result || agent.error) && (
          <div>
            <div style={{ fontSize: '13px', color: '#a1a1aa', marginBottom: '8px' }}>
              交付結果
            </div>
            <div
              style={{
                padding: '12px',
                background: '#0f0f10',
                borderRadius: '8px',
                fontSize: '13px',
                color: agent.error ? '#f85149' : '#9ca3af',
                whiteSpace: 'pre-wrap' as const,
                maxHeight: '300px',
                overflow: 'auto',
              }}
            >
              {agent.error || agent.result}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function AgentDashboard() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch('/api/agents')
      const data = await res.json()
      setAgents(data.agents || [])
    } catch (err) {
      toast.error('載入代理失敗', err instanceof Error ? err.message : undefined)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAgents()
    const interval = setInterval(fetchAgents, 2000)
    return () => clearInterval(interval)
  }, [fetchAgents])

  const runningAgents = agents.filter((a) => a.status === 'running')
  const completedAgents = agents.filter((a) => a.status !== 'running')

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1000px', margin: '0 auto' }}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#e6e6e6', marginBottom: '8px' }}>
          代理監控面板
        </h1>
        <p style={{ fontSize: '13px', color: '#71717a' }}>
          監控所有後台運行的代理，即時查看任務狀態和結果
        </p>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '60px' }}>
          <LoadingSpinner size={32} />
        </div>
      ) : agents.length === 0 ? (
        <EmptyState
          icon="🤖"
          title="暫無代理"
          description="創建新代理後，它們將在此處顯示狀態"
          action={{
            label: '創建代理',
            onClick: () => window.location.href = '/agents',
          }}
        />
      ) : (
        <>
          {runningAgents.length > 0 && (
            <div style={{ marginBottom: '32px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#e6e6e6', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#22c55e' }}>●</span>
                運行中的代理 ({runningAgents.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {runningAgents.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} onView={() => setSelectedAgent(agent)} />
                ))}
              </div>
            </div>
          )}

          {completedAgents.length > 0 && (
            <div>
              <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#e6e6e6', marginBottom: '16px' }}>
                已完成的代理 ({completedAgents.length})
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {completedAgents.map((agent) => (
                  <AgentCard key={agent.id} agent={agent} onView={() => setSelectedAgent(agent)} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {selectedAgent && (
        <AgentDetailModal agent={selectedAgent} onClose={() => setSelectedAgent(null)} />
      )}
    </div>
  )
}

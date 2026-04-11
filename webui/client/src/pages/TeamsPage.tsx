import { useState, useEffect } from 'react'

interface TeamMember {
  agentId: string
  name: string
  agentType?: string
  model?: string
  color?: string
  status: 'active' | 'inactive'
  joinedAt: number
}

interface Team {
  name: string
  description?: string
  leadAgentId: string
  members: TeamMember[]
}

const styles = {
  container: { padding: '24px 32px', maxWidth: '900px', margin: '0 auto' },
  title: { fontSize: '22px', fontWeight: 700, color: '#e6e6e6', marginBottom: '8px' },
  subtitle: { fontSize: '13px', color: '#a1a1aa', marginBottom: '24px' },
  section: { background: '#1b1b1f', border: '1px solid #2a2a2e', borderRadius: '12px', padding: '20px', marginBottom: '16px' },
  sectionTitle: { fontSize: '16px', fontWeight: 600, marginBottom: '14px', color: '#e6e6e6' },
  memberCard: { background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '8px', padding: '14px', marginBottom: '10px' },
  memberName: { fontSize: '14px', fontWeight: 600, color: '#e6e6e6', display: 'flex', alignItems: 'center', gap: '8px' },
  memberMeta: { fontSize: '12px', color: '#71717a', marginTop: '4px' },
  colorDot: (color: string) => ({ width: 10, height: 10, borderRadius: '50%', background: color || '#6366f1' }),
  statusBadge: (status: string) => ({
    padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: 500,
    background: status === 'active' ? 'rgba(34,197,94,0.12)' : 'rgba(113,113,122,0.1)',
    color: status === 'active' ? '#22c55e' : '#71717a',
    border: `1px solid ${status === 'active' ? 'rgba(34,197,94,0.3)' : 'rgba(113,113,122,0.2)'}`,
  }),
  leadBadge: { padding: '2px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 600, background: 'rgba(249,115,22,0.1)', color: '#f97316', border: '1px solid rgba(249,115,22,0.3)' },
  createBtn: { padding: '8px 16px', borderRadius: '8px', border: 'none', background: '#f97316', color: '#fff', fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit' },
  empty: { textAlign: 'center' as const, padding: '30px', color: '#71717a', fontSize: '13px' },
  infoBox: { background: '#0f0f10', border: '1px solid #2a2a2e', borderRadius: '8px', padding: '14px', fontSize: '13px', color: '#a1a1aa', lineHeight: 1.6 },
  emptyTeam: { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', padding: '40px', gap: '12px' },
}

const COLORS = ['#f97316', '#3b82f6', '#22c55e', '#a855f7', '#f85149', '#eab308', '#06b6d4', '#ec4899']

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null)

  useEffect(() => {
    const mockTeams: Team[] = [
      {
        name: 'dev-team',
        description: 'Development team for the main project',
        leadAgentId: 'agent-1',
        members: [
          { agentId: 'agent-1', name: 'coordinator', agentType: 'coordinator', status: 'active', joinedAt: Date.now() - 3600000, color: '#f97316' },
          { agentId: 'agent-2', name: 'frontend-dev', agentType: 'worker', status: 'active', joinedAt: Date.now() - 3000000, color: '#3b82f6' },
          { agentId: 'agent-3', name: 'backend-dev', agentType: 'worker', status: 'active', joinedAt: Date.now() - 2500000, color: '#22c55e' },
          { agentId: 'agent-4', name: 'tester', agentType: 'worker', status: 'inactive', joinedAt: Date.now() - 2000000, color: '#a855f7' },
        ],
      },
    ]
    setTeams(mockTeams)
    setSelectedTeam(mockTeams[0]?.name || null)
    setLoading(false)
  }, [])

  const currentTeam = teams.find((t) => t.name === selectedTeam)
  const lead = currentTeam?.members.find((m) => m.agentId === currentTeam.leadAgentId)

  return (
    <div style={styles.container}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={styles.title}>Teams</div>
        <button style={styles.createBtn}>+ Create Team</button>
      </div>
      <div style={styles.subtitle}>Manage multi-agent teams with coordinator/worker patterns.</div>

      {loading ? (
        <div style={styles.empty}>Loading teams...</div>
      ) : (
        <>
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Your Teams</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {teams.map((team) => (
                <button
                  key={team.name}
                  onClick={() => setSelectedTeam(team.name)}
                  style={{
                    padding: '8px 16px', borderRadius: '8px', border: `1px solid ${selectedTeam === team.name ? '#f97316' : '#2a2a2e'}`,
                    background: selectedTeam === team.name ? 'rgba(249,115,22,0.1)' : 'transparent',
                    color: selectedTeam === team.name ? '#f97316' : '#a1a1aa', fontSize: '13px', cursor: 'pointer', fontFamily: 'inherit',
                  }}
                >
                  {team.name} ({team.members.length})
                </button>
              ))}
              {teams.length === 0 && <div style={styles.empty}>No teams yet. Create one to get started.</div>}
            </div>
          </div>

          {currentTeam && (
            <div style={styles.section}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <div style={{ fontSize: '18px', fontWeight: 600, color: '#e6e6e6' }}>{currentTeam.name}</div>
                  {currentTeam.description && <div style={{ fontSize: '13px', color: '#71717a', marginTop: '4px' }}>{currentTeam.description}</div>}
                </div>
                <div style={styles.infoBox}>
                  <div style={{ color: '#e6e6e6', fontWeight: 500, marginBottom: '4px' }}>Coordinator Pattern</div>
                  <div>Coordinator assigns tasks to workers and synthesizes results.</div>
                </div>
              </div>

              <div style={styles.sectionTitle}>Members ({currentTeam.members.length})</div>
              {currentTeam.members.map((member) => (
                <div key={member.agentId} style={styles.memberCard}>
                  <div style={styles.memberName}>
                    <span style={styles.colorDot(member.color ?? '#6366f1')} />
                    <span>{member.name}</span>
                    {member.agentId === currentTeam.leadAgentId && <span style={styles.leadBadge}>Lead</span>}
                    <span style={styles.statusBadge(member.status)}>{member.status}</span>
                  </div>
                  <div style={styles.memberMeta}>
                    Type: {member.agentType || 'worker'} | Joined: {new Date(member.joinedAt).toLocaleTimeString()}
                  </div>
                </div>
              ))}

              {lead && (
                <div style={{ marginTop: '16px', padding: '12px', background: '#0f0f10', borderRadius: '8px', border: '1px solid #2a2a2e' }}>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: '#e6e6e6', marginBottom: '8px' }}>Coordinator ({lead.name})</div>
                  <div style={{ fontSize: '13px', color: '#a1a1aa', lineHeight: 1.5 }}>
                    The coordinator assigns tasks to workers, collects results, and synthesizes a final response.
                    Workers operate autonomously on their assigned tasks.
                  </div>
                </div>
              )}
            </div>
          )}

          <div style={styles.section}>
            <div style={styles.sectionTitle}>How Teams Work</div>
            <div style={styles.infoBox}>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>1. Coordinator</div>
                <div>The coordinator (lead) receives the main task and breaks it into subtasks for workers.</div>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>2. Workers</div>
                <div>Workers execute subtasks in parallel using available tools. Each worker can spawn sub-agents.</div>
              </div>
              <div>
                <div style={{ fontWeight: 600, color: '#e6e6e6', marginBottom: '4px' }}>3. Synthesis</div>
                <div>The coordinator collects worker results, resolves conflicts, and produces the final response.</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

import { create } from 'zustand'
import { wsManager } from '../api/client'
import type { AgentSummaryMessage } from '../api/endpoints'

interface AgentSummaryState {
  summaries: Record<string, string>
  statuses: Record<string, 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'unknown'>
  connections: Set<string>

  connectAgentSummary: (agentId: string) => void
  disconnectAgentSummary: (agentId: string) => void
  getSummary: (agentId: string) => string | undefined
  getStatus: (agentId: string) => 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'unknown'
  clearSummary: (agentId: string) => void
}

export const useAgentSummaryStore = create<AgentSummaryState>((set, get) => ({
  summaries: {},
  statuses: {},
  connections: new Set(),

  connectAgentSummary: (agentId) => {
    const handler = (msg: Record<string, unknown>) => {
      if (msg.type === 'agent_summary') {
        const summaryMsg = msg as unknown as AgentSummaryMessage
        set((state) => ({
          summaries: { ...state.summaries, [agentId]: summaryMsg.summary },
        }))
      }
    }

    const statusHandler = (status: 'connecting' | 'connected' | 'disconnected' | 'reconnecting') => {
      set((state) => ({
        statuses: { ...state.statuses, [agentId]: status },
      }))
    }

    wsManager.connectAgentSummary(agentId, handler)
    statusHandler('connecting')
  },

  disconnectAgentSummary: (agentId) => {
    wsManager.disconnectAgentSummary(agentId)
    set((state) => {
      const newSummaries = { ...state.summaries }
      const newStatuses = { ...state.statuses }
      const newConnections = new Set(state.connections)
      delete newSummaries[agentId]
      delete newStatuses[agentId]
      newConnections.delete(agentId)
      return { summaries: newSummaries, statuses: newStatuses, connections: newConnections }
    })
  },

  getSummary: (agentId) => get().summaries[agentId],

  getStatus: (agentId) => wsManager.getAgentSummaryStatus(agentId),

  clearSummary: (agentId) => {
    set((state) => {
      const newSummaries = { ...state.summaries }
      delete newSummaries[agentId]
      return { summaries: newSummaries }
    })
  },
}))

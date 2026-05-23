import { create } from 'zustand'

export interface CircuitStateEntry {
  timestamp: number
  from_state: string
  to_state: string
}

export interface ProviderHeartbeat {
  provider_id: string
  latency_samples: number[]
  circuit_state_history: CircuitStateEntry[]
  failure_timestamps: number[]
  custom_thresholds: {
    latency_ms: number
    failure_count: number
  }
}

export interface HeartbeatResponse {
  providers: ProviderHeartbeat[]
  server_time: number
}

interface ProviderHeartbeatState {
  heartbeatData: Record<string, ProviderHeartbeat>
  serverTime: number
  loading: boolean
  error: string | null
  lastFetched: number | null

  fetchHeartbeat: () => Promise<void>
}

export const useProviderHeartbeatStore = create<ProviderHeartbeatState>((set) => ({
  heartbeatData: {},
  serverTime: 0,
  loading: false,
  error: null,
  lastFetched: null,

  fetchHeartbeat: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/providers/heartbeat')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: HeartbeatResponse = await res.json()

      const heartbeatMap: Record<string, ProviderHeartbeat> = {}
      for (const provider of data.providers) {
        heartbeatMap[provider.provider_id] = provider
      }

      set({
        heartbeatData: heartbeatMap,
        serverTime: data.server_time,
        loading: false,
        lastFetched: Date.now(),
      })
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Failed to fetch heartbeat', loading: false })
    }
  },
}))
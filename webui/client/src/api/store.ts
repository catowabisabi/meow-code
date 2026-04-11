import { create } from 'zustand'
import {
  loadAPIConfig,
  saveAPIConfig,
  getActiveProfile,
  type ConnectionProfile,
  type APIConfig,
} from './config'

interface ConnectionState {
  activeProfile: ConnectionProfile
  profiles: Record<string, ConnectionProfile>
  wsStatus: Record<string, 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'unknown'>

  loadConfig: () => void
  addProfile: (profile: ConnectionProfile) => void
  updateProfile: (id: string, updates: Partial<ConnectionProfile>) => void
  removeProfile: (id: string) => void
  setActiveProfile: (id: string) => void
  setWsStatus: (id: string, status: ConnectionState['wsStatus'][string]) => void
  testConnection: (profile: ConnectionProfile) => Promise<{ ok: boolean; latencyMs?: number; error?: string }>
}

export const useConnectionStore = create<ConnectionState>((set, get) => ({
  activeProfile: getActiveProfile(),
  profiles: loadAPIConfig().profiles,
  wsStatus: {},

  loadConfig: () => {
    const config = loadAPIConfig()
    set({
      activeProfile: config.profiles[config.activeProfile] || getActiveProfile(),
      profiles: config.profiles,
    })
  },

  addProfile: (profile) => {
    const config = loadAPIConfig()
    config.profiles[profile.id] = profile
    saveAPIConfig(config)
    set({ profiles: config.profiles })
  },

  updateProfile: (id, updates) => {
    const config = loadAPIConfig()
    if (config.profiles[id]) {
      config.profiles[id] = { ...config.profiles[id], ...updates }
      saveAPIConfig(config)
      set({ profiles: config.profiles })
      
      if (id === config.activeProfile) {
        set({ activeProfile: config.profiles[id] })
      }
    }
  },

  removeProfile: (id) => {
    const config = loadAPIConfig()
    if (id !== 'local' && config.profiles[id]) {
      delete config.profiles[id]
      
      if (config.activeProfile === id) {
        config.activeProfile = 'local'
        saveAPIConfig(config)
        set({
          profiles: config.profiles,
          activeProfile: config.profiles.local,
        })
      } else {
        saveAPIConfig(config)
        set({ profiles: config.profiles })
      }
    }
  },

  setActiveProfile: (id) => {
    const config = loadAPIConfig()
    if (config.profiles[id]) {
      config.activeProfile = id
      saveAPIConfig(config)
      set({ activeProfile: config.profiles[id] })
    }
  },

  setWsStatus: (id, status) => {
    set((s) => ({ wsStatus: { ...s.wsStatus, [id]: status } }))
  },

  testConnection: async (profile) => {
    const start = Date.now()
    try {
      const url = profile.httpUrl
        ? `${profile.httpUrl.replace(/\/$/, '')}/api/health`
        : '/api/health'
      
      const response = await fetch(url, {
        method: 'GET',
        headers: profile.apiKey
          ? { Authorization: `Bearer ${profile.apiKey}` }
          : {},
        signal: AbortSignal.timeout(5000),
      })

      if (response.ok) {
        return { ok: true, latencyMs: Date.now() - start }
      }
      return { ok: false, error: `HTTP ${response.status}` }
    } catch (err) {
      return { ok: false, error: err instanceof Error ? err.message : 'Connection failed' }
    }
  },
}))

import { create } from 'zustand'
import { modelsAPI } from '../api'

export interface ProviderInfo {
  type: string
  displayName?: string
  baseUrl: string
  apiKey: string
  models: string[]
  enabled: boolean
  customHeaders?: Record<string, string>
}

export interface AvailableModel {
  providerId: string
  providerName: string
  model: string
  type: string
}

export interface HotkeyBinding {
  key: string
  model: string
  provider: string
}

interface ModelState {
  providers: Record<string, ProviderInfo>
  availableModels: AvailableModel[]
  hotkeys: HotkeyBinding[]
  defaultModel: string
  defaultProvider: string
  loading: boolean
  error: string | null

  fetchModels: () => Promise<void>
  addProvider: (id: string, config: Partial<ProviderInfo> & { type: string; baseUrl: string }) => Promise<void>
  updateProvider: (id: string, updates: Partial<ProviderInfo>) => Promise<void>
  removeProvider: (id: string) => Promise<void>
  testProvider: (id: string) => Promise<{ ok: boolean; error?: string; latencyMs?: number }>
  setDefault: (model: string, provider: string) => Promise<void>
  updateHotkeys: (hotkeys: HotkeyBinding[]) => Promise<void>
}

export const useModelStore = create<ModelState>((set) => ({
  providers: {},
  availableModels: [],
  hotkeys: [],
  defaultModel: '',
  defaultProvider: '',
  loading: false,
  error: null,

  fetchModels: async () => {
    set({ loading: true, error: null })
    try {
      const data = await modelsAPI.list()
      set({
        providers: data.providers,
        availableModels: data.availableModels,
        hotkeys: data.hotkeys,
        defaultModel: data.defaultModel,
        defaultProvider: data.defaultProvider,
        loading: false,
      })
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false })
    }
  },

  addProvider: async (id, config) => {
    const data = await modelsAPI.add(id, config)
    set({ providers: data.providers })
  },

  updateProvider: async (id, updates) => {
    const data = await modelsAPI.update(id, updates)
    set((s) => ({
      providers: { ...s.providers, [id]: data.provider },
    }))
  },

  removeProvider: async (id) => {
    const data = await modelsAPI.remove(id)
    set({ providers: data.providers })
  },

  testProvider: async (id) => {
    return modelsAPI.test(id)
  },

  setDefault: async (model, provider) => {
    await modelsAPI.setDefault(model, provider)
    set({ defaultModel: model, defaultProvider: provider })
  },

  updateHotkeys: async (hotkeys) => {
    await modelsAPI.updateHotkeys(hotkeys)
    set({ hotkeys })
  },
}))

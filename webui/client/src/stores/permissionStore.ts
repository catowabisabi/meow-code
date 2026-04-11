import { create } from 'zustand'
import { permissionsAPI, type PermissionRule, type PendingPermission } from '../api'

interface PermissionState {
  rules: PermissionRule[]
  pending: PendingPermission[]
  loading: boolean
  error: string | null

  fetchRules: () => Promise<void>
  fetchPending: () => Promise<void>
  createRule: (rule: Omit<PermissionRule, 'id' | 'created_at'>) => Promise<void>
  deleteRule: (ruleId: string) => Promise<void>
  approve: (permissionId: string) => Promise<void>
  deny: (permissionId: string) => Promise<void>
}

export const usePermissionStore = create<PermissionState>((set) => ({
  rules: [],
  pending: [],
  loading: false,
  error: null,

  fetchRules: async () => {
    set({ loading: true, error: null })
    try {
      const rules = await permissionsAPI.list()
      set({ rules, loading: false })
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false })
    }
  },

  fetchPending: async () => {
    set({ loading: true, error: null })
    try {
      const pending = await permissionsAPI.getPending()
      set({ pending, loading: false })
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err), loading: false })
    }
  },

  createRule: async (rule) => {
    try {
      const newRule = await permissionsAPI.create(rule)
      set((s) => ({ rules: [...s.rules, newRule] }))
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },

  deleteRule: async (ruleId) => {
    try {
      await permissionsAPI.delete(ruleId)
      set((s) => ({ rules: s.rules.filter((r) => r.id !== ruleId) }))
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },

  approve: async (permissionId) => {
    try {
      const updated = await permissionsAPI.approve(permissionId)
      set((s) => ({
        pending: s.pending.filter((p) => p.id !== permissionId),
      }))
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },

  deny: async (permissionId) => {
    try {
      const updated = await permissionsAPI.deny(permissionId)
      set((s) => ({
        pending: s.pending.filter((p) => p.id !== permissionId),
      }))
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err) })
    }
  },
}))
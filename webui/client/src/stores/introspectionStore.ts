import { create } from 'zustand'

export type AgentStatus = 'idle' | 'thinking' | 'tool-use' | 'error'

const CONTEXT_WINDOW = 200_000

export interface IntrospectionState {
  tokenBudgetUsed: number
  tokenBudgetTotal: number
  inputTokens: number
  outputTokens: number
  recursionDepth: number
  selfReflectionCount: number
  thinkingContent: string
  contextPressure: number
  status: AgentStatus
  lastActivity: number
  appendThinking: (text: string) => void
  setUsage: (inputTokens: number, outputTokens: number) => void
  incrementRecursion: () => void
  decrementRecursion: () => void
  incrementSelfReflection: () => void
  setStatus: (status: AgentStatus) => void
  setContextPressure: (pressure: number) => void
  reset: () => void
}

export const useIntrospectionStore = create<IntrospectionState>((set) => ({
  tokenBudgetUsed: 0,
  tokenBudgetTotal: CONTEXT_WINDOW,
  inputTokens: 0,
  outputTokens: 0,
  recursionDepth: 0,
  selfReflectionCount: 0,
  thinkingContent: '',
  contextPressure: 0,
  status: 'idle',
  lastActivity: Date.now(),

  appendThinking: (text) =>
    set((s) => ({
      thinkingContent: s.thinkingContent + text,
      lastActivity: Date.now(),
      status: s.status === 'idle' ? 'thinking' : s.status,
    })),

  setUsage: (input, output) =>
    set(() => {
      const total = input + output
      const contextPressure = Math.min(100, Math.round((total / CONTEXT_WINDOW) * 100))
      return { inputTokens: input, outputTokens: output, tokenBudgetUsed: total, contextPressure, lastActivity: Date.now() }
    }),

  incrementRecursion: () => set((s) => ({ recursionDepth: s.recursionDepth + 1, lastActivity: Date.now() })),
  decrementRecursion: () => set((s) => ({ recursionDepth: Math.max(0, s.recursionDepth - 1), lastActivity: Date.now() })),
  incrementSelfReflection: () => set((s) => ({ selfReflectionCount: s.selfReflectionCount + 1, lastActivity: Date.now() })),
  setStatus: (status) => set(() => ({ status, lastActivity: Date.now() })),
  setContextPressure: (pressure) => set(() => ({ contextPressure: Math.min(100, Math.max(0, pressure)) })),
  reset: () => set({ tokenBudgetUsed: 0, inputTokens: 0, outputTokens: 0, recursionDepth: 0, selfReflectionCount: 0, thinkingContent: '', contextPressure: 0, status: 'idle', lastActivity: Date.now() }),
}))
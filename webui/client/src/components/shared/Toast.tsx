import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'info' | 'loading'

export interface Toast {
  id: string
  type: ToastType
  message: string
  description?: string
  duration?: number
}

interface ToastState {
  toasts: Toast[]
  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
  updateToast: (id: string, updates: Partial<Toast>) => void
  clearAll: () => void
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],

  addToast: (toast) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`
    const newToast: Toast = { ...toast, id }
    
    set((state) => ({
      toasts: [...state.toasts, newToast],
    }))

    if (toast.type !== 'loading' && toast.duration !== 0) {
      const duration = toast.duration || (toast.type === 'error' ? 5000 : 3000)
      setTimeout(() => {
        get().removeToast(id)
      }, duration)
    }

    return id
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },

  updateToast: (id, updates) => {
    set((state) => ({
      toasts: state.toasts.map((t) =>
        t.id === id ? { ...t, ...updates } : t
      ),
    }))
  },

  clearAll: () => {
    set({ toasts: [] })
  },
}))

// Convenience functions
export const toast = {
  success: (message: string, description?: string) =>
    useToastStore.getState().addToast({ type: 'success', message, description }),
  
  error: (message: string, description?: string) =>
    useToastStore.getState().addToast({ type: 'error', message, description }),
  
  info: (message: string, description?: string) =>
    useToastStore.getState().addToast({ type: 'info', message, description }),
  
  loading: (message: string, description?: string) =>
    useToastStore.getState().addToast({ type: 'loading', message, description, duration: 0 }),
  
  dismiss: (id: string) =>
    useToastStore.getState().removeToast(id),
}

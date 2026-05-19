import { create } from 'zustand'

export type AppMode = 'chat' | 'cowork' | 'code'

interface LayoutState {
  mode: AppMode
  setMode: (mode: AppMode) => void

  /** Per-mode working folder for cowork/code modes */
  currentFolder: Record<AppMode, string | null>
  setCurrentFolder: (folder: string | null) => void
  getCurrentFolder: () => string | null

  /** Right panel visibility */
  rightPanelOpen: boolean
  toggleRightPanel: () => void
  setRightPanelOpen: (open: boolean) => void

  /** Left sidebar collapsed */
  sidebarCollapsed: boolean
  toggleSidebar: () => void

  /** User menu open */
  userMenuOpen: boolean
  setUserMenuOpen: (open: boolean) => void
}

export const useLayoutStore = create<LayoutState>((set, get) => ({
  mode: 'chat',
  setMode: (mode) => set({ mode, rightPanelOpen: mode !== 'chat' }),

  currentFolder: { chat: null, cowork: null, code: null },
  setCurrentFolder: (folder) => set((s) => ({
    currentFolder: { ...s.currentFolder, [s.mode]: folder },
  })),
  getCurrentFolder: () => get().currentFolder[get().mode],

  rightPanelOpen: false,
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),

  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  userMenuOpen: false,
  setUserMenuOpen: (open) => set({ userMenuOpen: open }),
}))

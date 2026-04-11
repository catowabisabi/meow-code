import { create } from 'zustand'

export type AppMode = 'chat' | 'cowork' | 'code'

interface LayoutState {
  mode: AppMode
  setMode: (mode: AppMode) => void

  /** Current working folder for cowork/code modes */
  currentFolder: string | null
  setCurrentFolder: (folder: string | null) => void

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

export const useLayoutStore = create<LayoutState>((set) => ({
  mode: 'chat',
  setMode: (mode) => set({ mode, rightPanelOpen: mode !== 'chat' }),

  currentFolder: null,
  setCurrentFolder: (folder) => set({ currentFolder: folder }),

  rightPanelOpen: false,
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),

  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  userMenuOpen: false,
  setUserMenuOpen: (open) => set({ userMenuOpen: open }),
}))

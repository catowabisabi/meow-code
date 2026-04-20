import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Sidebar from './components/shared/Sidebar.tsx'
import TopBar from './components/shared/TopBar.tsx'
import RightPanel from './components/shared/RightPanel.tsx'
import HotkeyManager from './components/shared/HotkeyManager.tsx'
import ChatPage from './pages/ChatPage.tsx'
import CoworkPage from './pages/CoworkPage.tsx'
import CodeModePage from './pages/CodeModePage.tsx'
import ModelsPage from './pages/ModelsPage.tsx'
import HistoryPage from './pages/HistoryPage.tsx'
import SettingsPage from './pages/SettingsPage.tsx'
import NotionPage from './pages/NotionPage.tsx'
import MemoryPage from './pages/MemoryPage.tsx'
import SkillsPage from './pages/SkillsPage.tsx'
import DatabasePage from './pages/DatabasePage.tsx'
import MCPPage from './pages/MCPPage.tsx'
import AgentsPage from './pages/AgentsPage.tsx'
import AgentDashboard from './pages/AgentDashboard.tsx'
import TeamsPage from './pages/TeamsPage.tsx'
import HooksPage from './pages/HooksPage.tsx'
import ConnectionsPage from './pages/ConnectionsPage.tsx'
import SearchPage from './pages/SearchPage.tsx'
import CustomizePage from './pages/CustomizePage.tsx'
import ToastContainer from './components/shared/ToastContainer.tsx'
import ApiSetupModal from './components/ApiSetupModal.tsx'
import { useLayoutStore } from './stores/layoutStore.ts'
import { useChatStore } from './stores/chatStore.ts'

const MAIN_MODES = ['/chat', '/cowork', '/code']

function GlobalWarningBanner() {
  const permissionMode = useChatStore((s) => s.permissionMode)
  const setPermissionMode = useChatStore((s) => s.setPermissionMode)

  if (permissionMode !== 'always-allow') return null

  return (
    <div
      style={{
        background: '#dc2626',
        color: '#fff',
        padding: '8px 16px',
        fontSize: '13px',
        fontWeight: 600,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
      }}
    >
      <span>⚠️ 全域授權已啟用 — 所有工具將自動執行，無需確認</span>
      <button
        onClick={() => setPermissionMode('ask')}
        style={{
          background: 'rgba(255,255,255,0.2)',
          border: '1px solid rgba(255,255,255,0.4)',
          borderRadius: '4px',
          color: '#fff',
          padding: '2px 10px',
          fontSize: '12px',
          cursor: 'pointer',
        }}
      >
        關閉
      </button>
    </div>
  )
}

export default function App() {
  const location = useLocation()
  const rightPanelOpen = useLayoutStore((s) => s.rightPanelOpen)
  const sidebarCollapsed = useLayoutStore((s) => s.sidebarCollapsed)
  const isMainMode = (MAIN_MODES.some((m) => location.pathname === m || location.pathname.startsWith(m + '/')) || location.pathname === '/')
  const [needsSetup, setNeedsSetup] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/settings/setup-required')
      .then(r => r.json())
      .then(data => {
        if (data.setup_required) {
          setNeedsSetup(true)
        }
        setLoading(false)
      })
      .catch(() => {
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    return () => {
      useChatStore.getState().cleanupAllWs()
    }
  }, [])

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: '#0f0f10',
        color: '#fff',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>載入中...</div>
          <div style={{ fontSize: '14px', color: '#888' }}>正在初始化...</div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'var(--bg-primary)' }}>
      <GlobalWarningBanner />
      <HotkeyManager />
      <ToastContainer />
      {needsSetup && <ApiSetupModal />}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
          {isMainMode && <TopBar />}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            <main style={{ flex: 1, overflow: 'auto', minWidth: 0 }}>
              <Routes>
                <Route path="/" element={<Navigate to="/chat" replace />} />
                <Route path="/chat" element={<ChatPage key="chat-list" />} />
                <Route path="/chat/:sessionId" element={<ChatPage />} />
                <Route path="/cowork" element={<CoworkPage />} />
                <Route path="/cowork/:sessionId" element={<CoworkPage />} />
                <Route path="/code" element={<CodeModePage key="code-list" />} />
                <Route path="/code/:sessionId" element={<CodeModePage key="code-session" />} />
                <Route path="/models" element={<ModelsPage />} />
                <Route path="/history" element={<HistoryPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/notion" element={<NotionPage />} />
                <Route path="/memory" element={<MemoryPage />} />
                <Route path="/skills" element={<SkillsPage />} />
                <Route path="/database" element={<DatabasePage />} />
                <Route path="/mcp" element={<MCPPage />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/agent-dashboard" element={<AgentDashboard />} />
                <Route path="/teams" element={<TeamsPage />} />
                <Route path="/hooks" element={<HooksPage />} />
                <Route path="/connections" element={<ConnectionsPage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/customize" element={<CustomizePage />} />
              </Routes>
            </main>
            {isMainMode && rightPanelOpen && <RightPanel />}
          </div>
        </div>
      </div>
    </div>
  )
}

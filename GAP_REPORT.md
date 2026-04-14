# Claude Code TypeScript vs Python API Server 功能缺失報告

## 進度概覽

| 項目 | 數量 |
|------|------|
| 已分析 TypeScript 檔案 | 7 |
| 總 TypeScript 檔案 | 1884 |
| 分析覆盖率 | 0.37% |

---

## 一、History 模組 Gap (TypeScript → Python)

| Gap | 說明 | 優先級 |
|-----|------|--------|
| 粘貼內容引用系統 | `[Pasted text #N +X lines]` 格式化和解析 | 高 |
| 粘貼內容展開 | `expandPastedTextRefs()` 將占位符替換為實際內容 | 高 |
| 歷史條目 Undo | `removeLastFromHistory()` 撤銷最後添加 | 高 |
| 歷史流式讀取 | `makeLogEntryReader()` 異步生成器逐行讀取 | 中 |
| 時間戳歷史 | `getTimestampedHistory()` ctrl+r picker 專用 | 中 |
| pending buffer | 內存緩冲區加速讀取 + 異步刷寫 | 中 |
| tmux 環境檢測 | `CLAaude_CODE_SKIP_PROMPT_HISTORY` 開關 | 低 |
| 圖像單獨存儲 | image-cache 分離圖像 | 低 |
| 文件鎖機制 | `lock()` 防並發寫入 | 低 |

---

## 二、Auth 模組 Gap (TypeScript → Python)

| Gap | 說明 | 優先級 |
|-----|------|--------|
| CLI 登入/登出 | 無 `authLogin()` / `performLogout()` 端點 | 高 |
| Auth Status 查詢 | 無 `authStatus()` 當前登入狀態 | 高 |
| API Key 管理 | 無 Keychain/Config 讀寫 | 高 |
| AWS STS 身份驗證 | 無 `checkStsCallerIdentity()` | 高 |
| AWS/GCP Credential Export | 無雲端認證 credential 導出 | 高 |
| macOS Keychain | 完全無 Keychain 整合 | 高 |
| Workspace Trust | 無 `checkHasTrustDialogAccepted()` | 高 |
| JWT Payload 解碼 | 無 `decodeJwtPayload()` | 中 |
| 主動 Token 刷新 | 無 `createTokenRefreshScheduler()` | 中 |
| OAuth 401 錯誤處理 | 無 `handleOAuth401Error()` | 中 |
| Token 鎖檔機制 | 無 `lockfile.lock()` 防 race condition | 低 |
| 訂閱/計費資訊 | 無 subscriptionType / rateLimitTier | 中 |

---

## 三、User 模組 Gap (TypeScript → Python)

| Gap | 說明 | 優先級 |
|-----|------|--------|
| CoreUserData 結構 | 無 deviceId/sessionId/email bundle | 高 |
| Email 獲取 | 無 `getEmail()` / `getEmailAsync()` | 高 |
| OAuth 帳戶資訊 | 無 `getOauthAccountInfo()` | 高 |
| Git Email | 無 `getGitEmail()` (git config) | 中 |
| GitHub Actions Metadata | 無 GA 環境變數追蹤 | 中 |
| Analytics 整合 | 無 GrowthBook / firstTokenTime | 中 |
| 快取管理 | 無 `resetUserCache()` 機制 | 低 |
| 平臺識別 | 無 `getHostPlatformForAnalytics()` | 低 |

---

## 四、Agents 模組 Gap (TypeScript → Python)

| Gap | 說明 | 優先級 |
|-----|------|--------|
| Coordinator Mode | 多 Worker 協調者模式 | 高 |
| Companion System | 虛擬夥伴 + gamification (species/rarity/stats) | 高 |
| 多 Worker 協調 | 並行啟動 + XML 任務通知 | 高 |
| Claude Code Guide Agent | 內建互動式引導 | 中 |
| Statusline Setup Agent | 狀態列設定 | 低 |

---

## 五、Memory 模組 Gap (TypeScript → Python)

| Gap | 說明 | 優先級 |
|-----|------|--------|
| LLM 語義搜索 | `findRelevantMemories()` 用 Sonnet 選擇最相關記憶 | 高 |
| 記憶類型 Taxonomy | user/feedback/project/reference 四類型 | 高 |
| 自動索引重建 | `_rebuild_index()` 寫 MEMORY.md | 高 |
| 記憶新鲜度提示 | 超過 1 天顯示 staleness warning | 中 |
| Team Memory 目錄 | auto + team 雙目錄組合 | 中 |
| KAIROS 每日日誌 | Assistant mode 專用 append-only 日誌 | 高 |
| 背景提取代理 | `extractMemories.ts` 主動寫入記憶 | 高 |
| 路徑安全驗證 | `validateMemoryPath()` 防 traversal | 中 |
| MEMORY.md 截斷 | 200 行 + 25KB 雙重上限 | 低 |

---

## 六、Tools 模組 Gap (TypeScript → Python)

| 缺失工具 | 說明 |
|----------|------|
| McpAuthTool | MCP 認證工具 |
| WebBrowserTool | 網頁瀏覽工具 |
| REPLTool | REPL 模式 (ant only) |
| MonitorTool | 監控工具 |
| PushNotificationTool | 推送通知 |
| SendUserFileTool | 發送用戶檔案 |
| SubscribePRTool | PR 訂閱 |
| ListPeersTool | 同級列表 |
| TerminalCaptureTool | 終端擷取 |
| CtxInspectTool | 上下文檢查 |
| OverflowTestTool | 溢位測試 |
| TestingPermissionTool | 測試權限 |
| SnipTool | 歷程剪輯 |
| TungstenTool | Ant 內部工具 |
| SuggestBackgroundPRTool | 後台 PR 建議 |

---

## 七、架構差異總結

| 維度 | TypeScript (Claude Code) | Python (API Server) |
|------|-------------------------|---------------------|
| **存儲** | JSONL 文件 + Markdown | SQLite + JSON |
| **搜索** | LLM 语义 + keyword | FTS5 全文 + substring |
| **用戶模型** | 單用戶 + project 隔離 | 多用戶 + folder 分類 |
| **認證** | OAuth + API Key + Keychain + Cloud | 僅 OAuth PKCE |
| **記憶** | 4 類型 taxonomy + 背景提取 | 基本 CRUD |
| **並發** | 文件鎖 + pending buffer | SQLite 事務 |
| **即時性** | 內存緩冲 + 異步刷寫 | 直接寫入 |

---

## 八、高優先級填補目標

1. **粘貼內容引用系統** - History 必備
2. **CLI 登入/登出/狀態** - Auth 必備
3. **API Key 管理** - 實用性高
4. **Workspace Trust** - 安全相關
5. **LLM 语义搜索** - Memory 核心功能
6. **記憶類型 Taxonomy** - Memory 結構化
7. **Coordinator Mode** - 多代理必備
8. **Companion System** - 差異化功能

---

報告生成時間: 2026-04-12

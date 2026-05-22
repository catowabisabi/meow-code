# User Intention — Cato Claude

> 自動建立：2026-05-22 02:08
> 狀態：待用戶確認

## 從程式碼推斷的 Project Intent

**Cato Claude** 係一個開源既 Claude Code 替代方案，目標係打造一個企業級 AI Coding Agent。

### 核心價值
- **多 Provider 支持**：Anthropic / OpenAI / DeepSeek / MiniMax / Ollama
- **WebSocket 實時聊天**：流式 AI 響應
- **工具執行引擎**：47+ 內置工具（Shell、File、Web、Agent、Memory、Notion、SQLite...）
- **Skills 系統**：可擴展的 Skill 定義
- **Session 管理**：對話持久化 + 恢復
- **Memory 系統**：長期記憶讀寫
- **Plan 模式**：只讀工具安全模式

### 技術棧
- **後端**：Python FastAPI（api_server/）
- **前端**：React + Vite + Zustand（webui/client/src/）
- **通訊**：REST API + WebSocket

### 已知 Gap / 需關注範疇
1. Type safety：routes 大量 `(req as any).pathParams` → 需正式 type
2. Auth 系統：無完整 login/logout/API key 管理
3. History 模組：粘貼內容引用、歷史 Undo 等缺失
4. Multi-agent 協調：Coordinator Mode、Companion System 未實現

---

## ⚠️ 待用戶確認

如果你睇到呢份文件，請回覆確認或修正以下内容：

1. 呢個 project 係為你自己用、定係想做 product？
2. 你最想優化邊方面？（安全？UX？功能完整度？）
3. 有冇特定 priority 我應該跟？
4. 有冇任何範圍唔想郁？
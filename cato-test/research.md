# Research: Chat vs Code vs Cowork Agents

**Mode**: ULW (Ultra Large Workflow) Research
**Date**: 2026-05-05
**Objective**: Understand differences between Chat, Code, and Cowork agent modes

---

## Executive Summary

The AI coding tool landscape has fragmented into three distinct interaction paradigms: **Chat Agents**, **Code Agents (Copilots)**, and **Cowork Agents**. Each represents a different point on the autonomy spectrum, with fundamentally different architectures, capabilities, and use cases.

| Aspect | Chat Agent | Code/Copilot Agent | Cowork Agent |
|--------|-----------|-------------------|-------------|
| **Autonomy** | None - responds once | Low - suggests only | High - acts autonomously |
| **Tool Use** | None | Limited (editor only) | Full (shell, git, files, MCP) |
| **Task Scope** | Single Q&A | Single file | Multi-file, multi-step |
| **Human Role** | Do everything | Approve suggestions | Review at milestones |
| **Context** | Session only | Workspace-aware | Full codebase |
| **Example** | ChatGPT, Claude chat | GitHub Copilot, Cursor | Claude Code, Devin |

---

## 1. Chat Agent

### What It Is
A conversational interface powered by a language model. You type a question, it types an answer. That is the entire interaction loop.

### Architecture
```
User → [Chat Window] → LLM → [Text Response] → User acts manually
```

### Characteristics
- **Single-turn or short conversation** - no persistent state between sessions
- **No tool access** - cannot read files, run commands, or edit code
- **Passive** - generates text only, human must act on it
- **Copy-paste workflow** - human transfers output to actual work

### Examples
- ChatGPT (basic mode)
- Claude web chat
- Gemini

### Best For
- Answering questions
- Brainstorming ideas
- Explaining concepts
- Drafting content (that human then implements)

### Limitations
- Cannot see your codebase
- Cannot execute code or run tests
- Cannot modify files
- Every action requires human manual intervention

### Quote
> "A chatbot talks. A copilot suggests. An agent acts. If you only remember one thing from this article, let it be that."

---

## 2. Code/Copilot Agent

### What It Is
An AI assistant embedded inside a specific application (IDE). It watches what you are doing and offers contextual suggestions that you then execute.

### Architecture
```
User in IDE → [Copilot] → LLM + Context (current file, open tabs) → [Suggestion] → User accepts/rejects
```

### Characteristics
- **Reactive** - waits for you to type, then suggests completions
- **Editor-bound** - confined to one application
- **Inline suggestions** - ghost text, tab-to-accept
- **Context-aware** - sees current file, recent edits, open tabs
- **Low autonomy** - human drives every action

### Examples
- GitHub Copilot (inline completions)
- Tabnine
- Codeium
- Cursor (Cmd+K, Cmd+L modes)

### Best For
- Autocomplete while typing
- Quick single-file edits
- Learning new APIs
- Suggesting next line of code

### Capabilities by Tool

| Tool | Inline | Chat | Agent Mode | Multi-File |
|------|--------|------|------------|------------|
| GitHub Copilot | ✓ | ✓ | Limited | ✗ |
| Cursor | ✓ | ✓ | ✓ | Good |
| Codeium | ✓ | ✓ | Limited | ✗ |
| Tabnine | ✓ | ✗ | ✗ | ✗ |

### Limitations
- Cannot run shell commands
- Cannot execute tests
- Limited to single-file or tight context
- No autonomous multi-step planning
- Human must approve every change

### Quote
> "A copilot suggests code as you type. A coding agent builds the next feature. They sound similar, but the gap between a copilot and a coding agent is the gap between autocomplete and autonomous software development."

---

## 3. Cowork Agent

### What It Is
An autonomous AI system that plans, executes, and iterates on multi-step coding tasks. Given a goal, it reads your codebase, creates a plan, writes code across multiple files, runs tests, reads errors, and fixes them.

### Architecture
```
User → [Goal] → LLM + Tools + Planning Loop → Execute → Observe → Adjust → Repeat
```

### The Agent Loop (Observe-Plan-Act-Reflect)
1. **Observe** - read current state (files, errors, test output)
2. **Plan** - decompose goal into actionable steps
3. **Act** - call tools (read, edit, shell, git)
4. **Reflect** - evaluate result, decide next action
5. **Repeat** until goal is met or human intervenes

### Characteristics
- **Proactive** - doesn't wait for human input, drives the work
- **Tool-rich** - full filesystem, shell, git, MCP access
- **Multi-file** - reads and edits across entire codebase
- **Self-correcting** - reads errors, diagnoses, fixes, iterates
- **High autonomy** - human checks at milestones, not every step

### Examples
- Claude Code (Anthropic)
- Claude Cowork (Desktop app)
- Devin (Cognition)
- GitHub Copilot Coding Agent
- Aider
- Codex CLI

### Architectures

#### Single Agent
Claude Code runs as a single agent with tools:
- Read/write files
- Shell commands
- Git operations
- MCP server tools

#### Multi-Agent (Cowork/Teams)
Claude Cowork and Claude Code Agent Teams coordinate multiple agents:

```
User/Supervisor
    ├── Agent A (Frontend) → writes files, reports
    ├── Agent B (Backend) → writes files, reports
    ├── Agent C (Tests) → verifies, reports
    └── [Shared Task List + File Locking]
```

**Coordination Patterns:**
- **Orchestrator-Worker**: Central supervisor decomposes and delegates
- **Pipeline**: Output of Agent A becomes input of Agent B
- **Peer-to-Peer**: Agents message each other via shared inbox

**Coordination Mechanisms:**
- **Shared task list** with self-claiming and dependencies
- **File locking** - exclusive locks before editing (prevents race conditions)
- **Git worktrees** - each agent works on separate branch
- **Atomic writes** - write to temp file, then rename

### Best For
- Multi-file refactors
- Adding new features across stack layers
- Running test suites and fixing failures
- Architectural changes
- Long-running autonomous tasks

### Limitations
- Requires clear scope - vague goals produce wrong results
- Can make expensive mistakes without supervision
- Token-heavy - multi-agent burns 4-7x more than single agent
- Coordination overhead limits parallelism

### Quote
> "Agents that index the repository delivered 25% higher accuracy than agents relying purely on chat history."

---

## 4. Comparative Analysis

### Autonomy Spectrum

```
Chat ────────────── Copilot ────────────── Cowork
  │                   │                    │
  │                   │                    │
No tools         Editor-only          Full autonomy
Single turn      Suggest-approve      Plan-execute-iterate
Human does       Human approves       Human reviews
```

### Capability Comparison

| Capability | Chat | Copilot | Cowork |
|-----------|------|---------|--------|
| Text generation | ✓ | ✓ | ✓ |
| Inline completion | ✗ | ✓ | ✓ |
| File read | ✗ | Limited | ✓ |
| File write | ✗ | ✗ | ✓ |
| Shell commands | ✗ | ✗ | ✓ |
| Git operations | ✗ | ✗ | ✓ |
| Run tests | ✗ | ✗ | ✓ |
| Multi-file refactor | ✗ | ✗ | ✓ |
| Multi-agent parallel | ✗ | ✗ | ✓ |
| Long-running autonomy | ✗ | ✗ | ✓ |
| Self-correction | ✗ | ✗ | ✓ |

### Task Duration

| Task | Chat | Copilot | Cowork |
|------|------|---------|--------|
| Quick question | ✓ (fastest) | ✗ | ✗ |
| Single line fix | ✓ | ✓ | ✓ |
| Single file edit | ✗ | ✓ | ✓ |
| Multi-file feature | ✗ | Struggles | ✓ |
| Overnight migration | ✗ | ✗ | ✓ |

### Token Efficiency

Based on benchmark data (2026):

| Tool | Tokens/Task | Relative Cost |
|------|-------------|--------------|
| Codex CLI | 1.5M | $1.80 |
| Claude Code | 6.2M | $7.50 |
| Cursor 3 (parallel) | 4.1M | $4.20 |

Claude Code uses ~5.5x fewer tokens than Cursor for identical tasks.

### Accuracy / SWE-bench Verified

| Agent | Score |
|-------|-------|
| Claude Code | 78.4% |
| Codex | 71.0% |
| Cursor Agent | 67.2% |
| Devin | 60.8% |
| Replit | 54.1% |

---

## 5. Testing and Evaluation

### How to Evaluate Coding Agents

#### Offline Evals (Benchmark)
- **SWE-bench**: Real GitHub issues → fix → verified
- **Terminal-Bench**: CLI task completion
- **CursorBench**: Real Cursor sessions, graded by AI

#### Online Evals (Production)
- Track PR cycle time
- Bug escape rate
- Manual correction rate
- Developer satisfaction

### What to Test

| Dimension | Test Method |
|-----------|-------------|
| Solution correctness | Run test suite, check output |
| Code quality | Human review, lint scores |
| Context awareness | Multi-file coherence check |
| Tool use accuracy | Trace tool calls vs. actual needs |
| Error recovery | Inject errors, verify self-correction |
| Token efficiency | Per-task token count |

### Red Flags

- **Hallucination**: Agent invents APIs or files
- **Context loss**: Works on file 1, forgets file 2
- **No self-correction**: Repeats same mistake
- **Scope creep**: Changes files outside scope
- **Merge conflicts**: Multiple agents write same file

---

## 6. Best Practices for Each Mode

### Chat Mode
- Use for brainstorming and questions only
- Do not expect it to modify your codebase
- Treat output as draft, not final

### Copilot Mode
- Use for inline completion and quick single-file edits
- Keep files small and focused
- Review every suggestion before accepting
- Use `.cursorrules` or similar for project conventions

### Cowork Mode
- **Scope tightly**: "Add OAuth login" beats "improve auth"
- **Provide context**: CLAUDE.md, existing patterns, test expectations
- **Set boundaries**: Which files can/cannot be modified
- **Use checkpoints**: Review after major phases
- **Enable file locking**: Prevent concurrent writes
- **Start with 3-5 agents**: Scale up only when parallelism helps

### Multi-Agent Coordination

```
✓ DO:
- Decompose into independent, bounded tasks
- Define clear interfaces/contracts upfront
- Use file locking before writes
- Set quality gates (tests must pass)
- Communicate via structured docs, not freeform chat

✗ DON'T:
- Spawn agents for 2-line changes (overhead > savings)
- Vague specs ("write a good article")
- Parallel writes to same file
- No quality gates before accepting completion
- Deep nesting (orchestrator → workers → subworkers)
```

---

## 7. Key Research Findings (2026)

### Finding 1: Context and Retrieval Matter Most
Agents that index the repository (Cursor, Sweep, Devin) delivered 25% higher accuracy than agents relying purely on chat history.

### Finding 2: Multi-Agent Has Real Overhead
Multi-agent burns 4-7x more tokens than single-agent. Use when parallelism genuinely saves time, not by default.

### Finding 3: Structured Decomposition Wins
Hierarchical task decomposition completes complex tasks 58% faster with 34% higher completion rates vs. non-hierarchical approaches.

### Finding 4: The Best Teams Use Both
> "Most productive developers use two tools: one for inline flow and one for bigger tasks."

- Claude Code for autonomous multi-file work
- Cursor for inline completion and quick edits

### Finding 5: Accuracy > Speed
> "Claude Code uses 5.5x fewer tokens than Cursor. A task that costs $1.00 in Cursor costs $0.18 in Claude Code tokens."

But Claude Code is slower per task while being more accurate.

### Finding 6: Tests Are Mandatory Infrastructure
> "Red/green TDD ensures agents optimize toward correct behavior. Without tests, agents produce code that looks right but silently breaks."

### Finding 7: Specifications Are the Interface
> "Undocumented APIs cannot be utilized by agents. Clear specs are not just good practice; they are the primary interface through which work happens."

---

## 8. Implementation in Cato-Claude

Based on the codebase analysis, Cato-Claude implements three modes:

### Chat Mode
- Simple request-response
- No persistent context between turns
- No file or tool access
- Used for Q&A and brainstorming

### Code Mode (Cowork Light)
- File system access
- Shell command execution
- Single agent with planning loop
- Works in isolated workspace folder
- Current folder isolated per mode (not shared)

### Cowork Mode (Full Autonomy)
- Multiple agents possible
- Shared workspace across agents
- File locking for coordination
- Plan-approve-execute workflow
- MCP server integration

### Observed Implementation Details

```typescript
// Current folder is isolated per mode (from layoutStore)
currentFolder: Record<AppMode, string | null>
{
  chat: null,      // No folder context
  cowork: "src",   // Cowork has folder
  code: "src"      // Code has folder
}
```

```typescript
// Agent spawns with parent session context
const agent = await agentPool.spawnAgent({
  parentSessionId: body.sessionId || 'webui',
  name: body.name,
  type: body.type || 'general',
  task: body.task,
  model: config.defaultModel,
  provider: config.defaultProvider,
})
```

### WebSocket Streaming
- Real-time message streaming
- Iteration limits (max_iterations)
- Abort handling with stream_end events
- Session-scoped context

---

## 9. Recommendations for Testing

### Unit Tests (Per Mode)
1. **Chat**: Mock LLM responses, verify prompt construction
2. **Code**: File operations, shell execution, session management
3. **Cowork**: Multi-agent coordination, file locking, task decomposition

### Integration Tests
1. **API endpoints**: All route handlers (sessions, files, skills, agents, etc.)
2. **WebSocket**: Message streaming, iteration limits, abort
3. **MCP servers**: Tool discovery and execution

### E2E Tests (Playwright)
1. **Chat flow**: Send message, receive streamed response
2. **Code flow**: Open folder, request file structure, verify output
3. **Cowork flow**: Spawn agent, verify task completion, check file outputs

### Benchmark Tasks
1. **File structure**: "Show me the folder structure"
2. **Multi-file refactor**: "Rename function X across all files"
3. **Test writing**: "Add tests for module Y"
4. **Error recovery**: "Fix the failing tests in Z"

---

## 10. References

- [AI Agent vs Chatbot vs Copilot - Fazm Blog](https://fazm.ai/blog/ai-agent-vs-chatbot-vs-copilot) (2025-12)
- [Coding Agent vs Copilot - AgentsRoom](https://agentsroom.dev/coding-agent-vs-copilot) (2026-04)
- [GitHub Copilot Agent Mode vs Coding Agent](https://github.blog/developer-skills/github/less-todo-more-done-the-difference-between-coding-agent-and-agent-mode-in-github-copilot) (2025-06)
- [AI Coding Agents Evaluation - Propel Code](https://www.propelcode.ai/blog/ai-coding-agents-comprehensive-evaluation-2025) (2025-06)
- [Claude Cowork Guide - Ajit Singh](https://singhajit.com/claude-cowork-guide/) (2026-03)
- [Claude Code vs Cursor - Afterbuild Labs](https://www.afterbuildlabs.com/compare/claude-code-vs-cursor) (2026-04)
- [Multi-Agent Development - Zylos Research](https://zylos.ai/research/2026-03-09-multi-agent-software-development-ai-native-teams) (2026-03)
- [Cursor 3 vs Claude Code vs Codex CLI - Particula](https://particula.tech/blog/cursor-3-vs-claude-code-vs-codex-cli-parallel-agents) (2026-04)
- [AI Coding Benchmark - AI Multiple](https://research.aimultiple.com/ai-coding-benchmark/) (2026)

---

## 11. Appendix: Cato-Claude Specific Analysis

### Route Analysis (from codebase)

| Route | Method | Path | Handler |
|-------|--------|------|---------|
| sessions | POST | `/api/sessions` | Create new chat session |
| sessions | GET | `/api/sessions` | List all sessions |
| sessions | GET | `/api/sessions/:id` | Get session with messages |
| sessions | POST | `/api/sessions/:id/save` | Persist active session |
| sessions | PUT | `/api/sessions/:id` | Update session title |
| sessions | DELETE | `/api/sessions/:id` | Delete session |
| files | GET | `/api/files` | List directory |
| files | GET | `/api/files/read` | Read file (max 5MB) |
| files | POST | `/api/files/write` | Write file |
| agents | GET | `/api/agents` | List agents |
| agents | GET | `/api/agents/:id` | Get agent |
| agents | POST | `/api/agents` | Spawn agent |
| agents | POST | `/api/agents/:id/run` | Run agent task |
| agents | DELETE | `/api/agents/:id` | Remove agent |
| skills | GET | `/api/skills` | List skills |
| skills | POST | `/api/skills/execute` | Execute skill |
| skills | PUT | `/api/skills/:name` | Update skill |
| skills | DELETE | `/api/skills/:name` | Delete skill |

### WebSocket Protocol

```
Client → Server:
  { type: "chat", content: { role: "user", content: [...] }, stream: true }

Server → Client (streaming):
  { type: "chunk", content: "..." }
  { type: "chunk", content: "..." }
  { type: "done", content: "..." }

Server events:
  { type: "session_info", sessionId, model, provider }
  { type: "error", error: "..." }
  { type: "stream_end", stopReason: "max_iterations|abort|complete" }
```

### Known Path Parameter Bug (FIXED)

All route handlers now consistently use `req.pathParams` instead of manual URL parsing:
- `sessions.ts`: 4 routes fixed
- `database.ts`: 4 routes fixed
- `models.ts`: 3 routes fixed
- `notion.ts`: 3 routes fixed

---

*End of Research Document*

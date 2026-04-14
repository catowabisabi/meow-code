"""第二十二輪分析批量更新腳本 - commands 目錄分析"""
import sqlite3
from datetime import datetime

DB_PATH = r"F:\codebase\cato-claude\progress.db"

def update_record(src_path, category, summary, api_path, status, notes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE files SET 
            category = ?,
            summary = ?,
            api_path = ?,
            status = ?,
            analyzed_at = ?,
            notes = ?
        WHERE src_path = ?
    """, (category, summary, api_path, status, datetime.now().isoformat(), notes, src_path))
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows

def main():
    updates = [
        ("src\\commands\\add-dir\\add-dir.tsx", "commands/add-dir", "Add directory command UI", "NONE", "MEDIUM: Add-dir command."),
        ("src\\commands\\add-dir\\validation.ts", "commands/add-dir", "Add directory validation", "NONE", "MEDIUM: Validation logic."),
        ("src\\commands\\agents\\agents.tsx", "commands/agents", "Agents command UI", "NONE", "MEDIUM: Agents command."),
        ("src\\commands\\agents\\index.ts", "commands/agents", "Agents command index", "NONE", "LOW: Index file."),
        ("src\\commands\\branch\\index.ts", "commands/branch", "Branch command index", "NONE", "LOW: Index file."),
        ("src\\commands\\bridge\\bridge.tsx", "commands/bridge", "Bridge command UI", "NONE", "HIGH: Bridge UI missing."),
        ("src\\commands\\bridge\\index.ts", "commands/bridge", "Bridge command index", "NONE", "LOW: Index file."),
        ("src\\commands\\btw\\btw.tsx", "commands/btw", "BTW casual command", "NONE", "LOW: Casual command."),
        ("src\\commands\\chrome\\chrome.tsx", "commands/chrome", "Chrome integration", "NONE", "MEDIUM: Chrome integration."),
        ("src\\commands\\chrome\\index.ts", "commands/chrome", "Chrome index", "NONE", "LOW: Index file."),
        ("src\\commands\\clear\\caches.ts", "commands/clear", "Clear caches", "NONE", "MEDIUM: Cache clearing."),
        ("src\\commands\\clear\\clear.ts", "commands/clear", "Clear terminal", "NONE", "LOW: Clear command."),
        ("src\\commands\\clear\\conversation.ts", "commands/clear", "Clear conversation", "NONE", "MEDIUM: Conversation clearing."),
        ("src\\commands\\clear\\index.ts", "commands/clear", "Clear index", "NONE", "LOW: Index file."),
        ("src\\commands\\color\\color.ts", "commands/color", "Color configuration", "NONE", "LOW: Color settings."),
        ("src\\commands\\color\\index.ts", "commands/color", "Color index", "NONE", "LOW: Index file."),
        ("src\\commands\\compact\\index.ts", "commands/compact", "Compact index", "NONE", "LOW: Index file."),
        ("src\\commands\\config\\config.tsx", "commands/config", "Config command UI (2500+ lines)", "api_server/services/settings.py", "HIGH: Config UI missing - only settings.py stubs."),
        ("src\\commands\\copy\\copy.tsx", "commands/copy", "Copy command", "NONE", "LOW: Copy command."),
        ("src\\commands\\copy\\index.ts", "commands/copy", "Copy index", "NONE", "LOW: Index file."),
        ("src\\commands\\cost\\index.ts", "commands/cost", "Cost index", "NONE", "LOW: Index file."),
        ("src\\commands\\desktop\\desktop.tsx", "commands/desktop", "Desktop integration", "NONE", "MEDIUM: Desktop integration."),
        ("src\\commands\\desktop\\index.ts", "commands/desktop", "Desktop index", "NONE", "LOW: Index file."),
        ("src\\commands\\diff\\index.ts", "commands/diff", "Diff index", "NONE", "LOW: Index file."),
        ("src\\commands\\doctor\\index.ts", "commands/doctor", "Doctor index", "NONE", "LOW: Index file."),
        ("src\\commands\\effort\\effort.tsx", "commands/effort", "Effort indicator", "NONE", "LOW: UI component."),
        ("src\\commands\\effort\\index.ts", "commands/effort", "Effort index", "NONE", "LOW: Index file."),
        ("src\\commands\\exit\\exit.tsx", "commands/exit", "Exit command UI", "NONE", "MEDIUM: Exit command."),
        ("src\\commands\\export\\export.tsx", "commands/export", "Export command", "NONE", "MEDIUM: Export functionality."),
        ("src\\commands\\export\\index.ts", "commands/export", "Export index", "NONE", "LOW: Index file."),
        ("src\\commands\\extra-usage\\extra-usage-core.ts", "commands/extra-usage", "Extra usage core logic", "NONE", "MEDIUM: Extra usage tracking."),
        ("src\\commands\\extra-usage\\extra-usage-noninteractive.ts", "commands/extra-usage", "Extra usage non-interactive", "NONE", "MEDIUM: Non-interactive mode."),
        ("src\\commands\\extra-usage\\extra-usage.tsx", "commands/extra-usage", "Extra usage UI", "NONE", "MEDIUM: Usage display."),
        ("src\\commands\\extra-usage\\index.ts", "commands/extra-usage", "Extra usage index", "NONE", "LOW: Index file."),
        ("src\\commands\\fast\\fast.tsx", "commands/fast", "Fast mode command", "NONE", "MEDIUM: Fast mode."),
        ("src\\commands\\fast\\index.ts", "commands/fast", "Fast index", "NONE", "LOW: Index file."),
        ("src\\commands\\feedback\\feedback.tsx", "commands/feedback", "Feedback command", "NONE", "LOW: Feedback command."),
        ("src\\commands\\feedback\\index.ts", "commands/feedback", "Feedback index", "NONE", "LOW: Index file."),
        ("src\\commands\\files\\files.ts", "commands/files", "Files command", "NONE", "MEDIUM: File listing."),
        ("src\\commands\\files\\index.ts", "commands/files", "Files index", "NONE", "LOW: Index file."),
        ("src\\commands\\heapdump\\heapdump.ts", "commands/heapdump", "Heap dump command", "NONE", "MEDIUM: Debug heap dump."),
        ("src\\commands\\heapdump\\index.ts", "commands/heapdump", "Heap dump index", "NONE", "LOW: Index file."),
        ("src\\commands\\help\\help.tsx", "commands/help", "Help command UI", "NONE", "LOW: Help command."),
        ("src\\commands\\help\\index.ts", "commands/help", "Help index", "NONE", "LOW: Index file."),
        ("src\\commands\\hooks\\hooks.tsx", "commands/hooks", "Hooks command UI", "NONE", "HIGH: Hooks command UI."),
        ("src\\commands\\hooks\\index.ts", "commands/hooks", "Hooks index", "NONE", "LOW: Index file."),
        ("src\\commands\\init-verifiers.ts", "commands/init", "Init verifiers", "NONE", "MEDIUM: Init verification."),
        ("src\\commands\\install-github-app\\ApiKeyStep.tsx", "commands/install-github-app", "GitHub App API key step", "NONE", "HIGH: GitHub App installation flow."),
        ("src\\commands\\install-github-app\\CheckExistingSecretStep.tsx", "commands/install-github-app", "Check existing secret step", "NONE", "HIGH: Secret checking."),
        ("src\\commands\\install-github-app\\CheckGitHubStep.tsx", "commands/install-github-app", "Check GitHub step", "NONE", "HIGH: GitHub verification."),
        ("src\\commands\\install-github-app\\ChooseRepoStep.tsx", "commands/install-github-app", "Choose repo step", "NONE", "HIGH: Repo selection."),
        ("src\\commands\\install-github-app\\CreatingStep.tsx", "commands/install-github-app", "Creating step", "NONE", "HIGH: App creation."),
        ("src\\commands\\install-github-app\\ErrorStep.tsx", "commands/install-github-app", "Error step", "NONE", "HIGH: Error handling."),
        ("src\\commands\\install-github-app\\ExistingWorkflowStep.tsx", "commands/install-github-app", "Existing workflow step", "NONE", "HIGH: Workflow detection."),
        ("src\\commands\\install-github-app\\InstallAppStep.tsx", "commands/install-github-app", "Install app step", "NONE", "HIGH: App installation."),
        ("src\\commands\\install-github-app\\OAuthFlowStep.tsx", "commands/install-github-app", "OAuth flow step", "NONE", "HIGH: OAuth flow."),
        ("src\\commands\\install-github-app\\SuccessStep.tsx", "commands/install-github-app", "Success step", "NONE", "HIGH: Success handling."),
        ("src\\commands\\install-github-app\\WarningsStep.tsx", "commands/install-github-app", "Warnings step", "NONE", "HIGH: Warning display."),
        ("src\\commands\\install-github-app\\index.ts", "commands/install-github-app", "Install GitHub App index", "NONE", "LOW: Index file."),
        ("src\\commands\\install-github-app\\install-github-app.tsx", "commands/install-github-app", "Install GitHub App main", "NONE", "HIGH: Full installation flow."),
        ("src\\commands\\install-slack-app\\index.ts", "commands/install-slack-app", "Install Slack App index", "NONE", "MEDIUM: Slack installation."),
        ("src\\commands\\install-slack-app\\install-slack-app.ts", "commands/install-slack-app", "Install Slack App", "NONE", "MEDIUM: Slack integration."),
        ("src\\commands\\install.tsx", "commands/install", "Install command", "NONE", "HIGH: Install command."),
        ("src\\commands\\keybindings\\index.ts", "commands/keybindings", "Keybindings index", "NONE", "LOW: Index file."),
        ("src\\commands\\keybindings\\keybindings.ts", "commands/keybindings", "Keybindings command", "NONE", "LOW: Keybindings command."),
        ("src\\commands\\login\\index.ts", "commands/login", "Login index", "NONE", "LOW: Index file."),
        ("src\\commands\\login\\login.tsx", "commands/login", "Login command UI", "NONE", "HIGH: Login UI missing."),
        ("src\\commands\\logout\\index.ts", "commands/logout", "Logout index", "NONE", "LOW: Index file."),
        ("src\\commands\\logout\\logout.tsx", "commands/logout", "Logout command UI", "NONE", "HIGH: Logout UI missing."),
        ("src\\commands\\mcp\\addCommand.ts", "commands/mcp", "MCP add command", "NONE", "HIGH: MCP command adding."),
        ("src\\commands\\mcp\\mcp.tsx", "commands/mcp", "MCP command UI", "NONE", "HIGH: MCP management UI."),
        ("src\\commands\\mcp\\xaaIdpCommand.ts", "commands/mcp", "MCP IDP command", "NONE", "HIGH: MCP IDP."),
        ("src\\commands\\memory\\memory.tsx", "commands/memory", "Memory command UI", "NONE", "MEDIUM: Memory management."),
        ("src\\commands\\mobile\\index.ts", "commands/mobile", "Mobile index", "NONE", "LOW: Index file."),
        ("src\\commands\\mobile\\mobile.tsx", "commands/mobile", "Mobile command", "NONE", "MEDIUM: Mobile integration."),
        ("src\\commands\\model\\index.ts", "commands/model", "Model index", "NONE", "LOW: Index file."),
        ("src\\commands\\model\\model.tsx", "commands/model", "Model selection UI", "NONE", "MEDIUM: Model selection."),
        ("src\\commands\\output-style\\index.ts", "commands/output-style", "Output style index", "NONE", "LOW: Index file."),
        ("src\\commands\\output-style\\output-style.tsx", "commands/output-style", "Output style UI", "NONE", "MEDIUM: Output styling."),
        ("src\\commands\\passes\\index.ts", "commands/passes", "Passes index", "NONE", "LOW: Index file."),
        ("src\\commands\\passes\\passes.tsx", "commands/passes", "Passes command", "NONE", "MEDIUM: Passes command."),
        ("src\\commands\\permissions\\index.ts", "commands/permissions", "Permissions index", "NONE", "LOW: Index file."),
        ("src\\commands\\permissions\\permissions.tsx", "commands/permissions", "Permissions UI", "NONE", "HIGH: Permissions UI missing."),
        ("src\\commands\\plan\\plan.tsx", "commands/plan", "Plan command UI", "NONE", "MEDIUM: Plan display."),
        ("src\\commands\\plugin\\AddMarketplace.tsx", "commands/plugin", "Add marketplace UI", "NONE", "HIGH: Marketplace UI."),
        ("src\\commands\\plugin\\BrowseMarketplace.tsx", "commands/plugin", "Browse marketplace UI", "NONE", "HIGH: Marketplace browsing."),
        ("src\\commands\\plugin\\DiscoverPlugins.tsx", "commands/plugin", "Plugin discovery UI", "NONE", "HIGH: Plugin discovery."),
        ("src\\commands\\plugin\\ManageMarketplaces.tsx", "commands/plugin", "Manage marketplaces UI", "NONE", "HIGH: Marketplace management."),
        ("src\\commands\\plugin\\ManagePlugins.tsx", "commands/plugin", "Manage plugins UI", "NONE", "HIGH: Plugin management UI."),
        ("src\\commands\\plugin\\PluginErrors.tsx", "commands/plugin", "Plugin errors UI", "NONE", "MEDIUM: Error display."),
        ("src\\commands\\plugin\\PluginOptionsDialog.tsx", "commands/plugin", "Plugin options dialog", "NONE", "HIGH: Plugin options UI."),
        ("src\\commands\\plugin\\PluginOptionsFlow.tsx", "commands/plugin", "Plugin options flow", "NONE", "HIGH: Options flow."),
        ("src\\commands\\plugin\\PluginSettings.tsx", "commands/plugin", "Plugin settings UI", "NONE", "HIGH: Settings UI."),
        ("src\\commands\\plugin\\PluginTrustWarning.tsx", "commands/plugin", "Plugin trust warning", "NONE", "HIGH: Trust warning UI."),
        ("src\\commands\\plugin\\UnifiedInstalledCell.tsx", "commands/plugin", "Installed plugins cell", "NONE", "HIGH: Plugin cell UI."),
        ("src\\commands\\plugin\\ValidatePlugin.tsx", "commands/plugin", "Plugin validation UI", "NONE", "HIGH: Validation UI."),
        ("src\\commands\\plugin\\index.tsx", "commands/plugin", "Plugin index", "NONE", "LOW: Index file."),
        ("src\\commands\\plugin\\parseArgs.ts", "commands/plugin", "Plugin argument parsing", "NONE", "MEDIUM: Argument parsing."),
        ("src\\commands\\plugin\\plugin.tsx", "commands/plugin", "Plugin main UI", "NONE", "HIGH: Plugin main UI."),
        ("src\\commands\\plugin\\pluginDetailsHelpers.tsx", "commands/plugin", "Plugin details helpers", "NONE", "MEDIUM: Details helpers."),
    ]

    total = 0
    for src_path, category, summary, api_path, notes in updates:
        rows = update_record(src_path, category, summary, api_path, "analyzed", notes)
        if rows > 0:
            print(f"[+] {src_path}")
            total += rows
        else:
            print(f"[-] Not found: {src_path}")

    print(f"\nTotal records updated: {total}")

if __name__ == "__main__":
    main()
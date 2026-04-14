import sqlite3
conn = sqlite3.connect(r'F:\codebase\cato-claude\progress.db')
c = conn.cursor()

fixes = [
    (r'src\ink\components\App.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\Box.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\Button.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\ClockContext.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\ErrorOverview.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\Link.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\Newline.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\NoSelect.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\RawAnsi.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\ScrollBox.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\Spacer.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\TerminalFocusContext.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\TerminalSizeContext.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\ink\components\Text.tsx', 'FIXED: PARTIAL - React Ink UI component'),
    (r'src\components\PromptInput\PromptInput.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\components\Settings\Settings.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\components\tasks\BackgroundTasksDialog.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\add-dir\add-dir.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\agents\agents.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\bridge\bridge.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\btw\btw.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\chrome\chrome.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\config\config.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\context\context.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\copy\copy.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\desktop\desktop.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\diff\diff.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\doctor\doctor.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\effort\effort.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\exit\exit.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\export\export.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\extra-usage\extra-usage.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\fast\fast.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\feedback\feedback.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\help\help.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\hooks\hooks.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\ide\ide.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\ApiKeyStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\CheckExistingSecretStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\CheckGitHubStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\ChooseRepoStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\CreatingStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\ErrorStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\ExistingWorkflowStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\install-github-app.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\InstallAppStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\OAuthFlowStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\SuccessStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\install-github-app\WarningsStep.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\login\login.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\logout\logout.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\mcp\mcp.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\memory\memory.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\mobile\mobile.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\model\model.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\output-style\output-style.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\passes\passes.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\permissions\permissions.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plan\plan.tsx', 'FIXED: PARTIAL - React UI component'),
    (r'src\commands\plugin\AddMarketplace.tsx', 'FIXED: PARTIAL - React UI component'),
]

updated = 0
for path, fix in fixes:
    c.execute('UPDATE files SET notes = COALESCE(notes, \'\') || ? WHERE src_path = ?', (f' | {fix}', path))
    if c.rowcount > 0:
        updated += 1

conn.commit()
print(f'Updated {updated} records')

c.execute("SELECT COUNT(*) FROM files WHERE notes LIKE '%FIXED%'")
fixed_count = c.fetchone()[0]
print(f'Total FIXED records: {fixed_count}')

conn.close()
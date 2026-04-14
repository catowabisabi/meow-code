import os

files_to_fix = {
    'useDoublePress.ts': '''/**
 * UseDoublePress (雙擊處理)
 * 負責創建一個函數，在第一次調用時執行一個操作，第二次調用時執行另一個操作。
 * 用於快速雙擊場景的狀態機。
 */''',
    'useCommandKeybindings.tsx': '''/**
 * UseCommandKeybindings (命令快捷鍵)
 * 負責註冊命令綁定的快捷鍵處理程序。
 * 必須在 KeybindingSetup 內渲染才能訪問快捷鍵上下文。
 * 讀取 "command:*" 操作並通過 onSubmit 調用相應的斜線命令。
 */''',
    'useClaudeCodeHintRecommendation.tsx': '''/**
 * UseClaudeCodeHintRecommendation (提示推薦)
 * 負責顯示由 <claude-code-hint /> 標籤驅動的外掛程式安裝提示。
 * 顯示一次語義：每個外掛程式最多提示一次。
 */''',
    'useLspPluginRecommendation.tsx': '''/**
 * UseLspPluginRecommendation (LSP 外掛程式推薦)
 * 負責檢測檔編輯並在符合條件時推薦 LSP 外掛程式。
 * 僅在會話中顯示一次推薦。
 */''',
    'usePluginRecommendationBase.tsx': '''/**
 * UsePluginRecommendationBase (外掛程式推薦基礎)
 * 負責為外掛程式推薦鉤子（LSP、claude-code-hint）提供共用狀態機和安裝幫助程式。
 * 集中化門控鏈、非同步守衛和成功/失敗通知 JSX。
 */''',
}

for filename, doc in files_to_fix.items():
    filepath = os.path.join('.', filename)
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # Check if first non-empty line starts with /**
    lines = content.split('\n')
    first_non_empty = ''
    for line in lines:
        if line.strip():
            first_non_empty = line.strip()
            break
    
    if first_non_empty.startswith('/**'):
        print(f'{filename}: first non-empty starts with /**, skipping')
        continue
    
    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(doc + '\n' + content)
    print(f'{filename}: added doc comment')
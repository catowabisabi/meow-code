Fix: Clean up pendingPaste unused state in ChatPage.tsx

Project: Cato Claude
Repo: /mnt/f/codebase/cato-claude

## Context
InputArea in ChatPage.tsx has `pendingPaste` state + `showPasteTip` that are set in handlePaste but never rendered to user in a meaningful way. The paste tip only shows for 3 seconds then disappears without letting the user add a reference note. This is dead code that clutters the component.

## Task
Remove the dead code paths for pendingPaste:
1. Remove `const [pendingPaste, setPendingPaste] = useState('')` — state is set but never read
2. Remove `setPendingPaste(text)` call in handlePaste
3. Remove `pasteTipPos` state `const [pasteTipPos, setPasteTipPos] = useState({ x: 0, y: 0 })` — only used by the paste tip
4. Keep `showPasteTip` if you think it adds value, OR remove it too if it's purely decorative

## What NOT to change
- Do NOT change the handleInput or handleKeyDown logic
- Do NOT change the textarea styling or behavior
- Do NOT touch any other files

## Keywords for creative problem-solving: dead code, cleanup, state management
## Output: commit hash + brief description after completing

ULW
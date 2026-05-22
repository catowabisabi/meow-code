# Task: History UX — Paste-Reference + Message Edit/Undo

## Context

Cato Claude's history module lacks critical UX for collaborative editing. Users pasting code snippets or references have no way to annotate WHY they pasted something. Typoes in sent messages cant be corrected. The audit trail is flat with no edit awareness.

## Source Files (read before starting)
- `api_server/routes/history.py` — backend history API (sessions, messages, search)
- `api_server/services/history/` — history service layer
- `webui/client/src/stores/chatStore.ts` — frontend chat/message state
- `webui/client/src/services/hooks.ts` — existing service pattern
- `shared/auth/cli.ts` — auth storage pattern to follow

## Deliverables

1. **Backend: History message edit support** (`api_server/routes/history.py`):
   - Add `PATCH /history/messages/{message_id}` endpoint
   - `HistoryMessageUpdate` schema: `{ content?: string, edited?: bool }`
   - Store original content in `edit_history` JSON column (append-only)
   - Return `edited=True` flag in response

2. **Backend: Paste reference annotation**:
   - Add `POST /history/messages/{message_id}/annotations` endpoint
   - `AnnotationCreate` schema: `{ type: "paste_ref", content: str, metadata?: object }`
   - Annotations table with `message_id, type, content, metadata, created_at`

3. **Frontend: Message edit UI**:
   - In `chatStore.ts` — add `editMessage(messageId, newContent)` action
   - In `webui/client/src/components/MessageBubble.tsx` — add edit button (hover reveal)
   - Show "edited" badge on edited messages
   - Long-press / right-click menu with "Edit" option on mobile

4. **Frontend: Paste reference chips**:
   - When user pastes from clipboard, show a small popover: "Add reference note?"
   - Store annotation alongside message, render as `📎 paste_ref` chip below message

5. **Backend: Undo for message deletion**:
   - `DELETE /history/messages/{message_id}` → soft delete (mark `deleted_at`)
   - Add `POST /history/sessions/{session_id}/undo` — restores last deleted message
   - Undo stack per session (last 10 deletions)

## Keywords
oscillation, wizard mode, aesthetic depth

## Verification
- [ ] PATCH /history/messages/{id} updates content, preserves edit_history
- [ ] GET /history/messages/{id} returns `edited: bool` flag
- [ ] POST /history/messages/{id}/annotations creates paste_ref
- [ ] DELETE /history/messages/{id} soft-deletes, undo restores
- [ ] Frontend: edit button appears on hover, save works
- [ ] Frontend: paste shows reference popover

ULW
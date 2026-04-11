"""Message grouping for API round boundaries."""
from api_server.models.message import Message


def group_messages_by_api_round(messages: list[Message]) -> list[list[Message]]:
    groups = []
    current = []
    last_assistant_id = None
    
    for msg in messages:
        if (
            msg.type == "assistant"
            and msg.message.id != last_assistant_id
            and current
        ):
            groups.append(current)
            current = [msg]
        else:
            current.append(msg)
        
        if msg.type == "assistant":
            last_assistant_id = msg.message.id
    
    if current:
        groups.append(current)
    
    return groups


def group_messages(messages: list[Message]) -> list[list[Message]]:
    return group_messages_by_api_round(messages)


def find_duplicate_content(messages: list[Message]) -> list[tuple[int, int]]:
    duplicates = []
    seen = {}
    
    for i, msg in enumerate(messages):
        if msg.type not in ("user", "assistant"):
            continue
        
        key = get_message_content_key(msg)
        if not key:
            continue
        
        if key in seen:
            duplicates.append((seen[key], i))
        else:
            seen[key] = i
    
    return duplicates


def get_message_content_key(msg) -> str | None:
    if not hasattr(msg, 'message') or not hasattr(msg.message, 'content'):
        return None
    
    content = msg.message.content
    if isinstance(content, str):
        return content[:200] if content else None
    elif isinstance(content, list):
        key_parts = []
        for block in content:
            if block.type == "text":
                key_parts.append(block.text[:100])
        return "|".join(key_parts) if key_parts else None
    
    return None


def merge_grouped_messages(groups: list[list[Message]]) -> list[Message]:
    return [msg for group in groups for msg in group]


def truncate_head_for_ptl_retry(
    messages: list[Message],
    ptl_response: any,
) -> list[Message] | None:
    PTL_RETRY_MARKER = "[earlier conversation truncated for compaction retry]"
    
    input_msgs = messages
    if messages and messages[0].type == "user" and getattr(messages[0], 'is_meta', False):
        if getattr(messages[0].message, 'content', '') == PTL_RETRY_MARKER:
            input_msgs = messages[1:]
    
    groups = group_messages_by_api_round(input_msgs)
    if len(groups) < 2:
        return None
    
    token_gap = get_prompt_too_long_token_gap(ptl_response)
    
    if token_gap is not None:
        acc = 0
        drop_count = 0
        for g in groups:
            acc += estimate_tokens_for_messages(g)
            drop_count += 1
            if acc >= token_gap:
                break
    else:
        drop_count = max(1, len(groups) // 5)
    
    drop_count = min(drop_count, len(groups) - 1)
    if drop_count < 1:
        return None
    
    sliced = [msg for group in groups[drop_count:] for msg in group]
    
    if sliced and sliced[0].type == "assistant":
        return [{"type": "user", "is_meta": True, "message": {"content": PTL_RETRY_MARKER}}, *sliced]
    
    return sliced


def get_prompt_too_long_token_gap(ptl_response: any) -> int | None:
    if not ptl_response:
        return None
    
    text = getattr(ptl_response, 'text', None)
    if not text:
        return None
    
    PROMPT_TOO_LONG_ERROR_MESSAGE = "Prompt too long"
    if PROMPT_TOO_LONG_ERROR_MESSAGE not in text:
        return None
    
    import re
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[0]) * 4
    
    return 50000


def estimate_tokens_for_messages(messages: list) -> int:
    total = 0
    for msg in messages:
        if hasattr(msg, 'message') and hasattr(msg.message, 'content'):
            content = msg.message.content
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        total += len(block.get("text", "")) // 4
    return total


class MessageGrouper:
    def __init__(self):
        self.groups = []
    
    def group(self, messages: list[Message]) -> list[list[Message]]:
        self.groups = group_messages_by_api_round(messages)
        return self.groups
    
    def find_duplicates(self) -> list[tuple[int, int]]:
        all_msgs = [msg for group in self.groups for msg in group]
        return find_duplicate_content(all_msgs)
    
    def merge(self) -> list[Message]:
        return merge_grouped_messages(self.groups)
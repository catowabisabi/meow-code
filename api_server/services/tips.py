from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Tip:
    id: str
    category: str
    title: str
    content: str
    priority: int = 0


TIPS_DATABASE = [
    Tip("1", "productivity", "Keyboard Shortcuts", "Use Ctrl+Shift+P to open command palette", 10),
    Tip("2", "productivity", "Slash Commands", "Type / to see available commands", 9),
    Tip("3", "memory", "Save Memories", "Use /mem save to store important information", 8),
    Tip("4", "session", "Session History", "Access previous sessions with Ctrl+O", 7),
    Tip("5", "tools", "Tool Usage", "Check tool usage stats with /stats", 6),
    Tip("6", "context", "Context Compression", "System automatically compresses long conversations", 5),
    Tip("7", "git", "Git Integration", "Use git commands directly in chat", 4),
    Tip("8", "search", "Code Search", "Use Ctrl+F to search within current file", 3),
]


class TipsService:
    _enabled_tips: List[str] = [t.id for t in TIPS_DATABASE]
    
    @classmethod
    def get_tip(cls, tip_id: str) -> Optional[Tip]:
        return next((t for t in TIPS_DATABASE if t.id == tip_id), None)
    
    @classmethod
    def get_all_tips(cls) -> List[Tip]:
        return [t for t in TIPS_DATABASE if t.id in cls._enabled_tips]
    
    @classmethod
    def get_tips_by_category(cls, category: str) -> List[Tip]:
        return [t for t in cls.get_all_tips() if t.category == category]
    
    @classmethod
    def get_random_tip(cls) -> Optional[Tip]:
        import random
        enabled = cls.get_all_tips()
        return random.choice(enabled) if enabled else None
    
    @classmethod
    def get_high_priority_tips(cls, limit: int = 3) -> List[Tip]:
        tips = cls.get_all_tips()
        tips.sort(key=lambda t: t.priority, reverse=True)
        return tips[:limit]
    
    @classmethod
    def disable_tip(cls, tip_id: str) -> None:
        if tip_id in cls._enabled_tips:
            cls._enabled_tips.remove(tip_id)
    
    @classmethod
    def enable_tip(cls, tip_id: str) -> None:
        if tip_id not in cls._enabled_tips:
            cls._enabled_tips.append(tip_id)
    
    @classmethod
    def reset_tips(cls) -> None:
        cls._enabled_tips = [t.id for t in TIPS_DATABASE]
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import re


@dataclass
class PromptSuggestion:
    text: str
    score: float
    suggestion_type: str


class PromptSuggestionService:
    _history: List[Dict[str, Any]] = []
    _max_history: int = 1000
    
    @classmethod
    def add_to_history(cls, text: str, role: str = "user") -> None:
        cls._history.append({
            "text": text,
            "role": role,
            "timestamp": datetime.utcnow().timestamp(),
        })
        if len(cls._history) > cls._max_history:
            cls._history = cls._history[-cls._max_history:]
    
    @classmethod
    async def get_next_suggestion(
        cls,
        current_input: str,
        context: Optional[List[str]] = None,
    ) -> List[PromptSuggestion]:
        suggestions = []
        
        if not current_input or len(current_input.strip()) < 2:
            return suggestions
        
        partial = current_input.strip().lower()
        
        for entry in reversed(cls._history):
            if entry["role"] != "user":
                continue
            text = entry["text"].lower()
            
            if text.startswith(partial) and text != partial:
                score = 0.8
                suggestions.append(PromptSuggestion(
                    text=entry["text"],
                    score=score,
                    suggestion_type="completion",
                ))
            
            if partial in text and len(text) > len(partial):
                score = 0.5
                suggestions.append(PromptSuggestion(
                    text=entry["text"],
                    score=score,
                    suggestion_type="similar",
                ))
        
        common_commands = [
            "show me the", "list all", "what is the", "how do I",
            "help me with", "can you show", "please explain",
        ]
        for cmd in common_commands:
            if current_input.startswith(cmd) and not current_input.endswith(" "):
                full = cmd + " "
                if not any(s.text.startswith(full) for s in suggestions):
                    suggestions.insert(0, PromptSuggestion(
                        text=full,
                        score=0.6,
                        suggestion_type="autocomplete",
                    ))
        
        suggestions.sort(key=lambda s: s.score, reverse=True)
        return suggestions[:5]
    
    @classmethod
    async def get_followup_suggestions(
        cls,
        current_input: str,
    ) -> List[PromptSuggestion]:
        suggestions = []
        
        input_lower = current_input.lower()
        
        if any(kw in input_lower for kw in ["error", "bug", "issue", "problem"]):
            suggestions.append(PromptSuggestion(
                text="show me the error details and stack trace",
                score=0.9,
                suggestion_type="followup",
            ))
            suggestions.append(PromptSuggestion(
                text="how do I fix this?",
                score=0.8,
                suggestion_type="followup",
            ))
        
        if any(kw in input_lower for kw in ["create", "add", "new"]):
            suggestions.append(PromptSuggestion(
                text="show me what was created",
                score=0.8,
                suggestion_type="followup",
            ))
        
        if any(kw in input_lower for kw in ["delete", "remove"]):
            suggestions.append(PromptSuggestion(
                text="confirm the deletion was successful",
                score=0.8,
                suggestion_type="followup",
            ))
        
        return suggestions[:3]
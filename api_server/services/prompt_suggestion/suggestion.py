from typing import List, Optional, Dict, Any, Callable, TYPE_CHECKING
from datetime import datetime
import re

if TYPE_CHECKING:
    from api_server.services.prompt_suggestion.types import Suggestion


SUGGESTION_PROMPT = """[SUGGESTION MODE: Suggest what the user might naturally type next into Claude Code.]

FIRST: Look at the user's recent messages and original request.

Your job is to predict what THEY would type - not what you think they should do.

THE TEST: Would they think "I was just about to type that"?

EXAMPLES:
User asked "fix the bug and run tests", bug is fixed → "run the tests"
After code written → "try it out"
Claude offers options → suggest the one the user would likely pick, based on conversation
Claude asks to continue → "yes" or "go ahead"
Task complete, obvious follow-up → "commit this" or "push it"
After error or misunderstanding → silence (let them assess/correct)

Be specific: "run the tests" beats "continue".

NEVER SUGGEST:
- Evaluative ("looks good", "thanks")
- Questions ("what about...?")
- Claude-voice ("Let me...", "I'll...", "Here's...")
- New ideas they didn't ask about
- Multiple sentences

Stay silent if the next step isn't obvious from what the user said.

Format: 2-12 words, match the user's style. Or nothing.

Reply with ONLY the suggestion, no quotes or explanation."""


ALLOWED_SINGLE_WORDS = frozenset([
    "yes", "yeah", "yep", "yea", "yup", "sure", "ok", "okay",
    "push", "commit", "deploy", "stop", "continue", "check", "exit", "quit", "no",
])


class PromptSuggestion:
    _history: List[Dict[str, Any]] = []
    _max_history: int = 1000
    _suggestion_callback: Optional[Callable[[str, str, float, str, Optional[str]], None]] = None

    @classmethod
    def set_suggestion_callback(
        cls,
        callback: Callable[[str, str, float, str, Optional[str]], None],
    ) -> None:
        cls._suggestion_callback = callback

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
    def clear_history(cls) -> None:
        cls._history.clear()

    @classmethod
    async def suggest_next_prompt(
        cls,
        messages: List[Dict[str, Any]],
        current_input: str,
        get_app_state: Callable[[], Dict[str, Any]],
    ) -> Optional[str]:
        assistant_turn_count = sum(1 for m in messages if m.get("type") == "assistant")
        if assistant_turn_count < 2:
            return None

        last_assistant = None
        for m in reversed(messages):
            if m.get("type") == "assistant":
                last_assistant = m
                break

        if last_assistant and last_assistant.get("isApiErrorMessage"):
            return None

        suggestion = await cls._generate_suggestion(messages)
        return suggestion

    @classmethod
    async def _generate_suggestion(
        cls,
        messages: List[Dict[str, Any]],
    ) -> Optional[str]:
        prompt = SUGGESTION_PROMPT
        return prompt

    @classmethod
    async def get_suggestions(
        cls,
        current_input: str,
        context: Optional[List[str]] = None,
    ) -> List["Suggestion"]:
        suggestions = []

        if not current_input or len(current_input.strip()) < 2:
            return suggestions

        partial = current_input.strip().lower()

        for entry in reversed(cls._history):
            if entry.get("role") != "user":
                continue
            text = entry["text"].lower()

            if text.startswith(partial) and text != partial:
                suggestions.append(cls._create_suggestion(
                    entry["text"],
                    0.8,
                    "completion",
                ))

            if partial in text and len(text) > len(partial):
                suggestions.append(cls._create_suggestion(
                    entry["text"],
                    0.5,
                    "similar",
                ))

        common_commands = [
            "show me the", "list all", "what is the", "how do I",
            "help me with", "can you show", "please explain",
        ]
        for cmd in common_commands:
            if current_input.startswith(cmd) and not current_input.endswith(" "):
                full = cmd + " "
                if not any(s.prompt.startswith(full) for s in suggestions):
                    suggestions.insert(0, cls._create_suggestion(
                        full,
                        0.6,
                        "autocomplete",
                        source="template",
                    ))

        suggestions.sort(key=lambda s: s.score, reverse=True)
        return suggestions[:5]

    @classmethod
    def _create_suggestion(
        cls,
        text: str,
        score: float,
        suggestion_type: str,
        source: str = "history",
    ) -> "Suggestion":
        from api_server.services.prompt_suggestion.types import Suggestion as TypesSuggestion, SuggestionType
        return TypesSuggestion(
            prompt=text,
            score=score,
            source=source,
            suggestion_type=SuggestionType(suggestion_type),
        )

    @classmethod
    def rank_suggestions(
        cls,
        suggestions: List["Suggestion"],
        current_input: str,
    ) -> List["Suggestion"]:
        if not current_input:
            return sorted(suggestions, key=lambda s: s.score, reverse=True)

        scored = []
        for s in suggestions:
            score = s.score
            if current_input.lower() in s.prompt.lower():
                score *= 1.2
            text_lower = s.prompt.lower()
            if text_lower.startswith(current_input.lower()):
                score *= 1.5
            scored.append((s, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored]

    @classmethod
    def should_filter_suggestion(
        cls,
        suggestion: Optional[str],
        prompt_id: str = "user_intent",
    ) -> bool:
        if not suggestion:
            return True

        lower = suggestion.lower()
        word_count = len(suggestion.strip().split())

        if lower == "done":
            return True

        if (lower == "nothing found" or
            lower == "nothing found." or
            lower.startswith("nothing to suggest") or
            lower.startswith("no suggestion") or
            re.search(r"\bsilence is\b|\bstay(s|ing)? silent\b", lower) or
            re.match(r"^\W*silence\W*$", lower)):
            return True

        if re.match(r"^\(.*\)$|^\[.*\]$", suggestion):
            return True

        if (lower.startswith("api error:") or
            lower.startswith("prompt is too long") or
            lower.startswith("request timed out") or
            lower.startswith("invalid api key") or
            lower.startswith("image was too large")):
            return True

        if re.match(r"^\w+:\s", suggestion):
            return True

        if word_count < 2:
            if not suggestion.startswith("/") and suggestion.lower() not in ALLOWED_SINGLE_WORDS:
                return True

        if word_count > 12:
            return True

        if len(suggestion) >= 100:
            return True

        if re.search(r"[.!?]\s+[A-Z]", suggestion):
            return True

        if re.search(r"[\n*]|\*\*", suggestion):
            return True

        if re.search(r"thanks|thank you|looks good|sounds good|that works|that worked|that's all|nice|great|perfect|makes sense|awesome|excellent", lower):
            return True

        if re.match(r"^(let me|i'll|i've|i'm|i can|i would|i think|i notice|here's|here is|here are|that's|this is|this will|you can|you should|you could|sure,|of course|certainly)", suggestion, re.IGNORECASE):
            return True

        return False


class PromptSuggestionService:
    _instance: Optional["PromptSuggestionService"] = None

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "PromptSuggestionService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_suggestions(
        self,
        context: dict,
        count: int = 5,
    ) -> List["Suggestion"]:
        current_input = context.get("current_input", "")
        user_history = context.get("user_history", [])
        
        for entry in user_history:
            if entry.get("role") == "user":
                PromptSuggestion.add_to_history(entry.get("text", ""), "user")
        
        suggestions = await PromptSuggestion.get_suggestions(current_input, None)
        return suggestions[:count]
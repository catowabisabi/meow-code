from dataclasses import dataclass
from typing import Optional, Dict, Any, List


TOKEN_ESTIMATES_PER_CHAR = {
    "english": 4,
    "cjk": 2,
    "code": 4,
    "mixed": 4.5,
}


def estimate_tokens_for_text(text: str, encoding: str = "cl100k_base") -> int:
    if not text:
        return 0
    
    char_count = len(text)
    
    has_cjk = any(ord(c) > 0x4E00 and ord(c) < 0x9FFF for c in text)
    has_english = any(c.isascii() and c.isalpha() for c in text)
    
    if has_cjk and has_english:
        avg_token_per_char = TOKEN_ESTIMATES_PER_CHAR["mixed"]
    elif has_cjk:
        avg_token_per_char = TOKEN_ESTIMATES_PER_CHAR["cjk"]
    elif has_english:
        avg_token_per_char = TOKEN_ESTIMATES_PER_CHAR["english"]
    else:
        avg_token_per_char = TOKEN_ESTIMATES_PER_CHAR["mixed"]
    
    return int(char_count / avg_token_per_char)


def estimate_tokens_for_messages(messages: List[Dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("text"):
                    total += estimate_tokens_for_text(block["text"])
                elif hasattr(block, "text"):
                    total += estimate_tokens_for_text(block.text)
        else:
            total += estimate_tokens_for_text(str(content))
    
    system_count = len([m for m in messages if m.get("role") == "system"])
    total += system_count * 50
    
    return total


@dataclass
class TokenEstimate:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    currency: str = "USD"


PRICING_PER_1K_TOKENS = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
}


class TokenEstimationService:
    @staticmethod
    def estimate_input(text: str) -> int:
        return estimate_tokens_for_text(text)
    
    @staticmethod
    def estimate_output(text: str) -> int:
        return estimate_tokens_for_text(text)
    
    @staticmethod
    def estimate_messages(messages: List[Dict[str, Any]]) -> int:
        return estimate_tokens_for_messages(messages)
    
    @staticmethod
    def estimate_cost(
        input_tokens: int,
        output_tokens: int,
        model: str = "gpt-3.5-turbo",
    ) -> TokenEstimate:
        pricing = PRICING_PER_1K_TOKENS.get(model, {"input": 0.001, "output": 0.002})
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return TokenEstimate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost=round(total_cost, 6),
        )
    
    @staticmethod
    def format_estimate(estimate: TokenEstimate) -> str:
        return (
            f"Input: {estimate.input_tokens} tokens, "
            f"Output: {estimate.output_tokens} tokens, "
            f"Total: {estimate.total_tokens} tokens, "
            f"Est. Cost: ${estimate.estimated_cost:.4f}"
        )
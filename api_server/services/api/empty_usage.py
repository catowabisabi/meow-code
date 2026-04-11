"""
Empty usage object - zero-initialized usage for logging.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class EMPTY_USAGE:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    server_tool_use: Dict[str, int] = None
    service_tier: str = "standard"
    cache_creation: Dict[str, int] = None
    inference_geo: str = ""
    iterations: list = None
    speed: str = "standard"

    def __post_init__(self):
        if self.server_tool_use is None:
            self.server_tool_use = {"web_search_requests": 0, "web_fetch_requests": 0}
        if self.cache_creation is None:
            self.cache_creation = {"ephemeral_1h_input_tokens": 0, "ephemeral_5m_input_tokens": 0}
        if self.iterations is None:
            self.iterations = []

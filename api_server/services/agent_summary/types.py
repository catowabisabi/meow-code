from typing import Optional
from dataclasses import dataclass


@dataclass
class AgentSummaryConfig:
    interval_seconds: float = 30.0
    max_summary_length: int = 200
    summary_delay_ms: float = 100.0

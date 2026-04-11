from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TTSProvider(str, Enum):
    EDGE = "edge"
    OPENAI = "openai"
    PYTTSX3 = "pyttsx3"


@dataclass
class Voice:
    id: str
    name: str
    language: str
    gender: Optional[str] = None
    provider: TTSProvider = TTSProvider.EDGE


@dataclass
class TTSConfig:
    provider: TTSProvider = TTSProvider.EDGE
    api_key: Optional[str] = None
    voice_id: str = "en-US-AriaNeural"
    rate: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    output_format: str = "mp3"
    extra: dict = field(default_factory=dict)
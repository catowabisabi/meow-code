"""TTS Service package for text-to-speech synthesis."""

from .tts_service import TTSService
from .types import TTSConfig, Voice, TTSProvider

__all__ = [
    "TTSService",
    "TTSConfig",
    "Voice",
    "TTSProvider",
]
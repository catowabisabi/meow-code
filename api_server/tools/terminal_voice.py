"""Voice and ANSI terminal - bridging gaps with ink/ and voice"""
import asyncio
import logging
import os
import re
import struct
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


DEC_PRIVATE_MODES = {
    1: "GATM",   # Guarded area transcendent attribute mode
    5: "SCORUS", # Reverse video
    6: "OM",     # Origin mode
    7: "AM",     # Auto-wrap mode
    8: "AM",     # Auto-repeat mode
    25: "CHT",   # Cursor show
    30: "HT",    # Show tab
    35: "XB",     # Extensible boolean
    40: "XRC",   # 132-column mode
    47: "GRPM",  # Graphical representation mode
    1047: "LRM", # Normal replacement buffer mode
    1048: "SCUSR", # Save/restore cursor position
    1049: "SCUSRS", # Alternate buffer mode
}


@dataclass
class TerminalCapabilities:
    supports_256_color: bool = False
    supports_true_color: bool = False
    supports_alternate_buffer: bool = True
    supports_mouse: bool = False
    max_color: int = 16


class DECMode:
    def __init__(self):
        self._modes: Dict[int, bool] = {}
    
    def set(self, mode: int, enabled: bool) -> None:
        self._modes[mode] = enabled
    
    def get(self, mode: int) -> bool:
        return self._modes.get(mode, False)
    
    def reset(self) -> None:
        self._modes.clear()


class ANSITokenizer:
    """
    ANSI tokenizer for terminal output.
    
    TypeScript equivalent: ink/termio/tokenize.ts
    Python gap: ANSI tokenizer missing.
    """
    
    ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    
    def __init__(self):
        self._mode = DECMode()
    
    def tokenize(self, text: str) -> List[Dict[str, Any]]:
        tokens = []
        
        for match in self.ANSI_ESCAPE.split(text):
            if match:
                tokens.append({"type": "text", "content": match})
        
        for match in self.ANSI_ESCAPE.finditer(text):
            seq = match.group()
            tokens.append({"type": "escape", "content": seq})
        
        return tokens
    
    def get_mode(self, mode: int) -> bool:
        return self._mode.get(mode)
    
    def set_mode(self, mode: int, enabled: bool) -> None:
        self._mode.set(mode, enabled)


class VoiceRecorder:
    """
    Voice recording with WebSocket STT integration.
    
    TypeScript equivalent: hooks/useVoice.ts
    Python gap: Zero WebSocket STT integration.
    """
    
    def __init__(self):
        self._recording = False
        self._ws_url: Optional[str] = None
        self._ws: Optional[Any] = None
        self._on_transcript: Optional[Callable] = None
    
    async def start_recording(
        self,
        ws_url: str,
        on_transcript: Optional[Callable] = None
    ) -> bool:
        self._ws_url = ws_url
        self._on_transcript = on_transcript
        self._recording = True
        
        return True
    
    async def stop_recording(self) -> None:
        self._recording = False
        
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    def is_recording(self) -> bool:
        return self._recording

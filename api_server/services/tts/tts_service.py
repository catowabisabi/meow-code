"""TTS Service for text-to-speech synthesis."""
import asyncio
from typing import AsyncIterator, Optional

from .types import TTSConfig, TTSProvider, Voice


class TTSService:
    def __init__(self, config: Optional[TTSConfig] = None):
        self.config = config or TTSConfig()
        self.provider = self.config.provider

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        if self.provider == TTSProvider.EDGE:
            return await self._edge_synthesize(text, voice)
        elif self.provider == TTSProvider.OPENAI:
            return await self._openai_synthesize(text, voice)
        elif self.provider == TTSProvider.PYTTSX3:
            return await self._pyttsx3_synthesize(text, voice)
        else:
            raise ValueError(f"Unknown TTS provider: {self.provider}")

    async def synthesize_stream(self, text: str, voice: str = "default") -> AsyncIterator[bytes]:
        if self.provider == TTSProvider.EDGE:
            async for chunk in self._edge_synthesize_stream(text, voice):
                yield chunk
        elif self.provider == TTSProvider.OPENAI:
            yield await self._openai_synthesize(text, voice)
        elif self.provider == TTSProvider.PYTTSX3:
            yield await self._pyttsx3_synthesize(text, voice)
        else:
            raise ValueError(f"Unknown TTS provider: {self.provider}")

    def get_available_voices(self) -> list[Voice]:
        if self.provider == TTSProvider.EDGE:
            return self._edge_get_voices()
        elif self.provider == TTSProvider.OPENAI:
            return self._openai_get_voices()
        elif self.provider == TTSProvider.PYTTSX3:
            return self._pyttsx3_get_voices()
        else:
            raise ValueError(f"Unknown TTS provider: {self.provider}")

    def is_available(self) -> bool:
        if self.provider == TTSProvider.EDGE:
            return self._edge_is_available()
        elif self.provider == TTSProvider.OPENAI:
            return self.config.api_key is not None
        elif self.provider == TTSProvider.PYTTSX3:
            return self._pyttsx3_is_available()
        else:
            return False

    def _edge_is_available(self) -> bool:
        try:
            import edge_tts
            return True
        except ImportError:
            return False

    async def _edge_synthesize(self, text: str, voice: str = "default") -> bytes:
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            voice if voice != "default" else self.config.voice_id,
            rate=self.config.rate,
            pitch=self.config.pitch,
            volume=self.config.volume,
        )
        audio = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return audio

    async def _edge_synthesize_stream(self, text: str, voice: str = "default") -> AsyncIterator[bytes]:
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            voice if voice != "default" else self.config.voice_id,
            rate=self.config.rate,
            pitch=self.config.pitch,
            volume=self.config.volume,
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    def _edge_get_voices(self) -> list[Voice]:
        import edge_tts
        voices = edge_tts.list_voices()
        return [
            Voice(
                id=v["Name"],
                name=v["Name"],
                language=v["Locale"],
                gender=v.get("Gender"),
                provider=TTSProvider.EDGE,
            )
            for v in voices
        ]

    async def _openai_synthesize(self, text: str, voice: str = "default") -> bytes:
        import openai

        client = openai.OpenAI(api_key=self.config.api_key)
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice if voice != "default" else "alloy",
            input=text,
            response_format=self.config.output_format,
        )
        return response.read()

    def _openai_get_voices(self) -> list[Voice]:
        return [
            Voice(id="alloy", name="Alloy", language="en", gender="neutral", provider=TTSProvider.OPENAI),
            Voice(id="echo", name="Echo", language="en", gender="neutral", provider=TTSProvider.OPENAI),
            Voice(id="fable", name="Fable", language="en", gender="neutral", provider=TTSProvider.OPENAI),
            Voice(id="onyx", name="Onyx", language="en", gender="neutral", provider=TTSProvider.OPENAI),
            Voice(id="nova", name="Nova", language="en", gender="neutral", provider=TTSProvider.OPENAI),
            Voice(id="shimmer", name="Shimmer", language="en", gender="neutral", provider=TTSProvider.OPENAI),
        ]

    def _pyttsx3_is_available(self) -> bool:
        try:
            import pyttsx3
            return True
        except ImportError:
            return False

    async def _pyttsx3_synthesize(self, text: str, voice: str = "default") -> bytes:
        loop = asyncio.get_event_loop()
        engine = await loop.run_in_executor(None, pyttsx3.init)
        voices = engine.getProperty("voices")
        if voice != "default" and voices:
            for v in voices:
                if voice.lower() in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
        import io
        import wave

        buffer = io.BytesIO()
        engine.save_to_file(text, "temp_audio.mp3")
        engine.runAndWait()
        with open("temp_audio.mp3", "rb") as f:
            audio = f.read()
        import os
        try:
            os.remove("temp_audio.mp3")
        except OSError:
            pass
        return audio

    def _pyttsx3_get_voices(self) -> list[Voice]:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        return [
            Voice(
                id=v.id,
                name=v.name,
                language=getattr(v, "languages", ["en-US"])[0] if hasattr(v, "languages") else "en-US",
                gender=None,
                provider=TTSProvider.PYTTSX3,
            )
            for v in voices
        ]
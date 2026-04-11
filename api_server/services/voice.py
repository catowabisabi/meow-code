"""
Voice service: audio recording for push-to-talk voice input.

Recording uses native audio capture (cpal) on macOS, Linux, and Windows
for in-process mic access. Falls back to SoX `rec` or arecord (ALSA)
on Linux if the native module is unavailable.
"""
import asyncio
import os
import platform
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Optional


# ─── Constants ───────────────────────────────────────────────────────

RECORDING_SAMPLE_RATE = 16000
RECORDING_CHANNELS = 1

# SoX silence detection: stop after this duration of silence
SILENCE_DURATION_SECS = '2.0'
SILENCE_THRESHOLD = '3%'

# ─── Native Audio Stub ───────────────────────────────────────────────

# ctypes/cffi stub for native audio (cpal).
# The actual implementation would use the cpal crate via FFI.
# This stub allows the service to compile and run without the native module.


def _is_native_audio_available() -> bool:
    """Stub: check if native audio module is available."""
    # TODO: Implement actual cpal detection via ctypes/cffi
    return False


def _start_native_recording(
    on_data: Callable[[bytes], None],
    on_end: Callable[[], None],
) -> bool:
    """Stub: start native recording via cpal."""
    # TODO: Implement actual cpal recording via ctypes/cffi
    return False


def _stop_native_recording() -> None:
    """Stub: stop native recording."""
    # TODO: Implement actual cpal stop via ctypes/cffi
    pass


def _is_native_recording_active() -> bool:
    """Stub: check if native recording is active."""
    # TODO: Implement actual cpal state check via ctypes/cffi
    return False


# ─── Types ───────────────────────────────────────────────────────────


@dataclass
class VoiceInput:
    audio_data: bytes
    duration_ms: int
    format: str = "mp3"
    transcription: Optional[str] = None


@dataclass
class VoiceOutput:
    audio_data: bytes
    duration_ms: int
    format: str = "mp3"


@dataclass
class RecordingAvailability:
    available: bool
    reason: Optional[str] = None


@dataclass
class VoiceDependencies:
    available: bool
    missing: list[str] = field(default_factory=list)
    install_command: Optional[str] = None


# ─── State ───────────────────────────────────────────────────────────

_active_recorder: Optional[subprocess.Popen] = None
_native_recording_active = False


# ─── Dependency Check ────────────────────────────────────────────────


def _has_command(cmd: str) -> bool:
    """
    Check if a command exists in PATH.
    
    Spawn the target directly instead of `which cmd`. On Termux/Android
    `which` is a shell builtin — the external binary is absent or
    kernel-blocked (EPERM) when spawned from Node.
    """
    try:
        result = subprocess.run(
            [cmd, '--version'],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
        return result.returncode == 0 or result.returncode != 127
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except PermissionError:
        return False


# ─── Package Manager Detection ────────────────────────────────────────


@dataclass
class PackageManagerInfo:
    cmd: str
    args: list[str]
    display_command: str


def _detect_package_manager() -> Optional[PackageManagerInfo]:
    """Detect the system package manager and return install command for SoX."""
    system = platform.system().lower()
    
    if system == 'darwin':
        if _has_command('brew'):
            return PackageManagerInfo(
                cmd='brew',
                args=['install', 'sox'],
                display_command='brew install sox',
            )
        return None
    
    if system == 'linux':
        if _has_command('apt-get'):
            return PackageManagerInfo(
                cmd='sudo',
                args=['apt-get', 'install', '-y', 'sox'],
                display_command='sudo apt-get install sox',
            )
        if _has_command('dnf'):
            return PackageManagerInfo(
                cmd='sudo',
                args=['dnf', 'install', '-y', 'sox'],
                display_command='sudo dnf install sox',
            )
        if _has_command('pacman'):
            return PackageManagerInfo(
                cmd='sudo',
                args=['pacman', '-S', '--noconfirm', 'sox'],
                display_command='sudo pacman -S --noconfirm sox',
            )
    
    return None


# ─── Linux Audio Detection ───────────────────────────────────────────


async def _probe_arecord() -> tuple[bool, str]:
    """
    Probe whether arecord can actually open a capture device.
    
    hasCommand() only checks PATH; on WSL1/Win10-WSL2/headless Linux the binary exists
    but fails at open() because there is no ALSA card and no PulseAudio server.
    On WSL2+WSLg (Win11), PulseAudio works via RDP pipes and arecord succeeds.
    
    Returns (ok, stderr)
    """
    proc = await asyncio.create_subprocess_exec(
        'arecord',
        '-f', 'S16_LE',
        '-r', str(RECORDING_SAMPLE_RATE),
        '-c', str(RECORDING_CHANNELS),
        '-t', 'raw',
        '/dev/null',
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    
    try:
        # Race: if still alive after 150ms, device opened successfully
        await asyncio.sleep(0.15)
        
        if proc.returncode is None:
            # Still running = device opened successfully
            proc.kill()
            await proc.wait()
            return (True, '')
        
        # Process exited early
        stderr = ''
        if proc.stderr:
            try:
                stderr = await asyncio.wait_for(
                    proc.stderr.read(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass
        
        return (proc.returncode == 0, stderr.decode().strip() if stderr else '')
    
    except asyncio.TimeoutError:
        # Shouldn't happen with sleep(0.15), but handle anyway
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return (False, 'Timeout waiting for arecord')
    except Exception as e:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return (False, str(e))


async def _linux_has_alsa_cards() -> bool:
    """
    Check if Linux has ALSA sound cards available.
    
    cpal's ALSA backend writes to our process stderr when it can't find any
    sound cards. We check /proc/asound/cards to detect card presence.
    """
    try:
        with open('/proc/asound/cards', 'r', encoding='utf-8') as f:
            cards = f.read().strip()
            return cards != '' and 'no soundcards' not in cards.lower()
    except (FileNotFoundError, PermissionError, IOError):
        return False


# ─── Voice Service API ───────────────────────────────────────────────


class VoiceService:
    _enabled: bool = False
    _default_format: str = "mp3"
    
    @classmethod
    def configure(cls, enabled: bool, default_format: str = "mp3") -> None:
        cls._enabled = enabled
        cls._default_format = default_format
    
    @classmethod
    def is_enabled(cls) -> bool:
        return cls._enabled
    
    @classmethod
    async def transcribe_audio(cls, audio_data: bytes) -> Optional[str]:
        if not cls._enabled:
            return None
        
        return "Transcribed audio content placeholder"
    
    @classmethod
    async def synthesize_speech(
        cls,
        text: str,
        voice_id: Optional[str] = None,
    ) -> Optional[VoiceOutput]:
        if not cls._enabled:
            return None
        
        audio_data = b"placeholder_audio_data"
        duration_ms = len(text) * 10
        
        return VoiceOutput(
            audio_data=audio_data,
            duration_ms=duration_ms,
            format=cls._default_format,
        )
    
    @classmethod
    async def get_available_voices(cls) -> list[str]:
        return ["default_voice"]
    
    @classmethod
    def set_voice_preference(cls, voice_id: str) -> None:
        pass
    
    @classmethod
    async def start_voice_input(cls) -> bool:
        if not cls._enabled:
            return False
        return True
    
    @classmethod
    async def stop_voice_input(cls) -> bool:
        return True


# ─── Dependency Check API ───────────────────────────────────────────


async def check_voice_dependencies() -> VoiceDependencies:
    """
    Check if voice recording dependencies are available.
    
    Returns:
        VoiceDependencies with availability status, missing dependencies,
        and install command if applicable.
    """
    global _native_recording_active
    
    # Native audio module (cpal) handles everything on macOS, Linux, and Windows
    if _is_native_audio_available():
        return VoiceDependencies(available=True, missing=[], install_command=None)
    
    # Windows has no supported fallback
    if platform.system().lower() == 'windows':
        return VoiceDependencies(
            available=False,
            missing=['Voice mode requires the native audio module (not loaded)'],
            install_command=None,
        )
    
    # On Linux, arecord (ALSA utils) is a valid fallback recording backend
    if platform.system().lower() == 'linux' and _has_command('arecord'):
        return VoiceDependencies(available=True, missing=[], install_command=None)
    
    missing: list[str] = []
    
    if not _has_command('rec'):
        missing.append('sox (rec command)')
    
    pm = _detect_package_manager() if missing else None
    return VoiceDependencies(
        available=len(missing) == 0,
        missing=missing,
        install_command=pm.display_command if pm else None,
    )


# ─── Recording Availability API ─────────────────────────────────────


async def check_recording_availability() -> RecordingAvailability:
    """
    Probe-record through the full fallback chain (native → arecord → SoX)
    to verify that at least one backend can record.
    
    Returns:
        RecordingAvailability with availability status and reason if unavailable.
    """
    # Remote environments have no local microphone
    if os.environ.get('CLAUDE_CODE_REMOTE'):
        return RecordingAvailability(
            available=False,
            reason=(
                'Voice mode requires microphone access, but no audio device is available in this environment.\n\n'
                'To use voice mode, run Claude Code locally instead.'
            ),
        )
    
    # Native audio module (cpal) handles everything on macOS, Linux, and Windows
    if _is_native_audio_available():
        return RecordingAvailability(available=True, reason=None)
    
    # Windows has no supported fallback
    if platform.system().lower() == 'windows':
        return RecordingAvailability(
            available=False,
            reason='Voice recording requires the native audio module, which could not be loaded.',
        )
    
    wsl_no_audio_reason = (
        'Voice mode could not access an audio device in WSL.\n\n'
        'WSL2 with WSLg (Windows 11) provides audio via PulseAudio — '
        'if you are on Windows 10 or WSL1, run Claude Code in native Windows instead.'
    )
    
    # On Linux (including WSL), probe arecord
    if platform.system().lower() == 'linux' and _has_command('arecord'):
        probe_ok, probe_stderr = await _probe_arecord()
        if probe_ok:
            return RecordingAvailability(available=True, reason=None)
        
        # Check if running on WSL
        if _is_wsl():
            return RecordingAvailability(available=False, reason=wsl_no_audio_reason)
    
    # Fallback: check for SoX
    if not _has_command('rec'):
        if _is_wsl():
            return RecordingAvailability(available=False, reason=wsl_no_audio_reason)
        
        pm = _detect_package_manager()
        if pm:
            return RecordingAvailability(
                available=False,
                reason=f'Voice mode requires SoX for audio recording. Install it with: {pm.display_command}',
            )
        return RecordingAvailability(
            available=False,
            reason=(
                'Voice mode requires SoX for audio recording. Install SoX manually:\n'
                '  macOS: brew install sox\n'
                '  Ubuntu/Debian: sudo apt-get install sox\n'
                '  Fedora: sudo dnf install sox'
            ),
        )
    
    return RecordingAvailability(available=True, reason=None)


def _is_wsl() -> bool:
    """Check if running on Windows Subsystem for Linux."""
    try:
        with open('/proc/version', 'r', encoding='utf-8') as f:
            version = f.read().lower()
            return 'microsoft' in version or 'wsl' in version
    except (FileNotFoundError, PermissionError, IOError):
        return False


# ─── Recording API ───────────────────────────────────────────────────


async def start_recording(
    on_data: Callable[[bytes], None],
    on_end: Callable[[], None],
    options: Optional[dict] = None,
) -> bool:
    """
    Start audio recording with the best available backend.
    
    Args:
        on_data: Callback for each audio data chunk
        on_end: Callback when recording ends
        options: Optional dict with silenceDetection key
    
    Returns:
        True if recording started successfully, False otherwise.
    """
    global _active_recorder, _native_recording_active
    
    options = options or {}
    
    # Try native audio module first (macOS, Linux, Windows via cpal)
    native_available = (
        _is_native_audio_available() and
        (platform.system().lower() != 'linux' or await _linux_has_alsa_cards())
    )
    
    if native_available:
        # Ensure any previous recording is fully stopped
        if _native_recording_active or _is_native_recording_active():
            _stop_native_recording()
            _native_recording_active = False
        
        started = _start_native_recording(on_data, on_end)
        if started:
            _native_recording_active = True
            return True
        # Native recording failed — fall through to platform fallbacks
    
    # Windows has no supported fallback
    if platform.system().lower() == 'windows':
        return False
    
    # On Linux, try arecord (ALSA utils) before SoX
    if platform.system().lower() == 'linux' and _has_command('arecord'):
        probe_ok, _ = await _probe_arecord()
        if probe_ok:
            return _start_arecord_recording(on_data, on_end)
    
    # Fallback: SoX rec (Linux, or macOS if native module unavailable)
    return _start_sox_recording(on_data, on_end, options)


def _start_sox_recording(
    on_data: Callable[[bytes], None],
    on_end: Callable[[], None],
    options: Optional[dict] = None,
) -> bool:
    """
    Start recording using SoX rec command.
    
    Records raw PCM: 16 kHz, 16-bit signed, mono, to stdout.
    """
    global _active_recorder
    
    options = options or {}
    use_silence_detection = options.get('silence_detection', True)
    
    # Build SoX arguments
    args = [
        '-q',  # quiet
        '--buffer', '1024',  # Flush audio in small chunks
        '-t', 'raw',
        '-r', str(RECORDING_SAMPLE_RATE),
        '-e', 'signed',
        '-b', '16',
        '-c', str(RECORDING_CHANNELS),
        '-',  # stdout
    ]
    
    # Add silence detection filter (auto-stop on silence)
    if use_silence_detection:
        args.extend([
            'silence',  # start/stop on silence
            '1', '0.1', SILENCE_THRESHOLD,
            '1', SILENCE_DURATION_SECS, SILENCE_THRESHOLD,
        ])
    
    try:
        proc = subprocess.Popen(
            ['rec'] + args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        _active_recorder = proc
        
        # Start a task to read stdout and call on_data
        async def read_stdout():
            try:
                loop = asyncio.get_event_loop()
                while True:
                    chunk = await loop.run_in_executor(None, proc.stdout.read, 4096)
                    if not chunk:
                        break
                    on_data(chunk)
            except Exception:
                pass
            finally:
                on_end()
        
        # Start background task for reading
        asyncio.create_task(read_stdout())
        
        return True
    
    except FileNotFoundError:
        _active_recorder = None
        on_end()
        return False
    except Exception:
        _active_recorder = None
        on_end()
        return False


def _start_arecord_recording(
    on_data: Callable[[bytes], None],
    on_end: Callable[[], None],
) -> bool:
    """
    Start recording using arecord (ALSA utils).
    
    Records raw PCM: 16 kHz, 16-bit signed little-endian, mono, to stdout.
    """
    global _active_recorder
    
    args = [
        '-f', 'S16_LE',  # signed 16-bit little-endian
        '-r', str(RECORDING_SAMPLE_RATE),
        '-c', str(RECORDING_CHANNELS),
        '-t', 'raw',  # raw PCM, no WAV header
        '-q',  # quiet
        '-',  # write to stdout
    ]
    
    try:
        proc = subprocess.Popen(
            ['arecord'] + args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        
        _active_recorder = proc
        
        # Start a task to read stdout and call on_data
        async def read_stdout():
            try:
                loop = asyncio.get_event_loop()
                while True:
                    chunk = await loop.run_in_executor(None, proc.stdout.read, 4096)
                    if not chunk:
                        break
                    on_data(chunk)
            except Exception:
                pass
            finally:
                on_end()
        
        # Start background task for reading
        asyncio.create_task(read_stdout())
        
        return True
    
    except FileNotFoundError:
        _active_recorder = None
        on_end()
        return False
    except Exception:
        _active_recorder = None
        on_end()
        return False


def stop_recording() -> None:
    """
    Stop the current recording.
    
    Handles both native recording (cpal) and subprocess-based recording (SoX/arecord).
    """
    global _active_recorder, _native_recording_active
    
    if _native_recording_active:
        _stop_native_recording()
        _native_recording_active = False
        return
    
    if _active_recorder:
        try:
            _active_recorder.kill(signal.SIGTERM)
            _active_recorder.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                _active_recorder.kill(signal.SIGKILL)
            except ProcessLookupError:
                pass
        finally:
            _active_recorder = None


# ─── Permission Check ────────────────────────────────────────────────


async def request_microphone_permission() -> bool:
    """
    Request microphone permission by attempting to start and stop a recording.
    
    On macOS this triggers the TCC permission dialog on first use.
    
    Returns:
        True if permission was granted (recording could start), False otherwise.
    """
    if not _is_native_audio_available():
        return True  # non-native platforms skip this check
    
    started = await start_recording(
        lambda chunk: None,  # discard audio data
        lambda: None,  # ignore silence-detection end signal
        {'silence_detection': False},
    )
    
    if started:
        stop_recording()
        return True
    
    return False

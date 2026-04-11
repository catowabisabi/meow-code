import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pathlib import Path


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


LOG_LEVEL_VALUES = {
    LogLevel.DEBUG: logging.DEBUG,
    LogLevel.INFO: logging.INFO,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.CRITICAL: logging.CRITICAL,
}


@dataclass
class LogEntry:
    timestamp: float
    level: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None


@dataclass
class LoggerConfig:
    min_level: LogLevel = LogLevel.INFO
    log_to_file: bool = True
    log_to_console: bool = True
    log_dir: Optional[Path] = None
    max_file_size_mb: int = 10
    backup_count: int = 5


class InternalLogger:
    _instance: Optional["InternalLogger"] = None
    _entries: List[LogEntry] = []
    _max_entries: int = 5000
    
    def __init__(self, config: Optional[LoggerConfig] = None):
        self.config = config or LoggerConfig()
        self._logger = logging.getLogger("cato_claude")
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        self._logger.setLevel(logging.DEBUG)
        self._logger.handlers.clear()
        
        if self.config.log_to_console:
            console = logging.StreamHandler(sys.stdout)
            console.setLevel(LOG_LEVEL_VALUES.get(self.config.min_level, logging.INFO))
            console.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            self._logger.addHandler(console)
        
        if self.config.log_to_file and self.config.log_dir:
            self.config.log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                self.config.log_dir / "cato_claude.log",
                encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
            self._logger.addHandler(file_handler)
    
    def _should_log(self, level: LogLevel) -> bool:
        return LOG_LEVEL_VALUES.get(level, logging.INFO) >= LOG_LEVEL_VALUES.get(self.config.min_level, logging.INFO)
    
    def log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> None:
        if not self._should_log(level):
            return
        
        entry = LogEntry(
            timestamp=datetime.utcnow().timestamp(),
            level=level.value,
            message=message,
            context=context or {},
            source=source,
        )
        self._entries.append(entry)
        
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        
        log_method = getattr(self._logger, level.value)
        log_method(message, extra={"context": context})
    
    def debug(self, message: str, context: Optional[Dict[str, Any]] = None, source: Optional[str] = None) -> None:
        self.log(LogLevel.DEBUG, message, context, source)
    
    def info(self, message: str, context: Optional[Dict[str, Any]] = None, source: Optional[str] = None) -> None:
        self.log(LogLevel.INFO, message, context, source)
    
    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, source: Optional[str] = None) -> None:
        self.log(LogLevel.WARNING, message, context, source)
    
    def error(self, message: str, context: Optional[Dict[str, Any]] = None, source: Optional[str] = None) -> None:
        self.log(LogLevel.ERROR, message, context, source)
    
    def critical(self, message: str, context: Optional[Dict[str, Any]] = None, source: Optional[str] = None) -> None:
        self.log(LogLevel.CRITICAL, message, context, source)
    
    def get_entries(self, limit: int = 100, level: Optional[LogLevel] = None) -> List[LogEntry]:
        entries = self._entries
        if level:
            entries = [e for e in entries if e.level == level.value]
        return entries[-limit:]
    
    def clear_entries(self) -> None:
        self._entries.clear()
    
    def set_level(self, level: LogLevel) -> None:
        self.config.min_level = level


_logger: Optional[InternalLogger] = None


def get_logger() -> InternalLogger:
    global _logger
    if _logger is None:
        _logger = InternalLogger()
    return _logger


def set_log_level(level: LogLevel) -> None:
    get_logger().set_level(level)
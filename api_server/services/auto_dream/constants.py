"""
Constants for the Auto Dream memory consolidation system.
"""

SESSION_SCAN_INTERVAL_MS = 10 * 60 * 1000  # 10 minutes

DEFAULTS = {
    "min_hours": 24.0,
    "min_sessions": 3,
}

AUTO_DREAM_FEATURE_FLAG = "auto-dream-memory-consolidation"

LOCK_FILE_NAME = ".consolidate-lock"

MAX_DREAM_TURNS = 50

DREAM_PHASE_STARTING = "starting"
DREAM_PHASE_UPDATING = "updating"

DREAM_STATUS_RUNNING = "running"
DREAM_STATUS_COMPLETED = "completed"
DREAM_STATUS_FAILED = "failed"
DREAM_STATUS_KILLED = "killed"

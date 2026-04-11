"""
Shared analytics configuration.

Determines when analytics should be disabled across all analytics systems.
"""

import os


def is_analytics_disabled() -> bool:
    if os.getenv("NODE_ENV") == "test":
        return True

    if os.getenv("CLAUDE_CODE_USE_BEDROCK"):
        return True

    if os.getenv("CLAUDE_CODE_USE_VERTEX"):
        return True

    if os.getenv("CLAUDE_CODE_USE_FOUNDRY"):
        return True

    try:
        from api_server.services.privacy import is_telemetry_disabled as _is_telemetry_disabled

        return _is_telemetry_disabled()
    except Exception:
        pass

    return False


def is_feedback_survey_disabled() -> bool:
    if os.getenv("NODE_ENV") == "test":
        return True

    try:
        from api_server.services.privacy import is_telemetry_disabled as _is_telemetry_disabled

        return _is_telemetry_disabled()
    except Exception:
        pass

    return False
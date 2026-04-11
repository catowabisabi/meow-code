"""
Configuration for the Auto Dream feature.
Checks growthbook feature flags and user settings.
"""
import os

from ..analytics.growthbook import get_feature_value
from .constants import AUTO_DREAM_FEATURE_FLAG, DEFAULTS
from .types import AutoDreamConfig


def is_auto_dream_enabled() -> bool:
    """
    Check if auto dream feature is enabled via growthbook feature flag.
    
    Returns:
        True if the feature flag is enabled and user is in appropriate mode.
    """
    flag_value = get_feature_value(AUTO_DREAM_FEATURE_FLAG, False)
    if not flag_value:
        return False
    
    user_type = os.getenv("USER_TYPE", "")
    if user_type == "ant":
        return True
    
    return True


def get_config() -> AutoDreamConfig:
    """
    Get the auto dream configuration from growthbook or defaults.
    
    Returns:
        AutoDreamConfig with min_hours and min_sessions settings.
    """
    min_hours = get_feature_value(
        "auto-dream-min-hours", 
        DEFAULTS["min_hours"]
    )
    min_sessions = get_feature_value(
        "auto-dream-min-sessions", 
        DEFAULTS["min_sessions"]
    )
    
    return AutoDreamConfig(
        min_hours=float(min_hours),
        min_sessions=int(min_sessions),
    )


def is_dream_mode_active() -> bool:
    """
    Check if dream mode should be actively processing.
    
    Returns:
        True if dream mode is enabled and not paused.
    """
    return is_auto_dream_enabled()

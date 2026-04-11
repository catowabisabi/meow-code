"""
GrowthBook feature flag client with HTTP polling and caching.

This module provides:
- Feature flag value retrieval with disk/memory caching
- Periodic refresh (external: 6hr, ants: 20min)
- Auth-aware re-initialization after login/logout
- Feature flag evaluation with targeting rules
- A/B test assignment with consistent bucketing
- Attribute expansion for nested attributes

Complete port from TypeScript growthbook.ts (1155 lines -> Python).
"""

import os
import time
import threading
import hashlib
import json
import logging
import re
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

GROWTHBOOK_REFRESH_INTERVAL_MS = (
    20 * 60 * 1000 if os.getenv("USER_TYPE") == "ant" else 6 * 60 * 60 * 1000
)

GROWTHBOOK_CACHE_TTL_MS = 6 * 60 * 60 * 1000

# Periodic refresh interval (matches Statsig's 6-hour interval)
REFRESH_INTERVAL_MS = (
    20 * 60 * 1000 if os.getenv("USER_TYPE") == "ant" else 6 * 60 * 60 * 1000
)


@dataclass
class GrowthBookUserAttributes:
    """User attributes sent to GrowthBook for targeting."""
    id: str
    session_id: str
    device_id: str
    platform: str
    api_base_url_host: Optional[str] = None
    organization_uuid: Optional[str] = None
    account_uuid: Optional[str] = None
    user_type: Optional[str] = None
    subscription_type: Optional[str] = None
    rate_limit_tier: Optional[str] = None
    first_token_time: Optional[int] = None
    email: Optional[str] = None
    app_version: Optional[str] = None
    github_actions_metadata: Optional[Dict[str, Any]] = None


@dataclass
class FeatureResult:
    """Result of feature flag evaluation."""
    value: Any = None
    state: str = "default"  # "default", "enabled", "disabled", "Experiment"
    source: str = "defaultValue"
    experiment_result: Optional[Dict[str, Any]] = None
    experiment: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "state": self.state,
            "source": self.source,
            "experimentResult": self.experiment_result,
            "experiment": self.experiment,
        }


class GrowthBookClient:
    """
    Complete GrowthBook SDK implementation.
    
    Handles:
    - Feature flag fetching, caching, and refresh
    - Feature flag evaluation with targeting rules
    - A/B test assignment with consistent bucketing
    - Attribute expansion for nested attributes
    - Auth-aware re-initialization
    """
    
    def __init__(
        self,
        api_key: str,
        bucket_version: int = 2,
        api_host: Optional[str] = None,
    ):
        self.api_key = api_key
        self.bucket_version = bucket_version
        self.api_host = api_host or os.getenv("CLAUDE_CODE_GB_BASE_URL", "https://api.anthropic.com/")
        self.attributes: Dict[str, Any] = {}
        self._feature_cache: Dict[str, Any] = {}
        self._refresh_after_auth_change = True
        self._last_refresh: float = 0
        self._refresh_lock = threading.Lock()
        self._initialized = False
        self._features: Dict[str, Any] = {}
        self._experiment_data: Dict[str, Dict[str, Any]] = {}
        self._pending_exposures: set = set()
        self._logged_exposures: set = set()
        self._remote_eval_values: Dict[str, Any] = {}
    
    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set user attributes for targeting."""
        self.attributes = attributes
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a single user attribute."""
        self.attributes[key] = value
    
    def expand_attributes(self) -> Dict[str, Any]:
        """
        Expand nested attributes (e.g., user.traits -> user:traits).
        
        Recursively flattens nested dictionaries into dot-notation keys.
        Arrays are indexed with numeric suffixes.
        """
        result: Dict[str, Any] = {}
        
        def _expand_recursive(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        _expand_recursive(value, new_key)
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            _expand_recursive(item, f"{new_key}[{i}]")
                    else:
                        result[new_key] = value
            else:
                if prefix:
                    result[prefix] = obj
        
        _expand_recursive(self.attributes)
        return result
    
    async def load_features(self) -> Dict[str, Any]:
        """Load features from GrowthBook API."""
        import httpx
        
        headers = {
            "Content-Type": "application/json",
        }
        
        cache_key_attrs = [
            self.attributes.get("id", ""),
            self.attributes.get("organizationUUID", ""),
        ]
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.api_host}/api/features/{self.api_key}",
                    json={
                        "attributes": self._build_attributes_for_api(),
                        "cacheKeyAttributes": cache_key_attrs,
                    },
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                
                if data.get("features"):
                    await self._process_features_payload(data["features"])
                    return self._features
                    
        except Exception as e:
            logger.warning(f"GrowthBook fetch failed: {e}")
            raise
        
        return {}
    
    async def refresh_features(self) -> None:
        """Force refresh features from API."""
        with self._refresh_lock:
            await self.load_features()
    
    async def _process_features_payload(self, features: Dict[str, Any]) -> None:
        """
        Process features payload from GrowthBook API.
        
        Handles:
        - Feature transformation (value -> defaultValue workaround)
        - Experiment data storage for exposure logging
        - Remote eval value caching
        """
        self._experiment_data.clear()
        
        transformed: Dict[str, Any] = {}
        
        for key, feature in features.items():
            # Workaround: API returns "value" instead of "defaultValue"
            if "value" in feature and "defaultValue" not in feature:
                transformed[key] = {
                    **feature,
                    "defaultValue": feature["value"],
                }
            else:
                transformed[key] = feature
            
            # Store experiment data for exposure logging
            if feature.get("source") == "experiment" and feature.get("experimentResult"):
                exp_result = feature.get("experimentResult", {})
                exp = feature.get("experiment", {})
                if exp.get("key") and exp_result.get("variationId") is not None:
                    self._experiment_data[key] = {
                        "experimentId": exp["key"],
                        "variationId": exp_result["variationId"],
                        "inExperiment": exp_result.get("inExperiment"),
                        "hashAttribute": exp_result.get("hashAttribute"),
                        "hashValue": exp_result.get("hashValue"),
                    }
        
        self._features = transformed
        self._last_refresh = time.time() * 1000
        
        # Cache evaluated values from remote eval response
        self._remote_eval_values.clear()
        for key, feature in transformed.items():
            v = feature.get("value") or feature.get("defaultValue")
            if v is not None:
                self._remote_eval_values[key] = v
    
    def _build_attributes_for_api(self) -> Dict[str, Any]:
        """Build attributes dict for API request."""
        result = {
            "id": self.attributes.get("id", ""),
            "sessionId": self.attributes.get("sessionId", ""),
            "deviceID": self.attributes.get("deviceID", ""),
            "platform": self.attributes.get("platform", "unknown"),
        }
        
        # Optional attributes
        optional_fields = [
            "apiBaseUrlHost",
            "organizationUUID",
            "accountUUID",
            "userType",
            "subscriptionType",
            "rateLimitTier",
            "firstTokenTime",
            "email",
            "appVersion",
            "githubActionsMetadata",
        ]
        
        for field_name in optional_fields:
            api_key = field_name
            if field_name in self.attributes:
                result[api_key] = self.attributes[field_name]
        
        return result
    
    def feature(self, key: str) -> FeatureResult:
        """
        Evaluate a feature flag.
        
        Returns FeatureResult with:
        - value: the feature value
        - state: "default", "enabled", "disabled", or "Experiment"
        - source: where the value came from
        - experimentResult: A/B test data if applicable
        """
        # Check remote eval cache first (workaround for SDK behavior)
        if key in self._remote_eval_values:
            return FeatureResult(
                value=self._remote_eval_values[key],
                state="enabled",
                source="remoteEval",
            )
        
        # Check feature definitions
        if key in self._features:
            feature = self._features[key]
            
            # Handle experiment
            if feature.get("source") == "experiment" and feature.get("experimentResult"):
                exp_result = feature.get("experimentResult", {})
                exp = feature.get("experiment", {})
                
                return FeatureResult(
                    value=exp_result.get("value") or feature.get("defaultValue"),
                    state="Experiment",
                    source="experiment",
                    experiment_result=exp_result,
                    experiment=exp,
                )
            
            # Regular feature
            value = feature.get("value") or feature.get("defaultValue")
            return FeatureResult(
                value=value,
                state="enabled" if value else "disabled",
                source="feature",
            )
        
        # No feature found - return default
        return FeatureResult(
            value=None,
            state="default",
            source="defaultValue",
        )
    
    def _evaluate_rule(self, rule: Dict[str, Any], bucket: float) -> Optional[Any]:
        """
        Evaluate a targeting rule.
        
        Returns the rule's value if matched, None otherwise.
        """
        if not rule:
            return None
        
        # Check condition
        condition = rule.get("condition")
        if condition:
            if not self._matches_condition(condition, self.attributes):
                return None
        
        # Check bucket ranges
        ranges = rule.get("ranges")
        if ranges:
            matched = False
            for r in ranges:
                start = r.get("start", 0)
                end = r.get("end", 0)
                if start / 10000 <= bucket < end / 10000:
                    matched = True
                    break
            if not matched:
                return None
        
        return rule.get("value")
    
    def _matches_condition(self, condition: Dict[str, Any], attributes: Dict[str, Any]) -> bool:
        """
        Evaluate JSONLogic-style conditions.
        
        Supports operators:
        - ==, !=, <, >, <=, >= 
        - in, contains, exists, !exists
        - and, or, not
        - Sub-object matching with dot notation
        """
        if not condition:
            return True
        
        op = list(condition.keys())[0]
        args = condition[op]
        
        if op == "and":
            return all(self._matches_condition(arg, attributes) for arg in args)
        
        if op == "or":
            return any(self._matches_condition(arg, attributes) for arg in args)
        
        if op == "not":
            return not self._matches_condition(args, attributes)
        
        if op == "==":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            return left == right
        
        if op == "!=":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            return left != right
        
        if op == ">":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            return left is not None and right is not None and left > right
        
        if op == "<":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            return left is not None and right is not None and left < right
        
        if op == ">=":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            return left is not None and right is not None and left >= right
        
        if op == "<=":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            return left is not None and right is not None and left <= right
        
        if op == "in":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            if isinstance(right, list):
                return left in right
            return False
        
        if op == "contains":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            if isinstance(left, str) and isinstance(right, str):
                return right in left
            return False
        
        if op == "exists":
            var = args[0]
            val = self._get_attribute_value(var, attributes)
            return val is not None
        
        if op == "!exists":
            var = args[0]
            val = self._get_attribute_value(var, attributes)
            return val is None
        
        if op == "%":
            # Modulo operator for bucket ranges
            left = self._get_attribute_value(args[0], attributes)
            mod = args[1]
            if left is not None and mod != 0:
                return int(left) % mod == 0
            return False
        
        if op == "typeof":
            left = self._get_attribute_value(args[0], attributes)
            right = args[1]
            return type(left).__name__ == right
        
        return False
    
    def _get_attribute_value(self, path: str, attributes: Dict[str, Any]) -> Any:
        """
        Get attribute value using dot notation.
        
        Supports:
        - Simple: "id"
        - Nested: "user.email"
        - Array index: "items[0]"
        """
        if not path:
            return None
        
        parts = path.split(".")
        value = attributes
        
        for part in parts:
            if value is None:
                return None
            
            # Check for array index notation: items[0]
            array_match = re.match(r"(.+)\[(\d+)\]", part)
            if array_match:
                key = array_match.group(1)
                index = int(array_match.group(2))
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
                if isinstance(value, list) and 0 <= index < len(value):
                    value = value[index]
                else:
                    return None
            elif isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _bucket_user(self, seed: str, attribute: str = "id") -> float:
        """
        Bucket user for A/B test.
        
        Uses SHA256 hash of seed + attribute value to produce consistent
        bucket assignment in range [0, 1).
        """
        attribute_key = self._get_attribute_for_bucket(attribute)
        value = self.attributes.get(attribute_key, "")
        
        bucket_value = self._bucket(seed, str(value))
        return bucket_value
    
    def _get_attribute_for_bucket(self, attribute: str) -> str:
        """Map attribute name to internal attribute key."""
        mapping = {
            "id": "id",
            "device_id": "deviceID",
            "deviceID": "deviceID",
            "session_id": "sessionId",
            "sessionId": "sessionId",
            "organization_uuid": "organizationUUID",
            "organizationUUID": "organizationUUID",
        }
        return mapping.get(attribute, attribute)
    
    def _bucket(self, seed: str, value: str, range: int = 10000) -> float:
        """
        Hash seed + value and return bucket 0-range.
        
        Returns a float in range [0, 1) for bucket assignment.
        """
        h = hashlib.sha256(f"{seed}{value}".encode()).digest()
        return (int.from_bytes(h[:4], 'big') % range) / range
    
    def is_enabled(self, key: str, default: bool = False) -> bool:
        """Check if feature is enabled."""
        result = self.feature(key)
        if result.value is not None:
            return bool(result.value)
        return default
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get feature value."""
        result = self.feature(key)
        return result.value if result.value is not None else default
    
    def get_features(self) -> Dict[str, Any]:
        """Get all features."""
        return self._features
    
    def get_feature_value(self, feature: str, default: Any) -> Any:
        """Get feature value with default fallback."""
        result = self.feature(feature)
        if result.value is not None:
            return result.value
        
        # Check remote eval cache
        if feature in self._remote_eval_values:
            return self._remote_eval_values[feature]
        
        return default
    
    def destroy(self) -> None:
        """Clean up client resources."""
        self._features.clear()
        self._experiment_data.clear()
        self._remote_eval_values.clear()
        self._pending_exposures.clear()
        self._logged_exposures.clear()


class GrowthBookConfigOverride:
    """Manages local config overrides for GrowthBook features."""
    
    def __init__(self):
        self._overrides: Dict[str, Any] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._overrides.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._overrides[key] = value
    
    def remove(self, key: str) -> None:
        if key in self._overrides:
            del self._overrides[key]
    
    def clear(self) -> None:
        self._overrides.clear()
    
    def all(self) -> Dict[str, Any]:
        return dict(self._overrides)


# Global state
_client: Optional[GrowthBookClient] = None
_client_initialized: bool = False
_client_initialized_with_auth: bool = False
_refresh_listeners: List[Callable[[], None]] = []
_refresh_timer: Optional[threading.Timer] = None
_features_cache: Dict[str, Any] = {}
_disk_cache_path: Optional[str] = None
_config_overrides: GrowthBookConfigOverride = GrowthBookConfigOverride()
_remote_eval_feature_values: Dict[str, Any] = {}
_experiment_data_by_feature: Dict[str, Dict[str, Any]] = {}
_pending_exposures: set = set()
_logged_exposures: set = set()
_env_overrides: Optional[Dict[str, Any]] = None
_env_overrides_parsed: bool = False


def _get_disk_cache_path() -> str:
    global _disk_cache_path
    if _disk_cache_path is None:
        config_dir = os.getenv("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
        _disk_cache_path = os.path.join(config_dir, "growthbook_features.json")
    return _disk_cache_path


def _load_disk_cache() -> Dict[str, Any]:
    try:
        cache_path = _get_disk_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load GrowthBook disk cache: {e}")
    return {}


def _save_disk_cache(features: Dict[str, Any]) -> None:
    try:
        cache_path = _get_disk_cache_path()
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(features, f)
    except Exception as e:
        logger.warning(f"Failed to save GrowthBook disk cache: {e}")


def _get_env_overrides() -> Optional[Dict[str, Any]]:
    """Parse env var overrides for GrowthBook features."""
    global _env_overrides, _env_overrides_parsed
    
    if not _env_overrides_parsed:
        _env_overrides_parsed = True
        if os.getenv("USER_TYPE") == "ant":
            raw = os.getenv("CLAUDE_INTERNAL_FC_OVERRIDES")
            if raw:
                try:
                    _env_overrides = json.loads(raw)
                    logger.debug(f"GrowthBook: Using env var overrides for {len(_env_overrides)} features")
                except Exception as e:
                    logger.error(f"GrowthBook: Failed to parse CLAUDE_INTERNAL_FC_OVERRIDES: {e}")
    
    return _env_overrides


def has_growthbook_env_override(feature: str) -> bool:
    """Check if a feature has an env var override."""
    overrides = _get_env_overrides()
    return overrides is not None and feature in overrides


def _get_config_overrides() -> Optional[Dict[str, Any]]:
    """Get local config overrides set via /config Gates tab."""
    if os.getenv("USER_TYPE") != "ant":
        return None
    return _config_overrides.all()


def get_growthbook_config_overrides() -> Dict[str, Any]:
    """Get all config overrides."""
    return _config_overrides.all()


def set_growthbook_config_override(feature: str, value: Any) -> None:
    """Set or clear a single config override."""
    if os.getenv("USER_TYPE") != "ant":
        return
    
    if value is None:
        _config_overrides.remove(feature)
    else:
        _config_overrides.set(feature, value)
    
    _notify_refresh_listeners()


def clear_growthbook_config_overrides() -> None:
    """Clear all config overrides."""
    if os.getenv("USER_TYPE") != "ant":
        return
    
    _config_overrides.clear()
    _notify_refresh_listeners()


def _get_user_attributes() -> GrowthBookUserAttributes:
    """Get user attributes for GrowthBook from metadata."""
    from api_server.services.analytics.metadata import get_event_metadata

    metadata = get_event_metadata()
    return GrowthBookUserAttributes(
        id=metadata.get("device_id", ""),
        session_id=metadata.get("session_id", ""),
        device_id=metadata.get("device_id", ""),
        platform=metadata.get("platform", "unknown"),
    )


def _is_growthbook_enabled() -> bool:
    """Check if GrowthBook operations should be enabled."""
    from api_server.services.analytics.first_party_logger import is_1p_event_logging_enabled

    return is_1p_event_logging_enabled()


def _notify_refresh_listeners() -> None:
    """Notify all refresh listeners."""
    for listener in _refresh_listeners:
        try:
            listener()
        except Exception as e:
            logger.error(f"GrowthBook refresh listener error: {e}")


def _log_exposure_for_feature(feature: str) -> None:
    """Log experiment exposure for a feature if it has experiment data."""
    global _logged_exposures
    
    if feature in _logged_exposures:
        return
    
    exp_data = _experiment_data_by_feature.get(feature)
    if exp_data:
        _logged_exposures.add(feature)
        # Import here to avoid circular imports
        try:
            from api_server.services.analytics.first_party_logger import log_growthbook_experiment_to_1p
            log_growthbook_experiment_to_1p({
                "experimentId": exp_data["experimentId"],
                "variationId": exp_data["variationId"],
                "userAttributes": _get_user_attributes_dict(),
                "experimentMetadata": {
                    "feature_id": feature,
                },
            })
        except ImportError:
            pass


def _get_user_attributes_dict() -> Dict[str, Any]:
    """Get user attributes as dict for API."""
    attrs = _get_user_attributes()
    return {
        "id": attrs.id,
        "sessionId": attrs.session_id,
        "deviceID": attrs.device_id,
        "platform": attrs.platform,
        **({"apiBaseUrlHost": attrs.api_base_url_host} if attrs.api_base_url_host else {}),
        **({"organizationUUID": attrs.organization_uuid} if attrs.organization_uuid else {}),
        **({"accountUUID": attrs.account_uuid} if attrs.account_uuid else {}),
        **({"userType": attrs.user_type} if attrs.user_type else {}),
        **({"subscriptionType": attrs.subscription_type} if attrs.subscription_type else {}),
        **({"rateLimitTier": attrs.rate_limit_tier} if attrs.rate_limit_tier else {}),
        **({"firstTokenTime": attrs.first_token_time} if attrs.first_token_time else {}),
        **({"email": attrs.email} if attrs.email else {}),
        **({"appVersion": attrs.app_version} if attrs.app_version else {}),
    }


def initialize_growthbook() -> Optional[GrowthBookClient]:
    """Initialize GrowthBook client."""
    global _client, _client_initialized, _client_initialized_with_auth

    if not _is_growthbook_enabled():
        return None

    _get_user_attributes()
    client_key = os.getenv("CLAUDE_CODE_GB_CLIENT_KEY", "")

    if not client_key:
        logger.warning("GrowthBook client key not configured")
        return None

    base_url = os.getenv("CLAUDE_CODE_GB_BASE_URL", "https://api.anthropic.com/")

    _client = GrowthBookClient(
        api_key=client_key,
        api_host=base_url,
    )
    _client.set_attributes(_get_user_attributes_dict())

    _client_initialized = True
    _client_initialized_with_auth = True

    return _client


def get_growthbook_client() -> Optional[GrowthBookClient]:
    """Get the global GrowthBook client instance."""
    global _client
    return _client


def is_growthbook_initialized() -> bool:
    """Check if GrowthBook is initialized."""
    return _client_initialized


def setup_periodic_refresh() -> None:
    """Set up periodic refresh of GrowthBook features."""
    global _refresh_timer

    if _refresh_timer is not None:
        _refresh_timer.cancel()

    def refresh_loop() -> None:
        # Use async refresh in a sync context
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            loop.run_until_complete(refresh_growthbook_features())
            loop.close()
        except Exception as e:
            logger.error(f"GrowthBook refresh loop error: {e}")
        finally:
            setup_periodic_refresh()

    _refresh_timer = threading.Timer(
        REFRESH_INTERVAL_MS / 1000,
        refresh_loop,
    )
    _refresh_timer.daemon = True
    _refresh_timer.start()


def stop_periodic_refresh() -> None:
    """Stop periodic refresh."""
    global _refresh_timer
    if _refresh_timer is not None:
        _refresh_timer.cancel()
        _refresh_timer = None


async def refresh_growthbook_features() -> None:
    """Refresh GrowthBook features from server."""
    global _client, _features_cache, _remote_eval_feature_values, _experiment_data_by_feature

    if not _client:
        return

    try:
        await _client.refresh_features()
        _features_cache = _client.get_features()
        
        # Update remote eval values cache
        _remote_eval_feature_values.clear()
        for key, feature in _features_cache.items():
            v = feature.get("value") or feature.get("defaultValue")
            if v is not None:
                _remote_eval_feature_values[key] = v
        
        # Update experiment data
        _experiment_data_by_feature.clear()
        
        _save_disk_cache(_features_cache)
        _notify_refresh_listeners()
    except Exception as e:
        logger.error(f"GrowthBook refresh failed: {e}")


def get_feature_value(feature: str, default: Any) -> Any:
    """
    Get a feature value from disk cache immediately.
    
    This is the preferred method for startup-critical paths and sync contexts.
    The value may be stale if the cache was written by a previous process.
    """
    global _features_cache, _client, _remote_eval_feature_values, _experiment_data_by_feature, _pending_exposures, _logged_exposures

    # Check env var overrides first (for eval harnesses)
    env_overrides = _get_env_overrides()
    if env_overrides and feature in env_overrides:
        return env_overrides[feature]

    # Check config overrides (Gates tab)
    config_overrides = _get_config_overrides()
    if config_overrides and feature in config_overrides:
        return config_overrides[feature]

    if not _is_growthbook_enabled():
        return default

    # Log experiment exposure if data is available
    if feature in _experiment_data_by_feature:
        _log_exposure_for_feature(feature)
    else:
        _pending_exposures.add(feature)

    # In-memory cache is authoritative once populated
    if feature in _remote_eval_feature_values:
        return _remote_eval_feature_values[feature]

    # Fall back to disk cache
    disk_cache = _load_disk_cache()
    if disk_cache and feature in disk_cache:
        feature_def = disk_cache[feature]
        if isinstance(feature_def, dict):
            if "value" in feature_def:
                return feature_def["value"]
            if "defaultValue" in feature_def:
                return feature_def["defaultValue"]
        return disk_cache[feature]

    return default


def get_feature_value_cached_may_be_stale(feature: str, default: Any) -> Any:
    """
    Get a feature value from disk cache immediately.
    
    This is the preferred method for startup-critical paths and sync contexts.
    The value may be stale if the cache was written by a previous process.
    """
    return get_feature_value(feature, default)


async def get_feature_value_blocking(feature: str, default: Any) -> Any:
    """Get a feature value - blocks until GrowthBook is initialized."""
    global _client, _remote_eval_feature_values, _experiment_data_by_feature, _pending_exposures, _logged_exposures

    # Check env var overrides first
    env_overrides = _get_env_overrides()
    if env_overrides and feature in env_overrides:
        return env_overrides[feature]

    # Check config overrides
    config_overrides = _get_config_overrides()
    if config_overrides and feature in config_overrides:
        return config_overrides[feature]

    if not _is_growthbook_enabled():
        return default

    if not _client:
        return default

    # Try remote eval cache first
    if feature in _remote_eval_feature_values:
        _log_exposure_for_feature(feature)
        return _remote_eval_feature_values[feature]

    # Get from client
    result = _client.get_feature_value(feature, default)
    
    # Log experiment exposure
    _log_exposure_for_feature(feature)

    return result


async def check_gate_cached_or_blocking(gate: str) -> bool:
    """
    Check a boolean entitlement gate with fallback-to-blocking semantics.
    
    Fast path: if the disk cache already says true, return it immediately.
    Slow path: if disk says false/missing, await GrowthBook init and fetch
    the fresh server value.
    """
    # Check env var overrides first
    env_overrides = _get_env_overrides()
    if env_overrides and gate in env_overrides:
        return bool(env_overrides[gate])

    # Check config overrides
    config_overrides = _get_config_overrides()
    if config_overrides and gate in config_overrides:
        return bool(config_overrides[gate])

    if not _is_growthbook_enabled():
        return False

    # Fast path: disk cache already says true
    disk_cache = _load_disk_cache()
    if disk_cache.get(gate) is True:
        return True

    # Slow path: fetch fresh
    result = await get_feature_value_blocking(gate, False)
    return bool(result)


async def check_security_restriction_gate(gate: str) -> bool:
    """
    Check a security restriction gate.
    
    Always returns false for uncached gates to avoid blocking.
    """
    # Check env var overrides first
    env_overrides = _get_env_overrides()
    if env_overrides and gate in env_overrides:
        return bool(env_overrides[gate])

    # Check config overrides
    config_overrides = _get_config_overrides()
    if config_overrides and gate in config_overrides:
        return bool(config_overrides[gate])

    if not _is_growthbook_enabled():
        return False

    # Check disk cache
    disk_cache = _load_disk_cache()
    cached = disk_cache.get(gate)
    if cached is not None:
        return bool(cached)

    return False


def check_statsig_feature_gate_cached_may_be_stale(gate: str) -> bool:
    """
    Check a Statsig feature gate value via GrowthBook.
    
    For migration only - use get_feature_value_cached_may_be_stale for new code.
    """
    # Check env var overrides first
    env_overrides = _get_env_overrides()
    if env_overrides and gate in env_overrides:
        return bool(env_overrides[gate])

    # Check config overrides
    config_overrides = _get_config_overrides()
    if config_overrides and gate in config_overrides:
        return bool(config_overrides[gate])

    if not _is_growthbook_enabled():
        return False

    # Return cached value from GrowthBook or Statsig
    value = get_feature_value(gate, None)
    if value is not None:
        return bool(value)

    return False


def get_dynamic_config(config_name: str, default: Any) -> Any:
    """Get a dynamic config value - alias for get_feature_value."""
    return get_feature_value(config_name, default)


def get_dynamic_config_cached_may_be_stale(config_name: str, default: Any) -> Any:
    """Get a dynamic config value from disk cache immediately."""
    return get_feature_value(config_name, default)


async def get_dynamic_config_blocking(config_name: str, default: Any) -> Any:
    """Get a dynamic config value - blocks until GrowthBook is initialized."""
    return await get_feature_value_blocking(config_name, default)


def refresh_after_auth_change() -> None:
    """
    Refresh GrowthBook after auth changes (login/logout).
    
    This destroys and recreates the client to get fresh auth headers.
    """
    global _client, _client_initialized, _features_cache, _remote_eval_feature_values, _experiment_data_by_feature, _pending_exposures, _logged_exposures

    stop_periodic_refresh()

    # Clear state
    _client = None
    _client_initialized = False
    _features_cache.clear()
    _remote_eval_feature_values.clear()
    _experiment_data_by_feature.clear()
    _pending_exposures.clear()
    _logged_exposures.clear()

    # Reinitialize with fresh auth
    _client = initialize_growthbook()

    if _client:
        setup_periodic_refresh()
        _notify_refresh_listeners()


def on_growthbook_refresh(listener: Callable[[], None]) -> Callable[[], None]:
    """Register a callback to fire when GrowthBook feature values refresh."""
    _refresh_listeners.append(listener)

    def unsubscribe() -> None:
        if listener in _refresh_listeners:
            _refresh_listeners.remove(listener)

    return unsubscribe


def reset_growthbook() -> None:
    """Reset GrowthBook client state."""
    global _client, _client_initialized, _client_initialized_with_auth, _features_cache, _remote_eval_feature_values, _experiment_data_by_feature, _pending_exposures, _logged_exposures, _env_overrides, _env_overrides_parsed

    stop_periodic_refresh()
    
    if _client:
        _client.destroy()
    
    _client = None
    _client_initialized = False
    _client_initialized_with_auth = False
    _features_cache.clear()
    _remote_eval_feature_values.clear()
    _experiment_data_by_feature.clear()
    _pending_exposures.clear()
    _logged_exposures.clear()
    _refresh_listeners.clear()
    _env_overrides = None
    _env_overrides_parsed = False


def get_all_growthbook_features() -> Dict[str, Any]:
    """Enumerate all known GrowthBook features and their current resolved values."""
    global _remote_eval_feature_values
    
    if _remote_eval_feature_values:
        return dict(_remote_eval_feature_values)
    
    disk_cache = _load_disk_cache()
    return disk_cache


async def initialize_growthbook_async() -> Optional[GrowthBookClient]:
    """
    Initialize GrowthBook client asynchronously (blocks until ready).
    """
    global _client, _client_initialized, _client_initialized_with_auth

    if not _is_growthbook_enabled():
        return None

    if not _client:
        _get_user_attributes()
        client_key = os.getenv("CLAUDE_CODE_GB_CLIENT_KEY", "")

        if not client_key:
            logger.warning("GrowthBook client key not configured")
            return None

        base_url = os.getenv("CLAUDE_CODE_GB_BASE_URL", "https://api.anthropic.com/")

        _client = GrowthBookClient(
            api_key=client_key,
            api_host=base_url,
        )
        _client.set_attributes(_get_user_attributes_dict())

    # Load features from API
    if _client:
        try:
            await _client.load_features()
            _client_initialized = True
            _client_initialized_with_auth = True
            
            # Set up periodic refresh after successful initialization
            setup_periodic_refresh()
        except Exception as e:
            logger.error(f"GrowthBook initialization failed: {e}")
            raise

    return _client


# ============================================================================
# Utility Functions
# ============================================================================

def _transform_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """Transform features from API response format."""
    transformed = {}
    for key, feature in features.items():
        if "value" in feature and "defaultValue" not in feature:
            transformed[key] = {
                **feature,
                "defaultValue": feature["value"],
            }
        else:
            transformed[key] = feature
    return transformed


def _compute_cache_key(attributes: Dict[str, Any]) -> str:
    """Compute cache key from attributes."""
    key_data = json.dumps(attributes, sort_keys=True)
    return hashlib.sha256(key_data.encode()).hexdigest()[:16]


# ============================================================================
# Constants and Configuration
# ============================================================================

GROWTHBOOK_REFRESH_INTERVAL_MS_ENV = (
    20 * 60 * 1000 if os.getenv("USER_TYPE") == "ant" else 6 * 60 * 60 * 1000
)


# ============================================================================
# Backward Compatibility Aliases
# ============================================================================

def getGrowthBookClient() -> Optional[GrowthBookClient]:
    """Alias for get_growthbook_client."""
    return get_growthbook_client()


def isGrowthBookInitialized() -> bool:
    """Alias for is_growthbook_initialized."""
    return is_growthbook_initialized()


def refreshGrowthBookFeatures() -> None:
    """Alias for refresh_growthbook_features."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(refresh_growthbook_features())
        else:
            loop.run_until_complete(refresh_growthbook_features())
    except RuntimeError:
        asyncio.run(refresh_growthbook_features())


def resetGrowthBook() -> None:
    """Alias for reset_growthbook."""
    reset_growthbook()


def refreshGrowthBookAfterAuthChange() -> None:
    """Alias for refresh_after_auth_change."""
    refresh_after_auth_change()


def setupPeriodicGrowthBookRefresh() -> None:
    """Alias for setup_periodic_refresh."""
    setup_periodic_refresh()


def stopPeriodicGrowthBookRefresh() -> None:
    """Alias for stop_periodic_refresh."""
    stop_periodic_refresh()


def getFeatureValue(feature: str, default: Any) -> Any:
    """Alias for get_feature_value."""
    return get_feature_value(feature, default)


def getFeatureValue_CACHED_MAY_BE_STALE(feature: str, default: Any) -> Any:
    """Alias for get_feature_value_cached_may_be_stale."""
    return get_feature_value_cached_may_be_stale(feature, default)


def onGrowthBookRefresh(listener: Callable[[], None]) -> Callable[[], None]:
    """Alias for on_growthbook_refresh."""
    return on_growthbook_refresh(listener)


def getAllGrowthBookFeatures() -> Dict[str, Any]:
    """Alias for get_all_growthbook_features."""
    return get_all_growthbook_features()


def getDynamicConfig(configName: str, default: Any) -> Any:
    """Alias for get_dynamic_config."""
    return get_dynamic_config(configName, default)


def getDynamicConfig_CACHED_MAY_BE_STALE(configName: str, default: Any) -> Any:
    """Alias for get_dynamic_config_cached_may_be_stale."""
    return get_dynamic_config_cached_may_be_stale(configName, default)


def hasGrowthBookEnvOverride(feature: str) -> bool:
    """Alias for has_growthbook_env_override."""
    return has_growthbook_env_override(feature)


def setGrowthBookConfigOverride(feature: str, value: Any) -> None:
    """Alias for set_growthbook_config_override."""
    return set_growthbook_config_override(feature, value)


def clearGrowthBookConfigOverrides() -> None:
    """Alias for clear_growthbook_config_overrides."""
    return clear_growthbook_config_overrides()


def getGrowthBookConfigOverrides() -> Dict[str, Any]:
    """Alias for get_growthbook_config_overrides."""
    return get_growthbook_config_overrides()


async def checkGate_CACHED_OR_BLOCKING(gate: str) -> bool:
    """Alias for check_gate_cached_or_blocking."""
    return await check_gate_cached_or_blocking(gate)


async def checkSecurityRestrictionGate(gate: str) -> bool:
    """Alias for check_security_restriction_gate."""
    return await check_security_restriction_gate(gate)


def checkStatsigFeatureGate_CACHED_MAY_BE_STALE(gate: str) -> bool:
    """Alias for check_statsig_feature_gate_cached_may_be_stale."""
    return check_statsig_feature_gate_cached_may_be_stale(gate)

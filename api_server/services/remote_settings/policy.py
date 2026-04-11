"""Remote policy enforcement for settings."""

from typing import Any, Dict, List, Optional

from .types import PolicyViolation, RemotePolicy, SecurityCheckResult


class RemotePolicyManager:
    _current_policy: Optional[RemotePolicy] = None

    def __init__(self) -> None:
        pass

    @classmethod
    def get_current_policy(cls) -> Optional[RemotePolicy]:
        return cls._current_policy

    @classmethod
    def set_current_policy(cls, policy: Optional[RemotePolicy]) -> None:
        cls._current_policy = policy

    def get_enforced_policy(self) -> Optional[RemotePolicy]:
        return self._current_policy

    def check_policy_compliance(
        self,
        settings: Dict[str, Any],
        policy: Optional[RemotePolicy] = None,
    ) -> SecurityCheckResult:
        policy_to_check = policy or self._current_policy
        if policy_to_check is None:
            return SecurityCheckResult(passed=True, violations=[])

        violations = self.get_policy_violations(settings, policy_to_check)
        requires_confirmation = any(v.severity == "error" for v in violations)

        return SecurityCheckResult(
            passed=len([v for v in violations if v.severity == "error"]) == 0,
            violations=violations,
            requires_confirmation=requires_confirmation,
        )

    def get_policy_violations(
        self,
        settings: Dict[str, Any],
        policy: Optional[RemotePolicy] = None,
    ) -> List[PolicyViolation]:
        policy_to_check = policy or self._current_policy
        if policy_to_check is None:
            return []

        violations: List[PolicyViolation] = []

        for key in policy_to_check.required_keys:
            if key not in settings:
                violations.append(PolicyViolation(
                    key=key,
                    violation_type="required",
                    message=f"Required setting '{key}' is missing",
                    severity="error",
                ))

        for key in policy_to_check.blocked_keys:
            if key in settings:
                violations.append(PolicyViolation(
                    key=key,
                    violation_type="blocked",
                    message=f"Setting '{key}' is blocked by policy",
                    severity="error",
                    current_value=settings[key],
                ))

        for key in policy_to_check.enforced_keys:
            if key in settings:
                if key in policy_to_check.default_values:
                    expected = policy_to_check.default_values[key]
                    if settings[key] != expected:
                        violations.append(PolicyViolation(
                            key=key,
                            violation_type="enforced",
                            message=f"Setting '{key}' must be '{expected}'",
                            severity="error",
                            current_value=settings[key],
                            expected_value=expected,
                        ))

        return violations

    def enforce_policy(
        self,
        settings: Dict[str, Any],
        policy: Optional[RemotePolicy] = None,
    ) -> Dict[str, Any]:
        policy_to_enforce = policy or self._current_policy
        if policy_to_enforce is None:
            return settings.copy()

        result = settings.copy()

        for key in policy_to_enforce.blocked_keys:
            if key in result:
                del result[key]

        for key in policy_to_enforce.required_keys:
            if key not in result:
                if key in (policy_to_enforce.default_values or {}):
                    result[key] = policy_to_enforce.default_values[key]

        for key in policy_to_enforce.enforced_keys:
            if key in policy_to_enforce.default_values:
                result[key] = policy_to_enforce.default_values[key]

        return result

    def validate_setting(
        self,
        key: str,
        value: Any,
        policy: Optional[RemotePolicy] = None,
    ) -> List[PolicyViolation]:
        policy_to_check = policy or self._current_policy
        if policy_to_check is None:
            return []

        violations: List[PolicyViolation] = []

        if key in policy_to_check.blocked_keys:
            violations.append(PolicyViolation(
                key=key,
                violation_type="blocked",
                message=f"Setting '{key}' is blocked by policy",
                severity="error",
                current_value=value,
            ))

        if key in policy_to_check.enforced_keys:
            if key in policy_to_check.default_values:
                expected = policy_to_check.default_values[key]
                if value != expected:
                    violations.append(PolicyViolation(
                        key=key,
                        violation_type="enforced",
                        message=f"Setting '{key}' must be '{expected}'",
                        severity="error",
                        current_value=value,
                        expected_value=expected,
                    ))

        return violations

    def is_setting_allowed(self, key: str, policy: Optional[RemotePolicy] = None) -> bool:
        policy_to_check = policy or self._current_policy
        if policy_to_check is None:
            return True
        return key not in policy_to_check.blocked_keys

    def get_allowed_keys(self, policy: Optional[RemotePolicy] = None) -> List[str]:
        policy_to_check = policy or self._current_policy
        if policy_to_check is None:
            return []
        return [k for k in policy_to_check.enforced_keys if k not in policy_to_check.blocked_keys]

    def get_blocked_keys(self, policy: Optional[RemotePolicy] = None) -> List[str]:
        policy_to_check = policy or self._current_policy
        if policy_to_check is None:
            return []
        return list(policy_to_check.blocked_keys)

    def get_required_keys(self, policy: Optional[RemotePolicy] = None) -> List[str]:
        policy_to_check = policy or self._current_policy
        if policy_to_check is None:
            return []
        return list(policy_to_check.required_keys)

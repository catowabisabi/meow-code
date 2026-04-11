"""
Violation handling for policy limits service.

Provides ViolationHandler class for handling and logging policy violations.
"""

from datetime import datetime
from typing import Dict, List, Optional

from .types import PolicyViolation, ViolationHistoryEntry


class ViolationHandler:
    """Handles policy violations and provides violation management."""

    _violations: List[PolicyViolation] = []
    _violation_history: Dict[str, List[ViolationHistoryEntry]] = {}
    _max_violations_in_memory: int = 1000

    @classmethod
    def handle_violation(
        cls,
        violation_type: str,
        policy_name: str,
        message: str,
        severity: str = "error",
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> PolicyViolation:
        """Handle a policy violation by recording it."""
        violation = PolicyViolation(
            violation_type=violation_type,
            policy_name=policy_name,
            message=message,
            severity=severity,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            org_id=org_id,
            details=details or {},
        )

        cls._violations.append(violation)

        if len(cls._violations) > cls._max_violations_in_memory:
            cls._violations = cls._violations[-cls._max_violations_in_memory:]

        history_key = cls._make_history_key(user_id, org_id)
        if history_key not in cls._violation_history:
            cls._violation_history[history_key] = []

        entry = ViolationHistoryEntry(violation=violation)
        cls._violation_history[history_key].append(entry)

        if len(cls._violation_history[history_key]) > cls._max_violations_in_memory:
            cls._violation_history[history_key] = cls._violation_history[history_key][
                -cls._max_violations_in_memory:
            ]

        return violation

    @classmethod
    def get_violation_message(cls, violation: PolicyViolation) -> str:
        """Get a user-friendly message for a violation."""
        messages = {
            "rate_limit": f"Rate limit exceeded for policy '{violation.policy_name}'. {violation.message}",
            "quota_exceeded": f"Quota exceeded for '{violation.policy_name}'. {violation.message}",
            "usage_limit": f"Usage limit reached for '{violation.policy_name}'. {violation.message}",
            "policy_denied": f"Policy '{violation.policy_name}' is not allowed. {violation.message}",
            "essential_traffic_only": f"Feature '{violation.policy_name}' is disabled in essential-traffic-only mode.",
        }
        return messages.get(violation.violation_type, violation.message)

    @classmethod
    def log_violation(cls, violation: PolicyViolation) -> None:
        """Log a violation (placeholder for actual logging integration)."""
        log_entry = {
            "timestamp": violation.timestamp.isoformat(),
            "type": violation.violation_type,
            "policy": violation.policy_name,
            "severity": violation.severity,
            "user_id": violation.user_id,
            "org_id": violation.org_id,
            "message": violation.message,
            "details": violation.details,
        }
        print(f"[POLICY VIOLATION] {log_entry}")

    @classmethod
    def get_violation_history(
        cls,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[PolicyViolation]:
        """Get violation history for a user or organization."""
        history_key = cls._make_history_key(user_id, org_id)
        entries = cls._violation_history.get(history_key, [])

        violations = [
            entry.violation for entry in entries[-limit:]
            if not entry.resolved
        ]
        return violations

    @classmethod
    def get_all_violations(
        cls,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> List[PolicyViolation]:
        """Get all recent violations, optionally filtered by time."""
        violations = cls._violations[-limit:]
        if since:
            violations = [v for v in violations if v.timestamp >= since]
        return violations

    @classmethod
    def resolve_violation(
        cls,
        violation: PolicyViolation,
        resolved_by: Optional[str] = None,
    ) -> None:
        """Mark a violation as resolved."""
        history_key = cls._make_history_key(violation.user_id, violation.org_id)
        entries = cls._violation_history.get(history_key, [])

        for entry in entries:
            if entry.violation == violation:
                entry.resolved = True
                entry.resolved_at = datetime.utcnow()
                entry.resolved_by = resolved_by
                break

    @classmethod
    def get_violation_count(
        cls,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Get count of violations for a user or organization."""
        if user_id or org_id:
            history_key = cls._make_history_key(user_id, org_id)
            entries = cls._violation_history.get(history_key, [])
            violations = [e.violation for e in entries]
        else:
            violations = cls._violations

        if since:
            violations = [v for v in violations if v.timestamp >= since]

        return len(violations)

    @classmethod
    def get_violations_by_type(
        cls,
        violation_type: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[PolicyViolation]:
        """Get violations of a specific type."""
        violations = cls.get_violation_history(user_id, org_id)
        return [v for v in violations if v.violation_type == violation_type]

    @classmethod
    def get_violations_by_policy(
        cls,
        policy_name: str,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> List[PolicyViolation]:
        """Get violations for a specific policy."""
        violations = cls.get_violation_history(user_id, org_id)
        return [v for v in violations if v.policy_name == policy_name]

    @classmethod
    def clear_violations(
        cls,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
    ) -> int:
        """Clear violations for a user or organization. Returns count cleared."""
        if user_id or org_id:
            history_key = cls._make_history_key(user_id, org_id)
            count = len(cls._violation_history.get(history_key, []))
            if history_key in cls._violation_history:
                del cls._violation_history[history_key]
            return count

        count = len(cls._violations)
        cls._violations.clear()
        return count

    @classmethod
    def set_max_violations_in_memory(cls, max_count: int) -> None:
        """Set the maximum number of violations to keep in memory."""
        cls._max_violations_in_memory = max_count
        if len(cls._violations) > max_count:
            cls._violations = cls._violations[-max_count:]

    @classmethod
    def _make_history_key(
        cls,
        user_id: Optional[str],
        org_id: Optional[str],
    ) -> str:
        """Create internal key for violation history storage."""
        if org_id:
            return f"org:{org_id}"
        if user_id:
            return f"user:{user_id}"
        return "global"

    @classmethod
    def get_recent_violations_summary(cls) -> Dict:
        """Get a summary of recent violations."""
        total = len(cls._violations)
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}

        for violation in cls._violations:
            by_type[violation.violation_type] = by_type.get(violation.violation_type, 0) + 1
            by_severity[violation.severity] = by_severity.get(violation.severity, 0) + 1

        return {
            "total_violations": total,
            "by_type": by_type,
            "by_severity": by_severity,
            "oldest_violation": cls._violations[0].timestamp.isoformat() if cls._violations else None,
            "newest_violation": cls._violations[-1].timestamp.isoformat() if cls._violations else None,
        }

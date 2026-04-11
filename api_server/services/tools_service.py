from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional


@dataclass
class ToolUsageStats:
    tool_name: str
    total_uses: int
    success_count: int
    failure_count: int
    total_duration_ms: int
    avg_duration_ms: float
    last_used: float


@dataclass
class ToolUsageRecord:
    tool_name: str
    duration_ms: int
    success: bool
    timestamp: float
    session_id: Optional[str] = None
    error: Optional[str] = None


class ToolsService:
    _usage_records: List[ToolUsageRecord] = []
    _max_records: int = 10000
    
    @classmethod
    def record_usage(
        cls,
        tool_name: str,
        duration_ms: int,
        success: bool,
        session_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        record = ToolUsageRecord(
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=success,
            timestamp=datetime.utcnow().timestamp(),
            session_id=session_id,
            error=error,
        )
        cls._usage_records.append(record)
        if len(cls._usage_records) > cls._max_records:
            cls._usage_records = cls._usage_records[-cls._max_records:]
    
    @classmethod
    def get_stats(cls, tool_name: Optional[str] = None) -> List[ToolUsageStats]:
        if tool_name:
            filtered = [r for r in cls._usage_records if r.tool_name == tool_name]
        else:
            filtered = cls._usage_records
        
        stats_dict: Dict[str, Dict[str, Any]] = {}
        for record in filtered:
            if record.tool_name not in stats_dict:
                stats_dict[record.tool_name] = {
                    "total_uses": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "total_duration_ms": 0,
                    "last_used": 0,
                }
            s = stats_dict[record.tool_name]
            s["total_uses"] += 1
            if record.success:
                s["success_count"] += 1
            else:
                s["failure_count"] += 1
            s["total_duration_ms"] += record.duration_ms
            if record.timestamp > s["last_used"]:
                s["last_used"] = record.timestamp
        
        result = []
        for name, s in stats_dict.items():
            avg = s["total_duration_ms"] / s["total_uses"] if s["total_uses"] > 0 else 0
            result.append(ToolUsageStats(
                tool_name=name,
                total_uses=s["total_uses"],
                success_count=s["success_count"],
                failure_count=s["failure_count"],
                total_duration_ms=s["total_duration_ms"],
                avg_duration_ms=avg,
                last_used=s["last_used"],
            ))
        
        return result
    
    @classmethod
    def get_recent_usage(cls, limit: int = 100) -> List[ToolUsageRecord]:
        return cls._usage_records[-limit:]
    
    @classmethod
    def clear_stats(cls) -> None:
        cls._usage_records.clear()
    
    @classmethod
    def get_success_rate(cls, tool_name: str) -> float:
        stats = cls.get_stats(tool_name)
        if not stats:
            return 0.0
        s = stats[0]
        if s.total_uses == 0:
            return 0.0
        return s.success_count / s.total_uses
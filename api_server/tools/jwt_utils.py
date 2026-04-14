"""JWT and session ingress - bridging gap with TypeScript bridge/jwtUtils.ts"""
import time
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


@dataclass
class JWTPayload:
    sub: str
    exp: int
    iat: int
    iss: str
    aud: Optional[str] = None
    nbf: Optional[int] = None
    jti: Optional[str] = None
    claims: Dict[str, Any] = None


def decode_jwt_payload(token: str) -> Optional[JWTPayload]:
    try:
        import base64
        import json
        
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        payload_b64 = parts[1]
        
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)
        
        return JWTPayload(
            sub=payload.get("sub", ""),
            exp=payload.get("exp", 0),
            iat=payload.get("iat", 0),
            iss=payload.get("iss", ""),
            aud=payload.get("aud"),
            nbf=payload.get("nbf"),
            jti=payload.get("jti"),
            claims=payload
        )
    except Exception as e:
        logger.error(f"Failed to decode JWT: {e}")
        return None


def is_token_expired(payload: JWTPayload, buffer_seconds: int = 300) -> bool:
    current_time = time.time()
    return payload.exp < (current_time + buffer_seconds)


def get_token_expiry_datetime(payload: JWTPayload) -> datetime:
    return datetime.fromtimestamp(payload.exp)


class JWTRefreshScheduler:
    """
    Proactive JWT refresh scheduler.
    
    TypeScript equivalent: jwtUtils.ts scheduleFromExpiresIn()
    Python gap: No proactive refresh scheduler.
    """
    
    def __init__(self, on_refresh: Optional[Callable[[str], None]] = None):
        self._on_refresh = on_refresh
        self._refresh_callbacks: Dict[str, Callable] = {}
        self._scheduled: Dict[str, float] = {}
        self._running = False
    
    def schedule_refresh(
        self,
        token: str,
        callback: Callable,
        buffer_seconds: int = 300
    ) -> None:
        payload = decode_jwt_payload(token)
        if not payload:
            return
        
        expiry_time = payload.exp - buffer_seconds
        current_time = time.time()
        
        if expiry_time <= current_time:
            logger.warning("Token already expired or within buffer")
            return
        
        delay = expiry_time - current_time
        self._scheduled[token] = expiry_time
        self._refresh_callbacks[token] = callback
        
        import threading
        timer = threading.Timer(delay, self._do_refresh, args=[token])
        timer.start()
    
    def _do_refresh(self, token: str) -> None:
        if token in self._refresh_callbacks:
            callback = self._refresh_callbacks[token]
            try:
                callback(token)
            except Exception as e:
                logger.error(f"Refresh callback failed: {e}")
    
    def cancel_refresh(self, token: str) -> None:
        if token in self._scheduled:
            del self._scheduled[token]
        if token in self._refresh_callbacks:
            del self._refresh_callbacks[token]


class SessionIngress:
    """
    Session ingress with token handling.
    
    TypeScript equivalent: session_ingress.ts
    Python gap: Basic token handling.
    """
    
    def __init__(self):
        self._tokens: Dict[str, str] = {}
        self._scheduler = JWTRefreshScheduler()
    
    def register_token(self, session_id: str, token: str) -> None:
        self._tokens[session_id] = token
        
        self._scheduler.schedule_refresh(
            token,
            lambda t: self._on_token_refresh(session_id, t)
        )
    
    def _on_token_refresh(self, session_id: str, old_token: str) -> None:
        logger.info(f"Token refresh needed for session {session_id}")
    
    def get_token(self, session_id: str) -> Optional[str]:
        return self._tokens.get(session_id)
    
    def revoke_token(self, session_id: str) -> None:
        if session_id in self._tokens:
            self._scheduler.cancel_refresh(self._tokens[session_id])
            del self._tokens[session_id]


_session_ingress: Optional[SessionIngress] = None


def get_session_ingress() -> SessionIngress:
    global _session_ingress
    if _session_ingress is None:
        _session_ingress = SessionIngress()
    return _session_ingress

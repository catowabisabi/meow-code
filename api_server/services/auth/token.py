from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    iat: datetime
    type: str


class TokenService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)

    def create_access_token(self, user_id: str, scopes: Optional[list[str]] = None) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "exp": now + self.access_token_expire,
            "iat": now,
            "type": "access",
            "scopes": scopes or [],
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "exp": now + self.refresh_token_expire,
            "iat": now,
            "type": "refresh",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str, expected_type: str = "access") -> Optional[TokenPayload]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != expected_type:
                return None
            return TokenPayload(**payload)
        except JWTError:
            return None

    def decode_token_unsafe(self, token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
        except JWTError:
            return None

    def get_token_iat(self, token: str) -> Optional[datetime]:
        """Extract the issued-at time from a token without full verification."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False, "verify_iat": False})
            iat = payload.get("iat")
            if iat:
                return datetime.fromtimestamp(iat, tz=timezone.utc)
            return None
        except JWTError:
            return None
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from api_server.db.repositories.api_key import ApiKeyRepository

class ApiKeyService:
    def __init__(self, api_key_repo: ApiKeyRepository):
        self.api_key_repo = api_key_repo
    
    def generate_key(self) -> tuple[str, str, str]:
        prefix = "ckey"
        random_part = secrets.token_urlsafe(32)
        full_key = f"{prefix}_{random_part}"
        key_hash = self._hash_key(full_key)
        return full_key, key_hash, prefix
    
    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()
    
    async def create_api_key(
        self,
        user_id: str,
        name: str,
        expires_in_days: Optional[int] = None,
    ) -> dict:
        full_key, key_hash, prefix = self.generate_key()
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        api_key = await self.api_key_repo.create(
            name=name,
            key_hash=key_hash,
            prefix=prefix,
            user_id=user_id,
            expires_at=expires_at,
            is_active=True,
        )
        
        return {
            **api_key,
            "full_key": full_key,
        }
    
    async def verify_api_key(self, key: str) -> Optional[dict]:
        if not key.startswith("ckey_"):
            return None
        
        key_hash = self._hash_key(key)
        prefix = key.split("_")[0] + "_"
        
        api_key = await self.api_key_repo.get_by_key_hash(key_hash)
        if not api_key:
            return None
        
        if not api_key.get("is_active"):
            return None
        
        if api_key.get("expires_at"):
            if datetime.now(timezone.utc) > api_key["expires_at"]:
                return None
        
        await self.api_key_repo.update_last_used(api_key["id"])
        
        return api_key
    
    async def list_user_api_keys(self, user_id: str) -> List[dict]:
        return await self.api_key_repo.get_by_user_id(user_id)
    
    async def revoke_api_key(self, key_id: str) -> bool:
        return await self.api_key_repo.update(key_id, is_active=False)
    
    async def delete_api_key(self, key_id: str) -> bool:
        return await self.api_key_repo.delete(key_id)
    
    async def get_api_key(self, key_id: str) -> Optional[dict]:
        return await self.api_key_repo.get_by_id(key_id)
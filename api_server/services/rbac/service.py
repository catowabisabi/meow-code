from typing import Optional, List
from api_server.db.repositories.role import RoleRepository
from api_server.db.repositories.user import UserRepository
from api_server.services.rbac.models import Permission, DEFAULT_PERMISSIONS, Resource, Action

class RoleService:
    def __init__(self, role_repo: RoleRepository, user_repo: UserRepository):
        self.role_repo = role_repo
        self.user_repo = user_repo
    
    async def create_role(self, name: str, description: Optional[str] = None, permissions: Optional[List[str]] = None, parent_id: Optional[str] = None) -> dict:
        perm_string = ",".join(permissions) if permissions else None
        return await self.role_repo.create(name=name, description=description, permissions=perm_string, parent_id=parent_id)
    
    async def get_role(self, role_id: str) -> Optional[dict]:
        return await self.role_repo.get_by_id(role_id)
    
    async def get_role_by_name(self, name: str) -> Optional[dict]:
        return await self.role_repo.get_by_name(name)
    
    async def list_roles(self) -> List[dict]:
        return await self.role_repo.get_all()
    
    async def update_role(self, role_id: str, **kwargs) -> Optional[dict]:
        return await self.role_repo.update(role_id, **kwargs)
    
    async def delete_role(self, role_id: str) -> bool:
        return await self.role_repo.delete(role_id)
    
    async def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            return False
        return True
    
    async def get_user_permissions(self, user_id: str) -> List[Permission]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return []
        if user.get("is_superuser"):
            return [Permission.from_string(p) for p in DEFAULT_PERMISSIONS["admin"]]
        role = await self.role_repo.get_by_name("viewer")
        if role:
            return [Permission.from_string(p) for p in DEFAULT_PERMISSIONS.get("viewer", [])]
        return []

class PermissionService:
    def __init__(self):
        self.resource_actions = {
            Resource.USER: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.ROLE: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.TEAM: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.DEPARTMENT: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.API_KEY: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.HOOK: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.EXECUTE, Action.ADMIN],
            Resource.MEMORY: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.AGENT: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
            Resource.PROJECT: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.ADMIN],
        }
    
    def check_permission(self, user_permissions: List[Permission], required: Permission) -> bool:
        return required in user_permissions
    
    def check_resource_access(self, user_permissions: List[Permission], resource: Resource, action: Action) -> bool:
        perm = Permission(resource, action)
        return self.check_permission(user_permissions, perm)
    
    def get_user_scopes(self, user_permissions: List[Permission]) -> List[str]:
        return [str(p) for p in user_permissions]
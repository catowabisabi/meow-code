from enum import Enum

class Resource(str, Enum):
    USER = "user"
    ROLE = "role"
    TEAM = "team"
    DEPARTMENT = "department"
    API_KEY = "api_key"
    HOOK = "hook"
    MEMORY = "memory"
    AGENT = "agent"
    PROJECT = "project"

class Action(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"

DEFAULT_PERMISSIONS = {
    "admin": [
        "user:create", "user:read", "user:update", "user:delete", "user:admin",
        "role:create", "role:read", "role:update", "role:delete", "role:admin",
        "team:create", "team:read", "team:update", "team:delete", "team:admin",
        "department:create", "department:read", "department:update", "department:delete", "department:admin",
        "api_key:create", "api_key:read", "api_key:update", "api_key:delete", "api_key:admin",
        "hook:create", "hook:read", "hook:update", "hook:delete", "hook:execute", "hook:admin",
        "memory:create", "memory:read", "memory:update", "memory:delete", "memory:admin",
        "agent:create", "agent:read", "agent:update", "agent:delete", "agent:admin",
        "project:create", "project:read", "project:update", "project:delete", "project:admin",
    ],
    "developer": [
        "user:read", "user:update",
        "role:read",
        "team:read", "team:create", "team:update",
        "department:read",
        "api_key:create", "api_key:read", "api_key:update", "api_key:delete",
        "hook:create", "hook:read", "hook:update", "hook:delete", "hook:execute",
        "memory:create", "memory:read", "memory:update",
        "agent:read",
        "project:create", "project:read", "project:update",
    ],
    "viewer": [
        "user:read",
        "role:read",
        "team:read",
        "department:read",
        "api_key:read",
        "hook:read",
        "memory:read",
        "agent:read",
        "project:read",
    ],
}

class Permission:
    def __init__(self, resource: Resource, action: Action):
        self.resource = resource
        self.action = action
    
    def __str__(self) -> str:
        return f"{self.resource.value}:{self.action.value}"
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Permission):
            return self.resource == other.resource and self.action == other.action
        return False
    
    def __hash__(self) -> int:
        return hash((self.resource, self.action))
    
    @classmethod
    def from_string(cls, perm_string: str) -> "Permission":
        parts = perm_string.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid permission string: {perm_string}")
        return cls(Resource(parts[0]), Action(parts[1]))
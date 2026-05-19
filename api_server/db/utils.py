def get_database_url() -> str:
    from api_server.core.config import settings
    return settings.DATABASE_URL

def parse_database_url(url: str) -> dict:
    result = {"driver": "sqlite", "database": ""}
    if "://" not in url:
        return result
    
    parts = url.split("://")
    driver_part = parts[0]
    
    if "+" in driver_part:
        result["driver"] = driver_part.split("+")[1]
    else:
        result["driver"] = driver_part
    
    if len(parts) > 1:
        auth_host = parts[1]
        if "@" in auth_host:
            auth_parts = auth_host.split("@")
            result["username"] = auth_parts[0].split(":")[0] if ":" in auth_parts[0] else ""
            result["password"] = auth_parts[0].split(":")[1] if ":" in auth_parts[0] else ""
            result["host"] = auth_parts[1].split("/")[0] if "/" in auth_parts[1] else auth_parts[1]
        else:
            result["host"] = auth_parts[1].split("/")[0] if "/" in auth_parts[1] else auth_parts[1]
        
        if "/" in auth_host and "?" in auth_host:
            result["database"] = auth_host.split("?")[0].split("/")[-1]
        elif "/" in auth_host:
            result["database"] = auth_host.split("/")[-1]
    
    return result

def supports_multiple_databases() -> bool:
    return True
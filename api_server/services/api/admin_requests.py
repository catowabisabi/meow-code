"""
Admin request service for limit increases and seat upgrades.

Provides functionality for Team/Enterprise users to request admin actions
when they don't have billing/admin permissions themselves.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union

import httpx

logger = logging.getLogger(__name__)


@dataclass
class AdminRequestSeatUpgradeDetails:
    """Details for seat upgrade requests."""
    message: Optional[str] = None
    current_seat_tier: Optional[str] = None


@dataclass
class AdminRequestLimitIncrease:
    """Admin request for limit increase."""
    request_type: str = "limit_increase"
    details: None = None


@dataclass
class AdminRequestSeatUpgrade:
    """Admin request for seat upgrade."""
    request_type: str = "seat_upgrade"
    details: AdminRequestSeatUpgradeDetails = field(default_factory=AdminRequestSeatUpgradeDetails)


AdminRequestCreateParams = Union[AdminRequestLimitIncrease, AdminRequestSeatUpgrade]


@dataclass
class AdminRequest:
    """Represents an admin request (limit increase or seat upgrade)."""
    uuid: str
    status: str
    request_type: str
    requester_uuid: Optional[str] = None
    created_at: str = ""
    details: Optional[Dict[str, Any]] = None


@dataclass 
class AdminRequestEligibilityResponse:
    """Response for admin request eligibility check."""
    request_type: str
    is_allowed: bool


def _get_oauth_config() -> Dict[str, str]:
    """Get OAuth configuration based on environment."""
    custom_oauth_url = None  # Would use os.environ.get in production
    if custom_oauth_url:
        base = custom_oauth_url.rstrip("/")
        return {"BASE_API_URL": base}
    return {"BASE_API_URL": "https://api.anthropic.com"}


def _get_oauth_tokens() -> Optional[Dict[str, Any]]:
    """Get OAuth tokens from secure storage."""
    # In production, would read from secure storage
    # This is a placeholder that returns None
    return None


def _get_organization_uuid() -> Optional[str]:
    """Get organization UUID from OAuth tokens or config."""
    # In production, would get from OAuth profile
    # This is a placeholder that returns None
    return None


def _get_oauth_headers(access_token: str) -> Dict[str, str]:
    """Create OAuth headers for API requests."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }


def _build_eligibility_url(org_uuid: str, request_type: str) -> str:
    """Build the eligibility check URL."""
    base_url = _get_oauth_config()["BASE_API_URL"]
    return f"{base_url}/api/oauth/organizations/{org_uuid}/admin_requests/eligibility?request_type={request_type}"


def _build_admin_requests_url(org_uuid: str) -> str:
    """Build the admin requests URL."""
    base_url = _get_oauth_config()["BASE_API_URL"]
    return f"{base_url}/api/oauth/organizations/{org_uuid}/admin_requests"


def _build_my_requests_url(org_uuid: str, request_type: str, statuses: List[str]) -> str:
    """Build URL for getting user's own admin requests."""
    base_url = _get_oauth_config()["BASE_API_URL"]
    url = f"{base_url}/api/oauth/organizations/{org_uuid}/admin_requests/me?request_type={request_type}"
    for status in statuses:
        url += f"&statuses={status}"
    return url


async def create_admin_request(
    params: AdminRequestCreateParams,
) -> AdminRequest:
    """
    Create an admin request (limit increase or seat upgrade).
    
    For Team/Enterprise users who don't have billing/admin permissions,
    this creates a request that their admin can act on.
    
    If a pending request of the same type already exists for this user,
    returns the existing request instead of creating a new one.
    
    Args:
        params: The admin request parameters (limit_increase or seat_upgrade)
        
    Returns:
        The created AdminRequest
        
    Raises:
        Exception: If authentication fails or request creation fails
    """
    access_token = _get_oauth_tokens()
    if not access_token:
        raise Exception(
            "Claude Code web sessions require authentication with a Claude.ai account. "
            "API key authentication is not sufficient. Please run /login to authenticate."
        )
    
    org_uuid = _get_organization_uuid()
    if not org_uuid:
        raise Exception("Unable to get organization UUID")
    
    headers = {
        **_get_oauth_headers(access_token),
        "x-organization-uuid": org_uuid,
    }
    
    url = _build_admin_requests_url(org_uuid)
    
    # Build request body based on params type
    request_body: Dict[str, Any]
    if isinstance(params, AdminRequestLimitIncrease):
        request_body = {
            "request_type": "limit_increase",
            "details": None,
        }
    elif isinstance(params, AdminRequestSeatUpgrade):
        request_body = {
            "request_type": "seat_upgrade",
            "details": {
                "message": params.details.message,
                "current_seat_tier": params.details.current_seat_tier,
            } if params.details else {},
        }
    else:
        raise ValueError(f"Invalid admin request params type: {type(params)}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=request_body, headers=headers)
        
        if response.status_code != 200 and response.status_code != 201:
            raise Exception(f"Failed to create admin request: {response.status_code}")
        
        data = response.json()
        return _parse_admin_request(data)


async def get_my_admin_requests(
    request_type: str,
    statuses: List[str],
) -> Optional[List[AdminRequest]]:
    """
    Get pending admin request of a specific type for the current user.
    
    Returns the pending request if one exists, otherwise null.
    
    Args:
        request_type: Type of admin request (limit_increase or seat_upgrade)
        statuses: List of statuses to filter by (pending, approved, dismissed)
        
    Returns:
        List of AdminRequests if successful, None otherwise
        
    Raises:
        Exception: If authentication fails
    """
    access_token = _get_oauth_tokens()
    if not access_token:
        raise Exception(
            "Claude Code web sessions require authentication with a Claude.ai account. "
            "API key authentication is not sufficient."
        )
    
    org_uuid = _get_organization_uuid()
    if not org_uuid:
        raise Exception("Unable to get organization UUID")
    
    headers = {
        **_get_oauth_headers(access_token),
        "x-organization-uuid": org_uuid,
    }
    
    url = _build_my_requests_url(org_uuid, request_type, statuses)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if data is None:
            return None
        
        return [_parse_admin_request(req) for req in data]


async def check_admin_request_eligibility(
    request_type: str,
) -> Optional[AdminRequestEligibilityResponse]:
    """
    Check if a specific admin request type is allowed for this org.
    
    Args:
        request_type: Type of admin request to check eligibility for
        
    Returns:
        AdminRequestEligibilityResponse if successful, None otherwise
        
    Raises:
        Exception: If authentication fails
    """
    access_token = _get_oauth_tokens()
    if not access_token:
        raise Exception(
            "Claude Code web sessions require authentication with a Claude.ai account. "
            "API key authentication is not sufficient."
        )
    
    org_uuid = _get_organization_uuid()
    if not org_uuid:
        raise Exception("Unable to get organization UUID")
    
    headers = {
        **_get_oauth_headers(access_token),
        "x-organization-uuid": org_uuid,
    }
    
    url = _build_eligibility_url(org_uuid, request_type)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        return AdminRequestEligibilityResponse(
            request_type=data.get("request_type", request_type),
            is_allowed=data.get("is_allowed", False),
        )


def _parse_admin_request(data: Dict[str, Any]) -> AdminRequest:
    """Parse admin request data into AdminRequest dataclass."""
    request_type = data.get("request_type", "")
    
    details: Optional[Dict[str, Any]] = None
    if request_type == "seat_upgrade" and "details" in data:
        details_data = data.get("details") or {}
        details = {
            "message": details_data.get("message"),
            "current_seat_tier": details_data.get("current_seat_tier"),
        }
    
    return AdminRequest(
        uuid=data.get("uuid", ""),
        status=data.get("status", "pending"),
        request_type=request_type,
        requester_uuid=data.get("requester_uuid"),
        created_at=data.get("created_at", ""),
        details=details,
    )


class AdminRequestService:
    """
    Service class for admin request operations.
    
    Provides methods for creating and querying admin requests
    for limit increases and seat upgrades.
    """
    
    @staticmethod
    async def create_limit_increase_request() -> AdminRequest:
        """Create a limit increase admin request."""
        params = AdminRequestLimitIncrease()
        return await create_admin_request(params)
    
    @staticmethod
    async def create_seat_upgrade_request(
        message: Optional[str] = None,
        current_seat_tier: Optional[str] = None,
    ) -> AdminRequest:
        """Create a seat upgrade admin request."""
        details = AdminRequestSeatUpgradeDetails(
            message=message,
            current_seat_tier=current_seat_tier,
        )
        params = AdminRequestSeatUpgrade(details=details)
        return await create_admin_request(params)
    
    @staticmethod
    async def get_pending_limit_increase_requests() -> Optional[List[AdminRequest]]:
        """Get pending limit increase requests for current user."""
        return await get_my_admin_requests("limit_increase", ["pending"])
    
    @staticmethod
    async def get_pending_seat_upgrade_requests() -> Optional[List[AdminRequest]]:
        """Get pending seat upgrade requests for current user."""
        return await get_my_admin_requests("seat_upgrade", ["pending"])
    
    @staticmethod
    async def check_limit_increase_eligibility() -> Optional[AdminRequestEligibilityResponse]:
        """Check if limit increase requests are allowed for this org."""
        return await check_admin_request_eligibility("limit_increase")
    
    @staticmethod
    async def check_seat_upgrade_eligibility() -> Optional[AdminRequestEligibilityResponse]:
        """Check if seat upgrade requests are allowed for this org."""
        return await check_admin_request_eligibility("seat_upgrade")

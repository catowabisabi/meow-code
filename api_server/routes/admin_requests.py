"""
FastAPI routes for admin requests (limit increases and seat upgrades).
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api_server.services.api.admin_requests import (
    AdminRequest,
    AdminRequestService,
    AdminRequestSeatUpgradeDetails,
)

router = APIRouter(prefix="/admin-requests", tags=["admin_requests"])


class SeatUpgradeDetailsRequest(BaseModel):
    message: Optional[str] = None
    current_seat_tier: Optional[str] = None


class LimitIncreaseRequest(BaseModel):
    pass


class SeatUpgradeRequest(BaseModel):
    details: Optional[SeatUpgradeDetailsRequest] = None


class AdminRequestResponse(BaseModel):
    uuid: str
    status: str
    request_type: str
    requester_uuid: Optional[str] = None
    created_at: str = ""
    details: Optional[dict] = None


class EligibilityResponse(BaseModel):
    request_type: str
    is_allowed: bool


@router.post("/limit_increase", response_model=AdminRequestResponse)
async def create_limit_increase_request():
    """
    Create a limit increase admin request.
    
    For Team/Enterprise users who don't have billing/admin permissions,
    this creates a request that their admin can act on.
    """
    try:
        result = await AdminRequestService.create_limit_increase_request()
        return _admin_request_to_response(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/seat_upgrade", response_model=AdminRequestResponse)
async def create_seat_upgrade_request(request: SeatUpgradeRequest):
    """
    Create a seat upgrade admin request.
    
    For Team/Enterprise users who don't have billing/admin permissions,
    this creates a request that their admin can act on.
    """
    try:
        details = None
        if request.details:
            details = AdminRequestSeatUpgradeDetails(
                message=request.details.message,
                current_seat_tier=request.details.current_seat_tier,
            )
        result = await AdminRequestService.create_seat_upgrade_request(
            message=details.message if details else None,
            current_seat_tier=details.current_seat_tier if details else None,
        )
        return _admin_request_to_response(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/limit_increase/me", response_model=list[AdminRequestResponse])
async def get_my_limit_increase_requests():
    """
    Get pending limit increase requests for the current user.
    """
    try:
        results = await AdminRequestService.get_pending_limit_increase_requests()
        if results is None:
            return []
        return [_admin_request_to_response(r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/seat_upgrade/me", response_model=list[AdminRequestResponse])
async def get_my_seat_upgrade_requests():
    """
    Get pending seat upgrade requests for the current user.
    """
    try:
        results = await AdminRequestService.get_pending_seat_upgrade_requests()
        if results is None:
            return []
        return [_admin_request_to_response(r) for r in results]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/eligibility/limit_increase", response_model=EligibilityResponse)
async def check_limit_increase_eligibility():
    """
    Check if limit increase requests are allowed for this org.
    """
    try:
        result = await AdminRequestService.check_limit_increase_eligibility()
        if result is None:
            raise HTTPException(status_code=400, detail="Unable to check eligibility")
        return EligibilityResponse(
            request_type=result.request_type,
            is_allowed=result.is_allowed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/eligibility/seat_upgrade", response_model=EligibilityResponse)
async def check_seat_upgrade_eligibility():
    """
    Check if seat upgrade requests are allowed for this org.
    """
    try:
        result = await AdminRequestService.check_seat_upgrade_eligibility()
        if result is None:
            raise HTTPException(status_code=400, detail="Unable to check eligibility")
        return EligibilityResponse(
            request_type=result.request_type,
            is_allowed=result.is_allowed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _admin_request_to_response(req: AdminRequest) -> AdminRequestResponse:
    """Convert AdminRequest dataclass to response model."""
    return AdminRequestResponse(
        uuid=req.uuid,
        status=req.status,
        request_type=req.request_type,
        requester_uuid=req.requester_uuid,
        created_at=req.created_at,
        details=req.details,
    )

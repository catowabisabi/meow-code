"""
FastAPI routes for bootstrap endpoint.
"""
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api_server.services.api.bootstrap import (
    BootstrapConfig,
    BootstrapService,
    fetch_bootstrap_data,
)
from api_server.db.settings_db import has_any_api_key

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


class ModelOptionResponse(BaseModel):
    model: str
    name: str
    description: str
    value: str
    label: str


class BootstrapResponse(BaseModel):
    client_data: Optional[dict] = None
    additional_model_options: list[ModelOptionResponse] = []
    needs_setup: bool = False
    setup_url: Optional[str] = None


@router.get("/bootstrap", response_model=BootstrapResponse)
async def get_bootstrap():
    """
    Get bootstrap configuration for Claude CLI.
    
    Fetches bootstrap data from the API including client_data and
    additional model options. Results are cached to avoid redundant calls.
    """
    service = BootstrapService.get_instance()
    cached = service.get_cached_config()
    
    if cached:
        return _config_to_response(cached)
    
    config = await fetch_bootstrap_data()
    if not config:
        return BootstrapResponse()
    
    return _config_to_response(config)


@router.post("/bootstrap/refresh", response_model=BootstrapResponse)
async def refresh_bootstrap():
    """
    Force refresh of bootstrap configuration.
    
    Clears the cache and fetches fresh data from the API.
    """
    service = BootstrapService.get_instance()
    service.clear_cache()
    
    config = await fetch_bootstrap_data()
    if not config:
        return BootstrapResponse()
    
    return _config_to_response(config)


def _config_to_response(config: BootstrapConfig) -> BootstrapResponse:
    model_options = [
        ModelOptionResponse(
            model=opt.model,
            name=opt.name,
            description=opt.description,
            value=opt.value,
            label=opt.label,
        )
        for opt in config.additional_model_options
    ]
    
    needs_setup = not has_any_api_key()
    
    return BootstrapResponse(
        client_data=config.client_data,
        additional_model_options=model_options,
        needs_setup=needs_setup,
        setup_url="/settings/api-keys" if needs_setup else None,
    )

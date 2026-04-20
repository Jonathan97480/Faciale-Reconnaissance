from fastapi import APIRouter, Depends

from app.api.routes.auth import get_current_user
from app.core.schemas import ConfigPayload
from app.services.config_service import read_config, update_config

router = APIRouter(
    prefix="/config",
    tags=["config"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ConfigPayload)
def get_config() -> ConfigPayload:
    return read_config(mask_secrets=True)


@router.put("", response_model=ConfigPayload)
def put_config(payload: ConfigPayload) -> ConfigPayload:
    update_config(payload)
    return read_config(mask_secrets=True)

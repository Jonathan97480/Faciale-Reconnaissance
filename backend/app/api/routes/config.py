from fastapi import APIRouter

from app.core.schemas import ConfigPayload
from app.services.config_service import read_config, update_config

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=ConfigPayload)
def get_config() -> ConfigPayload:
    return read_config(mask_secrets=True)


@router.put("", response_model=ConfigPayload)
def put_config(payload: ConfigPayload) -> ConfigPayload:
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.info(f"[API] PUT /api/config reçu, payload: {payload}")
    update_config(payload)
    return read_config(mask_secrets=True)

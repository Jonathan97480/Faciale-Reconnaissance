from datetime import datetime, timedelta, timezone
import os
import secrets
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, WebSocket, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.services.auth_settings_service import (
    create_initial_admin,
    get_auth_bootstrap_status,
    get_auth_settings,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_TOKEN_COOKIE_NAME = "face_access_token"


class AuthenticatedUser(BaseModel):
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BootstrapStatusResponse(BaseModel):
    setup_required: bool
    auth_source: str


class BootstrapAdminPayload(BaseModel):
    username: str
    password: str


def _get_auth_settings() -> dict[str, str | int | None]:
    expires_minutes_raw = os.getenv("JWT_EXPIRE_MINUTES", "").strip()
    expires_minutes = 60
    if expires_minutes_raw:
        try:
            expires_minutes = max(1, int(expires_minutes_raw))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWT_EXPIRE_MINUTES doit etre un entier positif",
            ) from exc
    auth_settings = get_auth_settings()
    return {
        "admin_username": auth_settings.admin_username,
        "admin_password_hash": auth_settings.admin_password_hash,
        "admin_password_plain": auth_settings.admin_password_plain,
        "secret_key": auth_settings.secret_key,
        "expires_minutes": expires_minutes,
    }


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        return None
    return credentials


def verify_user(username: str, password: str) -> bool:
    settings = _get_auth_settings()
    if username != settings["admin_username"]:
        return False

    if settings["admin_password_plain"] is not None:
        return secrets.compare_digest(password, str(settings["admin_password_plain"]))

    password_hash = settings["admin_password_hash"]
    if password_hash is None:
        return False
    return verify_password(password, str(password_hash))


def _create_access_token(username: str) -> str:
    settings = _get_auth_settings()
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=int(settings["expires_minutes"]))
    payload: dict[str, Any] = {
        "sub": username,
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, str(settings["secret_key"]), algorithm="HS256")


def authenticate_token(token: str | None) -> AuthenticatedUser:
    if not token:
        raise HTTPException(status_code=401, detail="Authentification requise")

    settings = _get_auth_settings()
    try:
        payload = jwt.decode(
            token,
            str(settings["secret_key"]),
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expire") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Token invalide") from exc

    username = payload.get("sub")
    if username != settings["admin_username"]:
        raise HTTPException(status_code=401, detail="Utilisateur inconnu")
    return AuthenticatedUser(username=str(username))


@router.post("/login", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    if not verify_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
        )

    token = _create_access_token(form_data.username)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=int(_get_auth_settings()["expires_minutes"]) * 60,
        path="/",
    )
    return Token(access_token=token)


@router.get("/bootstrap/status", response_model=BootstrapStatusResponse)
def get_bootstrap_status() -> BootstrapStatusResponse:
    status_snapshot = get_auth_bootstrap_status()
    return BootstrapStatusResponse(
        setup_required=status_snapshot.setup_required,
        auth_source=status_snapshot.auth_source,
    )


@router.post("/bootstrap", response_model=Token)
def bootstrap_admin(
    response: Response,
    payload: BootstrapAdminPayload,
) -> Token:
    settings = create_initial_admin(payload.username, payload.password)
    token = _create_access_token(settings.admin_username)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=int(_get_auth_settings()["expires_minutes"]) * 60,
        path="/",
    )
    return Token(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE_NAME, path="/")
    return response


def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE_NAME)] = None,
) -> AuthenticatedUser:
    token = _extract_bearer_token(authorization) or access_token
    return authenticate_token(token)


def get_websocket_user(websocket: WebSocket) -> AuthenticatedUser:
    return authenticate_token(websocket.cookies.get(ACCESS_TOKEN_COOKIE_NAME))


@router.get("/me", response_model=AuthenticatedUser)
def get_me(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    return current_user

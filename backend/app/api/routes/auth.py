from datetime import datetime, timedelta, timezone
import os
import secrets
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, WebSocket, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_TOKEN_COOKIE_NAME = "face_access_token"


class AuthenticatedUser(BaseModel):
    username: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _read_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"{name} doit etre configure",
    )


def _get_auth_settings() -> dict[str, str | int]:
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
    return {
        "admin_username": _read_required_env("ADMIN_USERNAME"),
        "admin_password": _read_required_env("ADMIN_PASSWORD"),
        "secret_key": _read_required_env("JWT_SECRET"),
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
    return username == settings["admin_username"] and secrets.compare_digest(
        password,
        str(settings["admin_password"]),
    )


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

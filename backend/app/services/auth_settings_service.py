import base64
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.database import get_connection

PASSWORD_HASH_ITERATIONS = 200_000


@dataclass
class AuthSettings:
    admin_username: str
    admin_password_hash: str | None
    admin_password_plain: str | None
    secret_key: str


@dataclass
class AuthBootstrapStatus:
    setup_required: bool
    auth_source: str


def _hash_password(password: str, salt: bytes | None = None) -> str:
    effective_salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        effective_salt,
        PASSWORD_HASH_ITERATIONS,
    )
    encoded_salt = base64.b64encode(effective_salt).decode("ascii")
    encoded_hash = base64.b64encode(derived).decode("ascii")
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${encoded_salt}${encoded_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, encoded_salt, encoded_hash = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations_raw)
        salt = base64.b64decode(encoded_salt.encode("ascii"))
        expected_hash = base64.b64decode(encoded_hash.encode("ascii"))
    except (ValueError, base64.binascii.Error):
        return False

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(derived, expected_hash)


def _read_env_auth_settings() -> AuthSettings | None:
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    secret_key = os.getenv("JWT_SECRET", "").strip()
    provided = [bool(username), bool(password), bool(secret_key)]
    if any(provided) and not all(provided):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_USERNAME, ADMIN_PASSWORD et JWT_SECRET doivent etre configures ensemble",
        )
    if not all(provided):
        return None
    return AuthSettings(
        admin_username=username,
        admin_password_hash=None,
        admin_password_plain=password,
        secret_key=secret_key,
    )


def _read_db_auth_settings() -> AuthSettings | None:
    with get_connection() as connection:
        user_row = connection.execute(
            """
            SELECT username, password_hash
            FROM admin_users
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        secret_row = connection.execute(
            "SELECT value FROM auth_settings WHERE key = 'jwt_secret'"
        ).fetchone()

    if user_row is None or secret_row is None:
        return None
    return AuthSettings(
        admin_username=str(user_row["username"]),
        admin_password_hash=str(user_row["password_hash"]),
        admin_password_plain=None,
        secret_key=str(secret_row["value"]),
    )


def get_auth_settings() -> AuthSettings:
    env_settings = _read_env_auth_settings()
    if env_settings is not None:
        return env_settings

    db_settings = _read_db_auth_settings()
    if db_settings is not None:
        return db_settings

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Aucun compte admin configure",
    )


def get_auth_bootstrap_status() -> AuthBootstrapStatus:
    env_settings = _read_env_auth_settings()
    if env_settings is not None:
        return AuthBootstrapStatus(setup_required=False, auth_source="env")

    db_settings = _read_db_auth_settings()
    if db_settings is not None:
        return AuthBootstrapStatus(setup_required=False, auth_source="db")

    return AuthBootstrapStatus(setup_required=True, auth_source="none")


def create_initial_admin(username: str, password: str) -> AuthSettings:
    cleaned_username = username.strip()
    if len(cleaned_username) < 3:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur trop court")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Mot de passe trop court")

    status_snapshot = get_auth_bootstrap_status()
    if not status_snapshot.setup_required:
        raise HTTPException(status_code=409, detail="Un compte admin existe deja")

    secret_key = secrets.token_urlsafe(48)
    password_hash = _hash_password(password)
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
            (cleaned_username, password_hash),
        )
        connection.execute(
            "INSERT OR REPLACE INTO auth_settings (key, value) VALUES (?, ?)",
            ("jwt_secret", secret_key),
        )
        connection.commit()

    return AuthSettings(
        admin_username=cleaned_username,
        admin_password_hash=password_hash,
        admin_password_plain=None,
        secret_key=secret_key,
    )

import base64
import hashlib
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


_LEGACY_PREFIX = "enc:v1:"
_CURRENT_PREFIX = "enc:v2:"
_PBKDF2_ITERATIONS = 390000
_SALT_SIZE = 16


def _get_secret_phrase() -> str:
    raw = os.getenv("FACE_CONFIG_SECRET", "").strip()
    if raw:
        return raw
    raise RuntimeError("FACE_CONFIG_SECRET must be configured")


def _build_fernet(secret_phrase: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_phrase.encode("utf-8")))
    return Fernet(key)


def _legacy_secret_key(secret_phrase: str) -> bytes:
    return hashlib.sha256(secret_phrase.encode("utf-8")).digest()


def _legacy_keystream(length: int, nonce: bytes, key: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _decrypt_legacy_secret(value: str, secret_phrase: str) -> str:
    encoded = value[len(_LEGACY_PREFIX) :]
    try:
        payload = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except Exception:
        return ""
    if len(payload) < 13:
        return ""
    nonce = payload[:12]
    cipher = payload[12:]
    key = _legacy_secret_key(secret_phrase)
    stream = _legacy_keystream(len(cipher), nonce, key)
    plain = bytes(a ^ b for a, b in zip(cipher, stream))
    try:
        return plain.decode("utf-8")
    except Exception:
        return ""


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    if plain.startswith(_CURRENT_PREFIX):
        return plain
    secret_phrase = _get_secret_phrase()
    salt = secrets.token_bytes(_SALT_SIZE)
    token = _build_fernet(secret_phrase, salt).encrypt(plain.encode("utf-8"))
    payload = base64.urlsafe_b64encode(salt + token).decode("ascii")
    return f"{_CURRENT_PREFIX}{payload}"


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith((_CURRENT_PREFIX, _LEGACY_PREFIX)):
        return value

    secret_phrase = _get_secret_phrase()
    if value.startswith(_LEGACY_PREFIX):
        return _decrypt_legacy_secret(value, secret_phrase)

    encoded = value[len(_CURRENT_PREFIX) :]
    try:
        payload = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except Exception:
        return ""
    if len(payload) <= _SALT_SIZE:
        return ""

    salt = payload[:_SALT_SIZE]
    token = payload[_SALT_SIZE:]
    try:
        plain = _build_fernet(secret_phrase, salt).decrypt(token)
    except InvalidToken:
        return ""
    return plain.decode("utf-8")

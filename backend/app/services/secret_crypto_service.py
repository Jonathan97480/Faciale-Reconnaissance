import base64
import hashlib
import os
import secrets


_PREFIX = "enc:v1:"


def _get_secret_key() -> bytes:
    raw = os.getenv("FACE_CONFIG_SECRET", "dev-insecure-change-me")
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _keystream(length: int, nonce: bytes, key: bytes) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_secret(plain: str) -> str:
    if not plain:
        return ""
    if plain.startswith(_PREFIX):
        return plain
    key = _get_secret_key()
    nonce = secrets.token_bytes(12)
    data = plain.encode("utf-8")
    stream = _keystream(len(data), nonce, key)
    cipher = bytes(a ^ b for a, b in zip(data, stream))
    payload = base64.urlsafe_b64encode(nonce + cipher).decode("ascii")
    return f"{_PREFIX}{payload}"


def decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(_PREFIX):
        return value
    encoded = value[len(_PREFIX):]
    try:
        payload = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except Exception:
        return ""
    if len(payload) < 13:
        return ""
    nonce = payload[:12]
    cipher = payload[12:]
    key = _get_secret_key()
    stream = _keystream(len(cipher), nonce, key)
    plain = bytes(a ^ b for a, b in zip(cipher, stream))
    try:
        return plain.decode("utf-8")
    except Exception:
        return ""

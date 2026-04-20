import pytest
import base64
import hashlib

from app.services.secret_crypto_service import decrypt_secret, encrypt_secret


def _build_legacy_payload(secret_phrase: str, plain: str) -> str:
    nonce = b"123456789012"
    key = hashlib.sha256(secret_phrase.encode("utf-8")).digest()
    out = bytearray()
    counter = 0
    while len(out) < len(plain):
        block = hashlib.sha256(key + nonce + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    cipher = bytes(
        ord(char) ^ stream for char, stream in zip(plain, bytes(out[: len(plain)]))
    )
    payload = base64.urlsafe_b64encode(nonce + cipher).decode("ascii")
    return f"enc:v1:{payload}"


def test_encrypt_secret_uses_current_version(monkeypatch):
    monkeypatch.setenv("FACE_CONFIG_SECRET", "unit-test-secret-with-safe-length")

    encrypted = encrypt_secret("camera-password")

    assert encrypted.startswith("enc:v2:")
    assert decrypt_secret(encrypted) == "camera-password"


def test_decrypt_secret_supports_legacy_payload(monkeypatch):
    monkeypatch.setenv("FACE_CONFIG_SECRET", "legacy-secret")
    legacy_value = _build_legacy_payload("legacy-secret", "hello")

    assert decrypt_secret(legacy_value) == "hello"


def test_encrypt_secret_requires_config_secret(monkeypatch):
    monkeypatch.delenv("FACE_CONFIG_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="FACE_CONFIG_SECRET"):
        encrypt_secret("camera-password")

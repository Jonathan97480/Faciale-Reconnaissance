AUTH_USERNAME = "test-admin"
AUTH_PASSWORD = "test-password"
AUTH_SECRET = "test-jwt-secret-with-safe-length-123456"


def configure_auth_env(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", AUTH_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", AUTH_PASSWORD)
    monkeypatch.setenv("JWT_SECRET", AUTH_SECRET)
    monkeypatch.setenv("JWT_EXPIRE_MINUTES", "60")


def login(client):
    response = client.post(
        "/api/auth/login",
        data={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
    )
    assert response.status_code == 200
    return response

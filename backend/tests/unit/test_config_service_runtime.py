from app.core.database import get_connection, init_db
from app.services.config_service import invalidate_config_cache, read_config, update_config


def test_read_config_does_not_apply_inference_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_CONFIG_SECRET", "config-runtime-test-secret")
    init_db()
    invalidate_config_cache()

    called = {"count": 0}

    def fail_if_called(_preference: str) -> str:
        called["count"] += 1
        raise AssertionError("configure_inference_device should not be called by read_config")

    monkeypatch.setattr(
        "app.services.encoder_service.configure_inference_device",
        fail_if_called,
    )

    config = read_config()

    assert config.inference_device_preference == "auto"
    assert config.inference_device_active == "cpu"
    assert called["count"] == 0


def test_update_config_applies_inference_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_CONFIG_SECRET", "config-runtime-test-secret")
    init_db()
    invalidate_config_cache()

    applied = {"preference": None}

    def fake_configure(preference: str) -> str:
        applied["preference"] = preference
        return "cpu"

    monkeypatch.setattr(
        "app.services.encoder_service.configure_inference_device",
        fake_configure,
    )

    current = read_config(mask_secrets=False)
    updated = update_config(
        current.model_copy(
            update={
                "inference_device_preference": "cpu",
                "inference_device_active": "cpu",
            }
        )
    )

    assert applied["preference"] == "cpu"
    assert updated.inference_device_preference == "cpu"


def test_read_config_uses_cache_until_db_changes(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_CONFIG_SECRET", "config-runtime-test-secret")
    init_db()
    invalidate_config_cache()

    from app.core.database import get_connection as base_get_connection

    query_count = {"select_config": 0}

    class CountingConnection:
        def __init__(self, connection) -> None:
            self._connection = connection

        def execute(self, sql, params=()):
            if sql == "SELECT key, value FROM config":
                query_count["select_config"] += 1
            return self._connection.execute(sql, params)

        def __getattr__(self, name):
            return getattr(self._connection, name)

        def __enter__(self):
            self._connection.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._connection.__exit__(exc_type, exc, tb)

    monkeypatch.setattr(
        "app.services.config_service.get_connection",
        lambda: CountingConnection(base_get_connection()),
    )

    first = read_config()
    second = read_config()

    assert first.match_threshold == second.match_threshold
    assert query_count["select_config"] == 1


def test_read_config_refreshes_cache_after_direct_db_update(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_CONFIG_SECRET", "config-runtime-test-secret")
    init_db()
    invalidate_config_cache()

    initial = read_config()
    assert initial.match_threshold == 0.6

    with get_connection() as connection:
        connection.execute(
            "UPDATE config SET value = ? WHERE key = ?",
            ("0.77", "match_threshold"),
        )
        connection.commit()

    refreshed = read_config()

    assert refreshed.match_threshold == 0.77

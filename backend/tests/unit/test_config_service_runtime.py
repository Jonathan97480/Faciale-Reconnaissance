from app.core.database import init_db
from app.services.config_service import read_config, update_config


def test_read_config_does_not_apply_inference_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("FACE_CONFIG_SECRET", "config-runtime-test-secret")
    init_db()

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

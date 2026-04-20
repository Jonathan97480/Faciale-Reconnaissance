from app.core.database import init_db
from app.core.schemas import FaceCreatePayload
from app.services.face_service import create_face, delete_face


def test_create_face_invalidates_recognition_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()

    invalidated = {"count": 0}

    monkeypatch.setattr(
        "app.services.face_service.invalidate_face_reference_cache",
        lambda: invalidated.__setitem__("count", invalidated["count"] + 1),
    )

    create_face(FaceCreatePayload(name="Alice", encoding=[0.1, 0.2]))

    assert invalidated["count"] == 1


def test_delete_face_invalidates_cache_only_when_row_deleted(monkeypatch, tmp_path):
    monkeypatch.setenv("FACE_APP_DB_PATH", str(tmp_path / "test.db"))
    init_db()

    invalidated = {"count": 0}

    monkeypatch.setattr(
        "app.services.face_service.invalidate_face_reference_cache",
        lambda: invalidated.__setitem__("count", invalidated["count"] + 1),
    )

    created = create_face(FaceCreatePayload(name="Alice", encoding=[0.1, 0.2]))
    deleted = delete_face(created.id)
    missing = delete_face(created.id)

    assert deleted is True
    assert missing is False
    assert invalidated["count"] == 2

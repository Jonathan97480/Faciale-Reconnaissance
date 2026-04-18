import pytest
from pydantic import ValidationError

from app.core.schemas import ConfigPayload


def test_rejects_invalid_detection_interval():
    with pytest.raises(ValidationError):
        ConfigPayload(
            detection_interval_seconds=0,
            match_threshold=0.5,
            camera_index=0,
        )


def test_rejects_invalid_match_threshold():
    with pytest.raises(ValidationError):
        ConfigPayload(
            detection_interval_seconds=3,
            match_threshold=1.5,
            camera_index=0,
        )


def test_rejects_invalid_face_crop_padding_ratio():
    with pytest.raises(ValidationError):
        ConfigPayload(
            detection_interval_seconds=3,
            match_threshold=0.7,
            camera_index=0,
            face_crop_padding_ratio=1.2,
        )

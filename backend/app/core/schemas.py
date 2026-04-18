from typing import Literal

from pydantic import BaseModel, Field


class ConfigPayload(BaseModel):
    detection_interval_seconds: float = Field(gt=0)
    match_threshold: float = Field(ge=0, le=1)
    camera_index: int = Field(ge=0)
    camera_source: str = Field(default="", description="URL réseau, chemin vidéo, ou vide pour webcam locale")
    enroll_frames_count: int = Field(default=5, ge=1, le=30)
    face_crop_padding_ratio: float = Field(default=0.2, ge=0, le=1)


class FaceCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    encoding: list[float] | None = None
    adresse: str | None = None
    metier: str | None = None
    lieu_naissance: str | None = None
    age: int | None = None
    annee_naissance: int | None = None
    autres_infos_html: str | None = None


class FaceRecord(BaseModel):
    id: int
    name: str
    encoding: list[float] | None = None
    adresse: str | None = None
    metier: str | None = None
    lieu_naissance: str | None = None
    age: int | None = None
    annee_naissance: int | None = None
    autres_infos_html: str | None = None
    created_at: str


class FaceEnrollPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class RecognitionCheckPayload(BaseModel):
    embedding: list[float] | None = None


class RecognitionResult(BaseModel):
    status: Literal["reconnu", "inconnu"]
    face_id: int | None = None
    face_name: str | None = None
    score: float | None = None


class FaceBoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class ImageRecognitionFaceResult(BaseModel):
    status: Literal["reconnu", "inconnu"]
    face_id: int | None = None
    face_name: str | None = None
    score: float | None = None
    box: FaceBoundingBox
    expanded_box: FaceBoundingBox
    face_image_base64: str | None = None


class ImageRecognitionResponse(BaseModel):
    faces_count: int = Field(ge=0)
    faces: list[ImageRecognitionFaceResult]


class ImageBatchItemResponse(BaseModel):
    filename: str
    content_type: str | None = None
    ok: bool
    error: str | None = None
    result: ImageRecognitionResponse | None = None


class ImageBatchRecognitionResponse(BaseModel):
    items_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    items: list[ImageBatchItemResponse]


class ImageBatchInputItem(BaseModel):
    image_base64: str = Field(min_length=1)
    filename: str = Field(default="image")
    content_type: str | None = None


class ImageBatchAnalyzeRequest(BaseModel):
    items: list[ImageBatchInputItem] = Field(min_length=1, max_length=50)

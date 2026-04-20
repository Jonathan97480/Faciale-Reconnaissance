from typing import Literal

from pydantic import AliasChoices, BaseModel, Field


class NetworkCameraProfile(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    protocol: Literal["rtsp", "mjpeg", "http", "hls"] = "rtsp"
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=554, ge=1, le=65535)
    path: str = Field(default="/")
    username: str = Field(default="")
    password: str = Field(default="")
    has_password: bool = False
    onvif_url: str = Field(default="")
    enabled: bool = True


class ConfigPayload(BaseModel):
    detection_interval_seconds: float = Field(gt=0)
    match_threshold: float = Field(ge=0, le=1)
    match_margin_threshold: float = Field(default=0.03, ge=0, le=1)
    camera_index: int = Field(ge=0)
    camera_source: str = Field(default="", description="URL réseau, chemin vidéo, ou vide pour webcam locale")
    network_camera_sources: list[str] = Field(default_factory=list, max_length=10)
    network_camera_profiles: list[NetworkCameraProfile] = Field(default_factory=list, max_length=10)
    multi_camera_cycle_budget_seconds: float = Field(default=2.0, gt=0.1, le=10)
    enroll_frames_count: int = Field(default=5, ge=1, le=30)
    face_crop_padding_ratio: float = Field(default=0.2, ge=0, le=1)
    inference_device_preference: Literal["auto", "cpu", "cuda"] = "auto"
    inference_device_active: Literal["cpu", "cuda"] = "cpu"
    production_api_rate_limit_window_seconds: float = Field(default=60, gt=0.1, le=3600)
    production_api_rate_limit_max_requests: int = Field(default=30, ge=1, le=10000)


class FaceCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    encoding: list[float] | None = None
    adresse: str | None = None
    metier: str | None = None
    lieu_naissance: str | None = None
    age: int | None = None
    annee_naissance: int | None = None
    autres_infos: str | None = Field(
        default=None,
        validation_alias=AliasChoices("autres_infos", "autres_infos_html"),
    )


class FaceRecord(BaseModel):
    id: int
    name: str
    has_encoding: bool
    adresse: str | None = None
    metier: str | None = None
    lieu_naissance: str | None = None
    age: int | None = None
    annee_naissance: int | None = None
    autres_infos: str | None = None
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

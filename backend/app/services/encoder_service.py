import cv2
from PIL import Image
import threading

_model_lock = threading.Lock()
_FACENET_AVAILABLE = False
_active_device = "cpu"
_device_preference = "auto"
_torch = None
_F = None
_MTCNN = None
_InceptionResnetV1 = None
_mtcnn = None
_mtcnn_aligned = None
_resnet = None


def _sanitize_device_preference(preference: str | None) -> str:
    value = str(preference or "auto").strip().lower()
    if value in {"auto", "cpu", "cuda"}:
        return value
    return "auto"


def _resolve_device(preference: str) -> str:
    if _torch is None:
        return "cpu"
    if preference == "cpu":
        return "cpu"
    if preference == "cuda":
        return "cuda" if _torch.cuda.is_available() else "cpu"
    return "cuda" if _torch.cuda.is_available() else "cpu"


def _load_dependencies() -> bool:
    global _torch, _F, _MTCNN, _InceptionResnetV1
    if _torch is not None and _MTCNN is not None and _InceptionResnetV1 is not None:
        return True
    try:
        import torch as torch_module
        import torch.nn.functional as F_module
        from facenet_pytorch import MTCNN as MTCNNClass, InceptionResnetV1 as ResnetClass
    except ImportError:
        return False

    _torch = torch_module
    _F = F_module
    _MTCNN = MTCNNClass
    _InceptionResnetV1 = ResnetClass
    return True


def _build_models(device_name: str) -> bool:
    global _FACENET_AVAILABLE, _active_device, _mtcnn, _mtcnn_aligned, _resnet
    if not _load_dependencies():
        _FACENET_AVAILABLE = False
        return False

    device = _torch.device(device_name)
    try:
        # Detection + preview: post_process=False, keep all faces
        _mtcnn = _MTCNN(keep_all=True, post_process=False, device=device)
        # Enrollment/recognition: aligned + whitened crops → better embeddings
        _mtcnn_aligned = _MTCNN(
            keep_all=True,
            post_process=True,
            image_size=160,
            margin=14,
            device=device,
        )
        _resnet = _InceptionResnetV1(pretrained="vggface2").to(device).eval()
        _active_device = device_name
        _FACENET_AVAILABLE = True
        return True
    except Exception:
        _FACENET_AVAILABLE = False
        _mtcnn = None
        _mtcnn_aligned = None
        _resnet = None
        return False


def _ensure_models_loaded(preference: str | None = None) -> bool:
    global _device_preference
    requested = _sanitize_device_preference(preference or _device_preference)

    with _model_lock:
        _device_preference = requested
        if not _load_dependencies():
            return False
        target = _resolve_device(requested)

        if _FACENET_AVAILABLE and _mtcnn and _mtcnn_aligned and _resnet and _active_device == target:
            return True
        if _build_models(target):
            return True

        if target == "cuda":
            return _build_models("cpu")
        return False


def configure_inference_device(preference: str) -> str:
    _ensure_models_loaded(preference)
    return _active_device


def peek_active_device() -> str:
    return _active_device


def get_active_device() -> str:
    _ensure_models_loaded()
    return _active_device


def _to_unit_embeddings(raw_embeddings) -> list[list[float]]:
    """L2-normalize embeddings so cosine similarity = dot product."""
    normalized = _F.normalize(raw_embeddings, p=2, dim=1)
    return [e.tolist() for e in normalized]


def _resnet_device():
    if _resnet is None:
        return None
    try:
        return next(_resnet.parameters()).device
    except StopIteration:
        return None


def extract_embeddings(frame) -> list[list[float]]:
    """Return L2-normalized 512-d embeddings for all faces in a BGR frame."""
    if frame is None or not _ensure_models_loaded():
        return []

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    faces = _mtcnn_aligned(pil_img)
    if faces is None:
        return []
    model_device = _resnet_device()
    if model_device is not None:
        faces = faces.to(model_device)

    with _torch.no_grad():
        embeddings = _resnet(faces)

    return _to_unit_embeddings(embeddings)


def extract_averaged_embedding(frames: list) -> list[float] | None:
    """Capture embeddings across multiple frames and return their average.

    Returns None when no face is detected in any frame.
    This produces a more stable reference vector for enrollment.
    """
    if not frames or not _ensure_models_loaded():
        return None

    all_embeddings: list[list[float]] = []
    for frame in frames:
        embs = extract_embeddings(frame)
        if embs:
            all_embeddings.append(embs[0])

    if not all_embeddings:
        return None

    dim = len(all_embeddings[0])
    averaged = [sum(e[i] for e in all_embeddings) / len(all_embeddings) for i in range(dim)]
    # Re-normalize the averaged vector so it stays on the unit sphere.
    norm = sum(x * x for x in averaged) ** 0.5
    if norm == 0:
        return averaged
    return [x / norm for x in averaged]


def _clip_box(box, width: int, height: int) -> tuple[int, int, int, int] | None:
    x1, y1, x2, y2 = box
    left = max(0, min(width - 1, int(x1)))
    top = max(0, min(height - 1, int(y1)))
    right = max(0, min(width - 1, int(x2)))
    bottom = max(0, min(height - 1, int(y2)))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def extract_face_boxes(frame) -> list[tuple[int, int, int, int]]:
    """Return detected face boxes as (x1, y1, x2, y2) in image coordinates."""
    if frame is None or not _ensure_models_loaded():
        return []

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    boxes, _ = _mtcnn.detect(pil_img)
    if boxes is None:
        return []

    height, width = frame.shape[:2]
    return [b for box in boxes if (b := _clip_box(box, width, height)) is not None]


def extract_faces_with_boxes(
    frame,
) -> list[tuple[tuple[int, int, int, int], list[float]]]:
    """Return list of (box, embedding) for every face found in a BGR frame."""
    if frame is None or not _ensure_models_loaded():
        return []

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    boxes, _ = _mtcnn.detect(pil_img)
    if boxes is None:
        return []

    face_tensors = _mtcnn_aligned(pil_img)
    if face_tensors is None:
        return []
    model_device = _resnet_device()
    if model_device is not None:
        face_tensors = face_tensors.to(model_device)

    height, width = frame.shape[:2]
    with _torch.no_grad():
        embeddings = _resnet(face_tensors)
    unit_embeddings = _to_unit_embeddings(embeddings)

    results = []
    for box, emb in zip(boxes, unit_embeddings):
        clipped = _clip_box(box, width, height)
        if clipped is None:
            continue
        results.append((clipped, emb))

    return results


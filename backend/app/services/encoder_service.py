import cv2
from PIL import Image

try:
    import torch
    import torch.nn.functional as F
    from facenet_pytorch import MTCNN, InceptionResnetV1
    # Detection + preview: post_process=False, keep all faces
    _mtcnn = MTCNN(keep_all=True, post_process=False)
    # Enrollment/recognition: aligned + whitened crops → better embeddings
    _mtcnn_aligned = MTCNN(keep_all=True, post_process=True, image_size=160, margin=14)
    _resnet = InceptionResnetV1(pretrained="vggface2").eval()
    _FACENET_AVAILABLE = True
except ImportError:
    _FACENET_AVAILABLE = False


def _to_unit_embeddings(raw_embeddings) -> list[list[float]]:
    """L2-normalize embeddings so cosine similarity = dot product."""
    normalized = F.normalize(raw_embeddings, p=2, dim=1)
    return [e.tolist() for e in normalized]


def extract_embeddings(frame) -> list[list[float]]:
    """Return L2-normalized 512-d embeddings for all faces in a BGR frame."""
    if frame is None or not _FACENET_AVAILABLE:
        return []

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    faces = _mtcnn_aligned(pil_img)
    if faces is None:
        return []

    with torch.no_grad():
        embeddings = _resnet(faces)

    return _to_unit_embeddings(embeddings)


def extract_averaged_embedding(frames: list) -> list[float] | None:
    """Capture embeddings across multiple frames and return their average.

    Returns None when no face is detected in any frame.
    This produces a more stable reference vector for enrollment.
    """
    if not frames or not _FACENET_AVAILABLE:
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
    if frame is None or not _FACENET_AVAILABLE:
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
    if frame is None or not _FACENET_AVAILABLE:
        return []

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    boxes, _ = _mtcnn.detect(pil_img)
    if boxes is None:
        return []

    face_tensors = _mtcnn_aligned(pil_img)
    if face_tensors is None:
        return []

    height, width = frame.shape[:2]
    with torch.no_grad():
        embeddings = _resnet(face_tensors)
    unit_embeddings = _to_unit_embeddings(embeddings)

    results = []
    for box, emb in zip(boxes, unit_embeddings):
        clipped = _clip_box(box, width, height)
        if clipped is None:
            continue
        results.append((clipped, emb))

    return results


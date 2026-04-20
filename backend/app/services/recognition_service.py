import json
import math
import threading

from app.core.database import get_connection, get_db_path
from app.core.schemas import RecognitionResult
from app.services.config_service import read_config

_cache_lock = threading.Lock()
_face_reference_cache: list[dict[str, object]] | None = None
_face_reference_cache_db_path: str | None = None


def _cosine_distance(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm_l = math.sqrt(sum(a * a for a in left))
    norm_r = math.sqrt(sum(b * b for b in right))
    if norm_l == 0.0 and norm_r == 0.0:
        return 0.0
    if norm_l == 0.0 or norm_r == 0.0:
        return 1.0
    return 1.0 - dot / (norm_l * norm_r)


def invalidate_face_reference_cache() -> None:
    global _face_reference_cache, _face_reference_cache_db_path
    with _cache_lock:
        _face_reference_cache = None
        _face_reference_cache_db_path = None


def _load_face_reference_cache() -> list[dict[str, object]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT fp.id, fp.name, fe.encoding_json
            FROM face_profiles fp
            JOIN face_embeddings fe ON fe.face_id = fp.id
            WHERE fe.encoding_json IS NOT NULL
            """
        ).fetchall()

    references: list[dict[str, object]] = []
    for row in rows:
        try:
            reference = json.loads(row["encoding_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(reference, list) or not reference:
            continue
        references.append(
            {
                "id": int(row["id"]),
                "name": str(row["name"]),
                "reference": reference,
            }
        )
    return references


def _get_face_reference_cache() -> list[dict[str, object]]:
    global _face_reference_cache, _face_reference_cache_db_path
    current_db_path = str(get_db_path())
    with _cache_lock:
        if _face_reference_cache is None or _face_reference_cache_db_path != current_db_path:
            _face_reference_cache = _load_face_reference_cache()
            _face_reference_cache_db_path = current_db_path
        return list(_face_reference_cache)


def recognize_face(embedding: list[float] | None) -> RecognitionResult:
    if not embedding:
        return RecognitionResult(status="inconnu")

    config = read_config()
    threshold = config.match_threshold
    match_margin_threshold = config.match_margin_threshold
    references = _get_face_reference_cache()

    best_match: dict[str, float | int | str] | None = None
    second_best_score: float | None = None
    for entry in references:
        distance = _cosine_distance(embedding, entry["reference"])
        score = 1 / (1 + distance)
        if best_match is None or score > float(best_match["score"]):
            if best_match is not None:
                second_best_score = float(best_match["score"])
            best_match = {
                "id": int(entry["id"]),
                "name": str(entry["name"]),
                "score": score,
            }
            continue
        if second_best_score is None or score > second_best_score:
            second_best_score = score

    if not best_match or float(best_match["score"]) < threshold:
        return RecognitionResult(status="inconnu")
    if (
        second_best_score is not None
        and float(best_match["score"]) - second_best_score < match_margin_threshold
    ):
        return RecognitionResult(status="inconnu")

    return RecognitionResult(
        status="reconnu",
        face_id=int(best_match["id"]),
        face_name=str(best_match["name"]),
        score=float(best_match["score"]),
    )


def recognize_faces(embeddings: list[list[float]]) -> list[RecognitionResult]:
    return [recognize_face(embedding) for embedding in embeddings]


def _result_to_dict(result: RecognitionResult) -> dict[str, object | None]:
    return {
        "status": result.status,
        "face_id": result.face_id,
        "face_name": result.face_name,
        "score": result.score,
    }


def save_detection(results: list[RecognitionResult]) -> None:
    if not results:
        results = [RecognitionResult(status="inconnu")]

    primary = max(
        results,
        key=lambda item: (
            item.status == "reconnu",
            item.score if item.score is not None else -1.0,
        ),
    )
    faces_json = json.dumps([_result_to_dict(result) for result in results])

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO detections (status, face_id, score, faces_json)
            VALUES (?, ?, ?, ?)
            """,
            (primary.status, primary.face_id, primary.score, faces_json),
        )
        connection.commit()


def _parse_detection_faces(row) -> list[dict[str, object | None]]:
    faces: list[dict[str, object | None]] = []
    raw_faces_json = row["faces_json"]
    if raw_faces_json:
        try:
            parsed_faces = json.loads(raw_faces_json)
            if isinstance(parsed_faces, list):
                faces = parsed_faces
        except json.JSONDecodeError:
            faces = []
    if not faces:
        faces = [
            {
                "status": str(row["status"]),
                "face_id": row["face_id"],
                "face_name": row["face_name"],
                "score": row["score"],
            }
        ]
    return faces


def get_latest_detection() -> dict[str, object] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT d.id, d.status, d.face_id, fp.name AS face_name, d.score, d.faces_json, d.created_at
            FROM detections d
            LEFT JOIN face_profiles fp ON fp.id = d.face_id
            ORDER BY d.id DESC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return None
    faces = _parse_detection_faces(row)
    return {
        "id": int(row["id"]),
        "status": str(row["status"]),
        "face_id": row["face_id"],
        "face_name": row["face_name"],
        "score": row["score"],
        "faces": faces,
        "faces_count": len(faces),
        "created_at": str(row["created_at"]),
    }


def get_detection_history(limit: int = 10) -> list[dict[str, object]]:
    bounded_limit = max(1, min(50, limit))
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT d.id, d.status, d.face_id, fp.name AS face_name, d.score, d.faces_json, d.created_at
            FROM detections d
            LEFT JOIN face_profiles fp ON fp.id = d.face_id
            ORDER BY d.id DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()

    history: list[dict[str, object]] = []
    for row in rows:
        faces = _parse_detection_faces(row)
        history.append(
            {
                "id": int(row["id"]),
                "status": str(row["status"]),
                "face_id": row["face_id"],
                "face_name": row["face_name"],
                "score": row["score"],
                "faces": faces,
                "faces_count": len(faces),
                "created_at": str(row["created_at"]),
            }
        )
    return history

import json

from app.core.database import get_connection
from app.core.schemas import FaceCreatePayload, FaceRecord
from app.services.recognition_service import invalidate_face_reference_cache


def create_face(payload: FaceCreatePayload) -> FaceRecord:
    encoding_json = json.dumps(payload.encoding) if payload.encoding is not None else None
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO faces (name, encoding_json, adresse, metier, lieu_naissance, age, annee_naissance, autres_infos_html)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                encoding_json,
                getattr(payload, "adresse", None),
                getattr(payload, "metier", None),
                getattr(payload, "lieu_naissance", None),
                getattr(payload, "age", None),
                getattr(payload, "annee_naissance", None),
                getattr(payload, "autres_infos_html", None),
            ),
        )
        face_id = cursor.lastrowid
        row = connection.execute(
            "SELECT id, name, encoding_json, adresse, metier, lieu_naissance, age, annee_naissance, autres_infos_html, created_at FROM faces WHERE id = ?",
            (face_id,),
        ).fetchone()
        connection.commit()
    invalidate_face_reference_cache()

    return FaceRecord(
        id=row["id"],
        name=row["name"],
        has_encoding=bool(row["encoding_json"]),
        adresse=row["adresse"],
        metier=row["metier"],
        lieu_naissance=row["lieu_naissance"],
        age=row["age"],
        annee_naissance=row["annee_naissance"],
        autres_infos_html=row["autres_infos_html"],
        created_at=row["created_at"],
    )


def list_faces() -> list[FaceRecord]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, encoding_json, adresse, metier, lieu_naissance, age, annee_naissance, autres_infos_html, created_at FROM faces ORDER BY id DESC"
        ).fetchall()

    return [
        FaceRecord(
            id=row["id"],
            name=row["name"],
            has_encoding=bool(row["encoding_json"]),
            adresse=row["adresse"],
            metier=row["metier"],
            lieu_naissance=row["lieu_naissance"],
            age=row["age"],
            annee_naissance=row["annee_naissance"],
            autres_infos_html=row["autres_infos_html"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def delete_face(face_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM faces WHERE id = ?", (face_id,)
        )
        connection.commit()
    if cursor.rowcount > 0:
        invalidate_face_reference_cache()
    return cursor.rowcount > 0

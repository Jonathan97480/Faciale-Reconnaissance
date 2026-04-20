import json

from app.core.database import get_connection
from app.core.schemas import FaceCreatePayload, FaceRecord
from app.services.recognition_service import invalidate_face_reference_cache


def _row_to_face_record(row) -> FaceRecord:
    return FaceRecord(
        id=row["id"],
        name=row["name"],
        has_encoding=bool(row["encoding_json"]),
        adresse=row["adresse"],
        metier=row["metier"],
        lieu_naissance=row["lieu_naissance"],
        age=row["age"],
        annee_naissance=row["annee_naissance"],
        autres_infos=row["autres_infos_text"],
        created_at=row["created_at"],
    )


def create_face(payload: FaceCreatePayload) -> FaceRecord:
    encoding_json = json.dumps(payload.encoding) if payload.encoding is not None else None
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO face_profiles (
                name, adresse, metier, lieu_naissance, age, annee_naissance, autres_infos_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.adresse,
                payload.metier,
                payload.lieu_naissance,
                payload.age,
                payload.annee_naissance,
                payload.autres_infos,
            ),
        )
        face_id = cursor.lastrowid
        if encoding_json is not None:
            connection.execute(
                """
                INSERT INTO face_embeddings (face_id, encoding_json)
                VALUES (?, ?)
                """,
                (face_id, encoding_json),
            )
        row = connection.execute(
            """
            SELECT fp.id, fp.name, fe.encoding_json, fp.adresse, fp.metier, fp.lieu_naissance,
                   fp.age, fp.annee_naissance, fp.autres_infos_text, fp.created_at
            FROM face_profiles fp
            LEFT JOIN face_embeddings fe ON fe.face_id = fp.id
            WHERE fp.id = ?
            """,
            (face_id,),
        ).fetchone()
        connection.commit()
    invalidate_face_reference_cache()
    return _row_to_face_record(row)


def list_faces() -> list[FaceRecord]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT fp.id, fp.name, fe.encoding_json, fp.adresse, fp.metier, fp.lieu_naissance,
                   fp.age, fp.annee_naissance, fp.autres_infos_text, fp.created_at
            FROM face_profiles fp
            LEFT JOIN face_embeddings fe ON fe.face_id = fp.id
            ORDER BY fp.id DESC
            """
        ).fetchall()
    return [_row_to_face_record(row) for row in rows]


def delete_face(face_id: int) -> bool:
    with get_connection() as connection:
        connection.execute("DELETE FROM face_embeddings WHERE face_id = ?", (face_id,))
        cursor = connection.execute("DELETE FROM face_profiles WHERE id = ?", (face_id,))
        connection.commit()
    if cursor.rowcount > 0:
        invalidate_face_reference_cache()
    return cursor.rowcount > 0

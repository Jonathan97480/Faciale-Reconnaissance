from fastapi import APIRouter, HTTPException

from app.core.schemas import FaceCreatePayload, FaceRecord
from app.services.face_service import create_face, delete_face, list_faces

router = APIRouter(prefix="/faces", tags=["faces"])


@router.get("", response_model=list[FaceRecord])
def get_faces() -> list[FaceRecord]:
    return list_faces()


@router.post("", response_model=FaceRecord)
def post_face(payload: FaceCreatePayload) -> FaceRecord:
    return create_face(payload)


@router.delete("/{face_id}", status_code=204)
def remove_face(face_id: int) -> None:
    if not delete_face(face_id):
        raise HTTPException(status_code=404, detail="Face not found")

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import os
import secrets

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Pour démo : un seul utilisateur admin
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "adminpass")
SECRET_KEY = os.getenv("JWT_SECRET", "change_me_jwt")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

def verify_user(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and secrets.compare_digest(password, ADMIN_PASSWORD)

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if not verify_user(form_data.username, form_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides")
    # Génère un JWT minimal (ici juste un token factice pour démo)
    import jwt
    token = jwt.encode({"sub": form_data.username}, SECRET_KEY, algorithm="HS256")
    return Token(access_token=token)

def get_current_user(token: str = Depends(oauth2_scheme)):
    import jwt
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")
        if username != ADMIN_USERNAME:
            raise HTTPException(status_code=401, detail="Utilisateur inconnu")
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide")

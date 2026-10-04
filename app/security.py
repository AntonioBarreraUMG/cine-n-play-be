from datetime import datetime, timezone
from hashlib import sha256
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .database import get_db
from .models import Sesion, Usuario

password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash("dummy-password-for-timing")
bearer = HTTPBearer(auto_error=False)

def hash_token(token: str):
    return sha256(token.encode()).hexdigest()

def current_session(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    error = HTTPException(401, "Sesión inválida o expirada", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise error
    session = db.get(Sesion, hash_token(credentials.credentials))
    if session is None or session.fecha_expiracion <= datetime.now(timezone.utc):
        raise error
    return session

def current_user(session: Sesion = Depends(current_session), db: Session = Depends(get_db)):
    user = db.get(Usuario, session.id_usuario)
    if user is None:
        raise HTTPException(401, "Usuario no disponible")
    return user

def require_admin(user: Usuario = Depends(current_user)):
    if user.rol != "admin":
        raise HTTPException(403, "Se requiere rol administrador")
    return user

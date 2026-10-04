from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import Sesion, Usuario
from .schemas import Login, TokenOut, UsuarioOut
from .security import current_session, current_user, password_hash, dummy_hash, hash_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/login", response_model=TokenOut)
def login(body: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(Usuario).where(Usuario.correo == str(body.correo).lower()))
    valid = password_hash.verify(body.password, user.password if user else dummy_hash)
    if not user or not valid:
        raise HTTPException(401, "Correo o contraseña incorrectos")
    token = secrets.token_urlsafe(32)
    seconds = get_settings().session_minutes * 60
    db.add(Sesion(token_hash=hash_token(token), id_usuario=user.id_usuario,
                  fecha_expiracion=datetime.now(timezone.utc) + timedelta(seconds=seconds)))
    db.commit()
    return TokenOut(access_token=token, expires_in=seconds)

@router.get("/me", response_model=UsuarioOut)
def me(user: Usuario = Depends(current_user)):
    return user

@router.post("/logout", status_code=204)
def logout(session: Sesion = Depends(current_session), db: Session = Depends(get_db)):
    db.delete(session)
    db.commit()
    return Response(status_code=204)

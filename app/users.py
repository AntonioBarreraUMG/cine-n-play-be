from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .database import get_db
from .models import Usuario
from .schemas import UsuarioCreate, UsuarioOut
from .security import require_admin, password_hash

router = APIRouter(prefix="/usuarios", tags=["Administración de usuarios"], dependencies=[Depends(require_admin)])

def save(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "El correo ya está registrado o existe un conflicto de datos")

def find_user(db, id_usuario):
    user = db.get(Usuario, id_usuario)
    if user is None:
        raise HTTPException(404, "Usuario no encontrado")
    return user

@router.get("", response_model=list[UsuarioOut])
def list_users(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    return db.scalars(select(Usuario).order_by(Usuario.id_usuario).offset(offset).limit(limit)).all()

@router.post("", response_model=UsuarioOut, status_code=201)
def create_user(body: UsuarioCreate, db: Session = Depends(get_db)):
    data = body.model_dump()
    data["correo"] = str(body.correo).lower()
    data["password"] = password_hash.hash(body.password)
    user = Usuario(**data)
    db.add(user)
    save(db)
    db.refresh(user)
    return user

@router.get("/{id_usuario}", response_model=UsuarioOut)
def get_user(id_usuario: int, db: Session = Depends(get_db)):
    return find_user(db, id_usuario)

@router.put("/{id_usuario}", response_model=UsuarioOut)
def update_user(id_usuario: int, body: UsuarioCreate, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    user = find_user(db, id_usuario)
    if user.id_usuario == admin.id_usuario and body.rol != "admin":
        raise HTTPException(409, "No puedes quitarte tu propio rol administrador")
    user.nombre, user.correo, user.rol = body.nombre, str(body.correo).lower(), body.rol
    user.password = password_hash.hash(body.password)
    save(db)
    db.refresh(user)
    return user

@router.delete("/{id_usuario}", status_code=204)
def delete_user(id_usuario: int, db: Session = Depends(get_db), admin: Usuario = Depends(require_admin)):
    if id_usuario == admin.id_usuario:
        raise HTTPException(409, "No puedes eliminar tu propia cuenta")
    db.delete(find_user(db, id_usuario))
    save(db)
    return Response(status_code=204)

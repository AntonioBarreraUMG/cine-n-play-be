"""Ejecutar desde backend: python -m app.create_admin"""
from getpass import getpass
from sqlalchemy import select
from .database import SessionLocal
from .models import Usuario
from .schemas import UsuarioCreate
from .security import password_hash

def main():
    body = UsuarioCreate(nombre=input("Nombre: "), correo=input("Correo: "),
                         password=getpass("Contraseña (mínimo 8 caracteres): "), rol="admin")
    with SessionLocal() as db:
        if db.scalar(select(Usuario).where(Usuario.correo == str(body.correo).lower())):
            raise SystemExit("El correo ya está registrado")
        db.add(Usuario(nombre=body.nombre, correo=str(body.correo).lower(),
                       password=password_hash.hash(body.password), rol="admin"))
        db.commit()
    print("Administrador creado")

if __name__ == "__main__":
    main()

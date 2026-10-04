from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(String(10), default="usuario")
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Sesion(Base):
    __tablename__ = "sesiones"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario", ondelete="CASCADE"))
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True))

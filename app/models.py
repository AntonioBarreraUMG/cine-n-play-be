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

class Conversacion(Base):
    __tablename__ = "conversaciones"
    id_conversacion: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario", ondelete="CASCADE"))
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Mensaje(Base):
    __tablename__ = "mensajes"
    id_mensaje: Mapped[int] = mapped_column(primary_key=True)
    id_conversacion: Mapped[int] = mapped_column(ForeignKey("conversaciones.id_conversacion", ondelete="CASCADE"))
    rol: Mapped[str] = mapped_column(String(10))
    contenido: Mapped[str] = mapped_column(Text)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ConsumoToken(Base):
    __tablename__ = "consumo_tokens"
    id_consumo: Mapped[int] = mapped_column(primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario", ondelete="CASCADE"))
    categoria: Mapped[str] = mapped_column(String(12))
    tokens: Mapped[int] = mapped_column()
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

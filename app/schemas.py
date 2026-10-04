from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class Login(BaseModel):
    correo: EmailStr
    password: str = Field(min_length=1, max_length=128)

class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)
    rol: Literal["usuario", "admin"] = "usuario"

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("El nombre es obligatorio")
        return value

class UsuarioOut(BaseModel):
    id_usuario: int
    nombre: str
    correo: EmailStr
    rol: Literal["usuario", "admin"]
    fecha_registro: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

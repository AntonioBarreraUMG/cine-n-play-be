"""Catálogo existente: solo reflexión; nunca crea ni altera tablas."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import MetaData, Table, select, insert, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .database import get_db
from .models import Usuario
from .security import current_user, require_admin

class CatalogBase(BaseModel):
    titulo: str = Field(min_length=1)
    genero: str | None = None
    plataforma: str | None = None
    anio_lanzamiento: int | None = None
    calificacion: Decimal | None = Field(default=None, allow_inf_nan=False)
    fecha_registro: datetime | None = None
    model_config = ConfigDict(extra='forbid')

    @field_validator('titulo')
    @classmethod
    def title_nonempty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('El título es obligatorio')
        return value

    @field_validator('fecha_registro')
    @classmethod
    def date_without_timezone(cls, value):
        if value is not None and value.tzinfo is not None:
            raise ValueError('fecha_registro debe ser una fecha sin zona horaria')
        return value

class PeliculaIn(CatalogBase):
    director: str | None = None
    actores: str | None = None
    productora: str | None = None
    duracion_minutos: int | None = Field(default=None, ge=1)
    clasificacion: str | None = None

class VideojuegoIn(CatalogBase):
    desarrollador: str | None = None
    jugadores: str | None = None

class PeliculaOut(PeliculaIn):
    id_pelicula: int

class VideojuegoOut(VideojuegoIn):
    id_videojuego: int

# Reflexión por solicitud: acepta los defaults reales del catálogo.
# Los nombres se limitan a dos constantes; no provienen de SQL del usuario.
def get_catalog_tables(db: Session = Depends(get_db)):
    metadata = MetaData()
    return {name: Table(name, metadata, schema='public', autoload_with=db.connection())
            for name in ('peliculas', 'videojuegos')}

router = APIRouter(tags=['Catálogo'])

def install_routes(name, id_column, input_schema, output_schema):
    def listing(
        titulo: str | None = None,
        genero: str | None = None,
        plataforma: str | None = None,
        calificacion_min: Annotated[Decimal | None, Query(allow_inf_nan=False)] = None,
        calificacion_max: Annotated[Decimal | None, Query(allow_inf_nan=False)] = None,
        anio_lanzamiento: int | None = None,
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        db: Session = Depends(get_db),
        tables: dict = Depends(get_catalog_tables),
        user: Usuario = Depends(current_user),
    ):
        if calificacion_min is not None and calificacion_max is not None and calificacion_min > calificacion_max:
            raise HTTPException(422, 'La calificación mínima no puede superar la máxima')
        table = tables[name]
        query = select(table)
        # contains(autoescape=True) trata % y _ como texto, no como comodines.
        for column, value in (('titulo', titulo), ('genero', genero), ('plataforma', plataforma)):
            if value is not None:
                query = query.where(table.c[column].icontains(value, autoescape=True))
        if calificacion_min is not None:
            query = query.where(table.c.calificacion >= calificacion_min)
        if calificacion_max is not None:
            query = query.where(table.c.calificacion <= calificacion_max)
        if anio_lanzamiento is not None:
            query = query.where(table.c.anio_lanzamiento == anio_lanzamiento)
        return db.execute(query.order_by(table.c[id_column]).offset(offset).limit(limit)).mappings().all()

    def detail(item_id: int, db: Session = Depends(get_db), tables: dict = Depends(get_catalog_tables), user: Usuario = Depends(current_user)):
        table = tables[name]
        row = db.execute(select(table).where(table.c[id_column] == item_id)).mappings().first()
        if row is None:
            raise HTTPException(404, 'Registro no encontrado')
        return row

    def commit(db):
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'El registro entra en conflicto con las restricciones de la base')

    def create(body, db: Session = Depends(get_db), tables: dict = Depends(get_catalog_tables), admin: Usuario = Depends(require_admin)):
        table = tables[name]
        values = body.model_dump(exclude_unset=True)
        # El ID se genera mediante el default/identity real de PostgreSQL.
        try:
            row = db.execute(insert(table).values(**values).returning(table)).mappings().one()
            commit(db)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'No se pudo crear: revisa restricciones y generación automática del ID')
        return row
    create.__annotations__['body'] = input_schema

    def replace(item_id: int, body, db: Session = Depends(get_db), tables: dict = Depends(get_catalog_tables), admin: Usuario = Depends(require_admin)):
        table = tables[name]
        values = body.model_dump()
        # Omitir la fecha conserva el valor almacenado; enviarla en null lo borra.
        if 'fecha_registro' not in body.model_fields_set:
            values.pop('fecha_registro')
        try:
            row = db.execute(update(table).where(table.c[id_column] == item_id).values(**values).returning(table)).mappings().first()
            if row is None:
                db.rollback()
                raise HTTPException(404, 'Registro no encontrado')
            commit(db)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Los datos entran en conflicto con las restricciones de la base')
        return row
    replace.__annotations__['body'] = input_schema

    def remove(item_id: int, db: Session = Depends(get_db), tables: dict = Depends(get_catalog_tables), admin: Usuario = Depends(require_admin)):
        table = tables[name]
        try:
            removed = db.execute(delete(table).where(table.c[id_column] == item_id).returning(table.c[id_column])).first()
            if removed is None:
                db.rollback()
                raise HTTPException(404, 'Registro no encontrado')
            commit(db)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'El registro está relacionado con otros datos')
        return Response(status_code=204)

    for path, endpoint, method, response_model, status in (
        ('', listing, 'GET', list[output_schema], 200),
        ('/{item_id}', detail, 'GET', output_schema, 200),
        ('', create, 'POST', output_schema, 201),
        ('/{item_id}', replace, 'PUT', output_schema, 200),
        ('/{item_id}', remove, 'DELETE', None, 204),
    ):
        router.add_api_route('/' + name + path, endpoint, methods=[method],
                             response_model=response_model, status_code=status,
                             name=f'{method.lower()}_{name}', operation_id=f'{method.lower()}_{name}_{"item" if path else "collection"}')

install_routes('peliculas', 'id_pelicula', PeliculaIn, PeliculaOut)
install_routes('videojuegos', 'id_videojuego', VideojuegoIn, VideojuegoOut)

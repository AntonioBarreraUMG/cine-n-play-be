from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.orm import Session, aliased
from .database import get_db
from .models import Usuario, Conversacion, Mensaje, ConsumoToken
from .security import current_user
from .openai_service import get_ai_service

router = APIRouter(tags=['Chat e historial'])

class ChatIn(BaseModel):
    pregunta: str = Field(min_length=1, max_length=4000)

    @field_validator('pregunta')
    @classmethod
    def nonempty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('La pregunta es obligatoria')
        return value

class ChatOut(BaseModel):
    id_conversacion: int
    pregunta: str
    respuesta: str
    categoria: Literal['peliculas', 'videojuegos', 'ambas']
    tokens: int
    fecha: datetime

class HistoryOut(BaseModel):
    id_conversacion: int
    fecha: datetime
    pregunta: str
    respuesta: str

class ConsumptionOut(BaseModel):
    peliculas: int
    videojuegos: int
    total: int

# Exactamente dos consultas de datos sin filtros, límites ni caché.
# Solo accede al catálogo; jamás incluye usuarios ni contraseñas en el contexto.
def load_full_catalog(db: Session):
    from sqlalchemy import text
    peliculas = db.execute(text('SELECT * FROM public.peliculas')).mappings().all()
    videojuegos = db.execute(text('SELECT * FROM public.videojuegos')).mappings().all()
    catalogo = {'peliculas':[dict(row) for row in peliculas],
                'videojuegos':[dict(row) for row in videojuegos]}
    # Libera la transacción de lectura antes de esperar la respuesta externa.
    db.rollback()
    return catalogo

def get_catalog_loader():
    return load_full_catalog

def token_distribution(categoria, total):
    if categoria == 'ambas':
        return {'peliculas':(total + 1) // 2, 'videojuegos':total // 2}
    return {categoria:total}

@router.post('/chat', response_model=ChatOut)
def chat(body: ChatIn, db: Session = Depends(get_db), user: Usuario = Depends(current_user),
         ai_service=Depends(get_ai_service), catalog_loader=Depends(get_catalog_loader)):
    user_id = user.id_usuario
    catalogo = catalog_loader(db)
    completion = ai_service(body.pregunta, catalogo)
    # Solo guarda una consulta si OpenAI devolvió una respuesta válida.
    # Pregunta, respuesta y consumo se confirman en una única transacción.
    conversation = Conversacion(id_usuario=user_id)
    try:
        db.add(conversation)
        db.flush()
        db.add(Mensaje(id_conversacion=conversation.id_conversacion, rol='user', contenido=body.pregunta))
        db.add(Mensaje(id_conversacion=conversation.id_conversacion, rol='assistant', contenido=completion.answer.respuesta))
        for categoria, tokens in token_distribution(completion.answer.categoria, completion.tokens).items():
            db.add(ConsumoToken(id_usuario=user_id, categoria=categoria, tokens=tokens))
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(conversation)
    return ChatOut(id_conversacion=conversation.id_conversacion, pregunta=body.pregunta,
                   respuesta=completion.answer.respuesta, categoria=completion.answer.categoria,
                   tokens=completion.tokens, fecha=conversation.fecha_creacion)

@router.get('/historial', response_model=list[HistoryOut])
def history(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
            db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    question, answer = aliased(Mensaje), aliased(Mensaje)
    query = (select(Conversacion.id_conversacion, Conversacion.fecha_creacion.label('fecha'),
                    question.contenido.label('pregunta'), answer.contenido.label('respuesta'))
             .join(question, (question.id_conversacion == Conversacion.id_conversacion) & (question.rol == 'user'))
             .join(answer, (answer.id_conversacion == Conversacion.id_conversacion) & (answer.rol == 'assistant'))
             .where(Conversacion.id_usuario == user.id_usuario)
             .order_by(Conversacion.fecha_creacion.desc(), Conversacion.id_conversacion.desc())
             .offset(offset).limit(limit))
    return db.execute(query).mappings().all()

@router.get('/consumo', response_model=ConsumptionOut)
def consumption(db: Session = Depends(get_db), user: Usuario = Depends(current_user)):
    rows = db.execute(select(ConsumoToken.categoria, func.sum(ConsumoToken.tokens))
                      .where(ConsumoToken.id_usuario == user.id_usuario).group_by(ConsumoToken.categoria)).all()
    values = {'peliculas':0, 'videojuegos':0}
    values.update({categoria:int(total) for categoria, total in rows})
    return ConsumptionOut(**values, total=sum(values.values()))

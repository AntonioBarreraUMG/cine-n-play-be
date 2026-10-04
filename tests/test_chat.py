import os
os.environ.setdefault('DATABASE_URL','postgresql+psycopg://test:test@localhost/test')
from decimal import Decimal
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import pytest
from app.main import app
from app.database import Base, get_db
from app.models import Usuario, Mensaje, Conversacion, ConsumoToken
from app.security import current_user
from app.chat import get_catalog_loader, load_full_catalog
from app.openai_service import get_ai_service, Completion, AIAnswer, build_messages

@pytest.fixture
def chat_client():
    engine=create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    calls=[]
    catalogs=[]
    with Session(engine, expire_on_commit=False) as db:
        user=Usuario(nombre='Uno',correo='one@example.com',password='unused',rol='usuario')
        other=Usuario(nombre='Otro',correo='other@example.com',password='unused',rol='usuario')
        db.add_all([user,other]); db.commit()
        def loader(session):
            catalog={'peliculas':[{'titulo':'Drama','calificacion':Decimal('9.2')}],
                     'videojuegos':[{'titulo':'Aventura'}]}
            catalogs.append(catalog)
            return catalog
        def ai(question,catalog):
            calls.append((question,catalog))
            return Completion(AIAnswer(respuesta='Respuesta sobre el catálogo',categoria='ambas'),101)
        app.dependency_overrides[get_db]=lambda:db
        app.dependency_overrides[current_user]=lambda:user
        app.dependency_overrides[get_catalog_loader]=lambda:loader
        app.dependency_overrides[get_ai_service]=lambda:ai
        with TestClient(app) as client:
            yield client,db,user,other,calls,catalogs
    app.dependency_overrides.clear()
    engine.dispose()

def test_chat_persists_independent_questions_and_consumption(chat_client):
    client,db,user,other,calls,catalogs=chat_client
    for question in ('Primera pregunta','Segunda pregunta'):
        result=client.post('/chat',json={'pregunta':question})
        assert result.status_code==200,result.text
        assert result.json()['tokens']==101
    assert len(catalogs)==2
    assert [call[0] for call in calls]==['Primera pregunta','Segunda pregunta']
    assert all(set(call[1])=={'peliculas','videojuegos'} for call in calls)
    assert db.scalar(select(func.count()).select_from(Conversacion))==2
    assert db.scalar(select(func.count()).select_from(Mensaje))==4
    assert len(client.get('/historial').json())==2
    assert client.get('/consumo').json()=={'peliculas':102,'videojuegos':100,'total':202}
    app.dependency_overrides[current_user]=lambda:other
    assert client.get('/historial').json()==[]
    assert client.get('/consumo').json()=={'peliculas':0,'videojuegos':0,'total':0}

def test_provider_failure_saves_nothing(chat_client):
    client,db,*_=chat_client
    def fail(question,catalog):
        raise HTTPException(429,'Límite de Groq')
    app.dependency_overrides[get_ai_service]=lambda:fail
    assert client.post('/chat',json={'pregunta':'Dame películas'}).status_code==429
    assert db.scalar(select(func.count()).select_from(Conversacion))==0
    assert db.scalar(select(func.count()).select_from(ConsumoToken))==0
    assert client.post('/chat',json={'pregunta':'  '}).status_code==422

def test_full_catalog_sql_has_no_filters_or_limits():
    class Result:
        def mappings(self):return self
        def all(self):return [{'titulo':'Completo'}]
    class DB:
        def __init__(self):self.sql=[];self.released=False
        def execute(self,query):self.sql.append(str(query));return Result()
        def rollback(self):self.released=True
    db=DB()
    catalog=load_full_catalog(db)
    assert db.sql==['SELECT * FROM public.peliculas','SELECT * FROM public.videojuegos']
    assert len(catalog['peliculas'])==len(catalog['videojuegos'])==1
    assert db.released

def test_messages_only_current_question_and_catalog():
    messages=build_messages('Pregunta actual',{'peliculas':[{'calificacion':Decimal('9.5')}],'videojuegos':[]})
    assert len(messages)==2
    assert 'Pregunta actual' in messages[1]['content']
    assert '9.5' in messages[1]['content']

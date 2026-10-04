import os
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://test:test@localhost/test')
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Numeric, DateTime
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import get_db
from app.catalog import get_catalog_tables
from app.security import current_user
from app.models import Usuario

@pytest.fixture
def catalog_client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    meta = MetaData()
    common = lambda: [Column('titulo', String, nullable=False), Column('genero', String), Column('plataforma', String),
                       Column('anio_lanzamiento', Integer), Column('calificacion', Numeric), Column('fecha_registro', DateTime)]
    movies = Table('peliculas', meta, Column('id_pelicula', Integer, primary_key=True), *common(),
                   Column('director', String), Column('actores', String), Column('productora', String),
                   Column('duracion_minutos', Integer), Column('clasificacion', String))
    games = Table('videojuegos', meta, Column('id_videojuego', Integer, primary_key=True), *common(),
                  Column('desarrollador', String), Column('jugadores', String))
    meta.create_all(engine)
    user = Usuario(id_usuario=1, nombre='Admin', correo='admin@example.com', password='unused', rol='admin', fecha_registro=datetime.now(timezone.utc))
    with Session(engine) as db:
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_catalog_tables] = lambda: {'peliculas':movies, 'videojuegos':games}
        app.dependency_overrides[current_user] = lambda: user
        with TestClient(app) as client:
            yield client, user
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.mark.parametrize('category,id_column', [('peliculas','id_pelicula'),('videojuegos','id_videojuego')])
def test_crud_filters_and_missing_records(catalog_client, category, id_column):
    client, _ = catalog_client
    response = client.post('/'+category, json={'titulo':'Aventura 100%', 'genero':'Aventura', 'calificacion':'9.2'})
    assert response.status_code == 201, response.text
    item_id = response.json()[id_column]
    assert client.post('/'+category, json={'titulo':'Otro', 'genero':'Drama','calificacion':'7.1'}).status_code == 201
    result = client.get('/'+category, params={'genero':'aventura', 'calificacion_min':'8.5'}).json()
    assert len(result) == 1 and result[0][id_column] == item_id
    assert len(client.get('/'+category, params={'titulo':'%'}).json()) == 1
    assert client.put(f'/{category}/{item_id}', json={'titulo':'Actualizado'}).status_code == 200
    assert client.get(f'/{category}/{item_id}').json()['titulo'] == 'Actualizado'
    assert client.delete(f'/{category}/{item_id}').status_code == 204
    assert client.get(f'/{category}/{item_id}').status_code == 404
    assert client.get('/'+category, params={'calificacion_min':9,'calificacion_max':2}).status_code == 422

def test_user_reads_but_cannot_modify(catalog_client):
    client, user = catalog_client
    user.rol = 'usuario'
    assert client.get('/peliculas').status_code == 200
    assert client.post('/peliculas', json={'titulo':'Prueba'}).status_code == 403
    assert client.put('/videojuegos/1', json={'titulo':'Prueba'}).status_code == 403
    assert client.delete('/videojuegos/1').status_code == 403

def test_validation_and_text_players(catalog_client):
    client, _ = catalog_client
    assert client.post('/peliculas', json={'titulo':'  '}).status_code == 422
    assert client.post('/peliculas', json={'titulo':'Prueba','duracion_minutos':-1}).status_code == 422
    assert client.post('/peliculas', json={'titulo':'Prueba','fecha_registro':'2026-10-04T12:00:00Z'}).status_code == 422
    assert client.post('/videojuegos', json={'titulo':'Prueba','jugadores':'1-4 jugadores'}).status_code == 201
    assert client.get('/peliculas', params={'limit':101}).status_code == 422

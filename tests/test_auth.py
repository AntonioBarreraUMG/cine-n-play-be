import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://test:test@localhost/test'
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import Usuario, Sesion
from app.security import password_hash

class FakeDB:
    def __init__(self):
        self.user = Usuario(id_usuario=1, nombre='Usuario', correo='user@example.com',
                            password=password_hash.hash('password123'), rol='usuario',
                            fecha_registro=datetime.now(timezone.utc))
        self.sessions = {}
    def scalar(self, query):
        return self.user
    def get(self, model, key):
        return self.sessions.get(key) if model is Sesion else self.user
    def add(self, value):
        self.sessions[value.token_hash] = value
    def commit(self):
        pass
    def delete(self, value):
        del self.sessions[value.token_hash]

@pytest.fixture
def setup_client():
    db = FakeDB()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client, db
    app.dependency_overrides.clear()

def login(client):
    result = client.post('/auth/login', json={'correo':'user@example.com','password':'password123'})
    assert result.status_code == 200
    return {'Authorization': 'Bearer ' + result.json()['access_token']}

def test_logout_revokes_token_and_hash_not_exposed(setup_client):
    client, db = setup_client
    headers = login(client)
    result = client.get('/auth/me', headers=headers)
    assert result.status_code == 200
    assert 'password' not in result.json()
    assert client.post('/auth/logout', headers=headers).status_code == 204
    assert client.get('/auth/me', headers=headers).status_code == 401

def test_normal_user_cannot_access_administration(setup_client):
    client, db = setup_client
    headers = login(client)
    assert client.get('/usuarios', headers=headers).status_code == 403
    assert client.post('/usuarios', headers=headers, json={}).status_code == 403

def test_wrong_password_and_missing_token(setup_client):
    client, db = setup_client
    assert client.post('/auth/login', json={'correo':'user@example.com','password':'wrong'}).status_code == 401
    assert client.get('/auth/me').status_code == 401

def test_expired_session(setup_client):
    client, db = setup_client
    headers = login(client)
    next(iter(db.sessions.values())).fecha_expiracion = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert client.get('/auth/me', headers=headers).status_code == 401

def test_invalid_user_input(setup_client):
    client, db = setup_client
    db.user.rol = 'admin'
    headers = login(client)
    assert client.post('/usuarios', headers=headers, json={'nombre':'  ','correo':'invalid','password':'x'}).status_code == 422

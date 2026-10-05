import os
os.environ.setdefault('DATABASE_URL','postgresql+psycopg://test:test@localhost/test')
import json
import httpx
import pytest
from fastapi import HTTPException
from app.config import Settings
from app import openai_service as service

@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(service,'get_settings',lambda:Settings(database_url='postgresql+psycopg://x:x@localhost/x',openai_api_key='fake-key'))
    real_client=httpx.Client
    def install(handler):
        monkeypatch.setattr(service.httpx,'Client',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    return install

def test_openai_request_and_word_count(provider):
    raw=json.dumps({'respuesta':'Una película disponible','categoria':'peliculas'},ensure_ascii=False)
    def handler(request):
        body=json.loads(request.content)
        assert request.url==httpx.URL('https://api.openai.com/v1/chat/completions')
        assert body['model']=='gpt-4.1-mini'
        assert body['response_format']['type']=='json_schema'
        assert body['response_format']['json_schema']['strict'] is True
        assert body['store'] is False
        assert len(body['messages'])==2
        assert 'Juego' in body['messages'][1]['content']
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':raw}}], 'usage':{'total_tokens':999999}})
    provider(handler)
    catalog={'peliculas':[{'titulo':'Película'}],'videojuegos':[{'titulo':'Juego'}]}
    completion=service.ask_openai('Dame películas',catalog)
    expected=len('Dame películas'.split())+len('Una película disponible'.split())
    assert completion.tokens==expected
    assert completion.answer.categoria=='peliculas'

@pytest.mark.parametrize('upstream,expected',[(429,429),(401,503),(403,503),(400,502),(500,502)])
def test_provider_errors(provider,upstream,expected):
    provider(lambda request:httpx.Response(upstream,json={'error':'provider detail'}))
    with pytest.raises(HTTPException) as e:
        service.ask_openai('Pregunta',{})
    assert e.value.status_code==expected

@pytest.mark.parametrize('choice',[
    {'finish_reason':'stop','message':{'content':'No es JSON'}},
    {'finish_reason':'length','message':{'content':'{}'}},
    {'finish_reason':'stop','message':{'content':'{"respuesta":" ","categoria":"peliculas"}'}},
])
def test_invalid_or_truncated_reply(provider,choice):
    provider(lambda request:httpx.Response(200,json={'choices':[choice]}))
    with pytest.raises(HTTPException) as e:service.ask_openai('Pregunta',{})
    assert e.value.status_code==502

def test_timeout(provider):
    def handler(request):raise httpx.ReadTimeout('timeout',request=request)
    provider(handler)
    with pytest.raises(HTTPException) as e:service.ask_openai('Pregunta',{})
    assert e.value.status_code==504

@pytest.mark.parametrize('status,code',[(404,'model_not_found'),(413,'context_length_exceeded'),(422,'json_validate_failed'),(503,None)])
def test_error_reports_actual_upstream_status(provider,status,code):
    provider(lambda request:httpx.Response(status,json={'error':{'code':code,'message':'private raw data'}}))
    with pytest.raises(HTTPException) as exc:service.ask_openai('Pregunta',{})
    assert f'HTTP {status}' in exc.value.detail
    assert 'private raw data' not in exc.value.detail
    if code:assert code in exc.value.detail

def test_oversize_rate_limit_reports_quantities_only(provider):
    provider(lambda request:httpx.Response(413,json={'error':{'code':'rate_limit_exceeded','message':'Organization private: Limit 8000, Requested 14000'}}))
    with pytest.raises(HTTPException) as exc:service.ask_openai('Pregunta',{})
    assert 'cuota' in exc.value.detail
    assert '8000' in exc.value.detail and '14000' in exc.value.detail
    assert 'private' not in exc.value.detail

def test_compact_catalog_preserves_every_value():
    catalog={'peliculas':[{'titulo':'Título uno','genero':'Drama','director':None},
                          {'titulo':'Título dos','genero':'Drama','director':'Director'}],
             'videojuegos':[{'titulo':'Juego','jugadores':'1-4'}]}
    content=service.build_messages('Pregunta',catalog)[1]['content']
    encoded=content.split('CATÁLOGO JSON:\n',1)[1].split('\nPREGUNTA:\n',1)[0]
    compact=json.loads(encoded)
    restored={category:[dict(zip(table['columnas'],row)) for row in table['filas']]
              for category,table in compact.items()}
    assert restored==catalog
    assert content.count('director')==1

def test_insufficient_quota_has_actionable_hint(provider):
    provider(lambda request:httpx.Response(429,json={'error':{'code':'insufficient_quota'}}))
    with pytest.raises(HTTPException) as exc:service.ask_openai('Pregunta',{})
    assert 'créditos' in exc.value.detail

def test_refusal_is_not_saved_as_response(provider):
    provider(lambda request:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':None,'refusal':'Refused'}}]}))
    with pytest.raises(HTTPException) as exc:service.ask_openai('Pregunta',{})
    assert exc.value.status_code==502
    assert 'rechazó' in exc.value.detail


def test_token_count_excludes_catalog_instructions_and_json(provider):
    raw=json.dumps({'respuesta':'Primera palabra\nsegunda palabra','categoria':'videojuegos'})
    provider(lambda request:httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':raw}}]}))
    small=service.ask_openai('Dame  juegos',{'peliculas':[],'videojuegos':[]})
    large=service.ask_openai('Dame  juegos',{'peliculas':[{'titulo':'Un catálogo enorme con muchas palabras '*100}],'videojuegos':[]})
    assert small.tokens==large.tokens==6

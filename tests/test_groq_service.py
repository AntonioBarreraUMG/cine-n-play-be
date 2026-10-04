import os
os.environ.setdefault('DATABASE_URL','postgresql+psycopg://test:test@localhost/test')
import json
import httpx
import pytest
from fastapi import HTTPException
from app.config import Settings
from app import groq_service as service

@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(service,'get_settings',lambda:Settings(database_url='postgresql+psycopg://x:x@localhost/x',groq_api_key='fake-key'))
    real_client=httpx.Client
    def install(handler):
        monkeypatch.setattr(service.httpx,'Client',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    return install

def test_groq_request_and_word_count(provider):
    raw=json.dumps({'respuesta':'Una película disponible','categoria':'peliculas'},ensure_ascii=False)
    def handler(request):
        body=json.loads(request.content)
        assert request.url==httpx.URL('https://api.groq.com/openai/v1/chat/completions')
        assert body['model']=='openai/gpt-oss-120b'
        assert body['response_format']=={'type':'json_object'}
        assert len(body['messages'])==2
        assert 'Juego' in body['messages'][1]['content']
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':raw}}], 'usage':{'total_tokens':999999}})
    provider(handler)
    catalog={'peliculas':[{'titulo':'Película'}],'videojuegos':[{'titulo':'Juego'}]}
    completion=service.ask_groq('Dame películas',catalog)
    expected=sum(len(m['content'].split()) for m in service.build_messages('Dame películas',catalog))+len(raw.split())
    assert completion.tokens==expected
    assert completion.answer.categoria=='peliculas'

@pytest.mark.parametrize('upstream,expected',[(429,429),(401,503),(403,503),(400,502),(500,502)])
def test_provider_errors(provider,upstream,expected):
    provider(lambda request:httpx.Response(upstream,json={'error':'provider detail'}))
    with pytest.raises(HTTPException) as e:
        service.ask_groq('Pregunta',{})
    assert e.value.status_code==expected

@pytest.mark.parametrize('choice',[
    {'finish_reason':'stop','message':{'content':'No es JSON'}},
    {'finish_reason':'length','message':{'content':'{}'}},
    {'finish_reason':'stop','message':{'content':'{"respuesta":" ","categoria":"peliculas"}'}},
])
def test_invalid_or_truncated_reply(provider,choice):
    provider(lambda request:httpx.Response(200,json={'choices':[choice]}))
    with pytest.raises(HTTPException) as e:service.ask_groq('Pregunta',{})
    assert e.value.status_code==502

def test_timeout(provider):
    def handler(request):raise httpx.ReadTimeout('timeout',request=request)
    provider(handler)
    with pytest.raises(HTTPException) as e:service.ask_groq('Pregunta',{})
    assert e.value.status_code==504

@pytest.mark.parametrize('status,code',[(404,'model_not_found'),(413,'context_length_exceeded'),(422,'json_validate_failed'),(503,None)])
def test_error_reports_actual_upstream_status(provider,status,code):
    provider(lambda request:httpx.Response(status,json={'error':{'code':code,'message':'private raw data'}}))
    with pytest.raises(HTTPException) as exc:service.ask_groq('Pregunta',{})
    assert f'HTTP {status}' in exc.value.detail
    assert 'private raw data' not in exc.value.detail
    if code:assert code in exc.value.detail

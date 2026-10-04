"""Desde backend: python -m app.check_groq. No usa PostgreSQL ni muestra la key."""
import httpx
from fastapi import HTTPException
from .config import get_settings
from .groq_service import ask_groq, raise_for_groq_error

def main():
    settings = get_settings()
    key = settings.groq_api_key.get_secret_value().strip() if settings.groq_api_key else ''
    if not key:
        raise SystemExit('Falta GROQ_API_KEY en .env')
    model = settings.groq_model.strip()
    print('Modelo configurado:', model)
    try:
        with httpx.Client(timeout=settings.groq_timeout_seconds) as client:
            response = client.get('https://api.groq.com/openai/v1/models', headers={'Authorization':'Bearer ' + key})
        raise_for_groq_error(response)
        models = sorted(item['id'] for item in response.json()['data'])
        print('Modelos publicados por Groq:')
        for item in models:
            print(' -', item)
        if model not in models:
            raise SystemExit('El modelo configurado no está en la lista. Copia un ID compatible con chat a GROQ_MODEL y reinicia.')
        print('Probando chat con catálogo vacío (consume una pequeña cuota)...')
        result = ask_groq('¿Hay películas disponibles?', {'peliculas':[], 'videojuegos':[]})
        print('Conexión y formato correctos:', result.answer.respuesta)
    except HTTPException as exc:
        raise SystemExit(exc.detail)
    except httpx.RequestError:
        raise SystemExit('No fue posible conectar con Groq')
    except (ValueError, KeyError, TypeError):
        raise SystemExit('Groq devolvió una lista de modelos con formato inesperado')

if __name__ == '__main__':
    main()

"""Desde backend: python -m app.check_openai. Prueba pequeña; consume créditos API."""
from fastapi import HTTPException
from .config import get_settings
from .openai_service import ask_openai

def main():
    settings = get_settings()
    print('Modelo configurado:', settings.openai_model)
    try:
        result = ask_openai('¿Hay películas disponibles?', {'peliculas':[], 'videojuegos':[]})
    except HTTPException as exc:
        raise SystemExit(exc.detail)
    print('Conexión y formato correctos:', result.answer.respuesta)

if __name__ == '__main__':
    main()

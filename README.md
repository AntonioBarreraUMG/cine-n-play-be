# Backend de películas y videojuegos con OpenAI

Python 3.11+, FastAPI, SQLAlchemy 2, psycopg 3 y PostgreSQL.
Incluye autenticación con sesiones revocables, roles, CRUD de usuarios y catálogo,
chat, historial propio y consumo de palabras del proyecto.

## Actualizar desde Groq

1. Sustituye app y tests por las carpetas de este proyecto. Conserva .env y .venv.
2. Instala `python -m pip install -r requirements.txt`.
3. Conserva DATABASE_URL, CORS_ORIGINS y SESSION_MINUTES en .env; añade:

```dotenv
OPENAI_API_KEY=TU_CLAVE_DEL_PROYECTO_CON_CREDITOS
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT_SECONDS=60
OPENAI_MAX_COMPLETION_TOKENS=2048
```

4. Elimina las variables GROQ_* que ya no uses. No repitas 001_app.sql.
5. Comprueba conexión: `python -m app.check_openai`. Envía una consulta pequeña y consume créditos API.
6. Reinicia: `python -m uvicorn app.main:app --reload`.
7. Abre http://127.0.0.1:8000/docs, inicia sesión, autoriza y prueba POST /chat:

```json
{"pregunta":"¿Cuáles son 3 películas de drama?"}
```

## Instalación inicial

Desde esta carpeta:

```bash
python -m venv .venv
```

Windows PowerShell: `.venv\Scripts\Activate.ps1`
Windows CMD: `.venv\Scripts\activate.bat`
macOS/Linux: `source .venv/bin/activate`

```bash
python -m pip install -r requirements.txt
```

Copia .env.example a .env. Ajusta DATABASE_URL a la base PostgreSQL existente.
El prefijo es postgresql+psycopg://. Codifica caracteres especiales de credenciales para URL.
No compartas la clave ni .env. La clave de OpenAI pertenece al proyecto donde tienes créditos de API.

En pgAdmin ejecuta sql/001_app.sql una sola vez, si no has creado sus tablas.
No crea ni modifica public.peliculas ni public.videojuegos. Si ya existen las tablas
propias de la aplicación, compara sus esquemas antes de ejecutar el script.

```bash
python -m app.create_admin
python -m uvicorn app.main:app --reload
```

## Endpoints

- POST /auth/login: correo y password; devuelve token.
- GET /auth/me: usuario autenticado, sin contraseña.
- POST /auth/logout: revoca el token actual.
- GET/POST /usuarios y GET/PUT/DELETE /usuarios/{id}: solo administrador.
- GET /peliculas y GET /videojuegos: catálogo paginado para usuarios autenticados.
- GET /peliculas/{id} y GET /videojuegos/{id}: detalle.
- POST/PUT/DELETE del catálogo: solo administrador.
- POST /chat: pregunta independiente con catálogo completo.
- GET /historial: historial propio, fecha/pregunta/respuesta; offset y limit.
- GET /consumo: acumulados peliculas, videojuegos y total para la gráfica del frontend.
- GET /health y GET /health/db: estado de aplicación y conexión.

Filtros de catálogo: titulo, genero, plataforma, anio_lanzamiento,
calificacion_min (>=), calificacion_max (<=), offset y limit (máximo 100).
Los filtros del catálogo administrativo no se utilizan en el chat.
PUT reemplaza campos; campos opcionales omitidos quedan null salvo fecha_registro del catálogo.
Los IDs del catálogo deben tener identity o default de secuencia. Usa
sql/verificar_ids_catalogo.sql para comprobarlos sin modificar tablas.
Jugadores es texto; fechas de catálogo no incluyen zona horaria; numeric usa Decimal.

## Flujo del chat

Cada pregunta ejecuta SELECT * FROM public.peliculas y SELECT * FROM public.videojuegos.
Se envían todas las filas y columnas a OpenAI con la pregunta actual. El JSON compacto
escribe columnas una vez y luego filas con valores en ese mismo orden.
No hay filtros, límites, caché de catálogo, SQL generado por IA ni memoria conversacional.
No se envían tablas de usuarios ni credenciales como contexto.
Se libera la transacción de lectura antes de llamar a OpenAI.
Una conversación por pregunta; pregunta, respuesta y consumo se guardan juntos.
Errores, rechazo del modelo o respuestas truncadas no se guardan como consultas exitosas.
Se utiliza Chat Completions, JSON Schema estricto y store=false.

## Consumo del proyecto

Cada unidad separada por espacios equivale a una palabra/token académico.
Cuenta el contenido de instrucciones, catálogo, pregunta y JSON de respuesta.
No representa los tokens reales ni el costo de OpenAI.
La IA identifica el tema. El total se asigna a la categoría principal de la pregunta.
Para preguntas mixtas o ajenas al catálogo, se reparte entre ambas categorías;
una unidad sobrante corresponde a películas. Es una convención documentada.

## Verificación y límites

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

31 pruebas pasan con SQLite y servicios simulados. Falta verificar PostgreSQL y
OpenAI reales desde tu equipo. La disponibilidad y cuotas dependen del proyecto API.
Si el catálogo supera la cuota o el contexto, se informa el error; no se recorta el catálogo.
Si el guardado falla después de la respuesta, OpenAI puede haber consumido créditos
sin quedar un registro local exitoso. Cambiar contraseña no revoca otras sesiones aún.
Eliminar usuarios elimina su historial, consumo y sesiones por ON DELETE CASCADE.
Para publicar, añadir HTTPS y límites de intentos de acceso.

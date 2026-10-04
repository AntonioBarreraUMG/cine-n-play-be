# Backend: primera etapa

Python 3.11 o superior. FastAPI + SQLAlchemy 2 + psycopg 3 + PostgreSQL.

Implementado: configuración, estado de API/base, autenticación con sesiones revocables,
contraseñas Argon2, roles, CRUD de usuarios, SQL para las tablas propias y creación del primer administrador.
Pendiente: integración del catálogo existente, chat con IA, historial y consumo.
No crea ni modifica películas/videojuegos al iniciar. No se ha conectado a tu PostgreSQL.

## Preparación

Abre una terminal en esta carpeta:

```bash
python -m venv .venv
```

Windows PowerShell: `.venv\Scripts\Activate.ps1`
Windows CMD: `.venv\Scripts\activate.bat`
macOS/Linux: `source .venv/bin/activate`

```bash
python -m pip install -r requirements.txt
```

Copia `.env.example` a `.env`. Configura DATABASE_URL con tus datos localmente.
Si la contraseña contiene caracteres especiales, codifícalos para URL (ejemplo: @ como %40).
No compartas `.env` ni lo subas a Git. Usa un usuario PostgreSQL con permisos apropiados.

En pgAdmin abre Query Tool de tu base, revisa y ejecuta `sql/001_app.sql` una sola vez.
Si ya tienes usuarios/conversaciones/mensajes/consumo_tokens/sesiones, primero compara
los esquemas: el script falla y se revierte si encuentra una tabla existente.
Eliminar usuarios elimina también sus sesiones, historial y consumo por ON DELETE CASCADE.

```bash
python -m app.create_admin
python -m uvicorn app.main:app --reload
```

Documentación: http://127.0.0.1:8000/docs
Estado de PostgreSQL: http://127.0.0.1:8000/health/db

## Prueba manual

1. POST /auth/login con correo y password del administrador.
2. Copia access_token y úsalo en Authorize en /docs (solo el token).
3. GET /auth/me y POST /usuarios.
4. Inicia sesión como usuario normal: GET /usuarios debe devolver 403.
5. POST /auth/logout: ese token debe devolver 401 al volver a consultar /auth/me.

PUT /usuarios/{id} reemplaza nombre, correo, contraseña y rol; todos son obligatorios.
La contraseña nunca se devuelve. Sesiones expiran a los 60 minutos (configurable).
Cerrar sesión invalida la sesión actual; cambiar contraseña no revoca otras sesiones todavía.
No hay registro público. Para una publicación real, añadir HTTPS y límites de intentos de acceso.

## Verificación

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Las pruebas HTTP usan un repositorio simulado; no demuestran integración PostgreSQL.

## Siguiente etapa

Ejecuta `sql/inspeccionar_catalogo.sql` y comparte el resultado para mapear nombres,
esquemas y tipos reales. Elegir el proveedor de IA y configurar su clave localmente.

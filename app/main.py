import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from .auth import router as auth_router
from .users import router as users_router
from .config import get_settings
from .database import get_db

app = FastAPI(title="Chat de películas y videojuegos", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins,
                   allow_methods=["GET", "POST", "PUT", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])
app.include_router(auth_router)
app.include_router(users_router)

@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logging.getLogger(__name__).error("Fallo de operación en base de datos: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Base de datos no disponible o esquema incompatible"})

@app.get("/health", tags=["Estado"])
def health():
    return {"status": "ok"}

@app.get("/health/db", tags=["Estado"])
def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "ok"}

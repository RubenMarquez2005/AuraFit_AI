"""Punto de entrada del backend FastAPI de AuraFit AI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.db import engine, verify_database_connection, Base
from app.models import Rol, Usuario, PerfilSalud, RegistroDiario
from app.api.auth import router as auth_router
import logging

# Configuracion basica de logs para desarrollo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Se importan los modelos para que SQLAlchemy registre su metadata en arranque.
_ = (Rol, Usuario, PerfilSalud, RegistroDiario)

# Inicializa la aplicacion FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API backend de AuraFit AI",
)

# Permite comunicacion con el frontend durante desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar por dominios concretos en produccion.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Eventos de ciclo de vida

@app.on_event("startup")
async def startup_event():
    """Inicializa tablas y valida conexion con la base de datos."""
    logger.info("=" * 60)
    logger.info("Iniciando backend de AuraFit AI")
    logger.info("=" * 60)

    try:
        # Crea las tablas definidas en los modelos si no existen.
        logger.info("Creando o validando tablas")
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas listas")
    except Exception as e:
        logger.error("Error al crear tablas: %s", str(e))
        raise

    # Comprueba conectividad real con MySQL.
    logger.info("Comprobando conexion a base de datos")
    is_connected = await verify_database_connection()

    if is_connected:
        logger.info("Conexion a base de datos correcta")
        logger.info("=" * 60)
        logger.info("Backend listo")
        logger.info("Documentacion disponible en /docs")
        logger.info("=" * 60)
    else:
        logger.error("No se pudo conectar con la base de datos")
        raise RuntimeError("Fallo de conexion con la base de datos en el arranque")


@app.on_event("shutdown")
async def shutdown_event():
    """Evento de cierre de la aplicacion."""
    logger.info("Cerrando backend de AuraFit AI")


# Endpoints de salud

app.include_router(auth_router)

@app.get("/")
async def root():
    """Endpoint raiz con informacion basica del servicio."""
    return {
        "message": f"Bienvenido a la API de {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health_check": "/health",
    }


@app.get("/health")
async def health_check():
    """Comprueba el estado general de la API."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health/db")
async def health_check_db():
    """Comprueba si la conexion con la base de datos esta operativa."""
    is_connected = await verify_database_connection()
    return {
        "status": "healthy" if is_connected else "unhealthy",
        "database": "connected" if is_connected else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )

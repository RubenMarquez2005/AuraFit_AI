"""Conexion y gestion de sesiones de base de datos."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Crea el motor con pool de conexiones para mejorar rendimiento.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Muestra SQL en consola si DEBUG=True.
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verifica la conexion antes de usarla.
)

# Fabrica de sesiones.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para todos los modelos ORM.
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI para inyectar una sesion de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def verify_database_connection() -> bool:
    """Comprueba conectividad con MySQL mediante una consulta simple."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("Conexion con la base de datos verificada")
        return True
    except Exception as e:
        logger.error("Error de conexion con la base de datos: %s", str(e))
        return False

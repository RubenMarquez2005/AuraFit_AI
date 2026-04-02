"""Punto de entrada del backend FastAPI de AuraFit AI."""

from datetime import time, datetime
from typing import Any, Dict, List, Optional
import re
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.db import Base, engine, get_db, verify_database_connection
from app.models import Rol, Usuario, PerfilSalud, RegistroDiario
from app.api.auth import router as auth_router
from app.services.auth_service import obtener_usuario_por_token
from services.gemini_service import consultar_ia
from services.rasa_service import enviar_mensaje_a_rasa
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


class ChatTestRequest(BaseModel):
    """Payload de prueba para consultar Gemini."""

    mensaje: str = Field(..., min_length=1, description="Mensaje del usuario")
    historial_chat: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Historial conversacional opcional",
    )


class PerfilCompletarRequest(BaseModel):
    """Datos antropometricos y de habitos para completar perfil de salud."""

    peso: float = Field(..., gt=0, le=400, description="Peso en kg")
    altura: int = Field(..., gt=0, le=250, description="Altura en cm")
    frecuencia_gym: str = Field(..., description="sedentario, 1-3 dias o +4 dias")
    hora_desayuno: time
    hora_comida: time
    hora_cena: time
    momento_picoteo: str = Field(..., description="manana, tarde o noche")
    percepcion_corporal: str = Field(..., min_length=1, description="Texto libre del usuario")

    @field_validator("frecuencia_gym")
    @classmethod
    def validar_frecuencia_gym(cls, value: str) -> str:
        """Normaliza y valida la frecuencia de entrenamiento."""
        frecuencia = value.strip().lower()
        equivalencias = {
            "sedentario": "sedentario",
            "1-3 dias": "1-3 dias",
            "1-3 días": "1-3 dias",
            "+4 dias": "+4 dias",
            "+4 días": "+4 dias",
            "4+ dias": "+4 dias",
            "4+ días": "+4 dias",
        }
        if frecuencia not in equivalencias:
            raise ValueError("frecuencia_gym debe ser: sedentario, 1-3 dias o +4 dias")
        return equivalencias[frecuencia]

    @field_validator("momento_picoteo")
    @classmethod
    def validar_momento_picoteo(cls, value: str) -> str:
        """Normaliza y valida el momento critico de picoteo."""
        momento = value.strip().lower()
        equivalencias = {
            "manana": "manana",
            "mañana": "manana",
            "tarde": "tarde",
            "noche": "noche",
        }
        if momento not in equivalencias:
            raise ValueError("momento_picoteo debe ser: manana, tarde o noche")
        return equivalencias[momento]


class PerfilCompletarResponse(BaseModel):
    """Respuesta de guardado de perfil antropometrico."""

    usuario_id: int
    imc_calculado: float
    mensaje: str


class RasaChatRequest(BaseModel):
    """Payload de mensaje para el webhook REST de RASA."""

    mensaje: str = Field(..., min_length=1, description="Texto del usuario")
    sender: str = Field(default="aurafit_user", min_length=1)


class RasaChatResponse(BaseModel):
    """Respuesta unificada del puente FastAPI hacia RASA."""

    ok: bool
    sender: str
    respuestas: List[Dict[str, Any]]


class ChatRequest(BaseModel):
    """Payload de mensaje de usuario para el endpoint POST /chat."""

    mensaje: str = Field(..., min_length=1, description="Mensaje del usuario")
    sender: str = Field(default="aurafit_user", min_length=1, description="ID único del usuario")


class ChatResponse(BaseModel):
    """Respuesta del endpoint POST /chat."""

    ok: bool
    sender: str
    respuesta_ia: str
    peso_registrado: Optional[float] = None
    mensaje_peso: Optional[str] = None


def _extraer_peso_del_mensaje(mensaje: str) -> Optional[float]:
    """
    Intenta extraer un peso en kg del mensaje del usuario.
    Busca patrones como: "80kg", "80 kg", "He pesado 80", "Mi peso es 80", etc.
    """
    # Busca números seguidos de 'kg' o 'kilos'
    patrones = [
        r"(\d+(?:[.,]\d+)?)\s*kg",  # Ej: 80kg, 80 kg, 80.5 kg
        r"pesé?\s+(\d+(?:[.,]\d+)?)",  # Ej: pesé 80, peso 80
        r"peso\s+(?:de\s+)?(\d+(?:[.,]\d+)?)",  # Ej: peso de 80
        r"pesan?\s+(\d+(?:[.,]\d+)?)",  # Ej: pesa 80
    ]
    
    for patron in patrones:
        match = re.search(patron, mensaje, re.IGNORECASE)
        if match:
            try:
                peso_str = match.group(1).replace(",", ".")
                peso = float(peso_str)
                if 30 <= peso <= 400:  # Validación de rango razonable
                    return peso
            except ValueError:
                continue
    
    return None


def _contiene_consejo_salud(respuesta: str) -> bool:
    """
    Detecta si una respuesta de RASA contiene consejos de salud.
    Busca palabras clave asociadas con nutrition, gym, salud mental.
    """
    palabras_clave = [
        "come", "comida", "nutrición", "desayuno", "almuerzo", "cena",
        "agua", "proteína", "carbohidrato", "grasa", "calorías",
        "ejercicio", "gym", "entrenamiento", "correr", "caminar",
        "estrés", "ansiedad", "ánimo", "meditación", "relajación",
        "salud", "bienestar", "recomiendo", "sugiero", "deberías"
    ]
    respuesta_lower = respuesta.lower()
    return any(palabra in respuesta_lower for palabra in palabras_clave)


class RasaChatResponse(BaseModel):
    """Respuesta unificada del puente FastAPI hacia RASA."""

    ok: bool
    sender: str
    respuestas: List[Dict[str, Any]]


def _extraer_token_bearer(authorization: Optional[str]) -> str:
    """Extrae token desde cabecera Authorization en formato Bearer."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado",
        )

    esquema, _, token = authorization.partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token invalido. Usa: Bearer <token>",
        )

    return token


def obtener_usuario_actual(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> Usuario:
    """Resuelve el usuario autenticado a partir del Bearer token."""
    token = _extraer_token_bearer(authorization)
    usuario = obtener_usuario_por_token(db, token)

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
        )

    return usuario


@app.post("/chat/test")
async def chat_test(payload: ChatTestRequest):
    """Prueba de conexion con Gemini para validar API Key y respuesta de IA."""
    try:
        resultado = consultar_ia(
            mensaje_usuario=payload.mensaje,
            historial_chat=payload.historial_chat,
        )
    except RuntimeError as e:
        # Normalmente indica API key ausente o configuracion incompleta.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Error al consultar Gemini en /chat/test")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error al consultar el servicio de IA",
        ) from e

    return {
        "ok": True,
        "entrada": payload.mensaje,
        **resultado,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Endpoint principal de chat que integra RASA con registro en BD.
    
    1. Envía el mensaje a RASA
    2. Extrae peso si está en el mensaje
    3. Guarda respuestas de salud en registros_diarios
    4. Actualiza perfil de salud si se detectó peso
    """
    try:
        # Enviar mensaje a RASA
        respuestas_rasa = enviar_mensaje_a_rasa(
            sender=payload.sender.strip(),
            mensaje=payload.mensaje.strip(),
        )
        
        # Construir respuesta del IA (concatenar respuestas de RASA)
        respuesta_ia = " ".join([
            resp.get("text", "") for resp in respuestas_rasa if isinstance(resp, dict)
        ]) or "He recibido tu mensaje. ¿Cómo puedo ayudarte?"
        
    except Exception as e:
        logger.exception("Error al consultar RASA en /chat")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo obtener respuesta desde RASA",
        ) from e
    
    peso_registrado = None
    mensaje_peso = None
    
    try:
        # Intentar extraer peso del mensaje
        peso = _extraer_peso_del_mensaje(payload.mensaje)
        
        if peso:
            peso_registrado = peso
            mensaje_peso = f"Peso registrado: {peso}kg"
            logger.info(f"Peso extraído del mensaje: {peso}kg")
            
            # TODO: Buscar usuario por sender_id en registros si es un usuario autenticado
            # Por ahora solo registramos el peso en el contexto de la respuesta
        
        # Guardar respuesta de salud en registros_diarios si aplica
        if _contiene_consejo_salud(respuesta_ia):
            # TODO: Asociar con usuario_id cuando tengamos autenticación
            # Por ahora solo lo registramos en logs
            logger.info(f"Respuesta de salud detectada: {respuesta_ia[:100]}...")
    
    except Exception as e:
        logger.exception("Error procesando información del mensaje")
        # No lanzamos error, continuamos con la respuesta
    
    return ChatResponse(
        ok=True,
        sender=payload.sender.strip(),
        respuesta_ia=respuesta_ia,
        peso_registrado=peso_registrado,
        mensaje_peso=mensaje_peso,
    )


@app.post("/chat/rasa", response_model=RasaChatResponse)
def chat_rasa(payload: RasaChatRequest) -> RasaChatResponse:
    """Envia un mensaje a RASA (puerto 5005) y devuelve su respuesta REST."""
    try:
        respuestas = enviar_mensaje_a_rasa(
            sender=payload.sender.strip(),
            mensaje=payload.mensaje.strip(),
        )
    except Exception as e:
        logger.exception("Error al consultar RASA")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo obtener respuesta desde RASA",
        ) from e

    return RasaChatResponse(
        ok=True,
        sender=payload.sender.strip(),
        respuestas=respuestas,
    )


@app.post("/perfil/completar", response_model=PerfilCompletarResponse)
def completar_perfil(
    payload: PerfilCompletarRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PerfilCompletarResponse:
    """Crea o actualiza el perfil antropometrico del usuario autenticado."""
    altura_m = payload.altura / 100
    imc = round(payload.peso / (altura_m * altura_m), 2)

    try:
        perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario_actual.id).first()
        perfil_existia = perfil is not None

        if not perfil:
            perfil = PerfilSalud(usuario_id=usuario_actual.id)
            db.add(perfil)

        perfil.peso_actual = payload.peso
        perfil.altura = payload.altura
        perfil.imc_actual = imc
        perfil.frecuencia_gym = payload.frecuencia_gym
        perfil.hora_desayuno = payload.hora_desayuno
        perfil.hora_comida = payload.hora_comida
        perfil.hora_cena = payload.hora_cena
        perfil.momento_critico_picoteo = payload.momento_picoteo
        perfil.percepcion_corporal = payload.percepcion_corporal.strip()

        db.commit()
        db.refresh(perfil)
    except Exception as e:
        db.rollback()
        logger.exception("Error guardando perfil antropometrico")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el perfil de salud",
        ) from e

    mensaje = (
        "Perfil antropometrico actualizado correctamente"
        if perfil_existia
        else "Perfil antropometrico creado correctamente"
    )

    return PerfilCompletarResponse(
        usuario_id=usuario_actual.id,
        imc_calculado=float(imc),
        mensaje=mensaje,
    )

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

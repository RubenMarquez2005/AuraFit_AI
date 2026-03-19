"""Servicio de IA con Gemini para AuraFit AI."""

from __future__ import annotations

import os
import unicodedata
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config.settings import settings

SYSTEM_PROMPT = (
    "Eres un experto en nutrición y psicología positiva. "
    "Tu objetivo es ayudar, pero si detectas riesgo de trastornos alimenticios "
    "o ansiedad grave, debes sugerir ayuda profesional"
)

PALABRAS_RIESGO = (
    "no comer",
    "atracon",
    "vomito",
    "odio mi cuerpo",
)

ETIQUETA_ALERTA_RIESGO = "ALERTA_RIESGO_TCA_ANSIEDAD"


def _normalizar_texto(texto: str) -> str:
    """Pasa texto a minusculas y sin acentos para detectar riesgos con consistencia."""
    texto_min = texto.lower().strip()
    texto_sin_acentos = "".join(
        ch for ch in unicodedata.normalize("NFKD", texto_min) if not unicodedata.combining(ch)
    )
    return " ".join(texto_sin_acentos.split())


def _extraer_texto_historial(item: Dict[str, Any]) -> str:
    """Obtiene texto de una entrada del historial con varias claves compatibles."""
    texto = item.get("mensaje") or item.get("content") or item.get("texto") or ""
    return texto if isinstance(texto, str) else ""


def _mapear_rol(rol: str) -> str:
    """Convierte roles genericos a los roles esperados por Gemini."""
    rol_norm = rol.strip().lower()
    if rol_norm in {"assistant", "asistente", "model"}:
        return "model"
    return "user"


def _preparar_partes_imagenes(imagenes: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Prepara partes multimodales para futuro envio de fotos a Gemini."""
    partes: List[Dict[str, Any]] = []

    for imagen in imagenes or []:
        if not isinstance(imagen, dict):
            continue

        data = imagen.get("data")
        mime_type = imagen.get("mime_type", "image/jpeg")

        # Formato esperado para Gemini: {"mime_type": "image/jpeg", "data": bytes}
        if data:
            partes.append({"mime_type": mime_type, "data": data})

    return partes


def detectar_alerta_riesgo(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Detecta palabras de riesgo en mensaje actual e historial de conversacion."""
    textos = [mensaje_usuario]
    for item in historial_chat or []:
        if isinstance(item, dict):
            textos.append(_extraer_texto_historial(item))

    texto_total = _normalizar_texto(" ".join(textos))
    return any(palabra in texto_total for palabra in PALABRAS_RIESGO)


def _obtener_api_key() -> str:
    """Prioriza Settings y fallback a variable de entorno directa."""
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("No se encontro GEMINI_API_KEY en el entorno")
    return api_key


def _es_error_cuota_o_modelo(error: Exception) -> bool:
    """Detecta errores de cuota o de modelo no disponible para activar fallback local."""
    texto = str(error).lower()
    return (
        "quota" in texto
        or "resourceexhausted" in texto
        or "429" in texto
        or "not found" in texto
        or "not supported" in texto
    )


def _respuesta_local_gratis(mensaje_usuario: str, alerta_riesgo: bool) -> str:
    """Genera una respuesta local sin coste para no bloquear el flujo del usuario."""
    if alerta_riesgo:
        return (
            "Gracias por compartirlo. Lo que expresas puede indicar malestar importante. "
            "Te recomiendo buscar apoyo profesional (psicologo/a o medico/a) cuanto antes. "
            "Mientras tanto, podemos trabajar con pasos pequenos: respiracion 4-4-4, "
            "comidas regulares y registrar como te sientes hoy en una escala del 1 al 10."
        )

    return (
        "Hola. Para empezar hoy, te propongo una accion simple y realista: "
        "toma agua, define una comida equilibrada para la siguiente hora "
        "y escribe un objetivo pequeno de autocuidado para el dia."
    )


def _construir_contenido(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]],
    imagenes: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Construye contenido conversacional compatible con Gemini."""
    contenido: List[Dict[str, Any]] = []

    for item in historial_chat or []:
        if not isinstance(item, dict):
            continue

        rol = item.get("rol") or item.get("role") or "user"
        texto = _extraer_texto_historial(item)
        if not texto:
            continue

        contenido.append({"role": _mapear_rol(str(rol)), "parts": [texto]})

    partes_mensaje: List[Any] = [mensaje_usuario]
    partes_mensaje.extend(_preparar_partes_imagenes(imagenes))
    contenido.append({"role": "user", "parts": partes_mensaje})

    return contenido


def consultar_ia(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
    imagenes: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Consulta Gemini con contexto conversacional y deteccion de alerta de riesgo."""
    if not mensaje_usuario or not mensaje_usuario.strip():
        raise ValueError("mensaje_usuario no puede estar vacio")

    alerta_riesgo = detectar_alerta_riesgo(mensaje_usuario, historial_chat)
    etiqueta_alerta = ETIQUETA_ALERTA_RIESGO if alerta_riesgo else None

    contenido = _construir_contenido(mensaje_usuario, historial_chat, imagenes)

    try:
        api_key = _obtener_api_key()
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
        )

        respuesta = model.generate_content(contenido)
        texto_respuesta = (getattr(respuesta, "text", "") or "").strip()

        if not texto_respuesta:
            texto_respuesta = "No he podido generar una respuesta en este momento."

        return {
            "respuesta": texto_respuesta,
            "etiqueta_alerta": etiqueta_alerta,
            "alerta_riesgo": alerta_riesgo,
            "modelo": settings.GEMINI_MODEL,
            "origen": "gemini",
        }
    except Exception as e:
        if not settings.IA_FALLBACK_LOCAL and not _es_error_cuota_o_modelo(e):
            raise

        return {
            "respuesta": _respuesta_local_gratis(mensaje_usuario, alerta_riesgo),
            "etiqueta_alerta": etiqueta_alerta,
            "alerta_riesgo": alerta_riesgo,
            "modelo": "fallback_local",
            "origen": "fallback_local",
            "motivo_fallback": e.__class__.__name__,
        }

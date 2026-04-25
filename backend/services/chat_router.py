"""Reglas simples para decidir si conviene usar RASA o la IA generativa."""

from __future__ import annotations

from typing import Optional
import unicodedata


INTENTOS_RASA_PRIORITARIOS = {
    "saludar",
    "despedir",
    "informar_peso",
    "informar_altura",
    "calular_imc",
    "estado_animo_malo",
    "estado_animo_bueno",
    "pedir_motivacion",
    "pedir_plan_nutricion",
    "preguntar_alimentos",
    "registrar_comida",
    "pedir_plan_ejercicio",
    "preguntar_tecnica_ejercicio",
    "registrar_ejercicio",
    "pedir_meditacion",
    "hablar_sueno",
    "pedir_consejo_general",
    "buscar_profesional",
    "solicitar_cita",
    "informacion_app",
    "ayuda_general",
    "charla_casual",
    "agradecimiento",
    "problema_nutricional",
    "falta_apetito",
    "objetivo_subir_peso",
    "objetivo_bajar_peso",
    "pedir_entrenador_personal",
    "plan_nutricion_entrenamiento",
    "profesional_nutricion_adherencia",
    "profesional_psicologia_riesgo",
    "profesional_coach_adherencia",
    "profesional_medico_farmacoterapia",
    "profesional_medicacion_consulta",
    "profesional_interaccion_farmacos",
    "profesional_recursos_trastornos",
    "profesional_escalado_clinico",
    "profesional_coordinacion_caso",
    "profesional_plan_multidisciplinar",
    "profesional_calorias_objetivo",
    "profesional_ajuste_macros",
    "profesional_gym_calorias",
    "profesional_dieta_prescrita",
}

PALABRAS_RIESGO = (
    "suicid",
    "autoles",
    "me quiero morir",
    "no quiero vivir",
    "dolor torac",
    "desmayo",
    "sangrado",
    "purga",
    "vomit",
    "crisis de panico",
)


def _normalizar_texto(texto: str) -> str:
    """Normaliza texto para comparaciones simples."""
    texto = texto or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().split())


def debe_priorizar_rasa(
    mensaje: str,
    area_detectada: Optional[str] = None,
    tiene_multimedia: bool = False,
    es_solicitud_experta: bool = False,
) -> bool:
    """Decide si merece la pena intentar RASA antes que la IA generativa."""
    texto = _normalizar_texto(mensaje)
    if not texto:
        return False
    if tiene_multimedia or es_solicitud_experta:
        return False
    if any(clave in texto for clave in PALABRAS_RIESGO):
        return False
    if len(texto) > 700:
        return False

    if area_detectada in {"nutricion", "entrenamiento", "salud_mental"}:
        return True

    if any(
        clave in texto
        for clave in (
            "hola",
            "buenas",
            "gracias",
            "ayuda",
            "peso",
            "altura",
            "imc",
            "dieta",
            "comida",
            "alimento",
            "entren",
            "ejercicio",
            "ansiedad",
            "animo",
            "sueno",
            "cita",
            "profesional",
        )
    ):
        return True

    return False


def es_intento_rasa_confiable(intent_name: str, confidence: float, umbral: float = 0.65) -> bool:
    """Valida si un intent de RASA tiene suficiente confianza para usarse."""
    if not intent_name:
        return False
    if confidence < umbral:
        return False
    return intent_name in INTENTOS_RASA_PRIORITARIOS

"""Punto de entrada del backend FastAPI de AuraFit AI."""

from datetime import time, datetime, timedelta
import base64
from io import BytesIO
import importlib
from typing import Any, Dict, List, Optional
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import inspect, text
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.db import Base, engine, get_db, verify_database_connection
from app.models import (
    Rol,
    Usuario,
    PerfilSalud,
    RegistroDiario,
    Derivacion,
    CitaDisponible,
    CitaReservada,
    HabitoAgenda,
    EvaluacionIA,
    MensajeChat,
    MemoriaChat,
    MedicacionAsignada,
    PlanNutricionalClinico,
    ProtocoloHospitalario,
    ChecklistClinicoPaciente,
    ChecklistClinicoHistorial,
    RecursoClinico,
    PlanIA,
)
from app.api.auth import router as auth_router
from app.services.auth_service import obtener_usuario_por_token, generar_hash_contrasena
from services.chat_router import debe_priorizar_rasa, es_intento_rasa_confiable
from services.gemini_service import consultar_ia, obtener_respuesta_local_segura, _detectar_duracion_plan
from services.media_generation_service import generar_imagen_premium, generar_video_premium
from services.rasa_service import analizar_mensaje_con_rasa, enviar_mensaje_a_rasa
import logging
from fpdf import FPDF

ROLES_BASE = ["administrador", "cliente", "nutricionista", "psicologo", "coach", "medico"]
ROLES_PROFESIONALES = {"administrador", "nutricionista", "psicologo", "coach", "medico"}
USUARIOS_PROFESIONALES_DEMO = [
    {"nombre": "Médico AuraFit", "email": "medico@aurafit.app", "rol": "medico"},
]
PASSWORD_DEMO_PROFESIONALES = "AuraFit123!"
USUARIOS_CLIENTES_DEMO = [
    {
        "nombre": "Paciente Demo 1",
        "email": "cliente1@aurafit.app",
        "peso": 72.0,
        "altura": 176,
        "animo": 6,
        "sentimiento": "neutral",
    },
    {
        "nombre": "Paciente Demo 2",
        "email": "cliente2@aurafit.app",
        "peso": 81.5,
        "altura": 170,
        "animo": 4,
        "sentimiento": "ansiedad",
    },
]
PASSWORD_DEMO_CLIENTES = "AuraFit123!"
HABITOS_BASE = [
    {"titulo": "Comida 1", "subtitulo": "Primera ingesta del día", "franja": "Mañana", "color_hex": "#4F46E5", "orden": 0},
    {"titulo": "Comida 2", "subtitulo": "Segunda ingesta con proteína", "franja": "Mañana", "color_hex": "#6366F1", "orden": 1},
    {"titulo": "Comida 3", "subtitulo": "Comida principal equilibrada", "franja": "Mediodía", "color_hex": "#8B5CF6", "orden": 2},
    {"titulo": "Comida 4", "subtitulo": "Merienda o snack planificado", "franja": "Tarde", "color_hex": "#A855F7", "orden": 3},
    {"titulo": "Comida 5", "subtitulo": "Cena ligera y saciante", "franja": "Noche", "color_hex": "#C084FC", "orden": 4},
    {"titulo": "Movimiento 20 min", "subtitulo": "Caminar o entrenar según energía", "franja": "Tarde", "color_hex": "#16A34A", "orden": 5},
    {"titulo": "Check-in emocional", "subtitulo": "Registrar ánimo, energía y estrés", "franja": "Noche", "color_hex": "#0EA5E9", "orden": 6},
    {"titulo": "Respiración 4-6", "subtitulo": "Regular eje HPA y reducir reactividad", "franja": "Noche", "color_hex": "#0891B2", "orden": 7},
    {"titulo": "Fuerza técnica", "subtitulo": "Bloque corto de 2-3 ejercicios sin impacto", "franja": "Tarde", "color_hex": "#15803D", "orden": 8},
    {"titulo": "Hidratación estructurada", "subtitulo": "2-2.5L agua con control de sodio diario", "franja": "Mañana", "color_hex": "#7C3AED", "orden": 9},
]
TRASTORNOS_CLINICOS = {
    "tca",
    "ansiedad",
    "depresion",
    "sop",
    "diabetes",
    "dolor_lumbar",
    "dolor_rodilla",
    "insomnio",
    "trastorno_alimentario",
    "celiaquia",
    "alergia_alimentaria",
    "sindrome_intestino_irritable",
    "fibromialgia",
}
SEVERIDADES_CLINICAS = {"leve", "moderado", "severo"}
OBJETIVOS_NUTRICIONALES = {
    "perdida_grasa",
    "mantenimiento",
    "ganancia_muscular",
    "recomposicion",
    "recuperacion_clinica",
}
RIESGOS_METABOLICOS = {"bajo", "medio", "alto"}
PROTOCOLS_BASE = [
    {
        "trastorno": "tca",
        "severidad": "leve",
        "especialidad": "nutricionista",
        "titulo": "TCA leve: estabilizacion nutricional inicial",
        "checklist": [
            "Validar patrón de ingestas mínimo de 3 comidas/día",
            "Descartar conductas compensatorias activas",
            "Pactar objetivo nutricional semanal realista",
        ],
        "ruta_escalado": "Si aparece restricción severa, purga o pérdida ponderal rápida, derivar a psicología clínica en 24h y valorar medicina.",
    },
    {
        "trastorno": "ansiedad",
        "severidad": "moderado",
        "especialidad": "psicologo",
        "titulo": "Ansiedad moderada: intervención psicológica estructurada",
        "checklist": [
            "Aplicar respiración diafragmática y reestructuración cognitiva",
            "Evaluar impacto funcional en sueño/comida/gym",
            "Planificar seguimiento semanal con métricas de activación",
        ],
        "ruta_escalado": "Escalar a medicina si hay insomnio refractario, ataques de pánico frecuentes o deterioro funcional marcado.",
    },
    {
        "trastorno": "depresion",
        "severidad": "severo",
        "especialidad": "medico",
        "titulo": "Depresión severa: protocolo de seguridad y coordinación",
        "checklist": [
            "Valorar riesgo suicida y red de apoyo inmediata",
            "Revisión farmacológica y adherencia",
            "Coordinar intervención conjunta medicina-psicología",
        ],
        "ruta_escalado": "Si hay riesgo autolítico activo, derivación urgente a dispositivo de crisis y notificación de circuito hospitalario.",
    },
    {
        "trastorno": "sop",
        "severidad": "leve",
        "especialidad": "nutricionista",
        "titulo": "SOP leve: control metabólico y adherencia alimentaria",
        "checklist": [
            "Evaluar patrón de hambre/saciedad y carga de carbohidratos",
            "Priorizar proteína y fibra en cada comida",
            "Coordinar actividad física progresiva y seguimiento del sueño",
        ],
        "ruta_escalado": "Si hay resistencia a la insulina marcada, ciclos muy irregulares o deterioro emocional, coordinar con medicina y psicología.",
    },
    {
        "trastorno": "diabetes",
        "severidad": "moderado",
        "especialidad": "medico",
        "titulo": "Diabetes moderada: control clínico y coordinación del equipo",
        "checklist": [
            "Revisar adherencia a medicación y autocontrol glucémico",
            "Valorar dieta, horarios y educación en hipoglucemia",
            "Coordinar con nutrición para ajuste de carbohidratos",
        ],
        "ruta_escalado": "Si hay hipoglucemias repetidas, síntomas agudos o descompensación, activar valoración médica prioritaria.",
    },
    {
        "trastorno": "dolor_lumbar",
        "severidad": "moderado",
        "especialidad": "coach",
        "titulo": "Dolor lumbar: ejercicio seguro y progresión de tolerancia",
        "checklist": [
            "Evitar rangos dolorosos agudos y cargas máximas",
            "Usar movilidad, core y bisagra de cadera progresiva",
            "Si el dolor irradia o empeora, derivar a medicina",
        ],
        "ruta_escalado": "Si el dolor persiste, se acompaña de debilidad o signos neurológicos, derivación médica inmediata.",
    },
    {
        "trastorno": "dolor_rodilla",
        "severidad": "moderado",
        "especialidad": "coach",
        "titulo": "Dolor de rodilla: rutina adaptada y control de impacto",
        "checklist": [
            "Reducir impacto y movimientos irritativos",
            "Priorizar cuádriceps, glúteo medio y control de apoyo",
            "Revisar dolor durante y 24h después del entrenamiento",
        ],
        "ruta_escalado": "Si hay bloqueo, inflamación importante o inestabilidad, derivar a medicina/traumatología.",
    },
    {
        "trastorno": "insomnio",
        "severidad": "leve",
        "especialidad": "psicologo",
        "titulo": "Insomnio leve: higiene del sueño y regulación",
        "checklist": [
            "Horario regular y reducción de pantallas nocturnas",
            "Rutina de descarga mental antes de dormir",
            "Controlar cafeína, siestas y activación nocturna",
        ],
        "ruta_escalado": "Si el insomnio es persistente o grave, valorar medicina y revisión de comorbilidades.",
    },
    {
        "trastorno": "trastorno_alimentario",
        "severidad": "moderado",
        "especialidad": "psicologo",
        "titulo": "TCA moderado: estabilización, seguridad y derivación",
        "checklist": [
            "Eliminar ayunos extremos y restricciones rígidas",
            "Registrar disparadores, culpa y conductas compensatorias",
            "Coordinar con nutrición y medicina según gravedad",
        ],
        "ruta_escalado": "Si hay purga, desmayo, pérdida rápida de peso o ideación autolesiva, activar derivación urgente.",
    },
]
CLINICAL_RESOURCES_BASE = [
    # TCA
    {"trastorno": "tca", "especialidad": "nutricionista", "titulo": "Guia de realimentacion gradual", "descripcion": "Progresion por fases para recuperar regularidad alimentaria y estabilidad digestiva.", "url": "", "nivel_evidencia": "consenso_clinico"},
    {"trastorno": "tca", "especialidad": "psicologo", "titulo": "Manejo de culpa alimentaria", "descripcion": "Intervencion cognitivo-conductual breve para reducir culpa, miedo a comer y rituales.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "tca", "especialidad": "medico", "titulo": "Vigilancia medica en TCA", "descripcion": "Screening de signos de alarma, alteraciones hemodinamicas y criterios de derivacion urgente.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "tca", "especialidad": "coach", "titulo": "Actividad fisica segura en recuperacion TCA", "descripcion": "Criterios para dosificar ejercicio sin reforzar conductas compensatorias.", "url": "", "nivel_evidencia": "moderado"},

    # ANSIEDAD
    {"trastorno": "ansiedad", "especialidad": "psicologo", "titulo": "Protocolo de regulacion autonoma", "descripcion": "Respiracion, grounding y exposicion interoceptiva graduada para ansiedad diaria.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "ansiedad", "especialidad": "medico", "titulo": "Evaluacion clinica en ansiedad compleja", "descripcion": "Diferencial medico, comorbilidades y criterios de tratamiento combinado.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "ansiedad", "especialidad": "nutricionista", "titulo": "Nutricion para ansiedad", "descripcion": "Distribucion de energia y cafeina para reducir picos de activacion y fatiga reactiva.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "ansiedad", "especialidad": "coach", "titulo": "Dosificacion de entrenamiento en ansiedad", "descripcion": "Ajuste de intensidad, volumen y recuperacion para evitar sobrecarga del sistema nervioso.", "url": "", "nivel_evidencia": "moderado"},

    # DEPRESION
    {"trastorno": "depresion", "especialidad": "psicologo", "titulo": "Activacion conductual estructurada", "descripcion": "Plan semanal de microacciones para recuperar energia, rutina y sentido de eficacia.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "depresion", "especialidad": "medico", "titulo": "Ruta de vigilancia clinica en depresion", "descripcion": "Seguimiento de riesgo, respuesta terapeutica y coordinacion multidisciplinar.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "depresion", "especialidad": "nutricionista", "titulo": "Patron alimentario en depresion", "descripcion": "Estrategia para mejorar adherencia de comidas, apetito y densidad nutricional.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "depresion", "especialidad": "coach", "titulo": "Entrenamiento de baja barrera en depresion", "descripcion": "Protocolo de inicio minimo viable para mejorar energia y constancia.", "url": "", "nivel_evidencia": "moderado"},

    # SOP
    {"trastorno": "sop", "especialidad": "nutricionista", "titulo": "Manejo nutricional del SOP", "descripcion": "Proteina, fibra y carbohidratos estrategicos para resistencia a insulina y saciedad.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "sop", "especialidad": "medico", "titulo": "SOP y riesgo cardiometabolico", "descripcion": "Control clinico de ciclo, metabolica y comorbilidades asociadas.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "sop", "especialidad": "psicologo", "titulo": "Intervencion emocional en SOP", "descripcion": "Manejo de imagen corporal, ansiedad y adherencia conductual sostenida.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "sop", "especialidad": "coach", "titulo": "Fuerza y condicionamiento en SOP", "descripcion": "Programacion orientada a sensibilidad insulinica y composicion corporal.", "url": "", "nivel_evidencia": "moderado"},

    # DIABETES
    {"trastorno": "diabetes", "especialidad": "medico", "titulo": "Revision terapeutica en diabetes", "descripcion": "Control glucemico, ajustes farmacologicos y prevencion de hipoglucemias.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "diabetes", "especialidad": "nutricionista", "titulo": "Plan por raciones y glucemia", "descripcion": "Estructura de comidas por raciones, horarios y respuesta glucemica individual.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "diabetes", "especialidad": "psicologo", "titulo": "Adherencia psicologica en diabetes", "descripcion": "Herramientas para reducir abandono, fatiga de enfermedad y desregulacion emocional.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "diabetes", "especialidad": "coach", "titulo": "Ejercicio seguro en diabetes", "descripcion": "Protocolos de actividad segun glucemia pre, durante y post entrenamiento.", "url": "", "nivel_evidencia": "moderado"},

    # DOLOR LUMBAR
    {"trastorno": "dolor_lumbar", "especialidad": "coach", "titulo": "Ejercicio seguro en dolor lumbar", "descripcion": "Progresion por tolerancia del dolor, trabajo de core y bisagra de cadera.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "dolor_lumbar", "especialidad": "medico", "titulo": "Banderas rojas en dolor lumbar", "descripcion": "Criterios de derivacion prioritaria por deficit neurologico o dolor no mecanico.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "dolor_lumbar", "especialidad": "psicologo", "titulo": "Dolor cronico y evitacion", "descripcion": "Intervencion para catastrofismo, miedo al movimiento y adherencia funcional.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "dolor_lumbar", "especialidad": "nutricionista", "titulo": "Nutricion antiinflamatoria en dolor lumbar", "descripcion": "Guia de alimentos y habitos para modular inflamacion y apoyar recuperacion.", "url": "", "nivel_evidencia": "moderado"},

    # DOLOR RODILLA
    {"trastorno": "dolor_rodilla", "especialidad": "coach", "titulo": "Adaptacion de entrenamiento en dolor de rodilla", "descripcion": "Control de impacto, rango y fuerza de gluteo/cuadriceps por fases.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "dolor_rodilla", "especialidad": "medico", "titulo": "Evaluacion clinica de dolor de rodilla", "descripcion": "Diferencial de lesiones intraarticulares, meniscales y criterios de imagen.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "dolor_rodilla", "especialidad": "psicologo", "titulo": "Manejo de miedo al movimiento", "descripcion": "Intervencion breve para reducir evitacion y mejorar adherencia al plan.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "dolor_rodilla", "especialidad": "nutricionista", "titulo": "Apoyo nutricional en dolor articular", "descripcion": "Estrategia para control de peso y nutrientes clave en salud osteoarticular.", "url": "", "nivel_evidencia": "moderado"},

    # INSOMNIO
    {"trastorno": "insomnio", "especialidad": "psicologo", "titulo": "Higiene del sueno y rutina de descarga", "descripcion": "Protocolo conductual para conciliar sueno y reducir despertares nocturnos.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "insomnio", "especialidad": "medico", "titulo": "Insomnio y comorbilidades medicas", "descripcion": "Evaluacion de causas organicas, farmacologicas y de riesgo cronico.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "insomnio", "especialidad": "nutricionista", "titulo": "Nutricion y ritmo circadiano", "descripcion": "Timing de comidas, cafeina y cena para mejorar arquitectura del sueno.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "insomnio", "especialidad": "coach", "titulo": "Entrenamiento segun higiene del sueno", "descripcion": "Ajuste de horario e intensidad de ejercicio para favorecer descanso nocturno.", "url": "", "nivel_evidencia": "moderado"},

    # CELIAQUIA Y ALERGIAS
    {"trastorno": "celiaquia", "especialidad": "nutricionista", "titulo": "Plan estricto sin gluten", "descripcion": "Guia de eliminacion completa de gluten y prevencion de contaminacion cruzada.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "celiaquia", "especialidad": "medico", "titulo": "Seguimiento clinico en celiaquia", "descripcion": "Control de sintomas, analitica y criterios de alarma digestiva.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "celiaquia", "especialidad": "psicologo", "titulo": "Adherencia a dieta de exclusion", "descripcion": "Apoyo emocional para reducir ansiedad social y fatiga por restriccion dietetica.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "alergia_alimentaria", "especialidad": "medico", "titulo": "Manejo clinico de alergia alimentaria", "descripcion": "Plan de accion ante reaccion aguda y educacion en evitacion de alergenos.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "alergia_alimentaria", "especialidad": "nutricionista", "titulo": "Plan de sustituciones en alergias", "descripcion": "Sustituciones nutricionales seguras para mantener calidad dietetica y adherencia.", "url": "", "nivel_evidencia": "alto"},

    # SII / DIGESTIVO FUNCIONAL
    {"trastorno": "sindrome_intestino_irritable", "especialidad": "nutricionista", "titulo": "FODMAP por fases", "descripcion": "Protocolo de eliminacion temporal y reintroduccion guiada para SII.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "sindrome_intestino_irritable", "especialidad": "medico", "titulo": "Descartar organicidad en SII", "descripcion": "Algoritmo de banderas rojas y pruebas complementarias en dolor abdominal funcional.", "url": "", "nivel_evidencia": "alto"},
    {"trastorno": "sindrome_intestino_irritable", "especialidad": "psicologo", "titulo": "Eje intestino-cerebro", "descripcion": "Intervencion en estres, hipervigilancia corporal y sintomas digestivos funcionales.", "url": "", "nivel_evidencia": "moderado"},

    # FIBROMIALGIA
    {"trastorno": "fibromialgia", "especialidad": "medico", "titulo": "Manejo integral de fibromialgia", "descripcion": "Abordaje multimodal del dolor difuso, sueno y fatiga persistente.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "fibromialgia", "especialidad": "psicologo", "titulo": "Intervencion cognitiva en dolor persistente", "descripcion": "Tecnicas para reducir catastrofismo, impotencia y impacto emocional del dolor.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "fibromialgia", "especialidad": "coach", "titulo": "Actividad fisica graduada en fibromialgia", "descripcion": "Plan progresivo de movimiento para evitar brotes y mejorar funcionalidad.", "url": "", "nivel_evidencia": "moderado"},
    {"trastorno": "fibromialgia", "especialidad": "nutricionista", "titulo": "Nutricion antiinflamatoria en fibromialgia", "descripcion": "Estrategias alimentarias para modular fatiga, dolor y tolerancia al esfuerzo.", "url": "", "nivel_evidencia": "moderado"},
]

DIETAS_CLINICAS_BASE: List[Dict[str, Any]] = [
    {
        "condicion": "celiaquia",
        "objetivo": "eliminacion_gluten",
        "titulo": "Plan estricto sin gluten y sin contaminacion cruzada",
        "para_quien": "Personas con celiaquia o alta sospecha clínica en estudio por especialista.",
        "alergenos_clave": ["gluten", "trigo", "cebada", "centeno", "avena contaminada"],
        "alimentos_evitar": ["pan común", "pasta de trigo", "salsas con harina", "rebozados", "cerveza"],
        "alimentos_priorizar": ["arroz", "quinoa", "maiz", "patata", "proteina magra", "verduras"],
        "ejemplo_menu_1_dia": [
            "Desayuno: tortilla francesa con fruta y avena certificada sin gluten",
            "Comida: arroz con pollo, aceite de oliva y ensalada",
            "Cena: salmon al horno con patata cocida y verduras",
        ],
        "suplementos_opcionales": ["hierro", "vitamina D", "B12"],
        "red_flags": ["perdida de peso involuntaria", "diarrea persistente", "fatiga intensa", "sangrado digestivo"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "alto",
        "nota_seguridad": "Confirmar etiquetas sin gluten y evitar utensilios compartidos para prevenir trazas.",
    },
    {
        "condicion": "alergia_proteina_leche_vaca",
        "objetivo": "eliminacion_alergeno",
        "titulo": "Eliminacion total de leche y derivados",
        "para_quien": "Alergia confirmada a proteína de leche de vaca (APLV) o sospecha en evaluación médica.",
        "alergenos_clave": ["caseina", "lactalbumina", "lactoglobulina", "suero lacteo", "leche"],
        "alimentos_evitar": ["leche", "yogur", "queso", "nata", "batidos lacteos"],
        "alimentos_priorizar": ["bebida vegetal fortificada", "pescado", "huevo", "legumbres", "verduras"],
        "ejemplo_menu_1_dia": [
            "Desayuno: bebida de soja fortificada con avena y fruta",
            "Comida: lentejas con verduras y arroz",
            "Cena: merluza con boniato y ensalada",
        ],
        "suplementos_opcionales": ["calcio", "vitamina D"],
        "red_flags": ["urticaria", "sibilancias", "edema de labios", "vomitos repetidos"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "alto",
        "nota_seguridad": "Llevar plan de accion para alergia y revisar trazas en etiquetado.",
    },
    {
        "condicion": "intolerancia_lactosa",
        "objetivo": "control_sintomas",
        "titulo": "Plan bajo en lactosa con tolerancia individual",
        "para_quien": "Personas con intolerancia a lactosa sin alergia a proteína de leche.",
        "alergenos_clave": ["lactosa"],
        "alimentos_evitar": ["leche entera", "helados", "postres lacteos"],
        "alimentos_priorizar": ["yogur sin lactosa", "quesos curados", "kefir tolerado", "proteina magra"],
        "ejemplo_menu_1_dia": [
            "Desayuno: yogur sin lactosa con fruta",
            "Comida: pechuga de pollo con quinoa y verduras",
            "Cena: tortilla con espinacas y patata",
        ],
        "suplementos_opcionales": ["enzima lactasa"],
        "red_flags": ["dolor abdominal severo", "diarrea persistente", "perdida de peso"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "moderado",
        "nota_seguridad": "Introducir lactosa de forma gradual y monitorizar tolerancia por raciones.",
    },
    {
        "condicion": "alergia_frutos_secos",
        "objetivo": "eliminacion_alergeno",
        "titulo": "Plan seguro libre de frutos secos y trazas",
        "para_quien": "Pacientes con alergia a nueces, almendras, avellanas, pistacho u otros frutos secos.",
        "alergenos_clave": ["nuez", "almendra", "avellana", "pistacho", "anacardo", "cacahuete"],
        "alimentos_evitar": ["frutos secos", "mantecas de frutos secos", "barritas con trazas", "pestos"],
        "alimentos_priorizar": ["semillas toleradas", "legumbres", "carnes", "huevos", "fruta"],
        "ejemplo_menu_1_dia": [
            "Desayuno: tostada sin trazas con pavo y tomate",
            "Comida: arroz con ternera y verduras",
            "Cena: crema de calabacin y tortilla",
        ],
        "suplementos_opcionales": [],
        "red_flags": ["dificultad respiratoria", "edema facial", "mareo", "anafilaxia previa"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "alto",
        "nota_seguridad": "Evitar productos sin etiquetado claro y revisar siempre la lista de alergenos.",
    },
    {
        "condicion": "alergia_huevo",
        "objetivo": "eliminacion_alergeno",
        "titulo": "Plan de eliminacion de huevo y ovoproductos",
        "para_quien": "Pacientes con alergia al huevo confirmada o en protocolo de reintroducción médica.",
        "alergenos_clave": ["huevo", "ovoalbumina", "lisozima"],
        "alimentos_evitar": ["huevo", "rebozados", "bolleria con huevo", "mayonesa tradicional"],
        "alimentos_priorizar": ["legumbres", "tofu", "pescado", "carne magra", "frutas y verduras"],
        "ejemplo_menu_1_dia": [
            "Desayuno: porridge con bebida vegetal y fruta",
            "Comida: garbanzos con verduras",
            "Cena: pescado blanco con arroz y ensalada",
        ],
        "suplementos_opcionales": [],
        "red_flags": ["urticaria generalizada", "sibilancias", "vomitos", "hipotension"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "alto",
        "nota_seguridad": "No realizar reintroducciones sin supervisión de alergología/medicina.",
    },
    {
        "condicion": "alergia_pescado_marisco",
        "objetivo": "eliminacion_alergeno",
        "titulo": "Plan libre de pescado y marisco",
        "para_quien": "Pacientes con alergia a pescado, crustaceos o moluscos.",
        "alergenos_clave": ["pescado", "marisco", "crustaceos", "moluscos"],
        "alimentos_evitar": ["pescado", "caldos de pescado", "sushi", "salsas con marisco"],
        "alimentos_priorizar": ["pollo", "pavo", "huevo", "legumbres", "aceite de oliva"],
        "ejemplo_menu_1_dia": [
            "Desayuno: yogur con fruta y copos de maiz",
            "Comida: pavo al horno con patata",
            "Cena: ensalada completa con legumbres",
        ],
        "suplementos_opcionales": ["omega 3 de microalgas"],
        "red_flags": ["disnea", "edema de lengua", "mareo", "sincope"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "alto",
        "nota_seguridad": "Atención a contaminación cruzada en restaurantes y freidoras compartidas.",
    },
    {
        "condicion": "sindrome_intestino_irritable",
        "objetivo": "baja_fodmap_temporal",
        "titulo": "Fase inicial baja en FODMAP con reintroduccion",
        "para_quien": "Pacientes con SII en brote digestivo y dolor abdominal funcional.",
        "alergenos_clave": ["fodmap", "fructanos", "polioles", "galactanos"],
        "alimentos_evitar": ["ajo", "cebolla", "trigo", "manzana", "legumbres en exceso"],
        "alimentos_priorizar": ["arroz", "avena", "platano", "calabacin", "proteina magra"],
        "ejemplo_menu_1_dia": [
            "Desayuno: avena con platano",
            "Comida: arroz con pollo y calabacin",
            "Cena: tortilla con espinacas y patata",
        ],
        "suplementos_opcionales": ["probiótico indicado por especialista"],
        "red_flags": ["sangrado en heces", "fiebre", "perdida de peso", "despertar nocturno por dolor"],
        "especialistas_recomendados": ["nutricionista", "medico", "psicologo"],
        "nivel_evidencia": "moderado",
        "nota_seguridad": "FODMAP debe ser temporal y con reintroducción guiada para evitar restricciones crónicas.",
    },
    {
        "condicion": "sop",
        "objetivo": "control_glucemico",
        "titulo": "Plan para SOP con enfoque antiinflamatorio y saciedad",
        "para_quien": "Mujeres con síndrome de ovario poliquístico y resistencia a insulina.",
        "alergenos_clave": [],
        "alimentos_evitar": ["ultraprocesados", "azucares liquidos", "alcohol frecuente"],
        "alimentos_priorizar": ["proteina en cada comida", "fibra", "grasa saludable", "legumbres"],
        "ejemplo_menu_1_dia": [
            "Desayuno: huevos con verduras y fruta",
            "Comida: quinoa con salmon y ensalada",
            "Cena: crema de verduras y pechuga de pavo",
        ],
        "suplementos_opcionales": ["inositol", "omega 3", "vitamina D"],
        "red_flags": ["amenorrea prolongada", "hiperglucemia", "fatiga extrema"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "moderado",
        "nota_seguridad": "Ajustar carbohidratos según tolerancia y fase del ciclo con seguimiento clínico.",
    },
    {
        "condicion": "diabetes_tipo_2",
        "objetivo": "control_glucemico",
        "titulo": "Plan de control glucemico por plato y horarios",
        "para_quien": "Personas con diabetes tipo 2 o prediabetes en intervención nutricional.",
        "alergenos_clave": [],
        "alimentos_evitar": ["bebidas azucaradas", "bolleria", "harinas refinadas en exceso"],
        "alimentos_priorizar": ["verduras", "proteina magra", "legumbres", "cereales integrales"],
        "ejemplo_menu_1_dia": [
            "Desayuno: yogur natural con semillas y fruta",
            "Comida: plato de legumbres con ensalada",
            "Cena: pescado azul con verduras salteadas",
        ],
        "suplementos_opcionales": ["fibra soluble"],
        "red_flags": ["hipoglucemias repetidas", "glucemias persistentemente altas", "vision borrosa"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "alto",
        "nota_seguridad": "Coordinar dieta con pauta farmacológica para evitar hipoglucemias.",
    },
    {
        "condicion": "hipertension",
        "objetivo": "control_presion_arterial",
        "titulo": "Plan DASH adaptado con control de sodio",
        "para_quien": "Pacientes con hipertensión arterial o riesgo cardiovascular elevado.",
        "alergenos_clave": [],
        "alimentos_evitar": ["embutidos", "snacks salados", "salsas ultraprocesadas"],
        "alimentos_priorizar": ["fruta", "verdura", "lacteos bajos en grasa", "legumbres", "frutos secos tolerados"],
        "ejemplo_menu_1_dia": [
            "Desayuno: avena con fruta",
            "Comida: ensalada grande con legumbres",
            "Cena: pechuga a la plancha con verduras",
        ],
        "suplementos_opcionales": ["potasio dietético guiado"],
        "red_flags": ["cefalea intensa", "dolor toracico", "disnea", "TA > 180/120"],
        "especialistas_recomendados": ["nutricionista", "medico"],
        "nivel_evidencia": "alto",
        "nota_seguridad": "Monitorizar presión arterial en casa y ajustar sal total diaria.",
    },
    {
        "condicion": "trastorno_alimentario_recuperacion",
        "objetivo": "recuperacion_clinica",
        "titulo": "Plan estructurado de recuperación nutricional",
        "para_quien": "Pacientes con TCA en fase de recuperación y seguimiento multidisciplinar.",
        "alergenos_clave": [],
        "alimentos_evitar": ["ayunos prolongados", "reglas rígidas", "restricciones no indicadas"],
        "alimentos_priorizar": ["regularidad de ingestas", "densidad nutricional", "colaciones seguras"],
        "ejemplo_menu_1_dia": [
            "Desayuno: tostada completa con queso y fruta",
            "Comida: arroz, proteína y verduras",
            "Cena: pasta con salsa de tomate y atún",
        ],
        "suplementos_opcionales": ["según analítica"],
        "red_flags": ["conductas compensatorias", "mareos", "rechazo de comidas", "ideación autolesiva"],
        "especialistas_recomendados": ["nutricionista", "psicologo", "medico"],
        "nivel_evidencia": "moderado",
        "nota_seguridad": "Necesita coordinación estrecha entre nutrición, psicología y medicina.",
    },
]

EJERCICIOS_CATALOGO_BASE: List[Dict[str, str]] = [
    # DOLOR DE RODILLA - Rehabilitación
    {"condicion": "dolor_rodilla", "objetivo": "rehabilitacion", "nombre": "Sentadilla a caja", "que_es": "Sentadilla parcial con apoyo para aprender patrón sin tanto estrés articular. Minimiza rango de movimiento para proteger articulación.", "para_que_sirve": "Mejorar patrón de rodilla y glúteo con menos dolor. Base para progresar a sentadilla completa.", "series": "3", "repeticiones": "8-12", "duracion": "5-8 min", "nivel": "basico", "imagen_referencia": "persona sentada en caja resistiendo con pies, levantándose lentamente"},
    {"condicion": "dolor_rodilla", "objetivo": "rehabilitacion", "nombre": "Extensión de rodilla sentado", "que_es": "Extensión controlada de rodilla desde posición sentada sin carga adicional.", "para_que_sirve": "Fortalecer cuádriceps sin carga de peso corporal. Técnica de bajo estrés para recuperación.", "series": "3", "repeticiones": "12-15", "duracion": "6-8 min", "nivel": "muy_basico", "imagen_referencia": "persona sentada extendiendo la pierna lentamente"},
    {"condicion": "dolor_rodilla", "objetivo": "rehabilitacion", "nombre": "Prensa de pierna con ROM limitado", "que_es": "Prensa de pierna limitando rango de movimiento a 45-60 grados.", "para_que_sirve": "Fortalecimiento sin dolor excesivo. Mantiene musculatura activa en recuperación.", "series": "3", "repeticiones": "10-15", "duracion": "8-10 min", "nivel": "basico", "imagen_referencia": "máquina prensa con persona empujando en rango limitado"},
    {"condicion": "dolor_rodilla", "objetivo": "fuerza", "nombre": "Step-up bajo", "que_es": "Subida a un escalón bajo (15-20 cm) controlando alineación de rodilla y cadera.", "para_que_sirve": "Fortalecer cuádriceps y glúteo sin alto impacto. Progresos en rehabilitación.", "series": "3", "repeticiones": "8-10", "duracion": "6-10 min", "nivel": "basico", "imagen_referencia": "persona subiendo escalín bajo con paso controlado"},
    {"condicion": "dolor_rodilla", "objetivo": "fuerza", "nombre": "Sentadilla goblet ligera", "que_es": "Sentadilla con mancuerna 5-10kg frente al pecho para estabilidad y feedback de cadera.", "para_que_sirve": "Transición hacia carga, mejora patrón con peso guía pequeño.", "series": "3", "repeticiones": "8-12", "duracion": "8-10 min", "nivel": "intermedio", "imagen_referencia": "persona con mancuerna pequeña frente al pecho haciendo sentadilla medio rango"},
    {"condicion": "dolor_rodilla", "objetivo": "fuerza", "nombre": "Peso muerto rumano (RDL) con pierna única", "que_es": "Bisagra de cadera con una pierna, sosteniendo pesa en mano del mismo lado.", "para_que_sirve": "Fortalecer cadena posterior y equilibrio single-leg. Protege rodilla enfocándose en cadera y glúteo.", "series": "3", "repeticiones": "8-10 por lado", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona de pie sobre una pierna, inclinando cadera con mancuerna"},
    
    # DOLOR LUMBAR - Rehabilitación
    {"condicion": "dolor_lumbar", "objetivo": "rehabilitacion", "nombre": "Bird-dog", "que_es": "Ejercicio de estabilidad lumbopélvica en cuadrupedia extendiendo brazo contrario y pierna.", "para_que_sirve": "Control de core y estabilidad sin carga axial alta. Esencial para recuperación lumbar.", "series": "3", "repeticiones": "6-10 por lado", "duracion": "5-8 min", "nivel": "basico", "imagen_referencia": "cuádrupedia extendiendo brazo derecho y pierna izquierda simultáneamente"},
    {"condicion": "dolor_lumbar", "objetivo": "rehabilitacion", "nombre": "Dead-bug", "que_es": "Tumbado boca arriba, alternando extensión de extremidades opuestas sin arquear lumbares.", "para_que_sirve": "Control ante de esfuerzo mínimo. Estabilización spinal neutra y disociación de cadera.", "series": "3", "repeticiones": "6-8 por lado", "duracion": "5-7 min", "nivel": "muy_basico", "imagen_referencia": "tumbado boca arriba alternando brazos y piernas"},
    {"condicion": "dolor_lumbar", "objetivo": "rehabilitacion", "nombre": "Puente glúteo básico", "que_es": "Levantamiento de cadera en posición supina con rodillas flexionadas.", "para_que_sirve": "Activación glútea sin carga. Inicia fuerza cadena posterior.", "series": "3", "repeticiones": "10-15", "duracion": "5-8 min", "nivel": "muy_basico", "imagen_referencia": "tumbado boca arriba levantando cadera con rodillas flexionadas"},
    {"condicion": "dolor_lumbar", "objetivo": "rehabilitacion", "nombre": "Plancha abdominal (versión de rodillas)", "que_es": "Posición prona sobre antebrazos con rodillas apoyadas en piso.", "para_que_sirve": "Activación isométrica de core sin presión lumbar excesiva. Anti-extensión progresiva.", "series": "3", "repeticiones": "20-40 seg", "duracion": "6-8 min", "nivel": "basico", "imagen_referencia": "persona en posición plancha sobre antebrazos y rodillas"},
    {"condicion": "dolor_lumbar", "objetivo": "fuerza", "nombre": "Peso muerto modificado (trap bar)", "que_es": "Levantamiento con barra trap manteniendo torso más vertical que RDL clásico.", "para_que_sirve": "Desarrollar cadena posterior con mayor seguridad lumbar. Espalda neutral y posición más segura.", "series": "4", "repeticiones": "5-8", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona levantando trap bar manteniendo columna neutra"},
    {"condicion": "dolor_lumbar", "objetivo": "fuerza", "nombre": "Remo en máquina", "que_es": "Tracción horizontal en máquina de remo, manteniendo espalda neutral.", "para_que_sirve": "Fortalecimiento de espalda baja y media sin compresión spinal. Anti-flexión.", "series": "4", "repeticiones": "8-12", "duracion": "8-10 min", "nivel": "basico", "imagen_referencia": "persona en máquina de remo jalando manija hacia el cuerpo"},
    
    # ANSIEDAD ALTA - Regulación
    {"condicion": "ansiedad_alta", "objetivo": "regulacion", "nombre": "Caminata rítmica", "que_es": "Caminar a ritmo constante (60-80 pasos/min) con respiración nasal si es posible.", "para_que_sirve": "Bajar activación del SNC y facilitar parasimpático. Adherencia máxima sin demanda.", "series": "1", "repeticiones": "20-30 min", "duracion": "20-30 min", "nivel": "muy_basico", "imagen_referencia": "persona caminando en ritmo constante al aire libre"},
    {"condicion": "ansiedad_alta", "objetivo": "regulacion", "nombre": "Respiración 4-7-8", "que_es": "Respiración: inhalar 4 tiempos, sostener 7, exhalar 8, durante 4-5 ciclos.", "para_que_sirve": "Activación directa del parasimpático. Reducción inmediata de ansiedad aguda.", "series": "1-3", "repeticiones": "4-5 ciclos", "duracion": "3-5 min", "nivel": "muy_basico", "imagen_referencia": "persona sentada realizando respiración lenta con contador visual"},
    {"condicion": "ansiedad_alta", "objetivo": "regulacion", "nombre": "Yoga lento (Hatha básico)", "que_es": "Secuencia lenta de posturas de yoga (Child's pose, Cat-cow) con énfasis en respiración.", "para_que_sirve": "Movilidad + regulación respiratoria. Integración somática.", "series": "1", "repeticiones": "15-20 min", "duracion": "15-20 min", "nivel": "basico", "imagen_referencia": "persona en postura child's pose respirando profundamente"},
    {"condicion": "ansiedad_alta", "objetivo": "regulacion", "nombre": "Sentadilla al aire + respiración", "que_es": "Sentadilla suave (45 grados) combinada con respiración lenta en 3 tiempos de inhalación y 4 de exhalación.", "para_que_sirve": "Unir movilidad y regulación para reducir tensión. Propiocepción + calma.", "series": "2", "repeticiones": "6-8", "duracion": "5-6 min", "nivel": "basico", "imagen_referencia": "persona en sentadilla suave con expresión relajada"},
    {"condicion": "ansiedad_alta", "objetivo": "regulacion", "nombre": "Tai chi básico", "que_es": "Movimientos lentos y fluidos de tai chi en posición de pie.", "para_que_sirve": "Regulación con movimiento meditativo. Balance y atención presente.", "series": "1", "repeticiones": "20-30 min", "duracion": "20-30 min", "nivel": "muy_basico", "imagen_referencia": "persona ejecutando movimiento de tai chi exterior"},
    {"condicion": "ansiedad_alta", "objetivo": "regulacion", "nombre": "Estiramiento suave de espalda", "que_es": "Estiramientos pasivos de espalda, hombros y cuello sin rebote.", "para_que_sirve": "Liberación de tensión acumulada. Toma de contacto con cuerpo.", "series": "1", "repeticiones": "5-6 estiramientos", "duracion": "8-10 min", "nivel": "muy_basico", "imagen_referencia": "persona estirando espalda en posición sentada"},
    
    # FATIGA - Recuperación
    {"condicion": "fatiga", "objetivo": "recuperacion", "nombre": "Movilidad de cadera y columna", "que_es": "Secuencia suave: Cat-cow, butterfly, hip circles, sin forzar rango.", "para_que_sirve": "Recuperar circulación sin acumular estrés. Antiinflamatorio mediante movimiento suave.", "series": "1", "repeticiones": "8-10 reps por movimiento", "duracion": "8-12 min", "nivel": "muy_basico", "imagen_referencia": "persona haciendo cat-cow en manos y rodillas"},
    {"condicion": "fatiga", "objetivo": "recuperacion", "nombre": "Caminata suave", "que_es": "Actividad aeróbica muy ligera a intensidad conversacional (<60% FCmax).", "para_que_sirve": "Mejorar recuperación cardiovascular y circulación sin fatiga acumulativa.", "series": "1", "repeticiones": "15-25 min", "duracion": "15-25 min", "nivel": "muy_basico", "imagen_referencia": "persona caminando despacio en parque"},
    {"condicion": "fatiga", "objetivo": "recuperacion", "nombre": "Respiración abdominal acostado", "que_es": "Acostado boca arriba respirando profundamente en abdomen, 2-3 min.", "para_que_sirve": "Recuperación parasimpática profunda. Reducción de cortisol.", "series": "1", "repeticiones": "2-3 min", "duracion": "3-5 min", "nivel": "muy_basico", "imagen_referencia": "persona acostada con mano en abdomen respirando lentamente"},
    {"condicion": "fatiga", "objetivo": "recuperacion", "nombre": "Estiramientos pasivos full-body", "que_es": "Secuencia de estiramientos suaves sin rebotar: flexores, isquios, pecho, espalda.", "para_que_sirve": "Reducción de rigidez y activación de parasimpático mediante relajación.", "series": "1", "repeticiones": "6-8 estiramientos", "duracion": "10-15 min", "nivel": "muy_basico", "imagen_referencia": "persona en posición de estiramiento suave en el piso"},
    {"condicion": "fatiga", "objetivo": "recuperacion", "nombre": "Nado suave", "que_es": "Nado libre a ritmo muy lento, sin competencia de velocidad.", "para_que_sirve": "Actividad de bajo impacto que mantiene circulación. Soporte completo del agua.", "series": "1", "repeticiones": "15-20 min", "duracion": "15-20 min", "nivel": "basico", "imagen_referencia": "persona nadando lentamente estilo libre en piscina"},
    {"condicion": "fatiga", "objetivo": "recuperacion", "nombre": "Foam-rolling pasivo", "que_es": "Autorrelease con foam roller lento en espalda, glúteos, quads (sin ejercer presión fuerte).", "para_que_sirve": "Liberación muscular fascial sin desgaste energético.", "series": "1", "repeticiones": "5-6 zonas", "duracion": "10-12 min", "nivel": "muy_basico", "imagen_referencia": "persona acostada sobre foam roller en espalda"},
    
    # GANANCIA MUSCULAR - Fuerza
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Sentadilla goblet", "que_es": "Sentadilla con mancuerna 20-30kg frente al pecho, rango completo controlado.", "para_que_sirve": "Desarrollar piernas y core con técnica estable. Facilita ROM completo.", "series": "4", "repeticiones": "6-10", "duracion": "8-12 min", "nivel": "intermedio", "imagen_referencia": "persona con mancuerna frente al pecho haciendo sentadilla rango completo"},
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Press de banca", "que_es": "Empuje horizontal en banco con barra o mancuernas, rango completo.", "para_que_sirve": "Ganar fuerza y masa en pecho, hombro anterior y tríceps.", "series": "4", "repeticiones": "5-8 (3-5RM)", "duracion": "10-15 min", "nivel": "intermedio", "imagen_referencia": "persona tumbada empujando barra en banco"},
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Peso muerto", "que_es": "Levantamiento de barra desde el piso hasta altura de cadera con técnica neutra.", "para_que_sirve": "Fuerza global cadena posterior, espalda baja y sistema nervioso central.", "series": "4", "repeticiones": "3-5 (2-5RM)", "duracion": "12-15 min", "nivel": "intermedio", "imagen_referencia": "persona levantando barra desde el piso manteniendo espalda neutra"},
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Remo barra (T-bar)", "que_es": "Tracción de barra angular contra pecho desde posición inclinada (45 grados).", "para_que_sirve": "Desarrollo de espalda media y lats con soporte de inclinación.", "series": "4", "repeticiones": "6-10", "duracion": "8-12 min", "nivel": "intermedio", "imagen_referencia": "persona tirando de barra angular hacia el pecho"},
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Press militar (overhead)", "que_es": "Empuje vertical de barra desde hombros hasta posición extendida sobre cabeza.", "para_que_sirve": "Desarrollo de hombro, tríceps y estabilidad de core.", "series": "4", "repeticiones": "5-8", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona empujando barra verticalmente sobre la cabeza"},
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Sentadilla frontal", "que_es": "Sentadilla con barra apoyada en hombros, torso vertical.", "para_que_sirve": "Mayor enfoque en cuádriceps y core anterior. Desarrollo completo de pierna.", "series": "4", "repeticiones": "5-8", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona con barra en hombros haciendo sentadilla vertical"},
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Jalón de polea", "que_es": "Tracción vertical de cable desde arriba hasta pecho.", "para_que_sirve": "Desarrollo de lats y espalda. Accesible y técnicamente seguro.", "series": "3-4", "repeticiones": "8-12", "duracion": "8-10 min", "nivel": "basico", "imagen_referencia": "persona tirando de cable hacia el pecho desde arriba"},
    {"condicion": "ganancia_muscular", "objetivo": "fuerza", "nombre": "Flexión de brazos (pull-ups)", "que_es": "Flexión del cuerpo suspendido en barra, asistida si es necesario.", "para_que_sirve": "Desarrollo de lats, espalda y bíceps. Fuerza funcional de tracción.", "series": "3-4", "repeticiones": "5-10", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona haciendo pull-up en barra suspendida"},
    
    # PÉRDIDA DE GRASA - Salud
    {"condicion": "perdida_grasa", "objetivo": "salud", "nombre": "Caminata inclinada", "que_es": "Caminar en cinta a inclinación 8-12% a velocidad lenta (3-4 km/h).", "para_que_sirve": "Aumentar gasto con menor impacto articular. Quemagrasas de bajo riesgo.", "series": "1", "repeticiones": "20-40 min", "duracion": "20-40 min", "nivel": "basico", "imagen_referencia": "persona caminando en cinta inclinada"},
    {"condicion": "perdida_grasa", "objetivo": "salud", "nombre": "Circuito full-body con descanso corto", "que_es": "Bloque de ejercicios: sentadilla, prensa pecho, remo, press, 45sec trabajo / 15sec descanso.", "para_que_sirve": "Mantener músculo mientras se facilita el déficit energético. EMOM training.", "series": "3", "repeticiones": "8-12 por ejercicio", "duracion": "20-30 min", "nivel": "intermedio", "imagen_referencia": "circuito de mancuernas en movimiento rápido"},
    {"condicion": "perdida_grasa", "objetivo": "salud", "nombre": "Burpees", "que_es": "Plancha + flexión + salto, movimiento completo coordinado.", "para_que_sirve": "Cardio de alta demanda. Quema máxima de calorías en tiempo corto.", "series": "3", "repeticiones": "10-15", "duracion": "8-10 min", "nivel": "intermedio", "imagen_referencia": "persona ejecutando burpee completo"},
    {"condicion": "perdida_grasa", "objetivo": "salud", "nombre": "Saltos en escalones (Box jumps)", "que_es": "Saltos sobre plataforma (40-60cm) aprovechando elasticidad muscular.", "para_que_sirve": "Explosividad + cardio intenso + activación completa de pierna.", "series": "3", "repeticiones": "8-10", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona saltando sobre plataforma"},
    {"condicion": "perdida_grasa", "objetivo": "salud", "nombre": "Battle ropes", "que_es": "Ondulación alterna de cuerdas gruesas a máxima velocidad, 40-50seg.", "para_que_sirve": "Cardio explosivo con trabajo de core y estabilidad.", "series": "3-4", "repeticiones": "40-50 seg", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona agitando battle ropes al máximo"},
    {"condicion": "perdida_grasa", "objetivo": "salud", "nombre": "Ciclismo a ritmo moderado-alto", "que_es": "Pedaleo continuo en bicicleta a 70-80% FCmax durante 20-40min.", "para_que_sirve": "Trabajo cardiovascular sostenido con bajo impacto en articulaciones.", "series": "1", "repeticiones": "20-40 min", "duracion": "20-40 min", "nivel": "basico", "imagen_referencia": "persona pedaleando en bicicleta exterior"},
    {"condicion": "perdida_grasa", "objetivo": "salud", "nombre": "HIIT (High Intensity Interval Training)", "que_es": "Alternancia 20-30seg máxima intensidad / 10-20seg recuperación, 8-10 rondas.", "para_que_sirve": "Máxima eficiencia temporal. EPOC elevado post-entrenamiento.", "series": "1", "repeticiones": "8-10 rondas", "duracion": "15-20 min", "nivel": "intermedio", "imagen_referencia": "persona corriendo a sprint en intervalo"},
    
    # DOLOR CERVICAL - Rehabilitación
    {"condicion": "dolor_cervical", "objetivo": "rehabilitacion", "nombre": "Movilización de cuello controlada", "que_es": "Rotación lenta, flexo-extensión y lateralización del cuello sin forzar extremo.", "para_que_sirve": "Restaurar ROM cervical seguro. Base para fortalecer estabilizadores.", "series": "2", "repeticiones": "6-8 en cada dirección", "duracion": "5-8 min", "nivel": "muy_basico", "imagen_referencia": "persona girando lentamente la cabeza en múltiples direcciones"},
    {"condicion": "dolor_cervical", "objetivo": "rehabilitacion", "nombre": "Retracción cervical (chin tucks)", "que_es": "Movimiento leve de barbilla hacia atrás, creando double chin temporal, sostenida 2-3 seg.", "para_que_sirve": "Activar extensores cervicales profundos. Corregir postura anterior.", "series": "2-3", "repeticiones": "10-12", "duracion": "4-6 min", "nivel": "muy_basico", "imagen_referencia": "persona retrayendo barbilla hacia atrás en postura sentada"},
    {"condicion": "dolor_cervical", "objetivo": "rehabilitacion", "nombre": "Estiramiento escalenos", "que_es": "Flexión lateral de cuello con mano apoyada en cabeza, sosteniendo 20-30seg por lado.", "para_que_sirve": "Bajar tensión muscular en cuello y parte superior de espalda.", "series": "2-3", "repeticiones": "2 repeticiones", "duracion": "6-10 min", "nivel": "muy_basico", "imagen_referencia": "persona estirando cuello lateralmente con gesto suave"},
    {"condicion": "dolor_cervical", "objetivo": "fuerza", "nombre": "Resistencia cervical con banda", "que_es": "Resistencia en las 4 direcciones (flexión, extensión, rotación) con banda elástica.", "para_que_sirve": "Fortalecer musculatura profunda cervical contra resistencia progresiva.", "series": "2-3", "repeticiones": "10-12 en cada dirección", "duracion": "8-10 min", "nivel": "basico", "imagen_referencia": "persona usando banda para resistir movimiento del cuello"},
    {"condicion": "dolor_cervical", "objetivo": "fuerza", "nombre": "Remo de fila baja estricto", "que_es": "Tracción manteniendo columna neutral, enfocándose en retraer escápulas.", "para_que_sirve": "Fortalecer romboides y espalda media. Soporte postural cervical.", "series": "3-4", "repeticiones": "8-10", "duracion": "10-12 min", "nivel": "intermedio", "imagen_referencia": "persona haciendo remo con estricta postura neutral"},
    {"condicion": "dolor_cervical", "objetivo": "fuerza", "nombre": "Shrug isométrico", "que_es": "Elevación de hombros contra banda en posición sentada, 5-10seg sostenida.", "para_que_sirve": "Fortalecimiento de trapecios superiores. Equilibración de tensión cervical.", "series": "3", "repeticiones": "6-8 sostenidas", "duracion": "8-10 min", "nivel": "basico", "imagen_referencia": "persona elevando hombros en posición isométrica"},
    
    # DEPRESIÓN - Regulación
    {"condicion": "depresion", "objetivo": "regulacion", "nombre": "Caminata exterior 20-30min", "que_es": "Caminata al aire libre a ritmo cómodo, exposición a luz natural y naturaleza.", "para_que_sirve": "Aumento de serotonina mediante luz solar y movimiento rítmico.", "series": "1", "repeticiones": "20-30 min", "duracion": "20-30 min", "nivel": "muy_basico", "imagen_referencia": "persona caminando en parque soleado"},
    {"condicion": "depresion", "objetivo": "regulacion", "nombre": "Entrenamiento de fuerza leve (Full-body)", "que_es": "Circuito suave: sentadilla goblet, remo, press tipo, 2-3 series, sin fatigar al máximo.", "para_que_sirve": "Liberación de endorfinas. Sensación de logro progresivo.", "series": "2-3", "repeticiones": "8-10", "duracion": "20-25 min", "nivel": "basico", "imagen_referencia": "circuito de pesas livianas en ambiente controlado"},
    {"condicion": "depresion", "objetivo": "regulacion", "nombre": "Baile libre 15-20min", "que_es": "Movimiento al ritmo de música preferida, sin estructura de pasos.", "para_que_sirve": "Integración somática. Autoexpresión + movimiento + diversión.", "series": "1", "repeticiones": "15-20 min", "duracion": "15-20 min", "nivel": "muy_basico", "imagen_referencia": "persona bailando libremente con energía"},
    {"condicion": "depresion", "objetivo": "regulacion", "nombre": "Intensidad moderada - Boxeo controlado", "que_es": "Boxeo contra saco o pads a intensidad 60-70% sin cansancio extremo.", "para_que_sirve": "Descarga emocional con control. Canal para procesamiento de emociones negativas.", "series": "3", "repeticiones": "30-40 seg", "duracion": "15-20 min", "nivel": "intermedio", "imagen_referencia": "persona haciendo boxeo contra saco"},
    {"condicion": "depresion", "objetivo": "regulacion", "nombre": "Yoga dinámico moderado", "que_es": "Secuencia de yoga vinyasa a ritmo lento-moderado, sincronizado con respiración.", "para_que_sirve": "Conexión mente-cuerpo. Liberación de tensión somática.", "series": "1", "repeticiones": "30-40 min", "duracion": "30-40 min", "nivel": "basico", "imagen_referencia": "persona haciendo asana de yoga en transición suave"},
    
    # SALUD GENERAL - Mantenimiento
    {"condicion": "salud_general", "objetivo": "recuperacion", "nombre": "Movilidad dinámica 10min", "que_es": "Secuencia de movimientos suave: cat-cow, hip circles, arm circles, marcha lenta.", "para_que_sirve": "Mantenimiento de rango articular. Calentamiento suave.", "series": "1", "repeticiones": "10 min", "duracion": "10 min", "nivel": "muy_basico", "imagen_referencia": "persona haciendo movilidad articular progresiva"},
    {"condicion": "salud_general", "objetivo": "recuperacion", "nombre": "Caminar 30-45min a ritmo conversacional", "que_es": "Caminata a intensidad tal que se pueda mantener conversación (60-70% FCmax).", "para_que_sirve": "Mantenimiento cardiovascular base. Bajo riesgo. Adherencia máxima.", "series": "1", "repeticiones": "30-45 min", "duracion": "30-45 min", "nivel": "basico", "imagen_referencia": "persona caminando en ritmo conversacional afuera"},
    {"condicion": "salud_general", "objetivo": "recuperacion", "nombre": "Estiramientos completos 15min", "que_es": "Secuencia de estiramientos pasivos sin rebotar: pecho, espalda, caderas, isquiotibiales.", "para_que_sirve": "Mantener movilidad. Reducir rigidez acumulada.", "series": "1", "repeticiones": "6-8 estiramientos", "duracion": "15 min", "nivel": "muy_basico", "imagen_referencia": "persona estirada en el piso en múltiples posturas"},
    {"condicion": "salud_general", "objetivo": "fuerza", "nombre": "Entrenamiento full-body 2-3x/semana", "que_es": "Rutina clásica: sentadilla, press, remo, 3 series x 8-10 reps con descanso 2-3min.", "para_que_sirve": "Mantenimiento de fuerza y masa muscular. Prevención de sarcopenia.", "series": "3", "repeticiones": "8-10", "duracion": "40-50 min", "nivel": "intermedio", "imagen_referencia": "rack con barras y mancuernas en gimnasio"},
    {"condicion": "salud_general", "objetivo": "fuerza", "nombre": "Actividad recreativa (tenis, natación, ciclismo)", "que_es": "Deportes recreativos a intensidad moderada 30-60min.", "para_que_sirve": "Cardiovascular + disfrute + adherencia social.", "series": "1", "repeticiones": "30-60 min", "duracion": "30-60 min", "nivel": "intermedio", "imagen_referencia": "persona jugando tenis o nadando de forma recreativa"},
    
    # FIBROMIALGIA - Recuperación
    {"condicion": "fibromialgia", "objetivo": "recuperacion", "nombre": "Piscina - caminata en agua tibia", "que_es": "Caminata en agua a cintura o pecho a ritmo lento, 15-25min.", "para_que_sirve": "Minimizar impacto articular. Soporte del cuerpo. Calidez del agua reduce fibro-brotes.", "series": "1", "repeticiones": "15-25 min", "duracion": "15-25 min", "nivel": "muy_basico", "imagen_referencia": "persona caminando lentamente en agua tibia"},
    {"condicion": "fibromialgia", "objetivo": "recuperacion", "nombre": "Tai Chi lento completo", "que_es": "Forma completa de tai chi o versión acortada, 45-60min.", "para_que_sirve": "Movimiento meditativo + regulación + control del dolor crónico.", "series": "1", "repeticiones": "45-60 min", "duracion": "45-60 min", "nivel": "basico", "imagen_referencia": "grupo de personas haciendo tai chi exterior"},
    {"condicion": "fibromialgia", "objetivo": "recuperacion", "nombre": "Meditación guiada 20-30min", "que_es": "Meditación de escaneo corporal o mindfulness guiada desde app o audio.", "para_que_sirve": "Reducción de percepción del dolor. Regulación del SNC.", "series": "1", "repeticiones": "20-30 min", "duracion": "20-30 min", "nivel": "muy_basico", "imagen_referencia": "persona sentada meditando con auriculares"},
    {"condicion": "fibromialgia", "objetivo": "recuperacion", "nombre": "Yoga yin 45-60min", "que_es": "Posturas mantenidas 3-5min en yoga yin para fascia profunda.", "para_que_sirve": "Liberación fascial sin demanda muscular. Regeneración profunda.", "series": "1", "repeticiones": "45-60 min", "duracion": "45-60 min", "nivel": "basico", "imagen_referencia": "persona en postura de yoga yin mantenida"},
    {"condicion": "fibromialgia", "objetivo": "regulacion", "nombre": "Pilates suave (reformador asistido)", "que_es": "Pilates en reformador con asistencia profesional, movimientos controlados.", "para_que_sirve": "Fortalecimiento sin impacto. Estabilidad con comodidad.", "series": "2-3", "repeticiones": "8-10 movimientos", "duracion": "45-50 min", "nivel": "intermedio", "imagen_referencia": "persona en máquina reformadora haciendo pilates controlado"},
    
    # INSOMNIO - Recuperación
    {"condicion": "insomnio", "objetivo": "recuperacion", "nombre": "Yoga restaurativo 30min (noche)", "que_es": "Yoga enfocado en relajación con soportes: almohadones, mantas, sin demanda muscular.", "para_que_sirve": "Preparación para sueño. Bajada de adrenalina y activación parasimpática.", "series": "1", "repeticiones": "30 min", "duracion": "30 min", "nivel": "muy_basico", "imagen_referencia": "persona en postura restaurativa con soportes"},
    {"condicion": "insomnio", "objetivo": "recuperacion", "nombre": "Caminata lenta 20-30min (mañana)", "que_es": "Caminata suave en la mañana a luz natural para regular melatonina.", "para_que_sirve": "Regulación de ritmo circadiano. Exposición a luz natural.", "series": "1", "repeticiones": "20-30 min", "duracion": "20-30 min", "nivel": "muy_basico", "imagen_referencia": "persona caminando a la luz del amanecer"},
    {"condicion": "insomnio", "objetivo": "recuperacion", "nombre": "Respiración 4-7-8 pre-sueño (5min)", "que_es": "Respiración lenta 5-10 ciclos justo antes de dormir.", "para_que_sirve": "Activación parasimpática inmediata. Preparación para sueño.", "series": "1", "repeticiones": "5-10 ciclos", "duracion": "5 min", "nivel": "muy_basico", "imagen_referencia": "persona acostada en cama respirando lentamente"},
    {"condicion": "insomnio", "objetivo": "recuperacion", "nombre": "Ejercicio intenso (NO noche)", "que_es": "Ejercicio cardio intenso 45-60min en mañana o temprano (nunca 3h antes de dormir).", "para_que_sirve": "Mejora de calidad de sueño profundo mediante fatiga fisiológica.", "series": "1", "repeticiones": "45-60 min", "duracion": "45-60 min", "nivel": "intermedio", "imagen_referencia": "persona corriendo o haciendo cardio en la mañana"},
    {"condicion": "insomnio", "objetivo": "recuperacion", "nombre": "Body scan meditación 20min", "que_es": "Meditación de atención lenta a cada parte del cuerpo, progresivamente relajante.", "para_que_sirve": "Disociación de preocupaciones. Desconexión mental.", "series": "1", "repeticiones": "20 min", "duracion": "20 min", "nivel": "muy_basico", "imagen_referencia": "persona acostada con expresión serena"},
]

MEDICAMENTOS_CATALOGO_BASE: List[Dict[str, str]] = [
    # PSIQUIATRÍA - ISRSs (Inhibidores Selectivos de Recaptación de Serotonina)
    {"seccion": "psiquiatria_isrs", "nombre": "Sertralina", "para_que_sirve": "Depresión mayor, ansiedad generalizada, TOC, trastorno de pánico, trastorno por estrés postraumático (TEPT), fobia social"},
    {"seccion": "psiquiatria_isrs", "nombre": "Escitalopram", "para_que_sirve": "Depresión mayor, ansiedad generalizada, trastorno de pánico, fobia social, trastorno de estrés postraumático"},
    {"seccion": "psiquiatria_isrs", "nombre": "Fluoxetina", "para_que_sirve": "Depresión mayor, TOC, trastorno de pánico, bulimia nerviosa, trastorno disfórico premenstrual (TDPM)"},
    {"seccion": "psiquiatria_isrs", "nombre": "Paroxetina", "para_que_sirve": "Depresión mayor, ansiedad generalizada, TOC, trastorno de pánico, TEPT, fobia social, TDPM"},
    {"seccion": "psiquiatria_isrs", "nombre": "Citalopram", "para_que_sirve": "Depresión mayor, ansiedad generalizada, depresión agitada, ansiedad coexistente"},
    {"seccion": "psiquiatria_isrs", "nombre": "Fluvoxamina", "para_que_sirve": "TOC, depresión mayor, ansiedad social, ansiedad generalizada, TEPT"},
    {"seccion": "psiquiatria_isrs", "nombre": "Sertralina Genérica", "para_que_sirve": "Alternativa económica a la marca: depresión, ansiedad, TOC, pánico"},
    
    # PSIQUIATRÍA - IRNs (Inhibidores de Recaptación de Noradrenalina y Serotonina)
    {"seccion": "psiquiatria_irns", "nombre": "Venlafaxina", "para_que_sirve": "Depresión mayor, ansiedad generalizada, trastorno de pánico, fobia social, trastorno del estrés postraumático"},
    {"seccion": "psiquiatria_irns", "nombre": "Duloxetina", "para_que_sirve": "Depresión mayor, ansiedad generalizada, dolor neuropático diabético, fibromialgia, dolor musculoesquelético crónico, incontinencia urinaria"},
    {"seccion": "psiquiatria_irns", "nombre": "Desvenlafaxina", "para_que_sirve": "Depresión mayor, sofocos en menopausia, depresión resistente"},
    {"seccion": "psiquiatria_irns", "nombre": "Milnacipran", "para_que_sirve": "Fibromialgia, depresión mayor, dolor crónico"},
    
    # PSIQUIATRÍA - Otros antidepresivos
    {"seccion": "psiquiatria_otros_antidepresivos", "nombre": "Bupropión", "para_que_sirve": "Depresión mayor, depresión bipolar, disfunción sexual inducida por antidepresivos, cese del tabaquismo"},
    {"seccion": "psiquiatria_otros_antidepresivos", "nombre": "Mirtazapina", "para_que_sirve": "Depresión mayor, depresión con insomnio, depresión con anorexia, ansiedad asociada a depresión"},
    {"seccion": "psiquiatria_otros_antidepresivos", "nombre": "Trazodona", "para_que_sirve": "Depresión mayor, insomnio, insomnio comórbido con ansiedad, depresión con insomnio"},
    {"seccion": "psiquiatria_otros_antidepresivos", "nombre": "Amitriptilina", "para_que_sirve": "Depresión mayor, neuralgia postherpética, fibromialgia, migraña, dolor neuropático, insomnio"},
    {"seccion": "psiquiatria_otros_antidepresivos", "nombre": "Nortriptilina", "para_que_sirve": "Depresión mayor, dolor neuropático, migraña, TDAH, enuresis nocturna"},
    
    # PSIQUIATRÍA - Ansiolíticos
    {"seccion": "psiquiatria_ansiedad", "nombre": "Buspirona", "para_que_sirve": "Ansiedad generalizada, síntomas de ansiedad aguda, ansiedad coadyuvante, depresión con ansiedad"},
    {"seccion": "psiquiatria_ansiedad", "nombre": "Pregabalina", "para_que_sirve": "Ansiedad generalizada, dolor neuropático, fibromialgia, trastorno de pánico, epilepsia parcial"},
    {"seccion": "psiquiatria_ansiedad", "nombre": "Gabapentina", "para_que_sirve": "Dolor neuropático, ansiedad, insomnio, migraña, síntomas de abstinencia de alcohol"},
    {"seccion": "psiquiatria_ansiedad", "nombre": "Lorazepam", "para_que_sirve": "Ansiedad aguda, insomnio, espasmos musculares, trastorno de pánico, convulsiones, sedación preoperatoria"},
    {"seccion": "psiquiatria_ansiedad", "nombre": "Alprazolam", "para_que_sirve": "Trastorno de pánico, ansiedad generalizada, ansiedad aguda, agorafobia"},
    {"seccion": "psiquiatria_ansiedad", "nombre": "Diazepam", "para_que_sirve": "Ansiedad, espasmos musculares, convulsiones, insomnio, síndrome de abstinencia alcohólica, sedación"},
    {"seccion": "psiquiatria_ansiedad", "nombre": "Clonazepam", "para_que_sirve": "Trastorno de pánico, epilepsia, convulsiones, espasmos musculares, insomnio, ansiedad severa"},
    
    # PSIQUIATRÍA - Estabilizadores del ánimo
    {"seccion": "psiquiatria_estabilizadores", "nombre": "Litio carbónico", "para_que_sirve": "Trastorno bipolar (manía aguda y prevención de recaídas), depresión bipolar, potenciación de antidepresivos"},
    {"seccion": "psiquiatria_estabilizadores", "nombre": "Valproato/Ácido valproico", "para_que_sirve": "Trastorno bipolar, episodios maníacos, epilepsia, migraña, agitación en demencia"},
    {"seccion": "psiquiatria_estabilizadores", "nombre": "Lamotrigina", "para_que_sirve": "Bipolaridad (depresión bipolar), epilepsia, mantenimiento de eutimia, trastorno bipolar resistente"},
    {"seccion": "psiquiatria_estabilizadores", "nombre": "Carbamazepina", "para_que_sirve": "Trastorno bipolar, epilepsia, dolor neuropático, abstinencia alcohólica, manía aguda"},
    {"seccion": "psiquiatria_estabilizadores", "nombre": "Levetiracetam", "para_que_sirve": "Epilepsia, agitación, comportamiento agresivo, trastorno ansioso"},
    
    # PSIQUIATRÍA - Antipsicóticos
    {"seccion": "psiquiatria_antipsicoticos", "nombre": "Quetiapina", "para_que_sirve": "Psicosis, esquizofrenia, trastorno bipolar, depresión resistente, insomnio, agitación en demencia"},
    {"seccion": "psiquiatria_antipsicoticos", "nombre": "Risperidona", "para_que_sirve": "Psicosis, esquizofrenia, manía bipolar, comportamiento disruptivo, agresividad, esquizofrenia negativa"},
    {"seccion": "psiquiatria_antipsicoticos", "nombre": "Olanzapina", "para_que_sirve": "Psicosis, esquizofrenia, trastorno bipolar (manía), depresión bipolar, agitación severa"},
    {"seccion": "psiquiatria_antipsicoticos", "nombre": "Aripiprazol", "para_que_sirve": "Esquizofrenia, manía bipolar, depresión bipolar, irritabilidad en autismo, depresión resistente"},
    {"seccion": "psiquiatria_antipsicoticos", "nombre": "Amisulprida", "para_que_sirve": "Esquizofrenia, psicosis, depresión negativa, apatía en trastornos psiquiátricos"},
    {"seccion": "psiquiatria_antipsicoticos", "nombre": "Paliperidona", "para_que_sirve": "Esquizofrenia, psicosis, trastorno esquizoafectivo, prevención de recaídas psicóticas"},
    {"seccion": "psiquiatria_antipsicoticos", "nombre": "Clozapina", "para_que_sirve": "Esquizofrenia resistente a tratamiento, psicosis resistente, riesgo suicida en esquizofrenia"},
    
    # METABOLISMO - Diabetes
    {"seccion": "metabolico_diabetes", "nombre": "Metformina", "para_que_sirve": "Diabetes tipo 2, prediabetes, resistencia a la insulina, síndrome de ovario poliquístico (SOP), prevención de diabetes"},
    {"seccion": "metabolico_diabetes", "nombre": "Metformina XR", "para_que_sirve": "Diabetes tipo 2 (liberación prolongada), mejor tolerancia gastrointestinal, control glucémico sostenido"},
    {"seccion": "metabolico_diabetes", "nombre": "Gliclazida", "para_que_sirve": "Diabetes tipo 2, estimulante de insulina, control glucémico, hiperglucemia"},
    {"seccion": "metabolico_diabetes", "nombre": "Glibenclamida", "para_que_sirve": "Diabetes tipo 2, control rápido de glucosa, sulfonilureas clásicas"},
    {"seccion": "metabolico_diabetes", "nombre": "Glipizida", "para_que_sirve": "Diabetes tipo 2, hiperglucemia, estimulación de células beta pancreáticas"},
    {"seccion": "metabolico_diabetes", "nombre": "Empagliflozina", "para_que_sirve": "Diabetes tipo 2, protección cardiovascular, reducción de peso, insuficiencia cardiaca"},
    {"seccion": "metabolico_diabetes", "nombre": "Dapagliflozina", "para_que_sirve": "Diabetes tipo 2, insuficiencia cardiaca, nefropatía diabética, protección renal"},
    {"seccion": "metabolico_diabetes", "nombre": "Canagliflozina", "para_que_sirve": "Diabetes tipo 2, protección renal, reducción de eventos cardiovasculares, pérdida de peso"},
    {"seccion": "metabolico_diabetes", "nombre": "Sitagliptina", "para_que_sirve": "Diabetes tipo 2, control glucémico, inhibidor de DPP-4, buena tolerancia"},
    {"seccion": "metabolico_diabetes", "nombre": "Saxagliptina", "para_que_sirve": "Diabetes tipo 2, inhibidor de DPP-4, control de glucosa postprandial"},
    {"seccion": "metabolico_diabetes", "nombre": "Linagliptina", "para_que_sirve": "Diabetes tipo 2, inhibidor de DPP-4, sin ajuste renal, buena tolerancia"},
    {"seccion": "metabolico_diabetes", "nombre": "Pioglitazona", "para_que_sirve": "Diabetes tipo 2, resistencia a la insulina, sensibilización a insulina, disminución de visceral"},
    {"seccion": "metabolico_diabetes", "nombre": "Rosiglitazona", "para_que_sirve": "Diabetes tipo 2, mejora de sensibilidad insulínica, control glucémico a largo plazo"},
    {"seccion": "metabolico_diabetes", "nombre": "Repaglinida", "para_que_sirve": "Diabetes tipo 2, metiglinida, control rápido de glucosa postprandial"},
    {"seccion": "metabolico_diabetes", "nombre": "Nateglinida", "para_que_sirve": "Diabetes tipo 2, metiglinida de acción rápida, glucosa postprandial"},
    {"seccion": "metabolico_diabetes", "nombre": "Acarbosa", "para_que_sirve": "Diabetes tipo 2, inhibidor de alfa-glucosidasa, reducción de glucosa postprandial"},
    {"seccion": "metabolico_diabetes", "nombre": "Miglitol", "para_que_sirve": "Diabetes tipo 2, inhibidor de alfaglucosidasa, síntomas de hiperglucemia"},
    {"seccion": "metabolico_diabetes", "nombre": "Insulina glargina", "para_que_sirve": "Diabetes tipo 1 y 2, control basal de glucosa, insulina de larga duración"},
    {"seccion": "metabolico_diabetes", "nombre": "Insulina detemir", "para_que_sirve": "Diabetes tipo 1 y 2, insulina basal de acción prolongada, insulina de depósito"},
    {"seccion": "metabolico_diabetes", "nombre": "Insulina NPH", "para_que_sirve": "Diabetes tipo 1 y 2, insulina de acción intermedia, control de glucosa"},
    {"seccion": "metabolico_diabetes", "nombre": "Insulina cristalina", "para_que_sirve": "Diabetes tipo 1 y 2, insulina rápida, control agudo de glucosa"},
    
    # METABOLISMO - Obesidad y pérdida de peso
    {"seccion": "metabolico_obesidad", "nombre": "Semaglutida", "para_que_sirve": "Obesidad, diabetes tipo 2, pérdida de peso acelerada, agente agonista GLP-1, protección cardiovascular"},
    {"seccion": "metabolico_obesidad", "nombre": "Liraglutida", "para_que_sirve": "Obesidad, diabetes tipo 2, pérdida de peso, neuropatía diabética, prevención cardiovascular"},
    {"seccion": "metabolico_obesidad", "nombre": "Tirzepatida", "para_que_sirve": "Obesidad, diabetes tipo 2, pérdida de peso acelerada, agonista dual GLP-1/GIP"},
    {"seccion": "metabolico_obesidad", "nombre": "Orlistat", "para_que_sirve": "Obesidad, inhibidor de lípasas pancreáticas, prevención de absorción de grasas, pérdida de peso"},
    {"seccion": "metabolico_obesidad", "nombre": "Fentermina", "para_que_sirve": "Obesidad severa, supresor del apetito, estimulante simpaticomimético, pérdida de peso acelerada"},
    {"seccion": "metabolico_obesidad", "nombre": "Naltrexona/Bupropión", "para_que_sirve": "Obesidad crónica, supresión del apetito, melanocortina y noradrenalina, pérdida de peso sostenida"},
    
    # ENDOCRINOLOGÍA - Tiroides
    {"seccion": "endocrino_tiroides", "nombre": "Levotiroxina", "para_que_sirve": "Hipotiroidismo, tiroiditis, cáncer de tiroides (supresión), mixedema, hormona tiroidea sintética"},
    {"seccion": "endocrino_tiroides", "nombre": "Liothyronina", "para_que_sirve": "Hipotiroidismo severo, mixedema, hormona tiroidea T3 pura, depresión refractaria"},
    {"seccion": "endocrino_tiroides", "nombre": "Liotrix", "para_que_sirve": "Hipotiroidismo, combinación T4/T3, hipotiroidismo refractario, mixedema severo"},
    {"seccion": "endocrino_tiroides", "nombre": "Tiamazol", "para_que_sirve": "Hipertiroidismo, enfermedad de Graves, tirotoxicosis, preparación para tiroidectomía"},
    {"seccion": "endocrino_tiroides", "nombre": "Propiltiouracilo (PTU)", "para_que_sirve": "Hipertiroidismo, crisis tiroidea, embarazo con tirotoxicosis, inhibidor de peroxidasa tiroidea"},
    {"seccion": "endocrino_tiroides", "nombre": "Yodo molecular", "para_que_sirve": "Hipertiroidismo agudo, preparación preoperatoria, crisis tiroidea, inhibidor de liberación tiroidea"},
    
    # ENDOCRINOLOGÍA - Esteroides y hormonas
    {"seccion": "endocrino_hormonas", "nombre": "Dexametasona", "para_que_sirve": "Inflamación severa, shock séptico, edema cerebral, supresión de ACTH, antiinflamatorio potente"},
    {"seccion": "endocrino_hormonas", "nombre": "Prednisona", "para_que_sirve": "Inflamación, autoinmunidad, EPOC, asma, insuficiencia adrenal, antiinflamatorio sistémico"},
    {"seccion": "endocrino_hormonas", "nombre": "Metilprednisolona", "para_que_sirve": "Inflamación severa, shock anafiláctico, esclerosis múltiple, artritis reumatoide"},
    {"seccion": "endocrino_hormonas", "nombre": "Hidrocortisona", "para_que_sirve": "Insuficiencia adrenal, shock séptico, inflamación severa, glucocorticoide natural"},
    
    # CARDIOVASCULAR - IECAs
    {"seccion": "cardiovascular_iecas", "nombre": "Enalapril", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, infarto de miocardio, nefropatía diabética, protección cardio-renal"},
    {"seccion": "cardiovascular_iecas", "nombre": "Lisinopril", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, infarto agudo de miocardio, protección renal"},
    {"seccion": "cardiovascular_iecas", "nombre": "Ramipril", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, prevención de eventos cardiovasculares, nefropatía"},
    {"seccion": "cardiovascular_iecas", "nombre": "Perindopril", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, prevención de infarto, cardioprotección"},
    {"seccion": "cardiovascular_iecas", "nombre": "Quinapril", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, protección vascular"},
    
    # CARDIOVASCULAR - ARBs (Antagonistas de Receptores de Angiotensina)
    {"seccion": "cardiovascular_arbs", "nombre": "Losartan", "para_que_sirve": "Hipertensión, protección renal, insuficiencia cardiaca, prevención de ictus, nefropatía diabética"},
    {"seccion": "cardiovascular_arbs", "nombre": "Valsartan", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, infarto de miocardio, protección ventricular"},
    {"seccion": "cardiovascular_arbs", "nombre": "Irbesartan", "para_que_sirve": "Hipertensión, protección renal, nefropatía diabética, insuficiencia cardiaca"},
    {"seccion": "cardiovascular_arbs", "nombre": "Olmesartan", "para_que_sirve": "Hipertensión, protección cardiovascular, prevención de ictus"},
    {"seccion": "cardiovascular_arbs", "nombre": "Candesartan", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, protección cardio-renal, prevención de arritmias"},
    
    # CARDIOVASCULAR - Calcio-antagonistas
    {"seccion": "cardiovascular_calcio", "nombre": "Amlodipino", "para_que_sirve": "Hipertensión, angina de pecho, cardioprotección, dilatador vascular"},
    {"seccion": "cardiovascular_calcio", "nombre": "Nifedipino", "para_que_sirve": "Hipertensión severa, angina, preeclampsia, crisis hipertensivas"},
    {"seccion": "cardiovascular_calcio", "nombre": "Diltiazem", "para_que_sirve": "Hipertensión, angina, arritmias supraventriculares, fibrilación auricular"},
    {"seccion": "cardiovascular_calcio", "nombre": "Verapamilo", "para_que_sirve": "Hipertensión, angina, arritmias, fibrilación auricular, taquicardia paroxística"},
    
    # CARDIOVASCULAR - Beta-bloqueantes
    {"seccion": "cardiovascular_beta", "nombre": "Bisoprolol", "para_que_sirve": "Hipertensión, insuficiencia cardiaca, angina, postinfarto, taquicardia, control de frecuencia"},
    {"seccion": "cardiovascular_beta", "nombre": "Metoprolol", "para_que_sirve": "Hipertensión, angina, infarto de miocardio, insuficiencia cardiaca, migraña"},
    {"seccion": "cardiovascular_beta", "nombre": "Atenolol", "para_que_sirve": "Hipertensión, angina, postinfarto, ansiedad, temblor esencial"},
    {"seccion": "cardiovascular_beta", "nombre": "Propranolol", "para_que_sirve": "Hipertensión, angina, arritmias, migraña, ansiedad, tremor, hipertiroidismo"},
    {"seccion": "cardiovascular_beta", "nombre": "Carvedilol", "para_que_sirve": "Insuficiencia cardiaca, hipertensión, infarto de miocardio, betabloqueante con vasodilatación"},
    
    # CARDIOVASCULAR - Estatinas y lípidos
    {"seccion": "cardiovascular_lipidos", "nombre": "Atorvastatina", "para_que_sirve": "Hipercolesterolemia, prevención de infarto, prevención de ictus, dislipidemia, cardioprotección"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Simvastatina", "para_que_sirve": "Hipercolesterolemia, prevención cardiovascular, reducción de triglicéridos"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Lovastatina", "para_que_sirve": "Hipercolesterolemia, prevención de enfermedad cardiovascular, dislipidemia"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Pravastatina", "para_que_sirve": "Hipercolesterolemia, prevención de eventos coronarios, reducción de LDL"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Rosuvastatina", "para_que_sirve": "Hipercolesterolemia severa, prevención cardiovascular agresiva, LDL refractaria"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Pitavastatina", "para_que_sirve": "Hipercolesterolemia, prevención cardiovascular, perfil lipídico mejorado"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Ezetimiba", "para_que_sirve": "Hipercolesterolemia, colesterol dietario, disminución de LDL, absorción intestinal"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Fenofibrato", "para_que_sirve": "Hipertrigliceridemia, dislipidemia mixta, niveles altos de triglicéridos"},
    {"seccion": "cardiovascular_lipidos", "nombre": "Gemfibrozilo", "para_que_sirve": "Hipertrigliceridemia, dislipidemia, prevención de eventos cardiovasculares"},
    
    # CARDIOVASCULAR - Otros
    {"seccion": "cardiovascular_otros", "nombre": "Aspirina", "para_que_sirve": "Prevención de infarto, prevención de ictus, analgesia, antiinflamación, antiagregación plaquetaria"},
    {"seccion": "cardiovascular_otros", "nombre": "Clopidogrel", "para_que_sirve": "Síndrome coronario agudo, postangioplastia, prevención de trombosis, antiagregante"},
    {"seccion": "cardiovascular_otros", "nombre": "Ticagrelor", "para_que_sirve": "Síndrome coronario agudo, postinfarto, prevención de trombosis, inhibidor P2Y12 potente"},
    {"seccion": "cardiovascular_otros", "nombre": "Warfarina", "para_que_sirve": "Fibrilación auricular, tromboembolismo, prótesis valvular, anticoagulante oral"},
    {"seccion": "cardiovascular_otros", "nombre": "Dabigatrán", "para_que_sirve": "Fibrilación auricular, tromboembolismo, anticoagulante directo, DOAC"},
    {"seccion": "cardiovascular_otros", "nombre": "Apixabán", "para_que_sirve": "Fibrilación auricular, prevención de ictus, tromboembolismo, anticoagulante directo"},
    {"seccion": "cardiovascular_otros", "nombre": "Rivaroxabán", "para_que_sirve": "Fibrilación auricular, tromboembolismo, infarto de miocardio, anticoagulante Factor Xa"},
    {"seccion": "cardiovascular_otros", "nombre": "Enoxaparina", "para_que_sirve": "Tromboembolismo venoso, síndrome coronario agudo, profilaxis quirúrgica, anticoagulante de bajo peso molecular"},
    {"seccion": "cardiovascular_otros", "nombre": "Heparina", "para_que_sirve": "Tromboembolismo agudo, síndrome coronario, anticoagulante agudo potente"},
    {"seccion": "cardiovascular_otros", "nombre": "Digoxina", "para_que_sirve": "Insuficiencia cardiaca, fibrilación auricular, control de frecuencia, inotropo"},
    
    # DIGESTIVO - Protectores gástricos
    {"seccion": "digestivo_gastricos", "nombre": "Omeprazol", "para_que_sirve": "Reflujo gastroesofágico, gastritis, úlcera péptica, Zollinger-Ellison, inhibidor de bomba de protones"},
    {"seccion": "digestivo_gastricos", "nombre": "Pantoprazol", "para_que_sirve": "Reflujo severo, proteción gástrica, gastritis erosiva, úlcera, inhibidor de protones potente"},
    {"seccion": "digestivo_gastricos", "nombre": "Esomeprazol", "para_que_sirve": "Reflujo resistente, úlcera péptica, gastroprotección en AINEs, isómero S del omeprazol"},
    {"seccion": "digestivo_gastricos", "nombre": "Lansoprazol", "para_que_sirve": "Reflujo, úlcera gástrica, gastroprotección, inhibidor de protones"},
    {"seccion": "digestivo_gastricos", "nombre": "Rabeprazol", "para_que_sirve": "Reflujo severo, úlcera duodenal, protección gástrica"},
    {"seccion": "digestivo_gastricos", "nombre": "Famotidina", "para_que_sirve": "Reflujo, úlcera péptica, gastroprotección, antagonista H2"},
    {"seccion": "digestivo_gastricos", "nombre": "Ranitidina", "para_que_sirve": "Reflujo, úlcera gástrica, protección gástrica, antagonista histaminérgico"},
    
    # DIGESTIVO - Antidiarreicos y motilidad
    {"seccion": "digestivo_motilidad", "nombre": "Loperamida", "para_que_sirve": "Diarrea aguda, diarrea crónica, síndrome del intestino irritable, antidiarreico opiáceo"},
    {"seccion": "digestivo_motilidad", "nombre": "Bismuto subsalicilato", "para_que_sirve": "Diarrea leve, gastroenteritis, protección gástrica, antidiarreico"},
    {"seccion": "digestivo_motilidad", "nombre": "Psyllium", "para_que_sirve": "Estreñimiento, diarrea, regulación intestinal, fibra soluble"},
    {"seccion": "digestivo_motilidad", "nombre": "Docusato", "para_que_sirve": "Estreñimiento, ablandador de heces, prevención de pujos en hemorroides"},
    {"seccion": "digestivo_motilidad", "nombre": "Lactulosa", "para_que_sirve": "Estreñimiento, encefalopatía hepática, regulador osmótico"},
    {"seccion": "digestivo_motilidad", "nombre": "Polietilenglicol (PEG)", "para_que_sirve": "Estreñimiento, preparación para colonoscopia, vaciamiento intestinal"},
    
    # DIGESTIVO - IBD (Enfermedad Inflamatoria Intestinal)
    {"seccion": "digestivo_ibu", "nombre": "Mesalazina", "para_que_sirve": "Colitis ulcerosa, Crohn leve-moderada, mantenimiento de remisión, aminosalicilato"},
    {"seccion": "digestivo_ibu", "nombre": "Sulfasalazina", "para_que_sirve": "Colitis ulcerosa, Crohn, artritis reumatoide, antiinflamatorio intestinal"},
    {"seccion": "digestivo_ibu", "nombre": "Budesonida", "para_que_sirve": "Crohn, colitis, inflamación intestinal leve-moderada, corticoide local"},
    {"seccion": "digestivo_ibu", "nombre": "Azatioprina", "para_que_sirve": "Crohn, colitis ulcerosa, inmunosupresión en IBD, mantenimiento de remisión"},
    {"seccion": "digestivo_ibu", "nombre": "Infliximab", "para_que_sirve": "Crohn moderada-severa, colitis ulcerosa, artritis reumatoide, anti-TNF biológico"},
    
    # DOLOR E INFLAMACIÓN - AINEs
    {"seccion": "dolor_inflamacion_aines", "nombre": "Paracetamol", "para_que_sirve": "Dolor leve-moderado, fiebre, migraña, cefalea, analgésico selectivo COX"},
    {"seccion": "dolor_inflamacion_aines", "nombre": "Ibuprofeno", "para_que_sirve": "Dolor e inflamación, artritis, dismenorrea, fiebre, inhibidor AINE no selectivo"},
    {"seccion": "dolor_inflamacion_aines", "nombre": "Naproxeno", "para_que_sirve": "Dolor musculoesquelético, artritis, dismenorrea, inflamación crónica, AINE duradero"},
    {"seccion": "dolor_inflamacion_aines", "nombre": "Diclofenaco", "para_que_sirve": "Dolor inflamatorio severo, migraña, cólico renal, AINE potente"},
    {"seccion": "dolor_inflamacion_aines", "nombre": "Meloxicam", "para_que_sirve": "Artritis, dolor crónico, inflamación, inhibidor selectivo COX-2"},
    {"seccion": "dolor_inflamacion_aines", "nombre": "Celecoxib", "para_que_sirve": "Artritis, dolor postoperatorio, dosis baja de COX-2, inhibidor selectivo"},
    {"seccion": "dolor_inflamacion_aines", "nombre": "Piroxicam", "para_que_sirve": "Artritis reumatoide, dolor crónico, inflamación, AINE de acción prolongada"},
    {"seccion": "dolor_inflamacion_aines", "nombre": "Indometacina", "para_que_sirve": "Migraña, cefalea, dolor neuropático, corticosteroides-resistencia"},
    
    # DOLOR - Opioides
    {"seccion": "dolor_opioides", "nombre": "Tramadol", "para_que_sirve": "Dolor moderado-severo, dolor postoperatorio, dolor crónico, opioide débil + IRNS"},
    {"seccion": "dolor_opioides", "nombre": "Codeína", "para_que_sirve": "Dolor leve-moderado, tos, opioide débil, combinado usualmente"},
    {"seccion": "dolor_opioides", "nombre": "Morfina", "para_que_sirve": "Dolor severo, dolor oncológico, infarto agudo, opioide potente"},
    {"seccion": "dolor_opioides", "nombre": "Fentanilo", "para_que_sirve": "Dolor severo, postoperatorio, dolor crónico terminal, opioide muy potente"},
    {"seccion": "dolor_opioides", "nombre": "Oxicodona", "para_que_sirve": "Dolor severo crónico, cáncer, trauma, opioide de potencia media-alta"},
    
    # SUEÑO
    {"seccion": "sueno", "nombre": "Melatonina", "para_que_sirve": "Trastornos del ritmo sueño-vigilia, jet lag, insomnio leve, regulador circadiano"},
    {"seccion": "sueno", "nombre": "Trazodona (uso en sueño)", "para_que_sirve": "Insomnio comórbido con depresión/ansiedad, insomnio crónico, sedación sin dependencia"},
    {"seccion": "sueno", "nombre": "Zolpidem", "para_que_sirve": "Insomnio de mantenimiento, insomnio agudo, hipnótico no benzodiazepina"},
    {"seccion": "sueno", "nombre": "Zaleplon", "para_que_sirve": "Insomnio de inicio, hipnótico de acción rápida y corta, fármaco no benzodiacepina"},
    {"seccion": "sueno", "nombre": "Eszopiclona", "para_que_sirve": "Insomnio crónico, mantenimiento de sueño, hipnótico no benzodiazepina"},
    {"seccion": "sueno", "nombre": "Flunitrazepam", "para_que_sirve": "Insomnio severo, benzodiazepina de acción prolongada, insomnio resistente"},
    
    # NEUROLOGÍA
    {"seccion": "neurologia", "nombre": "Levodopa/Carbidopa", "para_que_sirve": "Parkinson, síntomas motores parkinsonianos, rigidez, temblor, bradicinesia"},
    {"seccion": "neurologia", "nombre": "Bromocriptina", "para_que_sirve": "Parkinson, hiperprolactinemia, agonista dopaminérgico"},
    {"seccion": "neurologia", "nombre": "Pramipexol", "para_que_sirve": "Parkinson, síndrome de piernas inquietas, agonista dopaminérgico"},
    {"seccion": "neurologia", "nombre": "Ropinirol", "para_que_sirve": "Parkinson, síndrome de piernas inquietas, agonista D2/D3"},
    {"seccion": "neurologia", "nombre": "Biperideno", "para_que_sirve": "Parkinson, distonía, temblor, anticolinérgico"},
    {"seccion": "neurologia", "nombre": "Selegilina", "para_que_sirve": "Parkinson leve, neuroprotección, inhibidor MAO-B selectivo"},
    {"seccion": "neurologia", "nombre": "Entacapona", "para_que_sirve": "Parkinson avanzado, complicaciones motoras, inhibidor COMT"},
    
    # NEURODEGENERACIÓN
    {"seccion": "neurologia_neuro", "nombre": "Riluzol", "para_que_sirve": "ELA (Esclerosis Lateral Amiotrófica), extensión de supervivencia, neuroprotección"},
    {"seccion": "neurologia_neuro", "nombre": "Memantina", "para_que_sirve": "Alzheimer moderado-severo, demencia, antagonista NMDA"},
    {"seccion": "neurologia_neuro", "nombre": "Donepezilo", "para_que_sirve": "Alzheimer leve-moderada, deterioro cognitivo leve, inhibidor acetilcolinesterasa"},
    
    # INFECCIONES - Antibióticos
    {"seccion": "antibioticos", "nombre": "Amoxicilina", "para_que_sirve": "Infecciones bacterianas comunes, otitis, sinusitis, amigdalitis, penicilina oral"},
    {"seccion": "antibioticos", "nombre": "Amoxicilina/Ácido clavulánico", "para_que_sirve": "Infecciones complejas, resistencia a betalactamasa, bronquitis aguda"},
    {"seccion": "antibioticos", "nombre": "Cefalexina", "para_que_sirve": "Infecciones cutáneas, urinarias, óseas, cefalosporina oral"},
    {"seccion": "antibioticos", "nombre": "Cefdoxima", "para_que_sirve": "Neumonía, infecciones del tracto urinario, cefalosporina 3ª gen"},
    {"seccion": "antibioticos", "nombre": "Azitromicina", "para_que_sirve": "Neumonía atípica, infecciones respiratorias, macrolido azálida"},
    {"seccion": "antibioticos", "nombre": "Claritromicina", "para_que_sirve": "Infecciones respiratorias, Helicobacter pylori, macrolido potente"},
    {"seccion": "antibioticos", "nombre": "Eritromicina", "para_que_sirve": "Infecciones respiratorias, acné, gastroparesia, macrolido clásico"},
    {"seccion": "antibioticos", "nombre": "Ciprofloxacino", "para_que_sirve": "Infecciones urinarias, gastrointestinales, respiratorias, fluoroquinolona"},
    {"seccion": "antibioticos", "nombre": "Levofloxacino", "para_que_sirve": "Neumonía, infecciones urinarias, prostatitis, fluoroquinolona potente"},
    {"seccion": "antibioticos", "nombre": "Moxifloxacino", "para_que_sirve": "Neumonía comunitaria, infecciones severas, fluoroquinolona 4ª generación"},
    {"seccion": "antibioticos", "nombre": "Trimetoprima/Sulfametoxazol", "para_que_sirve": "Infecciones urinarias, neumonía PCP, Shigella, sulfonamida"},
    {"seccion": "antibioticos", "nombre": "Nitrofurantoína", "para_que_sirve": "Infecciones urinarias sin complicaciones, E. coli, bacilo gram negativo"},
    
    # ANTIFÚNGICOS
    {"seccion": "antifungicos", "nombre": "Fluconazol", "para_que_sirve": "Candidiasis oral y genital, meningitis criptocócica, triazol sistémico"},
    {"seccion": "antifungicos", "nombre": "Itraconazol", "para_que_sirve": "Candidosis sistémica, aspergillosis, blastomicosis, triazol lipófilo"},
    {"seccion": "antifungicos", "nombre": "Voriconazol", "para_que_sirve": "Aspergillosis invasiva, candidiasis severa, triazol de espectro amplio"},
    {"seccion": "antifungicos", "nombre": "Ketoconazol", "para_que_sirve": "Candidosis cutánea, infecciones fúngicas superficiales, imidazol tópico"},
    {"seccion": "antifungicos", "nombre": "Clotrimazol", "para_que_sirve": "Candidiasis oral, vaginal, dermatofitosis, imidazol local"},
    {"seccion": "antifungicos", "nombre": "Miconazol", "para_que_sirve": "Candidiasis vaginal, oral, dermatofitosis, imidazol tópico potente"},
    {"seccion": "antifungicos", "nombre": "Anfotericina B", "para_que_sirve": "Infecciones fúngicas sistémicas severas, polienos, anfifilina"},
    
    # ANTIVIRALES
    {"seccion": "antivirales", "nombre": "Aciclovir", "para_que_sirve": "Herpes simple, varicela, zóster, VHS, antiviral nucleósido"},
    {"seccion": "antivirales", "nombre": "Valaciclovir", "para_que_sirve": "Herpes labial, zóster, VHS, profármaco de aciclovir biodisponibilidad mejorada"},
    {"seccion": "antivirales", "nombre": "Famciclovir", "para_que_sirve": "Herpes zóster, herpes simple, varicela, prodrug guanosina"},
    
    # RESPIRATORIO - Asma y EPOC
    {"seccion": "respiratorio_asma", "nombre": "Salbutamol", "para_que_sirve": "Asma aguda, broncoespasmo, EPOC, beta-2 agonista inhalado de acción rápida"},
    {"seccion": "respiratorio_asma", "nombre": "Terbutalina", "para_que_sirve": "Asma, broncoespasmo, beta-2 agonista de acción rápida"},
    {"seccion": "respiratorio_asma", "nombre": "Salmeterol", "para_que_sirve": "Asma crónica, EPOC, beta-2 agonista de larga duración"},
    {"seccion": "respiratorio_asma", "nombre": "Formoterol", "para_que_sirve": "Asma persistente, EPOC, beta-2 agonista de acción prolongada"},
    {"seccion": "respiratorio_asma", "nombre": "Beclometasona", "para_que_sirve": "Asma persistente, inflamación de vías aéreas, corticoide inhalado"},
    {"seccion": "respiratorio_asma", "nombre": "Fluticasona", "para_que_sirve": "Asma crónica, rinitis alérgica, corticoide inhalado potente"},
    {"seccion": "respiratorio_asma", "nombre": "Budesonida inhalada", "para_que_sirve": "Asma, EPOC, inflamación respiratoria, corticoide inhalado"},
    {"seccion": "respiratorio_asma", "nombre": "Teofilina", "para_que_sirve": "Asma, EPOC, bronquitis crónica, xantina broncodilatadora"},
    {"seccion": "respiratorio_asma", "nombre": "Ipratropio", "para_que_sirve": "EPOC, asma, anticólinergico inhalado"},
    {"seccion": "respiratorio_asma", "nombre": "Tiotropio", "para_que_sirve": "EPOC, mantenimiento, anticólinergico de larga duración"},
    {"seccion": "respiratorio_asma", "nombre": "Montelukast", "para_que_sirve": "Asma alérgica, rinitis alérgica, antagonista de leucotrienos"},
    {"seccion": "respiratorio_asma", "nombre": "Zafirlukast", "para_que_sirve": "Asma persistente moderada, antagonista de leucotrienos"},
    
    # ALERGIAS
    {"seccion": "alergias", "nombre": "Loratadina", "para_que_sirve": "Rinitis alérgica, urticaria, alergia estacional, antihistamínico H1 no sedante"},
    {"seccion": "alergias", "nombre": "Cetirizina", "para_que_sirve": "Alergia, rinitis alérgica, urticaria, antihistamínico H1 selectivo"},
    {"seccion": "alergias", "nombre": "Fexofenadina", "para_que_sirve": "Rinitis alérgica, urticaria, alergia no sedante, antihistamínico potente"},
    {"seccion": "alergias", "nombre": "Desloratadina", "para_que_sirve": "Alergia estacional, urticaria crónica, antihistamínico H1 selectivo"},
    {"seccion": "alergias", "nombre": "Difenhidramina", "para_que_sirve": "Alergia aguda, reacciones anafilácticas, insomnio, antihistamínico sedante"},
    
    # REUMATOLOGÍA
    {"seccion": "reumatologia", "nombre": "Metotrexato", "para_que_sirve": "Artritis reumatoide, psoriasis, cáncer, inmunosupresor"},
    {"seccion": "reumatologia", "nombre": "Sulfasalazina (uso reumatológico)", "para_que_sirve": "Artritis reumatoide, colitis ulcerosa, enfermedad de Crohn, DMARD"},
    {"seccion": "reumatologia", "nombre": "Leflunomida", "para_que_sirve": "Artritis reumatoide, inhibidor de dihidrofolato reductasa"},
    {"seccion": "reumatologia", "nombre": "Tocilizumab", "para_que_sirve": "Artritis reumatoide severa, inhibidor IL-6 biológico"},
    {"seccion": "reumatologia", "nombre": "Adalimumab", "para_que_sirve": "Artritis reumatoide, Crohn, psoriasis, anti-TNF monoclonal"},
    
    # DERMATOLOGÍA
    {"seccion": "dermatologia", "nombre": "Tretinoína", "para_que_sirve": "Acné, cicatrices de acné, envejecimiento cutáneo, retinoides derivado"},
    {"seccion": "dermatologia", "nombre": "Adapaleno", "para_que_sirve": "Acné leve-moderado, fotoaging, retinoides de tercera generación"},
    {"seccion": "dermatologia", "nombre": "Isotretinoína", "para_que_sirve": "Acné severo resistente, acné conglobata, retinoides sistémica potente"},
    {"seccion": "dermatologia", "nombre": "Benzoilo peróxido", "para_que_sirve": "Acné leve-moderado, bactericida, peróxido antimicrobiano"},
    
    # REPRODUCCIÓN
    {"seccion": "reproduccion", "nombre": "Metformina (uso en SOP)", "para_que_sirve": "SOP, infertilidad, insulino-resistencia, diabetes tipo 2"},
    {"seccion": "reproduccion", "nombre": "Letrozol", "para_que_sirve": "Infertilidad PCOS, inducción de ovulación, inhibidor de aromatasa"},
    {"seccion": "reproduccion", "nombre": "Clomifeno", "para_que_sirve": "Infertilidad, anovulación, inducción de ovulación, modulador estrogénico"},
    {"seccion": "reproduccion", "nombre": "Progesterona natural", "para_que_sirve": "Apoyo lúteo, ciclo menstrual, menopausia, hormona reproduc"},
    
    # ONCOLOGÍA - Soporte
    {"seccion": "oncologia_soporte", "nombre": "Ondansetrón", "para_que_sirve": "Náuseas por quimioterapia, postoperatorio, antagonista 5-HT3"},
    {"seccion": "oncologia_soporte", "nombre": "Granisetrón", "para_que_sirve": "Vómitos inducidos por quimio, postoperatorio, antagonista 5-HT3 potente"},
    {"seccion": "oncologia_soporte", "nombre": "Dexametasona (soporte oncológico)", "para_que_sirve": "Náuseas por quimio, edema cerebral, corticoide potente antiemética"},
    {"seccion": "oncologia_soporte", "nombre": "Analgésicos opiáceos", "para_que_sirve": "Dolor oncológico, cáncer avanzado, paliación, opioides potentes"},
]

# Configuracion basica de logs para desarrollo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Se importan los modelos para que SQLAlchemy registre su metadata en arranque.
_ = (
    Rol,
    Usuario,
    PerfilSalud,
    RegistroDiario,
    Derivacion,
    HabitoAgenda,
    EvaluacionIA,
    MensajeChat,
    MedicacionAsignada,
    PlanNutricionalClinico,
    ProtocoloHospitalario,
    ChecklistClinicoPaciente,
    ChecklistClinicoHistorial,
    RecursoClinico,
    PlanIA,
)

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
        _asegurar_columna_cambio_contrasena()
        _asegurar_columna_activos_premium_chat()
        _asegurar_columnas_conversaciones_chat()
        _asegurar_columnas_perfil_plan_diario()
        with Session(bind=engine) as db:
            _asegurar_roles_base(db)
            _asegurar_profesionales_demo(db)
            _asegurar_pacientes_demo(db)
            _asegurar_protocolos_hospitalarios_base(db)
            _asegurar_recursos_clinicos_base(db)
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


class PerfilMetricasIMCRequest(BaseModel):
    """Payload minimo para actualizar IMC con peso y altura."""

    peso: float = Field(..., gt=30, le=400, description="Peso en kg")
    altura: int = Field(..., gt=100, le=250, description="Altura en cm")


class PerfilMetricasIMCResponse(BaseModel):
    """Respuesta de actualizacion rapida de IMC."""

    usuario_id: int
    peso_actual: float
    altura_cm: int
    imc_calculado: float
    imc_rango: str
    ultima_actualizacion_metricas: Optional[str] = None
    actualizacion_permitida_hoy: bool = False
    mensaje: str


class PerfilResumenResponse(BaseModel):
    """Resumen persistido del perfil de salud para hidratar frontend."""

    usuario_id: int
    peso_actual: Optional[float] = None
    altura_cm: Optional[int] = None
    imc_actual: Optional[float] = None
    imc_rango: Optional[str] = None
    objetivo_principal: str = "perder_grasa"
    deslices_hoy: List[str] = Field(default_factory=list)
    restricciones_alimentarias: List[str] = Field(default_factory=list)
    ultima_actualizacion_metricas: Optional[str] = None


class PerfilPlanDiarioUpdateRequest(BaseModel):
    """Persistencia del plan diario inteligente del usuario."""

    objetivo_principal: Optional[str] = Field(default=None, min_length=3, max_length=40)
    deslices_hoy: Optional[List[str]] = Field(default=None)
    restricciones_alimentarias: Optional[List[str]] = Field(default=None)

    @field_validator("objetivo_principal")
    @classmethod
    def validar_objetivo_principal(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        objetivo = value.strip().lower()
        permitidos = {"perder_grasa", "mantener", "ganar_masa"}
        if objetivo not in permitidos:
            raise ValueError("objetivo_principal debe ser: perder_grasa, mantener o ganar_masa")
        return objetivo


class PerfilPlanDiarioResponse(BaseModel):
    """Estado persistido de plan diario personalizado por usuario."""

    usuario_id: int
    objetivo_principal: str
    deslices_hoy: List[str] = Field(default_factory=list)
    restricciones_alimentarias: List[str] = Field(default_factory=list)
    fecha_deslices: str
    puede_actualizar_metricas_hoy: bool = True
    ultima_actualizacion_metricas: Optional[str] = None


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
    adjuntos: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Imágenes, videos o PDF codificados en base64 para análisis multimodal",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Proveedor opcional por solicitud: gemini o qwen",
    )
    model: Optional[str] = Field(
        default=None,
        description="Modelo opcional por solicitud para el proveedor seleccionado",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Identificador opcional de la conversación activa",
    )


class ChatResponse(BaseModel):
    """Respuesta del endpoint POST /chat."""

    ok: bool
    sender: str
    respuesta_ia: str
    motor_respuesta: Optional[str] = None
    peso_registrado: Optional[float] = None
    mensaje_peso: Optional[str] = None
    imc_calculado: Optional[float] = None
    imc_rango: Optional[str] = None  # "normal", "sobrepeso", "aviso"
    solicitar_altura: bool = False  # Si True, se debe pedir altura al usuario
    area_detectada: Optional[str] = None
    preguntas_precision: List[str] = Field(default_factory=list)
    plan_accion: List[str] = Field(default_factory=list)
    recursos_multimedia: List[Dict[str, str]] = Field(default_factory=list)
    activos_premium: List[Dict[str, str]] = Field(default_factory=list)
    lugar_entrenamiento: Optional[str] = None
    plan_visual_semanal: List[Dict[str, Any]] = Field(default_factory=list)
    adjuntos_recibidos: int = 0
    memoria_activa: bool = False
    memoria_tema: Optional[str] = None
    pregunta_actual: Optional[str] = None
    respuestas_memoria: Dict[str, Any] = Field(default_factory=dict)
    conversation_id: Optional[str] = None


class ChatProviderUpdateRequest(BaseModel):
    """Payload para actualizar proveedor IA en caliente."""

    provider: str = Field(..., description="gemini o qwen")


class ChatProviderResponse(BaseModel):
    """Estado del proveedor IA activo."""

    ok: bool
    provider: str
    supported_providers: List[str] = Field(default_factory=lambda: ["gemini", "qwen"])


class ChatConversationUpdateRequest(BaseModel):
    """Permite renombrar o fijar una conversación."""

    titulo: Optional[str] = Field(default=None, max_length=160)
    fijada: Optional[bool] = None


_RASA_RESPUESTAS_GENERICAS = (
    "disculpa, no entendi",
    "preguntame sobre salud",
    "como puedo ayudarte",
    "he recibido tu mensaje",
    "cuentame mas sobre ti",
    "en que puedo ayudarte",
    "hablemos sobre tu salud",
    "no estoy seguro de como responder", # Añade esta
    "puedes repetirlo", # Añade esta
    "no entiendo",
)

_CLAVES_IA_AVANZADA = (
    "plan",
    "dieta",
    "comida",
    "comidas",
    "menu",
    "menú",
    "desayuno",
    "almuerzo",
    "cena",
    "que como",
    "qué como",
    "rutina",
    "entren",
    "ejercicio",
    "nutric",
    "ansiedad",
    "estres",
    "atracon",
    "atracón",
    "sueno",
    "trabajo",
    "famil",
    "social",
    "alerg",
    "celiac",
    "avanzad",
    "objetivo",
    "semanal",
    "super",
    "entrenad",
    "turno",
    "productividad",
    "familia",
    "multi",
    "completo",
)

_PALABRAS_EXPERTO_DIRECTO = (
    "experto",
    "muy experto",
    "mas experto",
    "más experto",
    "mas entrenado",
    "más entrenado",
    "mucho mas entrenado",
    "mucho más entrenado",
    "super entrenado",
    "súper entrenado",
    "nivel pro",
    "modo experto",
    "modo pro",
    "ultra experto",
    "chat gpt",
    "chatgpt",
)

_PALABRAS_GENERACION_MEDIA = (
    "genera imagen",
    "genera una imagen",
    "crear imagen",
    "crea imagen",
    "generador de imagen",
    "imagen ia",
    "genera video",
    "genera un video",
    "crear video",
    "crea video",
    "video ia",
    "hazme un video",
    "hazme una imagen",
    "animacion",
)

_MEDIA_RECURSOS_BASE: Dict[str, List[Dict[str, str]]] = {
    "dieta": [
        {"tipo": "imagen", "titulo": "Plato saludable (referencia visual)", "url": "https://images.unsplash.com/photo-1490645935967-10de6ba17061"},
        {"tipo": "imagen", "titulo": "Ejemplo de meal prep semanal", "url": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c"},
        {"tipo": "video", "titulo": "Control de porciones y plato equilibrado", "url": "https://www.youtube.com/watch?v=TYeZVfPxwKM"},
        {"tipo": "video", "titulo": "Guia visual sin gluten (celiaquia)", "url": "https://www.youtube.com/watch?v=Q89qS2t1GmM"},
    ],
    "paciente_nutricion": [
        {"tipo": "guia", "titulo": "Paciente | Dietas recomendadas segun condicion", "url": "/pacientes/dietas/recomendadas"},
        {"tipo": "guia", "titulo": "Nutricion | Menu base de 7 dias (educativo)", "url": "https://www.eatright.org/food/planning-and-prep/meal-planning"},
        {"tipo": "video", "titulo": "Nutricion | Como construir un plato equilibrado", "url": "https://www.youtube.com/watch?v=TYeZVfPxwKM"},
        {"tipo": "imagen", "titulo": "Nutricion | Ejemplo visual de porciones", "url": "https://images.unsplash.com/photo-1490645935967-10de6ba17061"},
    ],
    "entrenamiento": [
        {"tipo": "imagen", "titulo": "Tecnica de sentadilla", "url": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438"},
        {"tipo": "imagen", "titulo": "Entrenamiento de fuerza en gimnasio", "url": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48"},
        {"tipo": "video", "titulo": "Rutina full body para principiantes", "url": "https://www.youtube.com/watch?v=U0bhE67HuDY"},
        {"tipo": "video", "titulo": "Movilidad y calentamiento seguro", "url": "https://www.youtube.com/watch?v=2L2lnxIcNmo"},
    ],
    "paciente_entrenamiento": [
        {"tipo": "video", "titulo": "Entrenamiento | Rutina full body para iniciar", "url": "https://www.youtube.com/watch?v=U0bhE67HuDY"},
        {"tipo": "video", "titulo": "Entrenamiento | Movilidad diaria en 10 minutos", "url": "https://www.youtube.com/watch?v=2L2lnxIcNmo"},
        {"tipo": "imagen", "titulo": "Entrenamiento | Posturas base de fuerza", "url": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438"},
        {"tipo": "guia", "titulo": "Paciente | Guia de progresion semanal simple", "url": "https://www.nhs.uk/live-well/exercise/"},
    ],
    "psicologia": [
        {"tipo": "imagen", "titulo": "Respiracion guiada (visual)", "url": "https://images.unsplash.com/photo-1506126613408-eca07ce68773"},
        {"tipo": "imagen", "titulo": "Espacio de regulacion emocional", "url": "https://images.unsplash.com/photo-1474418397713-7ede21d49118"},
        {"tipo": "video", "titulo": "Tecnica 4-7-8 para ansiedad", "url": "https://www.youtube.com/watch?v=kgTL5G1ibIo"},
        {"tipo": "video", "titulo": "Mindfulness basico en 10 minutos", "url": "https://www.youtube.com/watch?v=inpok4MKVLM"},
    ],
    "paciente_psicologia": [
        {"tipo": "video", "titulo": "Psicologia | Respiracion 4-7-8 guiada", "url": "https://www.youtube.com/watch?v=kgTL5G1ibIo"},
        {"tipo": "video", "titulo": "Psicologia | Mindfulness basico para ansiedad", "url": "https://www.youtube.com/watch?v=inpok4MKVLM"},
        {"tipo": "guia", "titulo": "Psicologia | Tecnicas de grounding 5-4-3-2-1", "url": "https://www.verywellmind.com/54321-grounding-technique-7367986"},
        {"tipo": "imagen", "titulo": "Psicologia | Espacio de calma y regulacion", "url": "https://images.unsplash.com/photo-1474418397713-7ede21d49118"},
    ],
    "especialista": [
        {"tipo": "guia", "titulo": "Catalogo clínico de dietas (API)", "url": "/profesionales/catalogos/dietas-clinicas"},
        {"tipo": "guia", "titulo": "Catalogo de ejercicios (API)", "url": "/profesionales/catalogos/ejercicios"},
        {"tipo": "guia", "titulo": "Biblioteca clínica (API)", "url": "/profesionales/biblioteca-clinica"},
        {"tipo": "guia", "titulo": "Recursos clínicos por especialidad (API)", "url": "/profesionales/recursos-clinicos"},
    ],
    "especialista_nutricion": [
        {"tipo": "guia", "titulo": "Especialista | Catalogo de dietas clinicas", "url": "/profesionales/catalogos/dietas-clinicas"},
        {"tipo": "guia", "titulo": "Especialista | Biblioteca clinica para TCA/SOP/diabetes", "url": "/profesionales/biblioteca-clinica?trastorno=tca"},
        {"tipo": "guia", "titulo": "Especialista | Recursos por especialidad nutricion", "url": "/profesionales/recursos-clinicos?especialidad=nutricionista"},
        {"tipo": "guia", "titulo": "Especialista | Checklist clinico del paciente", "url": "/profesionales/pacientes/{paciente_id}/checklist-clinico"},
    ],
    "especialista_psicologia": [
        {"tipo": "guia", "titulo": "Especialista | Recursos por especialidad psicologia", "url": "/profesionales/recursos-clinicos?especialidad=psicologo"},
        {"tipo": "guia", "titulo": "Especialista | Biblioteca clinica para ansiedad", "url": "/profesionales/biblioteca-clinica?trastorno=ansiedad"},
        {"tipo": "guia", "titulo": "Especialista | Biblioteca clinica para depresion", "url": "/profesionales/biblioteca-clinica?trastorno=depresion"},
        {"tipo": "guia", "titulo": "Especialista | Resumen clinico breve del paciente", "url": "/profesionales/pacientes/{paciente_id}/resumen-clinico-breve"},
    ],
    "especialista_entrenamiento": [
        {"tipo": "guia", "titulo": "Especialista | Catalogo de ejercicios terapeuticos", "url": "/profesionales/catalogos/ejercicios"},
        {"tipo": "guia", "titulo": "Especialista | Recursos por especialidad entrenamiento", "url": "/profesionales/recursos-clinicos?especialidad=coach"},
        {"tipo": "guia", "titulo": "Especialista | Biblioteca clinica de dolor lumbar", "url": "/profesionales/biblioteca-clinica?trastorno=dolor_lumbar"},
        {"tipo": "guia", "titulo": "Especialista | Biblioteca clinica de dolor rodilla", "url": "/profesionales/biblioteca-clinica?trastorno=dolor_rodilla"},
    ],
    "especialista_gestion": [
        {"tipo": "guia", "titulo": "Especialista | KPIs clinicos del paciente", "url": "/profesionales/pacientes/{paciente_id}/kpis"},
        {"tipo": "guia", "titulo": "Especialista | Informe hospitalario PDF", "url": "/profesionales/pacientes/{paciente_id}/informe-hospitalario-pdf"},
        {"tipo": "guia", "titulo": "Especialista | Gestion de medicacion", "url": "/profesionales/pacientes/{paciente_id}/medicacion"},
        {"tipo": "guia", "titulo": "Especialista | Severidad sugerida con IA", "url": "/profesionales/pacientes/{paciente_id}/severidad-sugerida"},
    ],
    "general": [
        {"tipo": "guia", "titulo": "Biblioteca de recursos clinicos", "url": "/profesionales/recursos-clinicos"},
        {"tipo": "guia", "titulo": "Paciente | Dietas recomendadas", "url": "/pacientes/dietas/recomendadas"},
    ],
}


def _normalizar_mensaje_chat(texto: str) -> str:
    """Limpia texto de entrada para mejorar el match de intents en RASA."""
    limpio = (texto or "").strip()
    limpio = re.sub(r"\s+", " ", limpio)
    return limpio


def _normalizar_adjuntos_chat(adjuntos: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Convierte adjuntos de chat en partes binarias listas para Gemini."""
    partes: List[Dict[str, Any]] = []
    max_bytes = max(1, int(settings.IA_ATTACHMENTS_MAX_MB)) * 1024 * 1024

    for adjunto in adjuntos or []:
        if not isinstance(adjunto, dict):
            continue

        mime_type = str(adjunto.get("mime_type") or adjunto.get("mimeType") or "").strip().lower()
        data_raw = adjunto.get("data")
        if not data_raw:
            continue

        if isinstance(data_raw, bytes):
            data_bytes = data_raw
        elif isinstance(data_raw, str):
            contenido = data_raw.strip()
            if contenido.startswith("data:") and "," in contenido:
                prefijo, contenido = contenido.split(",", 1)
                if not mime_type:
                    mime_data_url = prefijo[5:].split(";", 1)[0].strip().lower()
                    if mime_data_url:
                        mime_type = mime_data_url
            try:
                data_bytes = base64.b64decode(contenido, validate=True)
            except Exception:
                logger.warning("No se pudo decodificar un adjunto multimedia del chat")
                continue
        else:
            continue

        if not mime_type:
            mime_type = "image/jpeg"

        if not (
            mime_type.startswith("image/")
            or mime_type.startswith("video/")
            or mime_type == "application/pdf"
        ):
            logger.warning("Adjunto descartado por MIME no soportado: %s", mime_type)
            continue

        if len(data_bytes) > max_bytes:
            logger.warning(
                "Adjunto descartado por tamano (%s bytes > %s bytes maximos)",
                len(data_bytes),
                max_bytes,
            )
            continue

        partes.append({"mime_type": mime_type, "data": data_bytes})

    return partes


def _extraer_texto_pdf_adjuntos(
    adjuntos: Optional[List[Dict[str, Any]]],
    max_paginas_por_pdf: int = 12,
    max_caracteres_totales: int = 12000,
) -> str:
    """Extrae texto de PDFs adjuntos para enriquecer el análisis IA automáticamente."""
    if not adjuntos:
        return ""

    try:
        pypdf_module = importlib.import_module("pypdf")
        pdf_reader_cls = getattr(pypdf_module, "PdfReader")
    except Exception:
        logger.info("pypdf no disponible; se omite extracción automática de texto en PDF")
        return ""

    def _ocr_texto_desde_imagen_bytes(data: bytes) -> str:
        try:
            pytesseract = importlib.import_module("pytesseract")
            pil_image = importlib.import_module("PIL.Image")
            pil_ops = importlib.import_module("PIL.ImageOps")
        except Exception:
            return ""

        try:
            img = pil_image.open(BytesIO(bytes(data)))
            img.load()
            if getattr(img, "mode", "RGB") not in {"RGB", "RGBA", "L"}:
                img = img.convert("RGB")
            base = img.convert("L")
            variantes = [
                base,
                pil_ops.autocontrast(base),
                base.point(lambda px: 255 if px > 165 else 0),
                pil_ops.autocontrast(base).resize((max(1, base.width * 2), max(1, base.height * 2))),
            ]
            configuraciones = ("--oem 3 --psm 6", "--oem 3 --psm 11", "--oem 3 --psm 4")
            mejor = ""
            puntaje_mejor = 0
            for variante in variantes:
                for config in configuraciones:
                    try:
                        candidato = pytesseract.image_to_string(variante, lang="spa+eng", config=config)
                    except Exception:
                        continue
                    limpio = " ".join((candidato or "").split()).strip()
                    puntaje = sum(1 for ch in limpio if ch.isalnum())
                    if puntaje > puntaje_mejor:
                        puntaje_mejor = puntaje
                        mejor = limpio
            return mejor if puntaje_mejor >= 6 else ""
        except Exception:
            return ""

    def _extraer_texto_pdf_ocr_local(data: bytes, max_paginas: int = 6) -> str:
        try:
            fitz = importlib.import_module("fitz")
        except Exception:
            return ""

        try:
            documento = fitz.open(stream=bytes(data), filetype="pdf")
        except Exception:
            return ""

        bloques: List[str] = []
        total_local = 0
        try:
            limite_paginas = min(len(documento), max_paginas)
            for indice in range(limite_paginas):
                if total_local >= max_caracteres_totales:
                    break
                pagina = documento.load_page(indice)
                pix = pagina.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                texto_ocr = _ocr_texto_desde_imagen_bytes(pix.tobytes("png"))
                if not texto_ocr:
                    continue
                restante = max_caracteres_totales - total_local
                bloque = texto_ocr[:restante]
                bloques.append(bloque)
                total_local += len(bloque)
        finally:
            documento.close()

        return "\n\n".join(bloques).strip()

    fragmentos: List[str] = []
    total = 0

    for adjunto in adjuntos:
        if not isinstance(adjunto, dict):
            continue
        if str(adjunto.get("mime_type") or "").lower() != "application/pdf":
            continue

        data = adjunto.get("data")
        if not isinstance(data, (bytes, bytearray)) or not data:
            continue

        try:
            reader = pdf_reader_cls(BytesIO(bytes(data)))
        except Exception:
            logger.warning("No se pudo abrir un PDF adjunto para extracción automática de texto")
            continue

        paginas = reader.pages[:max_paginas_por_pdf]
        extraido_en_pdf = False
        for pagina in paginas:
            if total >= max_caracteres_totales:
                break
            try:
                texto = (pagina.extract_text() or "").strip()
            except Exception:
                texto = ""
            if not texto:
                continue

            espacio = max_caracteres_totales - total
            bloque = texto[:espacio]
            fragmentos.append(bloque)
            total += len(bloque)
            extraido_en_pdf = True

        if not extraido_en_pdf and total < max_caracteres_totales:
            texto_ocr = _extraer_texto_pdf_ocr_local(bytes(data), max_paginas=max_paginas_por_pdf)
            if texto_ocr:
                espacio = max_caracteres_totales - total
                bloque = texto_ocr[:espacio]
                fragmentos.append(bloque)
                total += len(bloque)

        if total >= max_caracteres_totales:
            break

    return "\n\n".join(fragmentos).strip()


def _es_respuesta_rasa_generica(texto: str) -> bool:
    """Detecta respuestas de baja utilidad para activar fallback de IA contextual."""
    base = (texto or "").strip().lower()
    normalizado = "".join(
        ch
        for ch in unicodedata.normalize("NFKD", base)
        if not unicodedata.combining(ch)
    )
    if not normalizado:
        return True
    return any(base in normalizado for base in _RASA_RESPUESTAS_GENERICAS)


def _normalizar_ascii(texto: str) -> str:
    """Normaliza texto para reglas de deteccion robustas sin acentos."""
    base = (texto or "").strip().lower()
    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", base)
        if not unicodedata.combining(ch)
    )


def _auto_guardar_plan_ia(
    db: Session,
    usuario_id: int,
    tipo: str,
    mensaje_usuario: str,
    respuesta: str,
    contexto: dict,
) -> None:
    """
    Detecta si la respuesta de la IA contiene un plan completo y lo persiste
    automáticamente en la tabla planes_ia.
    Más permisivo con psicología: puede guardarse con menos estructura.
    """
    indicadores = {
        "nutricion": ["kcal", "proteína", "carboh", "desayuno", "almuerzo", "cena", "macros"],
        "entrenamiento": ["series", "reps", "rpe", "ejercicio", "entrenamiento", "descanso"],
        "psicologia": ["técnica", "respiración", "mindfulness", "emoción", "tcc", "act", "emocional", "día 1", "dia 1", "semana", "ansiedad", "estres", "relaxacion", "meditacion"],
    }
    palabras_clave = indicadores.get(tipo, [])
    respuesta_lower = respuesta.lower()

    coincidencias = sum(1 for p in palabras_clave if p in respuesta_lower)
    encabezados = respuesta.count("##") + respuesta.count("###")
    tiene_tabla = "|" in respuesta and "---" in respuesta
    tiene_bloques_dias = any(k in respuesta_lower for k in ("día 1", "dia 1", "semana 1", "lunes", "martes"))
    tiene_estructura = encabezados >= 2 or tiene_tabla or tiene_bloques_dias
    longitud_respuesta = len(respuesta)
    
    # Requisitos flexibles por tipo
    es_psicologia = tipo == "psicologia"
    
    # Criterios de guardado:
    # - Nutrición: requiere 2+ palabras clave AND estructura
    # - Entrenamiento: requiere 2+ palabras clave AND estructura
    # - Psicología: requiere 1+ palabra clave Y respuesta decente (>200 chars)
    
    if es_psicologia:
        # Psicología es más flexible: puede guardarse sin estructura estricta
        if coincidencias < 1 or longitud_respuesta < 200:
            return  # No tiene suficiente contenido
    else:
        # Nutrición y entrenamiento requieren más estructura
        if coincidencias < 2 or not tiene_estructura:
            return  # No tiene estructura mínima

    duracion_dias = _detectar_duracion_plan(mensaje_usuario)
    objetivo = contexto.get("objetivo_principal") or None
    ahora = datetime.utcnow()

    # Desactivar plan activo previo del mismo tipo
    db.query(PlanIA).filter(
        PlanIA.usuario_id == usuario_id,
        PlanIA.tipo == tipo,
        PlanIA.activo == True,  # noqa: E712
    ).update({"activo": False})

    plan = PlanIA(
        usuario_id=usuario_id,
        tipo=tipo,
        objetivo=objetivo,
        contenido=respuesta,
        duracion_dias=duracion_dias,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=duracion_dias),
        activo=True,
    )
    db.add(plan)
    db.commit()


def _debe_priorizar_ia_avanzada(mensaje: str) -> bool:
    """Activa IA avanzada en consultas de planificacion o multiarea."""
    texto = _normalizar_ascii(mensaje)
    if not texto:
        return False

    # Frases cortas pero claramente orientadas a plan concreto.
    patrones_directos = (
        "que como",
        "que ceno",
        "que desayuno",
        "que almuerzo",
        "comidas me refiero",
        "no se que comer",
        "dame menu",
        "hazme menu",
        "tengo ansiedad y como",
        "no tengo apetito",
        "quiero rutina",
    )
    if any(p in texto for p in patrones_directos):
        return True

    hits = sum(1 for clave in _CLAVES_IA_AVANZADA if clave in texto)
    es_pregunta_larga = len(texto) >= 40 and any(q in texto for q in ("quiero", "necesito", "como", "haz"))
    return hits >= 2 or es_pregunta_larga


def _detectar_area_chat(texto: str) -> str:
    """Clasifica el mensaje en area dominante para respuestas mas precisas."""
    t = _normalizar_ascii(texto)
    if any(k in t for k in ("especialista", "medico", "nutricionista", "psicologo", "coach", "profesional")):
        return "especialista"
    if any(k in t for k in ("dieta", "menu", "celia", "alerg", "intoler", "comida", "nutric")):
        return "dieta"
    # Mejor detección de entrenamiento vs psicología para evitar conflictos
    if any(k in t for k in ("entren", "ejercicio", "gym", "fuerza", "cardio", "musculo", "peso", "flexiones")):
        return "entrenamiento"
    if any(k in t for k in ("ansiedad", "depres", "estres", "psicol", "emocion", "insomnio", "rutina psicol", "rutina mental", "salud mental", "mindfulness", "respir", "tecnica")):
        return "psicologia"
    return "general"


def _preguntas_precision_por_area(area: str) -> List[str]:
    """Devuelve preguntas clave para personalizar mejor la respuesta."""
    if area == "dieta":
        return [
            "¿Cuál es tu objetivo principal: perder grasa, ganar masa, controlar síntomas o mantenimiento?",
            "¿Tienes alergias/intolerancias o diagnóstico médico (celiaquía, diabetes, SOP, etc.)?",
            "¿Cómo es tu horario real de comidas y cuántas veces al día puedes comer?",
        ]
    if area == "entrenamiento":
        return [
            "¿Cuál es tu objetivo: fuerza, hipertrofia, pérdida de grasa, rehabilitación o rendimiento?",
            "¿Qué nivel tienes (principiante/intermedio/avanzado) y cuántos días puedes entrenar?",
            "¿Tienes dolor, lesión o limitación física que deba adaptar el plan?",
        ]
    if area == "psicologia":
        return [
            "¿Qué te está afectando más ahora: ansiedad, ánimo bajo, estrés o sueño?",
            "¿Desde cuándo te pasa y en qué momentos del día se intensifica?",
            "¿Qué has probado ya y qué te ayudó aunque fuera un poco?",
        ]
    if area == "especialista":
        return [
            "¿Qué especialidad y trastorno quieres priorizar en la intervención?",
            "¿Necesitas plan para paciente individual o protocolo general de servicio?",
            "¿Prefieres salida en formato checklist clínico, plan semanal o resumen ejecutivo?",
        ]
    return [
        "¿Qué objetivo quieres conseguir exactamente en las próximas 2-4 semanas?",
        "¿Qué limitaciones reales tienes ahora (tiempo, dolor, adherencia, recursos)?",
        "¿Prefieres un plan muy simple o uno más completo con seguimiento?",
    ]


def _plan_accion_base(area: str, texto: str) -> List[str]:
    """Genera un mini-plan accionable inmediato según area detectada."""
    t = _normalizar_ascii(texto)
    if area == "dieta":
        pasos = [
            "Define objetivo nutricional semanal y kcal/macros aproximados.",
            "Estructura 3 comidas base + 1 colación de seguridad.",
            "Aplica sustituciones seguras según alergias/intolerancias.",
            "Registra 7 días de adherencia y síntomas digestivos/energía.",
        ]
        if "celia" in t:
            pasos.append("Verifica etiquetado sin gluten y evita contaminación cruzada en cocina.")
        if "alerg" in t:
            pasos.append("Revisa trazas en etiqueta y ten plan de acción ante reacción aguda.")
        return pasos
    if area == "entrenamiento":
        return [
            "Establece frecuencia realista (3-4 sesiones/semana) y duración por sesión.",
            "Usa progresión básica: técnica -> volumen -> intensidad.",
            "Incluye 1 bloque de fuerza, 1 de movilidad y 1 de cardio según objetivo.",
            "Evalúa fatiga/dolor 24h post sesión y ajusta carga.",
        ]
    if area == "psicologia":
        return [
            "Implementa rutina diaria de regulación (respiración + grounding).",
            "Identifica disparadores y señales corporales de activación.",
            "Añade actividad conductual breve con objetivo pequeño y medible.",
            "Si hay riesgo alto o deterioro funcional, prioriza derivación clínica.",
        ]
    if area == "especialista":
        return [
            "Estratifica caso por severidad y riesgo clínico.",
            "Selecciona protocolo por especialidad y define checklist semanal.",
            "Coordina nutrición, psicología, medicina y entrenamiento cuando aplique.",
            "Mide adherencia y KPIs clínicos para ajustar plan.",
        ]
    return [
        "Define un objetivo concreto y medible para 14 días.",
        "Empieza con acciones mínimas sostenibles para asegurar adherencia.",
        "Evalúa resultados semanales y ajusta según respuesta real.",
    ]


def _recursos_multimedia_por_area(area: str, limit: int = 4) -> List[Dict[str, str]]:
    """Devuelve recursos de imagen/video/guia para hacer la respuesta más útil."""
    def _armar_lista(*claves: str) -> List[Dict[str, str]]:
        salida: List[Dict[str, str]] = []
        urls_vistas: set[str] = set()
        for clave in claves:
            for item in _MEDIA_RECURSOS_BASE.get(clave, []):
                url = (item.get("url") or "").strip()
                if not url or url in urls_vistas:
                    continue
                urls_vistas.add(url)
                salida.append(item)
        return salida

    if area == "dieta":
        recursos = _armar_lista("paciente_nutricion", "dieta", "general")
    elif area == "entrenamiento":
        recursos = _armar_lista("paciente_entrenamiento", "entrenamiento", "general")
    elif area == "psicologia":
        recursos = _armar_lista("paciente_psicologia", "psicologia", "general")
    elif area == "especialista":
        recursos = _armar_lista(
            "especialista_nutricion",
            "especialista_psicologia",
            "especialista_entrenamiento",
            "especialista_gestion",
            "especialista",
        )
    else:
        recursos = _armar_lista("general")

    return recursos[: max(1, min(limit, 18))]


def _solicita_generacion_media(texto_normalizado: str) -> bool:
    """Detecta si el usuario pide funciones premium de generacion de imagen/video."""
    return any(k in texto_normalizado for k in _PALABRAS_GENERACION_MEDIA)


def _prompt_imagen_premium(area: str, texto_normalizado: str) -> str:
    """Construye prompt maestro para imagen segun contexto funcional."""
    if area == "entrenamiento":
        return (
            "Ilustracion hiperrealista de tecnica correcta de entrenamiento, vista frontal y lateral, "
            "alineacion neutra de columna, rodillas y cadera, flechas de biomecanica, estilo guia profesional, "
            "fondo limpio, alta nitidez, enfoque educativo."
        )
    if area == "dieta":
        return (
            "Fotografia editorial de plato equilibrado por porciones, proteina magra, fibra alta, carbohidrato complejo, "
            "etiquetas de porcion y calorias aproximadas, estilo clinico-premium, iluminacion natural, alta definicion."
        )
    if area == "psicologia":
        return (
            "Escena de regulacion emocional guiada, respiracion consciente, ambiente minimalista y calmado, "
            "estilo premium terapeutico, composicion limpia, enfoque en postura y respiracion."
        )

    if "ejercicio" in texto_normalizado or "rutina" in texto_normalizado:
        return (
            "Poster visual profesional de rutina semanal con 4 bloques, iconografia clara, "
            "estilo premium de app de salud, jerarquia tipografica limpia y colores funcionales."
        )
    return (
        "Infografia premium en estilo app de salud, explicativa y accionable, con jerarquia visual clara, "
        "tipografia limpia y elementos orientados a ejecucion practica."
    )


def _prompt_video_premium(
    area: str,
    texto_normalizado: str,
    plan_visual_semanal: List[Dict[str, Any]],
) -> str:
    """Construye prompt maestro para video segun necesidad del usuario."""
    ejercicios: List[str] = []
    if plan_visual_semanal:
        for ej in (plan_visual_semanal[0].get("ejercicios") or []):
            nombre = str(ej.get("nombre") or "").strip()
            if nombre:
                ejercicios.append(nombre)
    ejercicios_texto = ", ".join(ejercicios[:4]) if ejercicios else "sentadilla, bisagra de cadera, empuje y tiron"

    if area == "entrenamiento" or "rutina" in texto_normalizado or "ejercicio" in texto_normalizado:
        return (
            "Video didactico premium de rutina de entrenamiento, duracion 45-60s, estructura: intro, tecnica correcta, "
            f"errores comunes y correccion para: {ejercicios_texto}. "
            "Camara frontal/lateral, subtitulos tecnicos, ritmo claro, enfoque profesional de coach senior."
        )
    if area == "dieta":
        return (
            "Video premium de meal-prep saludable, 45-60s, porciones visuales, pasos concretos, "
            "rotulos de macros aproximados y recomendaciones de adherencia."
        )
    if area == "psicologia":
        return (
            "Video premium de regulacion emocional, 45-60s, guia de respiracion y grounding, "
            "voz calmada, subtitulos claros, secuencia practica para aplicar de inmediato."
        )
    return (
        "Video explicativo premium orientado a accion, 45-60s, con pasos concretos, "
        "subtitulos tecnicos y cierre con siguiente accion ejecutable."
    )


def _activos_premium_para_chat(
    mensaje_limpio: str,
    area: str,
    plan_visual_semanal: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """Genera activos premium reales (imagen y video) cuando aplica."""
    texto = _normalizar_ascii(mensaje_limpio)
    solicita_media = _solicita_generacion_media(texto)
    rutina_entreno = area == "entrenamiento" and any(k in texto for k in ("rutina", "plan", "ejercicio", "entren"))

    if not solicita_media and not rutina_entreno:
        return []

    imagen_prompt = _prompt_imagen_premium(area, texto)
    video_prompt = _prompt_video_premium(area, texto, plan_visual_semanal)

    imagen = generar_imagen_premium(imagen_prompt)
    video = generar_video_premium(video_prompt)

    activos: List[Dict[str, str]] = [
        {
            "tipo": "imagen_generada",
            "titulo": "Visual premium generado",
            "prompt": imagen_prompt,
            "proveedor": imagen.get("proveedor", ""),
            "modelo": imagen.get("modelo", ""),
            "estado": imagen.get("estado", ""),
            "url_generada": imagen.get("url_generada", ""),
            "detalle": imagen.get("detalle", ""),
        },
        {
            "tipo": "video_generado",
            "titulo": "Video premium generado",
            "prompt": video_prompt,
            "proveedor": video.get("proveedor", ""),
            "modelo": video.get("modelo", ""),
            "estado": video.get("estado", ""),
            "url_generada": video.get("url_generada", ""),
            "detalle": video.get("detalle", ""),
        },
    ]

    return activos


def _detectar_lugar_entrenamiento(texto: str) -> str:
    """Detecta si el usuario quiere entrenar en casa, gym o mixto."""
    t = _normalizar_ascii(texto)
    if any(k in t for k in ("en casa", "casa", "hogar", "sin gym", "sin gimnasio")):
        return "casa"
    if any(k in t for k in ("gym", "gimnasio", "maquinas", "pesas")):
        return "gym"
    return "mixto"


def _extraer_duracion_semanas(texto: str, area: str) -> int:
    """Extrae duración del plan desde mensaje. Si no aparece, usa un valor por defecto."""
    t = _normalizar_ascii(texto)
    m_sem = re.search(r"(\d{1,2})\s*seman", t)
    if m_sem:
        semanas = int(m_sem.group(1))
        return max(1, min(semanas, 24))

    m_mes = re.search(r"(\d{1,2})\s*mes", t)
    if m_mes:
        meses = int(m_mes.group(1))
        semanas = meses * 4
        return max(1, min(semanas, 24))

    if area == "entrenamiento":
        return 8
    return 4


def _objetivo_entrenamiento_desde_texto(texto: str) -> str:
    """Mapea intención principal del texto al objetivo de catálogo de ejercicios."""
    t = _normalizar_ascii(texto)
    if any(k in t for k in ("perder grasa", "deficit", "bajar peso", "adelgazar")):
        return "salud"
    if any(k in t for k in ("fuerza", "hipertrof", "masa muscular", "musculo")):
        return "fuerza"
    if any(k in t for k in ("ansiedad", "estres", "regular", "calma")):
        return "regulacion"
    if any(k in t for k in ("dolor", "lesion", "rehab", "rehabilit")):
        return "rehabilitacion"
    return "fuerza"


def _condicion_entrenamiento_desde_texto(texto: str) -> str:
    """Detecta condición dominante para elegir ejercicios adecuados."""
    t = _normalizar_ascii(texto)
    if any(k in t for k in ("rodilla", "knee")):
        return "dolor_rodilla"
    if any(k in t for k in ("lumbar", "espalda baja")):
        return "dolor_lumbar"
    if any(k in t for k in ("cervical", "cuello")):
        return "dolor_cervical"
    if any(k in t for k in ("ansiedad", "estres", "insomnio")):
        return "ansiedad_alta"
    if any(k in t for k in ("depres", "animo")):
        return "depresion"
    if any(k in t for k in ("fibromialgia",)):
        return "fibromialgia"
    if any(k in t for k in ("perder grasa", "adelgazar", "deficit")):
        return "perdida_grasa"
    if any(k in t for k in ("musculo", "fuerza", "hipertrof")):
        return "ganancia_muscular"
    return "salud_general"


def _fase_semana(idx: int, total: int) -> str:
    """Etiqueta de fase para planes semanales largos."""
    tercio = max(1, total // 3)
    if idx <= tercio:
        return "adaptacion"
    if idx <= tercio * 2:
        return "progresion"
    return "consolidacion"


def _video_url_ejercicio(nombre_ejercicio: str, lugar: str) -> str:
    """Construye URL de búsqueda de video para técnica del ejercicio según contexto."""
    query = f"{nombre_ejercicio} tecnica {lugar}"
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def _imagen_url_lugar(lugar: str) -> str:
    """Imagen de referencia visual según entorno de entrenamiento."""
    if lugar == "casa":
        return "https://images.unsplash.com/photo-1518611012118-696072aa579a"
    if lugar == "gym":
        return "https://images.unsplash.com/photo-1534438327276-14e5300c3a48"
    return "https://images.unsplash.com/photo-1517836357463-d25dfeac3438"


def _generar_plan_visual_semanal_entrenamiento(texto: str) -> List[Dict[str, Any]]:
    """Genera plan semanal visual con ejercicios + videos para gym/casa."""
    lugar = _detectar_lugar_entrenamiento(texto)
    semanas = _extraer_duracion_semanas(texto, area="entrenamiento")
    objetivo = _objetivo_entrenamiento_desde_texto(texto)
    condicion = _condicion_entrenamiento_desde_texto(texto)

    ejercicios = [e for e in EJERCICIOS_CATALOGO_BASE if e["condicion"] == condicion]
    if objetivo:
        ejercicios_obj = [e for e in ejercicios if e["objetivo"] == objetivo]
        if ejercicios_obj:
            ejercicios = ejercicios_obj

    if len(ejercicios) < 4:
        ejercicios_extra = [e for e in EJERCICIOS_CATALOGO_BASE if e["condicion"] in {"salud_general", "ganancia_muscular", "perdida_grasa"}]
        ejercicios.extend(ejercicios_extra)

    ejercicios_unicos: List[Dict[str, str]] = []
    nombres = set()
    for e in ejercicios:
        n = e["nombre"].strip().lower()
        if n in nombres:
            continue
        nombres.add(n)
        ejercicios_unicos.append(e)
    ejercicios = ejercicios_unicos[:12]

    if not ejercicios:
        return []

    plan: List[Dict[str, Any]] = []
    base_imagen = _imagen_url_lugar(lugar)
    sesiones = 4 if lugar == "gym" else 3

    for semana in range(1, semanas + 1):
        fase = _fase_semana(semana, semanas)
        offset = (semana - 1) % len(ejercicios)
        bloque = []
        for i in range(min(4, len(ejercicios))):
            ej = ejercicios[(offset + i) % len(ejercicios)]
            bloque.append(
                {
                    "nombre": ej["nombre"],
                    "series": ej["series"],
                    "repeticiones": ej["repeticiones"],
                    "duracion": ej["duracion"],
                    "nivel": ej["nivel"],
                    "video_url": _video_url_ejercicio(ej["nombre"], lugar),
                    "imagen_url": base_imagen,
                    "imagen_referencia": ej["imagen_referencia"],
                }
            )

        plan.append(
            {
                "semana": semana,
                "fase": fase,
                "lugar": lugar,
                "sesiones_recomendadas": sesiones,
                "condicion": condicion,
                "objetivo": objetivo,
                "ejercicios": bloque,
            }
        )
    return plan


def _anexar_bloque_utilidad_chat(
    respuesta_base: str,
    preguntas: List[str],
    plan: List[str],
    recursos: List[Dict[str, str]],
) -> str:
    """Anexa utilidad práctica sin convertir la respuesta en una plantilla larga."""
    bloques: List[str] = [respuesta_base.strip()]
    if preguntas:
        bloques.append("\nClaves para afinar:")
        bloques.extend([f"- {p}" for p in preguntas[:2]])
    if plan:
        bloques.append("\nSiguiente paso:")
        bloques.extend([f"- {p}" for p in plan[:3]])
    if recursos:
        bloques.append("\nRecursos útiles:")
        for r in recursos[:3]:
            titulo = (r.get("titulo") or "").strip()
            tipo = (r.get("tipo") or "recurso").strip().title()
            url = (r.get("url") or "").strip()

            if "|" in titulo:
                seccion, detalle = [p.strip() for p in titulo.split("|", 1)]
            else:
                seccion, detalle = "General", titulo

            bloques.append(f"- [{seccion}] {tipo}: {detalle} -> {url}")
    return "\n".join(bloques).strip()


def _debe_anexar_bloque_utilidad(respuesta_base: str, origen_respuesta: str) -> bool:
    """Evita inyectar plantillas en respuestas ya elaboradas por IA."""
    if (origen_respuesta or "").strip().lower() != "rasa":
        return False

    texto = _normalizar_ascii(respuesta_base)
    if len((respuesta_base or "").strip()) > 420:
        return False

    marcadores = (
        "claves para afinar",
        "siguiente paso",
        "recursos utiles",
        "plan de accion",
    )
    return not any(m in texto for m in marcadores)


def _fusionar_texto_diario(actual: Optional[str], nuevo: Optional[str]) -> Optional[str]:
    """Combina dos textos diarios sin pisar un check-in ya guardado."""
    actual_limpio = (actual or "").strip()
    nuevo_limpio = (nuevo or "").strip()

    if not actual_limpio and not nuevo_limpio:
        return None
    if not actual_limpio:
        return nuevo_limpio
    if not nuevo_limpio:
        return actual_limpio
    if actual_limpio.startswith("CHECKIN|"):
        return actual_limpio
    if nuevo_limpio in actual_limpio:
        return actual_limpio
    return f"{actual_limpio}\n\n{nuevo_limpio}"


def _es_solicitud_experta(mensaje: str) -> bool:
    """Detecta peticiones que deben ir directas al motor experto sin pasar por RASA."""
    texto = _normalizar_ascii(mensaje)
    return any(clave in texto for clave in _PALABRAS_EXPERTO_DIRECTO)


def _historial_para_consulta_ia(
    db: Session,
    usuario_id: int,
    conversation_id: Optional[str] = None,
    limit: int = 8,
) -> List[Dict[str, str]]:
    """Prepara historial reciente de chat para mejorar continuidad de respuesta IA."""
    query = db.query(MensajeChat).filter(MensajeChat.usuario_id == usuario_id)
    if conversation_id:
        query = query.filter(MensajeChat.conversation_id == conversation_id)
    mensajes = query.order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc()).limit(limit).all()
    mensajes.reverse()
    return [
        {
            "rol": "assistant" if m.emisor == "ia" else "user",
            "mensaje": m.texto,
        }
        for m in mensajes
        if isinstance(m.texto, str) and m.texto.strip()
    ]


def _contexto_usuario_para_ia(
    db: Session,
    usuario: Optional[Usuario],
) -> Dict[str, Any]:
    """Recolecta contexto PROFUNDO del usuario para respuestas IA avanzadas y personalizadas."""
    if usuario is None:
        return {}

    # Inicializamos el diccionario al principio para evitar UnboundLocalError
    contexto: Dict[str, Any] = {
        "usuario_nombre": usuario.nombre,
        "usuario_rol": usuario.rol.nombre if usuario.rol else None,
        "usuario_id": usuario.id,
    }

    ultimo_registro = None
    try:
        # Se consulta primero para evitar referencias antes de asignacion.
        ultimo_registro = (
            db.query(RegistroDiario)
            .filter(RegistroDiario.usuario_id == usuario.id)
            .order_by(RegistroDiario.fecha.desc(), RegistroDiario.id.desc())
            .first()
        )
    except Exception:
        logger.exception("No se pudo cargar el ultimo registro diario para contexto IA")

    # 1. Perfil de salud base (Protegido con getattr para evitar AttributeErrors)
    perfil = None
    try:
        perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario.id).first()
    except Exception:
        logger.exception("No se pudo cargar el perfil de salud para contexto IA")

    if perfil is not None:
        # Detectamos contradicción: dice estar feliz pero ánimo es muy bajo
        alerta_ia = "Análisis: Usuario estable."
        animo_puntuacion = getattr(ultimo_registro, "estado_animo_puntuacion", None)
        if isinstance(animo_puntuacion, (int, float)) and animo_puntuacion <= 4:
            alerta_ia = "ALERTA CLÍNICA: Ánimo crítico. Ignora mensajes excesivamente positivos y prioriza soporte emocional y fatiga."

        # Extraer restricciones alimentarias desde JSON
        restricciones_dict = _leer_json_seguro(perfil.restricciones_alimentarias_json, {})
        restricciones_lista = []
        if restricciones_dict:
            if isinstance(restricciones_dict, dict):
                restricciones_lista = restricciones_dict.get("restricciones", []) or restricciones_dict.get("items", [])
            elif isinstance(restricciones_dict, list):
                restricciones_lista = restricciones_dict

        contexto.update({
            "peso_actual_kg": float(perfil.peso_actual) if perfil.peso_actual else None,
            "altura_cm": perfil.altura,
            "imc_actual": float(perfil.imc_actual) if perfil.imc_actual else None,
            "frecuencia_gym": perfil.frecuencia_gym,
            "diagnosticos_previos": getattr(perfil, 'diagnosticos_previos', "No registrados"),
            "restricciones_alimentarias": restricciones_lista if restricciones_lista else [],
            "objetivo_principal": getattr(perfil, 'objetivo_principal', "No especificado"),
            "instruccion_clinica": alerta_ia # Esto obliga a Gemini a ser empático y preciso
        })

    # 2. Registro diario reciente (ánimo, estrés, energía)
    if ultimo_registro is not None:
        contexto.update(
            {
                "sentimiento_reciente": ultimo_registro.sentimiento_detectado_ia,
                "animo_reciente": ultimo_registro.estado_animo_puntuacion,
                "nota_reciente": ultimo_registro.notas_diario,
                "fecha_ultimo_registro": ultimo_registro.fecha.isoformat() if ultimo_registro.fecha else None,
            }
        )

    # 3. Memoria de chat activa (temas previos, respuestas guardadas)
    try:
        memoria = db.query(MemoriaChat).filter(MemoriaChat.usuario_id == usuario.id).first()
        if memoria is not None:
            respuestas_memo = _leer_json_seguro(memoria.respuestas_json, {})
            contexto.update(
                {
                    "memoria_tema": memoria.tema,
                    "memoria_respuestas": respuestas_memo,
                    "memoria_activa": bool(memoria.activa),
                }
            )
    except Exception:
        logger.exception("No se pudo cargar memoria de chat para contexto IA")

    # 4. Plan nutricional clínico activo
    try:
        plan_nutri = (
            db.query(PlanNutricionalClinico)
            .filter(PlanNutricionalClinico.paciente_id == usuario.id)
            .filter(PlanNutricionalClinico.activo == True)
            .order_by(PlanNutricionalClinico.fecha_actualizacion.desc(), PlanNutricionalClinico.id.desc())
            .first()
        )
        if plan_nutri is not None:
            contexto.update(
                {
                    "plan_nutricional_objetivo": getattr(plan_nutri, "objetivo_clinico", None),
                    "plan_nutricional_riesgo": getattr(plan_nutri, "riesgo_metabolico", None),
                    "plan_nutricional_calorias": int(plan_nutri.calorias_objetivo) if getattr(plan_nutri, "calorias_objetivo", None) else 0,
                    "plan_nutricional_proteinas_g": int(plan_nutri.proteinas_g) if getattr(plan_nutri, "proteinas_g", None) else 0,
                    "plan_nutricional_activo": True,
                }
            )
    except Exception:
        logger.exception("No se pudo cargar plan nutricional para contexto IA")

    # 5. Medicación activa
    try:
        farmacos_activos = (
            db.query(MedicacionAsignada)
            .filter(MedicacionAsignada.paciente_id == usuario.id)
            .filter(MedicacionAsignada.activa == True)
            .all()
        )
        if farmacos_activos:
            contexto["medicacion_activa"] = [
                {
                    "medicamento": m.medicamento,
                    "dosis": m.dosis,
                    "frecuencia": m.frecuencia,
                }
                for m in farmacos_activos
            ]
    except Exception:
        logger.exception("No se pudo cargar medicacion activa para contexto IA")

    # 6. Derivaciones abiertas
    try:
        derivaciones = (
            db.query(Derivacion)
            .filter(Derivacion.paciente_id == usuario.id)
            .filter(Derivacion.estado.in_(["pendiente", "aceptada", "en_seguimiento"]))
            .all()
        )
        if derivaciones:
            contexto["derivaciones_abiertas"] = [
                {
                    "especialidad": d.especialidad_destino,
                    "motivo": d.motivo,
                }
                for d in derivaciones
            ]
    except Exception:
        logger.exception("No se pudo cargar derivaciones abiertas para contexto IA")

    # 7. Evaluaciones previas IA (últimas por sección)
    try:
        evals_nutricion = (
            db.query(EvaluacionIA)
            .filter(EvaluacionIA.usuario_id == usuario.id, EvaluacionIA.seccion == "nutricion")
            .order_by(EvaluacionIA.fecha_actualizacion.desc(), EvaluacionIA.id.desc())
            .limit(1)
            .all()
        )
        if evals_nutricion:
            plan_ia = evals_nutricion[0].plan_ia
            respuestas_eval = _leer_json_seguro(evals_nutricion[0].respuestas_json, {})
            contexto.update(
                {
                    "evaluacion_nutricion_previa": {
                        "plan": plan_ia,
                        "respuestas": respuestas_eval,
                    }
                }
            )
    except Exception:
        logger.exception("No se pudo cargar evaluacion previa de nutricion para contexto IA")

    try:
        evals_salud_mental = (
            db.query(EvaluacionIA)
            .filter(EvaluacionIA.usuario_id == usuario.id, EvaluacionIA.seccion == "salud_mental")
            .order_by(EvaluacionIA.fecha_actualizacion.desc(), EvaluacionIA.id.desc())
            .limit(1)
            .all()
        )
        if evals_salud_mental:
            contexto["evaluacion_salud_mental_previa"] = evals_salud_mental[0].plan_ia
    except Exception:
        logger.exception("No se pudo cargar evaluacion previa de salud mental para contexto IA")

    # 8. Hábitos completados hoy para entender adherencia actual
    try:
        hoy = datetime.utcnow().date()
        habitos_hoy = (
            db.query(HabitoAgenda)
            .filter(
                HabitoAgenda.usuario_id == usuario.id,
                HabitoAgenda.ultima_actualizacion >= datetime.combine(hoy, time.min),
            )
            .all()
        )
        if habitos_hoy:
            completados = len([h for h in habitos_hoy if bool(h.completado)])
            contexto["habitos_completados_hoy"] = f"{completados}/{len(habitos_hoy)}"
    except Exception:
        pass

    # 9. KPIs clínicos de 7 días para detectar tendencias
    try:
        kpis = _calcular_kpis_paciente(db, usuario.id)
        contexto.update(
            {
                "kpi_riesgo_emocional": kpis.riesgo_emocional,
                "kpi_promedio_animo_7d": kpis.promedio_animo_7d,
                "kpi_promedio_estres_7d": kpis.promedio_estres_7d,
                "kpi_adherencia_nutricional_pct": kpis.adherencia_nutricional_pct,
                "kpi_adherencia_habitos_pct": kpis.adherencia_habitos_pct,
                "kpi_checkins_7d": kpis.checkins_7d,
            }
        )
    except Exception:
        pass 

    # 10. Historial reciente de IA (últimas evaluaciones de severidad sugerida)
    try:
        kpis_check = _calcular_kpis_paciente(db, usuario.id)
        severidad = _sugerir_severidad_desde_kpis(kpis_check)
        contexto["severidad_sugerida_actual"] = severidad.severidad_sugerida
    except Exception:
        pass

    return contexto


def _leer_json_seguro(texto: Optional[str], valor_por_defecto: Any) -> Any:
    """Lee JSON persistido sin romper el flujo si el contenido está corrupto."""
    if not texto:
        return valor_por_defecto
    try:
        return json.loads(texto)
    except Exception:
        return valor_por_defecto


def _preguntas_memoria_por_area(area: str, mensaje: str, tiene_multimedia: bool) -> List[Dict[str, str]]:
    """Define preguntas cortas y ordenadas para recoger contexto antes de responder."""
    texto = _normalizar_ascii(mensaje)
    if tiene_multimedia:
        return [
            {
                "clave": "enfoque_visual",
                "pregunta": "¿Qué evalúo: comida, técnica, postura o riesgo?",
            },
            {
                "clave": "objetivo_visual",
                "pregunta": "¿Objetivo: corregir, decidir o validar?",
            },
        ]

    if area == "dieta":
        preguntas = [
            {
                "clave": "objetivo",
                "pregunta": "Objetivo: perder grasa, ganar masa o mantener.",
            },
            {
                "clave": "restricciones",
                "pregunta": "¿Alergias/intolerancias o indicación médica?",
            },
            {
                "clave": "horario",
                "pregunta": "¿Horario real y cuántas comidas puedes hacer?",
            },
        ]
        if any(k in texto for k in ("ansiedad", "atracon", "picoteo", "hambre nocturna")):
            preguntas.insert(
                1,
                {
                    "clave": "momento_complicado",
                    "pregunta": "¿Momento más difícil: mañana, tarde o noche?",
                },
            )
        return preguntas

    if area == "entrenamiento":
        return [
            {
                "clave": "objetivo",
                "pregunta": "Objetivo: músculo, perder grasa o salud.",
            },
            {
                "clave": "disponibilidad",
                "pregunta": "¿Días reales por semana y minutos por sesión?",
            },
            {
                "clave": "limites",
                "pregunta": "¿Dolor/lesión o material limitado?",
            },
        ]

    if area == "psicologia":
        return [
            {
                "clave": "sintoma_principal",
                "pregunta": "¿Qué pesa más ahora: ansiedad, ánimo o sueño?",
            },
            {
                "clave": "frecuencia",
                "pregunta": "¿Desde cuándo y con qué frecuencia?",
            },
            {
                "clave": "disparadores",
                "pregunta": "¿Qué lo dispara o empeora?",
            },
        ]

    if _debe_priorizar_ia_avanzada(mensaje):
        return [
            {
                "clave": "objetivo",
                "pregunta": "¿Objetivo exacto?",
            },
            {
                "clave": "restricciones",
                "pregunta": "¿Límites reales (tiempo/salud/recursos)?",
            },
        ]

    return []


def _parece_objetivo_dieta(texto: str) -> bool:
    """Detecta si la respuesta parece un objetivo nutricional, no una restricción."""
    t = _normalizar_ascii(texto)
    return any(k in t for k in ("ganar", "masa", "musculo", "perder", "grasa", "mantener", "definir"))


def _parece_restriccion_dieta(texto: str) -> bool:
    """Detecta si la respuesta parece una restricción clínica/alimentaria."""
    t = _normalizar_ascii(texto)
    return any(
        k in t
        for k in (
            "alerg",
            "intoler",
            "celia",
            "gluten",
            "lactosa",
            "diabetes",
            "sop",
            "hipotiroid",
            "no",
            "ninguna",
        )
    )


def _respuesta_breve_ambigua(texto: str) -> bool:
    """Identifica respuestas cortas ambiguas para repreguntar con formato guiado."""
    t = _normalizar_ascii(texto).strip()
    ambiguas = {"no", "si", "depende", "no se", "ni idea", "normal", "ok", "vale"}
    if t in ambiguas:
        return True
    partes = [p for p in t.split() if p]
    return len(partes) <= 2


def _cargar_memoria_chat(db: Session, usuario_id: Optional[int]) -> Optional[MemoriaChat]:
    """Recupera la memoria activa del usuario si existe."""
    if usuario_id is None:
        return None
    return (
        db.query(MemoriaChat)
        .filter(MemoriaChat.usuario_id == usuario_id, MemoriaChat.activa.is_(True))
        .first()
    )


def _guardar_memoria_chat(
    db: Session,
    usuario_id: int,
    tema: str,
    preguntas: List[Dict[str, str]],
    respuestas: Dict[str, Any],
    indice_pregunta: int,
) -> MemoriaChat:
    """Crea o actualiza el estado persistido de preguntas encadenadas."""
    memoria = db.query(MemoriaChat).filter(MemoriaChat.usuario_id == usuario_id).first()
    if memoria is None:
        memoria = MemoriaChat(usuario_id=usuario_id, tema=tema, preguntas_json="[]")
        db.add(memoria)

    preguntas_json = json.dumps(preguntas, ensure_ascii=False)
    respuestas_json = json.dumps(respuestas, ensure_ascii=False)
    memoria.tema = tema
    memoria.preguntas_json = preguntas_json
    memoria.respuestas_json = respuestas_json
    memoria.indice_pregunta = indice_pregunta
    memoria.pregunta_actual = preguntas[indice_pregunta]["pregunta"] if indice_pregunta < len(preguntas) else None
    memoria.activa = indice_pregunta < len(preguntas)
    memoria.fecha_actualizacion = datetime.utcnow()
    db.flush()
    return memoria


def _cerrar_memoria_chat(db: Session, memoria: Optional[MemoriaChat]) -> None:
    """Marca la memoria como cerrada sin borrar el rastro conversacional."""
    if memoria is None:
        return
    memoria.activa = False
    memoria.pregunta_actual = None
    memoria.fecha_actualizacion = datetime.utcnow()
    db.flush()


def _contexto_suficiente_para_area(area: str, contexto_adicional: Optional[Dict[str, Any]]) -> bool:
    """Determina si ya hay suficiente contexto para responder sin repetir intake."""
    if not isinstance(contexto_adicional, dict):
        return False

    memoria = contexto_adicional.get("memoria_respuestas")
    if not isinstance(memoria, dict):
        memoria = {}

    if area == "dieta":
        if memoria.get("objetivo") and memoria.get("restricciones") and memoria.get("horario"):
            return True
        return bool(contexto_adicional.get("peso_actual_kg") and contexto_adicional.get("altura_cm"))

    if area == "entrenamiento":
        if memoria.get("objetivo") and memoria.get("disponibilidad"):
            return True
        return bool(contexto_adicional.get("frecuencia_gym"))

    if area == "psicologia":
        if memoria.get("sintoma_principal") and memoria.get("frecuencia"):
            return True
        return bool(contexto_adicional.get("sentimiento_reciente"))

    return False


def _requiere_intake_paso_a_paso(
    mensaje: str,
    area: str,
    tiene_multimedia: bool,
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> bool:
    """Detecta consultas que DEBEN resolverse por pasos con memoria.
    
    POLÍTICA NUEVA (por demanda usuario):
    - Si user pide "dieta"/"plan" pero NO hay contexto completo → INTAKE OBLIGATORIO
    - Si user pide "rutina" pero NO hay contexto → INTAKE OBLIGATORIO
    - Solo si ya hay contexto guardado O es emergencia → responde directo
    """
    texto = _normalizar_ascii(mensaje)
    
    # EXCEPCIONES: Urgencias médicas o cambio de tema explícito
    if any(
        k in texto
        for k in (
            "suicid",
            "autoles",
            "no puedo respirar",
            "dolor torac",
            "desmayo",
            "sangrado",
            "fiebre alta",
            "purga",
            "crisis de panico",
            "emergencia",
            "urgente",
        )
    ):
        return False
    if any(k in texto for k in ("olvida", "nuevo tema", "cambia de tema", "empecemos de cero")):
        return False

    # YA TIENE CONTEXTO COMPLETO → Puede responder directo
    if _contexto_suficiente_para_area(area, contexto_adicional):
        return False

    # REGLA NUEVA: Si NO tiene contexto y pide dieta/rutina → INTAKE OBLIGATORIO
    tiene_contexto_incompleto = not _contexto_suficiente_para_area(area, contexto_adicional)
    pide_dieta = any(k in texto for k in ("dieta", "nutric", "comida", "menu", "plan nutric", "que como"))
    pide_rutina = any(k in texto for k in ("rutina", "entren", "plan entrenar", "ejercicio", "que entreno"))
    pide_salud_mental = any(k in texto for k in ("ansiedad", "estres", "depres", "psicol", "emoc"))

    if tiene_contexto_incompleto and (pide_dieta or pide_rutina or pide_salud_mental):
        return True

    # Multimedia: intentar análisis directo si hay credenciales
    if tiene_multimedia and settings.IA_TESTING_MODE:
        if settings.GEMINI_API_KEY:
            return False
        return True
    
    # IA avanzada multidisciplina
    if area in {"dieta", "entrenamiento", "psicologia"} and _debe_priorizar_ia_avanzada(mensaje):
        return True

    return False
    if area == "entrenamiento" and any(k in texto for k in ("rutina", "plan", "hipertrof", "musculo", "fuerza")):
        return not solicitud_directa
    if area == "psicologia" and any(k in texto for k in ("ansiedad", "estres", "depres", "emoc", "sueño", "sueno")):
        return not solicitud_directa
    return False


class ChatHistorialItemResponse(BaseModel):
    """Mensaje del historial persistido del chat."""

    id: int
    emisor: str
    texto: str
    peso_registrado: Optional[float] = None
    imc_calculado: Optional[float] = None
    imc_rango: Optional[str] = None
    solicitar_altura: bool = False
    activos_premium: List[Dict[str, str]] = Field(default_factory=list)
    fecha: str
    conversation_id: Optional[str] = None
    conversation_title: Optional[str] = None
    conversation_pinned: bool = False


class ChatConversationResponse(BaseModel):
    """Resumen de una conversación persistida del usuario."""

    conversation_id: str
    titulo: str
    ultimo_mensaje: str
    fecha_ultimo_mensaje: str
    total_mensajes: int
    fijada: bool = False


class AnimoDiaResponse(BaseModel):
    """Punto de serie temporal de estado de animo para graficas."""

    fecha: str
    sentimiento: str
    valor: int


class GraficaAnimoResponse(BaseModel):
    """Respuesta del endpoint de tendencia emocional de 7 dias."""

    usuario_id: int
    datos: List[AnimoDiaResponse]
    alerta_profesional: bool


class PacienteResumenResponse(BaseModel):
    """Resumen breve de paciente para panel profesional."""

    usuario_id: int
    nombre: str
    email: str
    ultimo_imc: Optional[float] = None
    sentimiento_detectado: Optional[str] = None
    ultima_comida: Optional[str] = None
    ultima_actualizacion: Optional[str] = None


class PacienteKpisResponse(BaseModel):
    """KPIs clínicos resumidos para panel profesional por paciente."""

    paciente_id: int
    checkins_7d: int
    promedio_animo_7d: Optional[float] = None
    promedio_estres_7d: Optional[float] = None
    adherencia_nutricional_pct: Optional[float] = None
    adherencia_habitos_pct: Optional[float] = None
    riesgo_emocional: str
    farmacos_activos: int
    derivaciones_abiertas: int
    coordinacion_especialistas: int


class ProfesionalAsignadoResponse(BaseModel):
    """Profesional recomendado para contacto segun seccion de la app."""

    usuario_id: int
    nombre: str
    email: str
    rol: str
    especialidad: str


class DerivacionCreateRequest(BaseModel):
    """Solicitud de derivacion de un profesional a otro."""

    paciente_id: int
    especialidad_destino: str = Field(..., min_length=3, max_length=50)
    motivo: str = Field(..., min_length=10, max_length=2000)
    nota_paciente: Optional[str] = Field(default=None, max_length=2000)


class SolicitarCitaNutricionRequest(BaseModel):
    """Solicitud de cita nutricional iniciada por paciente."""

    motivo: str = Field(default="Necesito valoración nutricional", min_length=10, max_length=2000)


class SolicitarContactoEspecialistaRequest(BaseModel):
    """Solicitud de contacto directo con un especialista desde la app."""

    especialidad_destino: str = Field(..., min_length=3, max_length=50)
    motivo: str = Field(..., min_length=10, max_length=2000)
    nota_paciente: Optional[str] = Field(default=None, max_length=2000)


class CitaDisponibleCreateRequest(BaseModel):
    """Alta de hueco disponible en calendario de especialista."""

    especialidad: str = Field(..., min_length=3, max_length=50)
    inicio: str = Field(..., min_length=10)
    fin: str = Field(..., min_length=10)
    notas: Optional[str] = Field(default=None, max_length=2000)


class CitaDisponibleResponse(BaseModel):
    """Hueco de calendario listo para reserva del paciente."""

    id: int
    especialista_id: int
    especialista_nombre: str
    especialidad: str
    inicio: str
    fin: str
    estado: str
    notas: Optional[str] = None


class CitaFormularioTriageRequest(BaseModel):
    """Formulario clínico breve para priorizar citas por necesidad."""

    nivel_dolor: int = Field(default=0, ge=0, le=10)
    ansiedad_actual: int = Field(default=0, ge=0, le=10)
    horas_sueno: float = Field(default=7.0, ge=0, le=24)
    sintomas_clave: List[str] = Field(default_factory=list)
    duracion_dias: int = Field(default=1, ge=1, le=3650)
    impacto_funcional: str = Field(default="leve", min_length=3, max_length=20)
    riesgo_psicologico: Optional[str] = Field(default=None, max_length=30)
    observaciones: Optional[str] = Field(default=None, max_length=2000)


class CitaReservarRequest(BaseModel):
    """Reserva de cita con motivo clínico y triaje de prioridad IA."""

    cita_disponible_id: Optional[int] = None
    especialidad_destino: str = Field(..., min_length=3, max_length=50)
    motivo: str = Field(..., min_length=10, max_length=3000)
    formulario: CitaFormularioTriageRequest = Field(default_factory=CitaFormularioTriageRequest)


class TriajeCitaIAResponse(BaseModel):
    """Resultado de evaluación IA para urgencia/prioridad de la cita."""

    prioridad: str
    puntuacion: int
    preferente: bool
    max_horas_recomendadas: int
    justificacion: str


class CitaReservadaResponse(BaseModel):
    """Representación de cita reservada con prioridad de IA."""

    id: int
    cita_disponible_id: Optional[int] = None
    paciente_id: int
    paciente_nombre: str
    especialista_id: int
    especialista_nombre: str
    especialidad: str
    inicio: str
    fin: str
    motivo: str
    prioridad_ia: str
    puntuacion_prioridad: int
    justificacion_ia: str
    estado: str
    fecha_creacion: str


class CitaReservaConTriageResponse(BaseModel):
    """Respuesta de reserva con datos de cita y clasificación IA."""

    cita: CitaReservadaResponse
    triaje: TriajeCitaIAResponse


class DerivacionResponse(BaseModel):
    """Representacion de una derivacion clinica."""

    id: int
    paciente_id: int
    paciente_nombre: str
    origen_profesional_id: int
    origen_profesional_nombre: str
    destino_profesional_id: int
    destino_profesional_nombre: str
    especialidad_destino: str
    motivo: str
    nota_paciente: Optional[str] = None
    estado: str
    leida_paciente: bool
    fecha_creacion: str


class SeguimientoCheckinRequest(BaseModel):
    """Check-in diario de bienestar para seguimiento del paciente."""

    estado_animo: int = Field(..., ge=1, le=10)
    energia: int = Field(..., ge=1, le=10)
    estres: int = Field(..., ge=1, le=10)
    horas_sueno: float = Field(..., ge=0, le=24)
    notas: Optional[str] = Field(default=None, max_length=1000)


class SeguimientoCheckinResponse(BaseModel):
    """Respuesta de guardado de check-in diario."""

    usuario_id: int
    fecha: str
    estado_animo: int
    energia: int
    estres: int
    horas_sueno: float
    sentimiento: str
    mensaje: str


class SeguimientoComidaRequest(BaseModel):
    """Registro rápido de comida diaria por parte del paciente."""

    tipo: str = Field(default="comida", min_length=3, max_length=30)
    descripcion: str = Field(..., min_length=3, max_length=500)
    hora: Optional[str] = Field(default=None, max_length=10)


class SeguimientoComidaItemResponse(BaseModel):
    """Comida registrada y visible para paciente/profesional."""

    id: int
    usuario_id: int
    tipo: str
    descripcion: str
    hora: Optional[str] = None
    fecha: str
    fecha_creacion: str


class SeguimientoResumenSemanalResponse(BaseModel):
    """Resumen semanal de indicadores de bienestar del paciente."""

    usuario_id: int
    dias_registrados: int
    promedio_animo: float
    promedio_energia: float
    promedio_estres: float
    promedio_sueno: float
    ultima_actualizacion: Optional[str] = None


class SeguimientoHistoricoItemResponse(BaseModel):
    """Punto historico reciente para graficas de seguimiento."""

    fecha: str
    estado_animo: int
    energia: int
    estres: int
    horas_sueno: float
    sentimiento: str


class SeguimientoRachaResponse(BaseModel):
    """Rachas de adherencia basadas en check-ins diarios."""

    usuario_id: int
    racha_actual: int
    mejor_racha: int
    ultimo_checkin: Optional[str] = None


class SeguimientoEstadoActualResponse(BaseModel):
    """Estado actual de bienestar (bien/regular/mal) y pasos inmediatos."""

    fecha: str
    estado: str
    score_bienestar: int
    checkin_realizado_hoy: bool
    mensaje: str
    pasos_recomendados: List[str]


class SeguimientoCumplimientoDiarioResponse(BaseModel):
    """Cumplimiento diario agregado por secciones de salud."""

    fecha: str
    total_tareas: int
    tareas_completadas: int
    cumplimiento_pct: float
    comidas_objetivo: int
    comidas_marcadas: int
    cumplimiento_nutricion_pct: float
    cumplimiento_gym_pct: float
    cumplimiento_salud_mental_pct: float
    checkin_realizado_hoy: bool


class RecursoPersonalizadoItem(BaseModel):
    """Recurso accionable para el estado actual del usuario."""

    titulo: str
    descripcion: str
    prioridad: str


class SeguimientoRecursosPersonalizadosResponse(BaseModel):
    """Recursos dinámicos personalizados por estado y sección solicitada."""

    fecha: str
    seccion: str
    estado: str
    recursos: List[RecursoPersonalizadoItem]


class PreferenciasRecursosRequest(BaseModel):
    """Preferencias de visualización en pantalla de recursos."""

    area_seleccionada: str = Field(default="todas", min_length=3, max_length=30)
    auto_area: bool = True


class PreferenciasRecursosResponse(BaseModel):
    """Preferencias persistidas por usuario para la vista de recursos."""

    area_seleccionada: str
    auto_area: bool
    actualizado_en: Optional[str] = None


class InteligenciaRecursosResponse(BaseModel):
    """Semáforo de riesgo y recomendación de área para personalización dinámica."""

    area_recomendada: str
    motivo: str
    riesgo_por_area: Dict[str, str]
    score_por_area: Dict[str, int]
    semaforo_global: str
    actualizado_en: str


class DerivacionEstadoUpdateRequest(BaseModel):
    """Cambio de estado para derivaciones del especialista destino."""

    estado: str = Field(..., min_length=3, max_length=30)


class HabitoAgendaResponse(BaseModel):
    """Elemento de agenda de habitos persistente."""

    id: int
    usuario_id: int
    dia_semana: int
    titulo: str
    subtitulo: str
    franja: str
    color_hex: str
    orden: int
    completado: bool
    ultima_actualizacion: Optional[str] = None


class HabitoAgendaUpdateRequest(BaseModel):
    """Actualizacion de un habito de agenda."""

    completado: bool


class EvaluacionIAGuardadoRequest(BaseModel):
    """Guardado de cuestionario IA por seccion."""

    respuestas: Dict[str, str] = Field(default_factory=dict)
    plan_ia: str = Field(..., min_length=1)


class EvaluacionIAResponse(BaseModel):
    """Evaluacion IA persistida por seccion."""

    seccion: str
    respuestas: Dict[str, str]
    plan_ia: str
    fecha_actualizacion: str


class MedicacionCreateRequest(BaseModel):
    """Solicitud de prescripción de medicación para paciente."""

    medicamento: str = Field(..., min_length=2, max_length=120)
    dosis: str = Field(..., min_length=1, max_length=120)
    frecuencia: str = Field(..., min_length=1, max_length=120)
    instrucciones: Optional[str] = Field(default=None, max_length=3000)


class MedicacionEstadoRequest(BaseModel):
    """Cambio de estado de una medicación."""

    activa: bool


class MedicacionResponse(BaseModel):
    """Medicacion asignada visible para el panel profesional."""

    id: int
    paciente_id: int
    profesional_id: int
    profesional_nombre: str
    medicamento: str
    dosis: str
    frecuencia: str
    instrucciones: Optional[str] = None
    activa: bool
    fecha_inicio: str
    fecha_actualizacion: str


class NotaClinicaCreateRequest(BaseModel):
    """Nota clínica redactada por especialista para seguimiento del paciente."""

    titulo: str = Field(..., min_length=3, max_length=120)
    contenido: str = Field(..., min_length=10, max_length=6000)


class NotaClinicaResponse(BaseModel):
    """Nota clínica visible en panel profesional e informe PDF."""

    id: int
    paciente_id: int
    profesional_id: int
    profesional_nombre: str
    titulo: str
    contenido: str
    fecha_creacion: str


class MedicamentoCatalogoResponse(BaseModel):
    """Elemento del catálogo farmacológico para apoyo en prescripción médica."""

    seccion: str
    nombre: str
    para_que_sirve: str
    requiere_supervision_medica: bool = True


class PlanNutricionalUpsertRequest(BaseModel):
    """Actualiza plan nutricional clínico y objetivo de macros."""

    calorias_objetivo: int = Field(..., ge=800, le=6000)
    proteinas_g: int = Field(..., ge=20, le=450)
    carbohidratos_g: int = Field(..., ge=20, le=900)
    grasas_g: int = Field(..., ge=10, le=250)
    objetivo_clinico: str = Field(default="mantenimiento", min_length=3, max_length=40)
    riesgo_metabolico: str = Field(default="bajo", min_length=3, max_length=20)
    observaciones: Optional[str] = Field(default=None, max_length=4000)


class PlanNutricionalResponse(BaseModel):
    """Plan nutricional clínico compartido entre nutrición, medicina y coach."""

    id: int
    paciente_id: int
    profesional_id: int
    profesional_nombre: str
    calorias_objetivo: int
    proteinas_g: int
    carbohidratos_g: int
    grasas_g: int
    objetivo_clinico: str
    riesgo_metabolico: str
    observaciones: Optional[str] = None
    activo: bool
    fecha_actualizacion: str


class ProtocoloHospitalarioUpsertRequest(BaseModel):
    """Define un protocolo clínico por trastorno, severidad y especialidad."""

    trastorno: str = Field(..., min_length=3, max_length=60)
    severidad: str = Field(..., min_length=3, max_length=20)
    especialidad: str = Field(..., min_length=3, max_length=50)
    titulo: str = Field(..., min_length=5, max_length=180)
    checklist: List[str] = Field(..., min_length=1, max_length=30)
    ruta_escalado: str = Field(..., min_length=10, max_length=4000)


class ProtocoloHospitalarioResponse(BaseModel):
    """Representación de protocolo hospitalario para el panel profesional."""

    id: int
    trastorno: str
    severidad: str
    especialidad: str
    titulo: str
    checklist: List[str]
    ruta_escalado: str
    activo: bool
    fecha_actualizacion: str


class ChecklistClinicoUpdateRequest(BaseModel):
    """Checklist clínico aplicado a paciente en contexto hospitalario."""

    trastorno: str = Field(..., min_length=3, max_length=60)
    severidad: str = Field(..., min_length=3, max_length=20)
    especialidad: str = Field(..., min_length=3, max_length=50)
    checklist: List[str] = Field(..., min_length=1, max_length=30)
    requiere_escalado: bool = False
    ruta_escalado_aplicada: Optional[str] = Field(default=None, max_length=4000)
    observaciones: Optional[str] = Field(default=None, max_length=4000)


class ChecklistClinicoResponse(BaseModel):
    """Checklist hospitalario persistido para paciente."""

    id: int
    paciente_id: int
    profesional_id: int
    profesional_nombre: str
    trastorno: str
    severidad: str
    especialidad: str
    checklist: List[str]
    requiere_escalado: bool
    ruta_escalado_aplicada: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_actualizacion: str


class ChecklistClinicoHistorialItemResponse(BaseModel):
    """Evento de auditoría temporal asociado a checklist clínico."""

    id: int
    checklist_id: int
    paciente_id: int
    profesional_id: int
    version: int
    checklist: List[str]
    requiere_escalado: bool
    ruta_escalado_aplicada: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_evento: str


class SeveridadSugeridaResponse(BaseModel):
    """Sugerencia automática de severidad clínica para apoyo al profesional."""

    paciente_id: int
    severidad_sugerida: str
    puntuacion_riesgo: int
    motivos: List[str]


class RecursoClinicoCreateRequest(BaseModel):
    """Alta de recurso clínico persistente por trastorno y especialidad."""

    trastorno: str = Field(..., min_length=3, max_length=60)
    especialidad: str = Field(..., min_length=3, max_length=50)
    titulo: str = Field(..., min_length=5, max_length=180)
    descripcion: str = Field(..., min_length=10, max_length=5000)
    url: Optional[str] = Field(default=None, max_length=500)
    nivel_evidencia: Optional[str] = Field(default=None, max_length=40)


class RecursoClinicoResponse(BaseModel):
    """Recurso clínico del repositorio hospitalario."""

    id: int
    trastorno: str
    especialidad: str
    titulo: str
    descripcion: str
    url: Optional[str] = None
    nivel_evidencia: Optional[str] = None
    activo: bool
    fecha_actualizacion: str


class EjercicioCatalogoResponse(BaseModel):
    """Ejercicio sugerido por condición, objetivo y nivel."""

    condicion: str
    objetivo: str
    nombre: str
    que_es: str
    para_que_sirve: str
    series: str
    repeticiones: str
    duracion: str
    nivel: str
    imagen_referencia: str


class DietaClinicaCatalogoResponse(BaseModel):
    """Plantilla nutricional clínica para filtrado profesional por condición o alergeno."""

    condicion: str
    objetivo: str
    titulo: str
    para_quien: str
    alergenos_clave: List[str]
    alimentos_evitar: List[str]
    alimentos_priorizar: List[str]
    ejemplo_menu_1_dia: List[str]
    suplementos_opcionales: List[str]
    red_flags: List[str]
    especialistas_recomendados: List[str]
    nivel_evidencia: str
    nota_seguridad: str


class DietaClinicaPacienteResponse(BaseModel):
    """Respuesta simplificada para que el paciente reciba pasos accionables."""

    condicion: str
    objetivo: str
    titulo: str
    resumen_paciente: str
    alimentos_evitar: List[str]
    alimentos_priorizar: List[str]
    pasos_hoy: List[str]
    cuando_pedir_ayuda: List[str]
    especialistas_recomendados: List[str]


class BibliotecaClinicaResponse(BaseModel):
    """Resumen unificado de biblioteca clínica por trastorno y severidad."""

    trastorno: str
    severidad: Optional[str] = None
    especialidad: Optional[str] = None
    protocolos: List[ProtocoloHospitalarioResponse]
    recursos: List[RecursoClinicoResponse]


class ResumenClinicoPacienteResponse(BaseModel):
    """Resumen breve para que el doctor lea rápido el caso del paciente."""

    paciente_id: int
    nombre: str
    ultima_actividad: Optional[str] = None
    objetivo_probable: str
    problemas_probables: List[str]
    señales_riesgo: List[str]
    faltan_datos: List[str]
    evidencia_sugerida: str
    resumen_breve: str
    mensajes_recientes: List[str]


def _asegurar_roles_base(db: Session) -> None:
    """Inserta roles base si no existen."""
    existentes = {r.nombre for r in db.query(Rol).all()}
    nuevos = [Rol(nombre=nombre) for nombre in ROLES_BASE if nombre not in existentes]
    if nuevos:
        db.add_all(nuevos)
        db.commit()


def _asegurar_columna_cambio_contrasena() -> None:
    """Añade la columna de primer acceso si la base ya existia sin ella."""
    inspector = inspect(engine)
    columnas = {columna["name"] for columna in inspector.get_columns("usuarios")}
    if "cambio_contrasena_pendiente" in columnas:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE usuarios ADD COLUMN cambio_contrasena_pendiente BOOLEAN NOT NULL DEFAULT 0"
            )
        )


def _asegurar_columna_activos_premium_chat() -> None:
    """Añade columna para persistir activos premium en historial de chat."""
    inspector = inspect(engine)
    columnas = {columna["name"] for columna in inspector.get_columns("mensajes_chat")}
    if "activos_premium_json" in columnas:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE mensajes_chat ADD COLUMN activos_premium_json TEXT NULL"
            )
        )


def _asegurar_columnas_conversaciones_chat() -> None:
    """Añade columnas para múltiples conversaciones de chat en instalaciones existentes."""
    inspector = inspect(engine)
    columnas = {columna["name"] for columna in inspector.get_columns("mensajes_chat")}
    sentencias: List[str] = []

    if "conversation_id" not in columnas:
        sentencias.append("ALTER TABLE mensajes_chat ADD COLUMN conversation_id VARCHAR(80) NULL")
    if "conversation_title" not in columnas:
        sentencias.append("ALTER TABLE mensajes_chat ADD COLUMN conversation_title VARCHAR(160) NULL")
    if "conversation_pinned" not in columnas:
        sentencias.append("ALTER TABLE mensajes_chat ADD COLUMN conversation_pinned BOOLEAN NOT NULL DEFAULT 0")

    if not sentencias:
        return

    with engine.begin() as conn:
        for sentencia in sentencias:
            conn.execute(text(sentencia))

def _asegurar_columnas_perfil_plan_diario() -> None:
    """Añade columnas para persistencia de plan diario en perfiles existentes."""
    inspector = inspect(engine)
    columnas = {columna["name"] for columna in inspector.get_columns("perfiles_salud")}
    sentencias: List[str] = []

    if "objetivo_principal" not in columnas:
        sentencias.append(
            "ALTER TABLE perfiles_salud ADD COLUMN objetivo_principal VARCHAR(40) NOT NULL DEFAULT 'perder_grasa'"
        )
    if "deslices_hoy_json" not in columnas:
        sentencias.append(
            "ALTER TABLE perfiles_salud ADD COLUMN deslices_hoy_json TEXT NULL"
        )
    if "deslices_fecha" not in columnas:
        sentencias.append(
            "ALTER TABLE perfiles_salud ADD COLUMN deslices_fecha DATE NULL"
        )
    if "restricciones_alimentarias_json" not in columnas:
        sentencias.append(
            "ALTER TABLE perfiles_salud ADD COLUMN restricciones_alimentarias_json TEXT NULL"
        )
    if "ultima_actualizacion_metricas" not in columnas:
        sentencias.append(
            "ALTER TABLE perfiles_salud ADD COLUMN ultima_actualizacion_metricas DATETIME NULL"
        )

    if not sentencias:
        return

    with engine.begin() as conn:
        for sentencia in sentencias:
            conn.execute(text(sentencia))


def _asegurar_profesionales_demo(db: Session) -> None:
    """Crea usuarios profesionales demo en desarrollo para poder iniciar sesión."""
    if not settings.DEBUG:
        return

    roles = {r.nombre: r.id for r in db.query(Rol).filter(Rol.nombre.in_(ROLES_BASE)).all()}
    password_hash = generar_hash_contrasena(PASSWORD_DEMO_PROFESIONALES)
    creados = 0
    actualizados = 0

    for item in USUARIOS_PROFESIONALES_DEMO:
        email_objetivo = item["email"].strip().lower()
        email_legacy = email_objetivo.replace("@aurafit.app", "@aurafit.local")
        existe = db.query(Usuario).filter(Usuario.email == email_objetivo).first()

        if existe:
            # Asegura contraseña demo consistente para entorno dev.
            existe.password_hash = password_hash
            existe.cambio_contrasena_pendiente = True
            actualizados += 1
            continue

        legacy = db.query(Usuario).filter(Usuario.email == email_legacy).first()
        if legacy:
            legacy.email = email_objetivo
            legacy.password_hash = password_hash
            legacy.cambio_contrasena_pendiente = True
            actualizados += 1
            continue

        rol_nombre = item["rol"]
        rol_id = roles.get(rol_nombre)
        if not rol_id:
            continue

        db.add(
            Usuario(
                nombre=item["nombre"],
                email=email_objetivo,
                password_hash=password_hash,
                rol_id=rol_id,
                cambio_contrasena_pendiente=True,
            )
        )
        creados += 1

    if creados or actualizados:
        db.commit()
        logger.info("Usuarios profesionales demo creados: %s | actualizados: %s", creados, actualizados)


def _asegurar_pacientes_demo(db: Session) -> None:
    """Crea pacientes demo en desarrollo para alimentar el panel profesional."""
    if not settings.DEBUG:
        return

    rol_cliente = db.query(Rol).filter(Rol.nombre == "cliente").first()
    if not rol_cliente:
        return

    password_hash = generar_hash_contrasena(PASSWORD_DEMO_CLIENTES)
    hoy = datetime.utcnow().date()
    creados = 0
    actualizados = 0

    for item in USUARIOS_CLIENTES_DEMO:
        email_objetivo = item["email"].strip().lower()
        usuario = db.query(Usuario).filter(Usuario.email == email_objetivo).first()

        if not usuario:
            usuario = Usuario(
                nombre=item["nombre"],
                email=email_objetivo,
                password_hash=password_hash,
                rol_id=rol_cliente.id,
                cambio_contrasena_pendiente=True,
            )
            db.add(usuario)
            db.flush()
            creados += 1
        else:
            usuario.password_hash = password_hash
            usuario.rol_id = rol_cliente.id
            actualizados += 1

        peso = float(item.get("peso") or 70.0)
        altura = int(item.get("altura") or 170)
        altura_m = altura / 100
        imc = round(peso / (altura_m * altura_m), 2)

        perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario.id).first()
        if not perfil:
            perfil = PerfilSalud(usuario_id=usuario.id)
            db.add(perfil)
        perfil.peso_actual = peso
        perfil.altura = altura
        perfil.imc_actual = imc
        perfil.ultima_actualizacion_metricas = datetime.utcnow()

        registro = (
            db.query(RegistroDiario)
            .filter(RegistroDiario.usuario_id == usuario.id, RegistroDiario.fecha == hoy)
            .first()
        )
        if not registro:
            registro = RegistroDiario(usuario_id=usuario.id, fecha=hoy)
            db.add(registro)
        registro.estado_animo_puntuacion = int(item.get("animo") or 6)
        registro.sentimiento_detectado_ia = str(item.get("sentimiento") or "neutral")
        registro.notas_diario = registro.notas_diario or "CHECKIN|energia=6|estres=4|sueno=7.0|notas=registro demo"

    if creados or actualizados:
        db.commit()
        logger.info("Pacientes demo creados: %s | actualizados: %s", creados, actualizados)


def _es_profesional(usuario: Usuario) -> bool:
    """Determina si el usuario autenticado pertenece al staff profesional."""
    rol_nombre = (usuario.rol.nombre if usuario.rol else "").strip().lower()
    return rol_nombre in ROLES_PROFESIONALES


def _rol_actual(usuario: Usuario) -> str:
    """Devuelve el rol normalizado del usuario autenticado."""
    return (usuario.rol.nombre if usuario.rol else "").strip().lower()


def _puede_prescribir_medicacion(usuario: Usuario) -> bool:
    """Solo medico y administrador pueden asignar o modificar medicacion."""
    rol_nombre = (usuario.rol.nombre if usuario.rol else "").strip().lower()
    return rol_nombre in {"medico", "administrador"}


def _catalogo_medicamentos_filtrado(
    seccion: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 300,
) -> List[Dict[str, str]]:
    """Filtra catálogo farmacológico por sección y texto libre."""
    seccion_norm = (seccion or "").strip().lower()
    q_norm = (q or "").strip().lower()

    items = MEDICAMENTOS_CATALOGO_BASE
    if seccion_norm:
        items = [m for m in items if m["seccion"] == seccion_norm]
    if q_norm:
        items = [
            m
            for m in items
            if q_norm in m["nombre"].lower() or q_norm in m["para_que_sirve"].lower()
        ]

    return items[: max(1, min(limit, 1000))]


def _catalogo_dietas_clinicas_filtrado(
    condicion: Optional[str] = None,
    alergeno: Optional[str] = None,
    objetivo: Optional[str] = None,
    especialidad: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Filtra catálogo nutricional clínico por condición, alergeno, objetivo y texto libre."""
    items = DIETAS_CLINICAS_BASE

    if condicion:
        condicion_norm = _normalizar_ascii(condicion)
        items = [i for i in items if _normalizar_ascii(i["condicion"]) == condicion_norm]

    if objetivo:
        objetivo_norm = _normalizar_ascii(objetivo)
        items = [i for i in items if _normalizar_ascii(i["objetivo"]) == objetivo_norm]

    if alergeno:
        alergeno_norm = _normalizar_ascii(alergeno)
        items = [
            i
            for i in items
            if any(alergeno_norm in _normalizar_ascii(a) for a in i["alergenos_clave"])
            or any(alergeno_norm in _normalizar_ascii(a) for a in i["alimentos_evitar"])
        ]

    if especialidad:
        especialidad_norm = _normalizar_ascii(especialidad)
        items = [
            i
            for i in items
            if any(especialidad_norm == _normalizar_ascii(e) for e in i["especialistas_recomendados"])
        ]

    if q:
        q_norm = _normalizar_ascii(q)
        items = [
            i
            for i in items
            if (
                q_norm in _normalizar_ascii(i["titulo"])
                or q_norm in _normalizar_ascii(i["para_quien"])
                or any(q_norm in _normalizar_ascii(a) for a in i["alimentos_evitar"])
                or any(q_norm in _normalizar_ascii(a) for a in i["alimentos_priorizar"])
                or any(q_norm in _normalizar_ascii(a) for a in i["alergenos_clave"])
            )
        ]

    return items[: max(1, min(limit, 1000))]


def _puede_editar_plan_nutricional(usuario: Usuario) -> bool:
    """Solo nutricionista, medico y administrador pueden editar plan nutricional."""
    rol_nombre = (usuario.rol.nombre if usuario.rol else "").strip().lower()
    return rol_nombre in {"nutricionista", "medico", "administrador"}


def _puede_editar_protocolo_hospitalario(usuario: Usuario) -> bool:
    """Solo staff clínico hospitalario central puede editar protocolos."""
    rol_nombre = (usuario.rol.nombre if usuario.rol else "").strip().lower()
    return rol_nombre in {"medico", "psicologo", "administrador"}


def _puede_editar_recursos_clinicos(usuario: Usuario) -> bool:
    """Edición de repositorio clínico reservada a áreas terapéuticas."""
    rol_nombre = (usuario.rol.nombre if usuario.rol else "").strip().lower()
    return rol_nombre in {"medico", "psicologo", "nutricionista", "administrador"}


def _assert_permitido_ver_usuario(usuario_actual: Usuario, usuario_objetivo_id: int) -> None:
    """Permite ver datos si es profesional o si es su propio usuario."""
    if _es_profesional(usuario_actual):
        return
    if usuario_actual.id == usuario_objetivo_id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para ver datos de otros usuarios",
    )


def _rol_objetivo_por_especialidad(especialidad: str) -> str:
    """Mapea cada seccion a su rol profesional correspondiente."""
    normalizada = especialidad.strip().lower()
    mapa = {
        "nutricion": "nutricionista",
        "nutricionista": "nutricionista",
        "gimnasio": "coach",
        "gym": "coach",
        "entrenamiento": "coach",
        "coach": "coach",
        "salud_mental": "psicologo",
        "psicologia": "psicologo",
        "psicologo": "psicologo",
        "mental": "psicologo",
        "medicina": "medico",
        "medico": "medico",
    }
    if normalizada not in mapa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Especialidad invalida. Usa: nutricion, psicologia, entrenamiento o medicina",
        )
    return mapa[normalizada]


def _roles_destino_permitidos_derivacion(rol_origen: str) -> set[str]:
    """Define a qué áreas puede derivar cada perfil profesional."""
    reglas = {
        "administrador": {"nutricionista", "psicologo", "coach", "medico"},
        "medico": {"nutricionista", "psicologo", "coach", "medico"},
        "nutricionista": {"psicologo", "medico"},
        "psicologo": {"medico"},
        "coach": {"nutricionista", "psicologo", "medico"},
    }
    return reglas.get(rol_origen, set())


def _especialidad_urgente_por_contexto(area_detectada: str, texto_normalizado: str) -> str:
    """Decide la especialidad preferente cuando se detecta urgencia clínica real."""
    if any(k in texto_normalizado for k in ("suicid", "autoles", "panico", "crisis emocional", "depres")):
        return "psicologia"
    if any(k in texto_normalizado for k in ("atracon", "purga", "vomito", "no comer", "tca")):
        return "nutricion"
    if any(k in texto_normalizado for k in ("dolor torac", "no puedo respirar", "sangrado", "desmayo", "fiebre alta", "lesion grave")):
        return "medicina"

    if area_detectada == "dieta":
        return "nutricion"
    if area_detectada == "psicologia":
        return "psicologia"
    return "medicina"


def _es_alerta_urgente_chat(
    mensaje_usuario: str,
    respuesta_ia: str,
    area_detectada: str,
    resultado_ia: Optional[Dict[str, Any]] = None,
) -> bool:
    """Activa escalado solo por señales del usuario o alerta explícita del motor IA."""
    _ = respuesta_ia
    texto_usuario = _normalizar_ascii(mensaje_usuario)
    if resultado_ia and bool(resultado_ia.get("alerta_riesgo")):
        return True

    banderas = (
        "suicid",
        "autoles",
        "no puedo respirar",
        "dolor torac",
        "desmayo",
        "sangrado",
        "fiebre alta",
        "purga",
        "vomito sangre",
        "crisis de panico",
    )
    if any(k in texto_usuario for k in banderas):
        return True

    if area_detectada == "psicologia" and any(k in texto_usuario for k in ("urgente", "emergencia")):
        return True
    return False


def _crear_derivacion_urgente_si_aplica(
    db: Session,
    paciente: Usuario,
    especialidad_destino: str,
    motivo: str,
) -> Optional[Derivacion]:
    """Crea (o reutiliza) una derivación preferente automática para urgencias."""
    rol_paciente = _rol_actual(paciente)
    if rol_paciente != "cliente":
        return None

    especialidad_norm = especialidad_destino.strip().lower()
    abierta = (
        db.query(Derivacion)
        .filter(Derivacion.paciente_id == paciente.id)
        .filter(Derivacion.especialidad_destino == especialidad_norm)
        .filter(Derivacion.estado.in_(["pendiente", "aceptada", "en_seguimiento"]))
        .order_by(Derivacion.fecha_creacion.desc(), Derivacion.id.desc())
        .first()
    )
    if abierta:
        return abierta

    rol_destino = _rol_objetivo_por_especialidad(especialidad_norm)
    destino = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == rol_destino)
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )
    if not destino:
        return None

    origen = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == "administrador")
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )

    resumen_clinico = _resumen_clinico_compacto_para_derivacion(db, paciente.id)
    motivo_base = (motivo or "").strip() or "Derivación preferente automática por alerta IA"
    if resumen_clinico:
        motivo_base = f"{motivo_base}\n\nResumen clínico automático:\n{resumen_clinico}"

    derivacion = Derivacion(
        paciente_id=paciente.id,
        origen_profesional_id=(origen.id if origen else destino.id),
        destino_profesional_id=destino.id,
        especialidad_destino=especialidad_norm,
        motivo=motivo_base[:2000],
        nota_paciente="Derivación preferente creada automáticamente por detección de urgencia en chat",
        estado="pendiente",
        leida_paciente=0,
    )
    db.add(derivacion)
    db.flush()
    return derivacion


def _resumen_clinico_compacto_para_derivacion(db: Session, paciente_id: int) -> str:
    """Genera un resumen breve para facilitar el triage del especialista destino."""
    perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == paciente_id).first()
    kpis = _calcular_kpis_paciente(db, paciente_id)
    ultimo_registro = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == paciente_id)
        .order_by(RegistroDiario.fecha.desc(), RegistroDiario.id.desc())
        .first()
    )

    partes: List[str] = []
    if perfil and perfil.imc_actual is not None:
        partes.append(f"IMC actual: {float(perfil.imc_actual):.2f} ({_clasificar_imc(float(perfil.imc_actual))})")
    if kpis.riesgo_emocional:
        partes.append(f"Riesgo emocional: {kpis.riesgo_emocional}")
    if kpis.promedio_estres_7d is not None:
        partes.append(f"Estrés 7 días: {kpis.promedio_estres_7d:.1f}/10")
    if kpis.adherencia_nutricional_pct is not None:
        partes.append(f"Adherencia nutricional: {kpis.adherencia_nutricional_pct:.0f}%")
    if ultimo_registro and ultimo_registro.sentimiento_detectado_ia:
        partes.append(f"Último sentimiento detectado: {ultimo_registro.sentimiento_detectado_ia}")
    partes.append("Acción sugerida: contactar al paciente en <24h y priorizar valoración de seguridad.")

    return " | ".join(partes)


def _sentimiento_desde_animo(animo: int, estres: int) -> str:
    """Normaliza una etiqueta de sentimiento para almacenamiento y graficas."""
    if animo <= 3 or estres >= 8:
        return "ansiedad"
    if animo <= 5:
        return "triste"
    if animo >= 8 and estres <= 4:
        return "feliz"
    return "neutral"


def _construir_nota_checkin(energia: int, estres: int, horas_sueno: float, notas: Optional[str]) -> str:
    """Serializa detalles del check-in en notas_diario manteniendo compatibilidad."""
    texto_libre = (notas or "").strip()
    return (
        f"CHECKIN|energia={energia}|estres={estres}|sueno={horas_sueno:.1f}|"
        f"notas={texto_libre}"
    )


def _parsear_nota_checkin(texto: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parsea notas_diario si fue guardada como check-in."""
    if not texto or not texto.startswith("CHECKIN|"):
        return None
    partes = texto.split("|")
    data: Dict[str, Any] = {}
    for parte in partes[1:]:
        if "=" not in parte:
            continue
        k, v = parte.split("=", 1)
        data[k] = v
    return data


def _normalizar_tipo_comida(tipo: str) -> str:
    """Normaliza el tipo de comida para mantener consistencia clínica."""
    t = _normalizar_ascii(tipo or "comida").strip()
    aliases = {
        "desayuno": "desayuno",
        "almuerzo": "comida",
        "comida": "comida",
        "cena": "cena",
        "snack": "snack",
        "merienda": "snack",
    }
    return aliases.get(t, "comida")


def _texto_meal_log(tipo: str, descripcion: str, hora: Optional[str]) -> str:
    """Codifica el registro de comida en un formato estable para parsing posterior."""
    payload = {
        "tipo": _normalizar_tipo_comida(tipo),
        "descripcion": (descripcion or "").strip(),
        "hora": (hora or "").strip() or None,
    }
    return f"[MEAL_LOG]{json.dumps(payload, ensure_ascii=False)}"


def _parsear_meal_log(texto: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parsea una entrada de comida persistida en MensajeChat."""
    base = (texto or "").strip()
    prefijo = "[MEAL_LOG]"
    if not base.startswith(prefijo):
        return None
    raw = base[len(prefijo):].strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    descripcion = str(data.get("descripcion") or "").strip()
    if not descripcion:
        return None
    return {
        "tipo": _normalizar_tipo_comida(str(data.get("tipo") or "comida")),
        "descripcion": descripcion,
        "hora": (str(data.get("hora") or "").strip() or None),
    }


def _normalizar_seccion_recurso(seccion: str) -> str:
    """Normaliza la sección de recursos solicitada por frontend."""
    s = (seccion or "").strip().lower()
    aliases = {
        "psicologia": "salud_mental",
        "mental": "salud_mental",
        "saludmental": "salud_mental",
        "nutricion": "nutricion",
        "alimentacion": "nutricion",
        "gym": "gym",
        "entrenamiento": "gym",
    }
    return aliases.get(s, s)


def _estado_bienestar_desde_checkin(parsed: Optional[Dict[str, Any]], animo: Optional[int]) -> Dict[str, Any]:
    """Calcula estado de bienestar (bien/regular/mal) con reglas simples y trazables."""
    if parsed is None or animo is None:
        return {
            "estado": "regular",
            "score": 50,
            "mensaje": "Aún no hay suficiente información de hoy para clasificar tu estado.",
        }

    try:
        energia = int(parsed.get("energia", "5"))
        estres = int(parsed.get("estres", "5"))
        sueno = float(parsed.get("sueno", "7"))
    except ValueError:
        energia, estres, sueno = 5, 5, 7.0

    score = (animo * 10) + (energia * 6) - (estres * 6) + int(sueno * 2)
    score = max(0, min(100, score))

    if score >= 65:
        return {
            "estado": "bien",
            "score": score,
            "mensaje": "Tu estado de hoy es estable. Mantén la constancia.",
        }
    if score >= 40:
        return {
            "estado": "regular",
            "score": score,
            "mensaje": "Tu estado de hoy es intermedio. Ajusta carga y prioriza hábitos base.",
        }
    return {
        "estado": "mal",
        "score": score,
        "mensaje": "Hoy estás en zona de riesgo. Baja exigencia y prioriza soporte.",
    }


def _pasos_por_estado(estado: str) -> List[str]:
    if estado == "bien":
        return ["Mantén tus horarios de comida.", "Sesión de fuerza de 30 min.", "Anota un logro hoy."]
    if estado == "regular":
        return ["Prioriza 2 litros de agua.", "Camina 15 min al aire libre.", "Cena ligera sin pantallas."]
    if estado == "mal":
        # --- PERFECCIÓN PSICOLÓGICA ---
        return [
            "⚠️ PROTOCOLO DE CRISIS: Baja la autoexigencia al mínimo. Solo hoy: hidratación y descanso.",
            "🧠 TÉCNICA CLÍNICA: Aplica la respiración 4-7-8 ahora (inhalar 4, retener 7, exhalar 8).",
            "📞 ACCIÓN: Identifica si el malestar es rumiación mental o fatiga física y escríbelo.",
            "Si el ánimo no mejora en 24h, el sistema solicitará una cita prioritaria con psicología."
        ]


def _recursos_personalizados_por_seccion(seccion: str, estado: str, registro: Optional[RegistroDiario]) -> List[RecursoPersonalizadoItem]:
    """Genera recursos dinámicos por sección y estado del día."""
    seccion_norm = _normalizar_seccion_recurso(seccion)
    notas = (registro.notas_diario if registro is not None else "") or ""
    parsed = _parsear_nota_checkin(notas)

    if seccion_norm == "salud_mental":
        recursos = [
            RecursoPersonalizadoItem(
                titulo="Respiración de descarga",
                descripcion="2-3 minutos de respiración 4-4-6 para bajar activación.",
                prioridad="alta" if estado == "mal" else "media",
            ),
            RecursoPersonalizadoItem(
                titulo="Grounding 5-4-3-2-1",
                descripcion="Conecta con el entorno para reducir rumiación y ansiedad aguda.",
                prioridad="alta" if estado != "bien" else "media",
            ),
        ]
        if estado == "mal":
            recursos.append(
                RecursoPersonalizadoItem(
                    titulo="Plan de protección",
                    descripcion="Activa apoyo: avisa a un profesional y evita quedarte aislado.",
                    prioridad="alta",
                )
            )
        if parsed is not None and int(parsed.get("estres", "5")) >= 8:
            recursos.append(
                RecursoPersonalizadoItem(
                    titulo="Bajar exigencia del día",
                    descripcion="Cancela tareas no críticas y conserva energía para descanso y autocuidado.",
                    prioridad="alta",
                )
            )
        return recursos

    if seccion_norm == "nutricion":
        recursos = [
            RecursoPersonalizadoItem(
                titulo="Comidas estructuradas",
                descripcion="Cumple 3-5 comidas pequeñas según tu energía de hoy.",
                prioridad="alta",
            ),
            RecursoPersonalizadoItem(
                titulo="Plato base",
                descripcion="Prioriza proteína, verdura y carbohidrato útil en la comida principal.",
                prioridad="media",
            ),
        ]
        if estado == "mal":
            recursos.append(
                RecursoPersonalizadoItem(
                    titulo="Modo anti-atracón",
                    descripcion="No saltes comidas; usa snack de seguridad cada 3-4 horas.",
                    prioridad="alta",
                )
            )
        return recursos

    recursos = [
        RecursoPersonalizadoItem(
            titulo="Movimiento ajustado",
            descripcion="Elige intensidad según estado: suave si estás mal, progresiva si estás bien.",
            prioridad="alta" if estado != "bien" else "media",
        ),
        RecursoPersonalizadoItem(
            titulo="Sesión corta útil",
            descripcion="20 minutos de rutina base son suficientes para mantener adherencia.",
            prioridad="media",
        ),
    ]
    if estado == "mal":
        recursos.append(
            RecursoPersonalizadoItem(
                titulo="Recuperación activa",
                descripcion="Prioriza movilidad y caminata suave en vez de alta intensidad.",
                prioridad="alta",
            )
        )
    return recursos


def _es_habito_nutricion(habito: HabitoAgenda) -> bool:
    """Clasifica hábitos nutricionales (incluye comidas marcadas)."""
    t = _normalizar_ascii(f"{habito.titulo} {habito.subtitulo}")
    return "comida" in t or "nutric" in t or "hidrat" in t


def _es_habito_gym(habito: HabitoAgenda) -> bool:
    """Clasifica hábitos de movimiento/entrenamiento."""
    t = _normalizar_ascii(f"{habito.titulo} {habito.subtitulo}")
    return any(k in t for k in ("movimiento", "caminar", "gym", "entren", "rutina"))


def _es_habito_mental(habito: HabitoAgenda) -> bool:
    """Clasifica hábitos de salud mental y regulación."""
    t = _normalizar_ascii(f"{habito.titulo} {habito.subtitulo}")
    return any(k in t for k in ("emoc", "estres", "respir", "check-in", "checkin", "sueno", "descanso"))


def _normalizar_area_recurso_preferencia(area: str) -> str:
    """Normaliza área seleccionada por el usuario en la pantalla de recursos."""
    a = _normalizar_ascii(area or "todas").strip()
    aliases = {
        "mental": "psicologia",
        "salud_mental": "psicologia",
        "saludmental": "psicologia",
        "gym": "entrenamiento",
        "entreno": "entrenamiento",
        "fitness": "entrenamiento",
        "alimentacion": "nutricion",
    }
    normalizada = aliases.get(a, a)
    validas = {"todas", "nutricion", "psicologia", "entrenamiento", "habitos"}
    return normalizada if normalizada in validas else "todas"


def _cargar_preferencias_recursos_usuario(db: Session, usuario_id: int) -> Dict[str, Any]:
    """Lee preferencias UI de recursos desde memoria persistida."""
    memoria = db.query(MemoriaChat).filter(MemoriaChat.usuario_id == usuario_id).first()
    if memoria is None:
        return {"area_seleccionada": "todas", "auto_area": True, "actualizado_en": None}

    respuestas = _leer_json_seguro(memoria.respuestas_json, {})
    if not isinstance(respuestas, dict):
        respuestas = {}

    ui = respuestas.get("ui_preferencias") if isinstance(respuestas.get("ui_preferencias"), dict) else {}
    recursos = ui.get("recursos") if isinstance(ui.get("recursos"), dict) else {}

    return {
        "area_seleccionada": _normalizar_area_recurso_preferencia(str(recursos.get("area_seleccionada") or "todas")),
        "auto_area": bool(recursos.get("auto_area", True)),
        "actualizado_en": recursos.get("actualizado_en"),
    }


def _guardar_preferencias_recursos_usuario(
    db: Session,
    usuario_id: int,
    area_seleccionada: str,
    auto_area: bool,
) -> Dict[str, Any]:
    """Guarda preferencias UI de recursos dentro de respuestas_json en MemoriaChat."""
    memoria = db.query(MemoriaChat).filter(MemoriaChat.usuario_id == usuario_id).first()
    if memoria is None:
        memoria = MemoriaChat(
            usuario_id=usuario_id,
            tema="preferencias_ui",
            preguntas_json="[]",
            respuestas_json="{}",
            activa=False,
        )
        db.add(memoria)
        db.flush()

    respuestas = _leer_json_seguro(memoria.respuestas_json, {})
    if not isinstance(respuestas, dict):
        respuestas = {}

    ui = respuestas.get("ui_preferencias") if isinstance(respuestas.get("ui_preferencias"), dict) else {}
    recursos = ui.get("recursos") if isinstance(ui.get("recursos"), dict) else {}

    recursos.update(
        {
            "area_seleccionada": _normalizar_area_recurso_preferencia(area_seleccionada),
            "auto_area": bool(auto_area),
            "actualizado_en": datetime.utcnow().isoformat(),
        }
    )
    ui["recursos"] = recursos
    respuestas["ui_preferencias"] = ui

    memoria.respuestas_json = json.dumps(respuestas, ensure_ascii=False)
    memoria.fecha_actualizacion = datetime.utcnow()
    db.commit()
    db.refresh(memoria)
    return _cargar_preferencias_recursos_usuario(db, usuario_id)


def _color_riesgo_desde_score(score: int) -> str:
    """Mapea score numérico a semáforo de riesgo."""
    if score >= 70:
        return "rojo"
    if score >= 40:
        return "amarillo"
    return "verde"


def _calcular_inteligencia_recursos(db: Session, usuario_id: int) -> Dict[str, Any]:
    """
    Calcula área recomendada + riesgo por área usando señales reales:
    check-in (ánimo/estrés/sueño/energía), adherencia diaria y lenguaje reciente de chat.
    """
    ahora = datetime.utcnow()
    hoy = ahora.date()

    registro = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_id)
        .order_by(RegistroDiario.fecha.desc(), RegistroDiario.id.desc())
        .first()
    )

    parsed = _parsear_nota_checkin(registro.notas_diario if registro else None)
    animo = int(registro.estado_animo_puntuacion) if registro and registro.estado_animo_puntuacion is not None else 6
    sentimiento = _normalizar_ascii(str(registro.sentimiento_detectado_ia or "")) if registro else ""

    energia = 5
    estres = 5
    sueno = 7.0
    if parsed is not None:
        try:
            energia = int(parsed.get("energia", "5"))
            estres = int(parsed.get("estres", "5"))
            sueno = float(parsed.get("sueno", "7"))
        except Exception:
            energia, estres, sueno = 5, 5, 7.0

    habitos = (
        db.query(HabitoAgenda)
        .filter(HabitoAgenda.usuario_id == usuario_id, HabitoAgenda.dia_semana == hoy.weekday())
        .all()
    )

    def _pct(items: List[HabitoAgenda]) -> float:
        if not items:
            return 50.0
        done = len([i for i in items if bool(i.completado)])
        return round((done / len(items)) * 100, 2)

    pct_nutri = _pct([h for h in habitos if _es_habito_nutricion(h)])
    pct_gym = _pct([h for h in habitos if _es_habito_gym(h)])
    pct_mental = _pct([h for h in habitos if _es_habito_mental(h)])

    # Score base por área (0-100)
    score = {
        "nutricion": 20,
        "psicologia": 20,
        "entrenamiento": 20,
    }

    # Señales de check-in
    if animo <= 3:
        score["psicologia"] += 35
        score["nutricion"] += 10
        score["entrenamiento"] += 10
    elif animo <= 5:
        score["psicologia"] += 20

    if estres >= 8:
        score["psicologia"] += 30
        score["nutricion"] += 12
        score["entrenamiento"] += 12
    elif estres >= 6:
        score["psicologia"] += 15

    if energia <= 3:
        score["entrenamiento"] += 25
        score["psicologia"] += 8
    elif energia <= 5:
        score["entrenamiento"] += 12

    if sueno < 5.5:
        score["psicologia"] += 18
        score["entrenamiento"] += 16
        score["nutricion"] += 8
    elif sueno < 6.5:
        score["psicologia"] += 10
        score["entrenamiento"] += 8

    # Adherencia por área
    if pct_nutri < 50:
        score["nutricion"] += 22
    elif pct_nutri < 70:
        score["nutricion"] += 12

    if pct_gym < 50:
        score["entrenamiento"] += 22
    elif pct_gym < 70:
        score["entrenamiento"] += 12

    if pct_mental < 50:
        score["psicologia"] += 22
    elif pct_mental < 70:
        score["psicologia"] += 12

    # Sentimiento detectado
    if any(k in sentimiento for k in ("ansied", "trist", "depres", "miedo", "agob")):
        score["psicologia"] += 15
    if any(k in sentimiento for k in ("atracon", "culpa", "hambre", "comida")):
        score["nutricion"] += 15

    # Señales recientes de chat del usuario
    mensajes = (
        db.query(MensajeChat)
        .filter(MensajeChat.usuario_id == usuario_id, MensajeChat.emisor == "user")
        .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
        .limit(12)
        .all()
    )
    texto_chat = _normalizar_ascii(" ".join([(m.texto or "") for m in mensajes]))

    claves = {
        "nutricion": ("dieta", "comida", "hambre", "atracon", "macros", "kcal", "cena"),
        "psicologia": ("ansiedad", "estres", "animo", "insomnio", "triste", "rumi", "psic"),
        "entrenamiento": ("rutina", "entreno", "gym", "fuerza", "cardio", "dolor", "lesion", "fitness"),
    }
    chat_hits = {
        area: sum(1 for k in keywords if k in texto_chat)
        for area, keywords in claves.items()
    }
    for area, hits in chat_hits.items():
        score[area] += min(18, hits * 3)

    for area in score:
        score[area] = max(0, min(100, int(score[area])))

    # Recomendación de área: mezcla riesgo + intención reciente
    ordenadas = sorted(score.items(), key=lambda x: x[1], reverse=True)
    area_top, score_top = ordenadas[0]
    area_second, score_second = ordenadas[1]

    # Si dos áreas están casi empatadas y en alto riesgo, recomendamos vista integral
    if score_top >= 65 and abs(score_top - score_second) <= 8:
        area_recomendada = "todas"
    else:
        area_recomendada = area_top

    riesgo_por_area = {
        "nutricion": _color_riesgo_desde_score(score["nutricion"]),
        "psicologia": _color_riesgo_desde_score(score["psicologia"]),
        "entrenamiento": _color_riesgo_desde_score(score["entrenamiento"]),
    }
    semaforo_global = _color_riesgo_desde_score(max(score.values()))

    motivo = (
        f"Recomendación basada en ánimo {animo}/10, estrés {estres}/10, sueño {round(sueno, 1)}h, "
        f"adherencia (N {pct_nutri:.0f}%, E {pct_gym:.0f}%, M {pct_mental:.0f}%) y señales recientes del chat."
    )

    return {
        "area_recomendada": area_recomendada,
        "motivo": motivo,
        "riesgo_por_area": riesgo_por_area,
        "score_por_area": score,
        "semaforo_global": semaforo_global,
        "actualizado_en": ahora.isoformat(),
    }


def _normalizar_trastorno(trastorno: str) -> str:
    """Normaliza trastornos clínicos soportados por el protocolo hospitalario."""
    normalizado = trastorno.strip().lower()
    if normalizado not in TRASTORNOS_CLINICOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trastorno inválido. Usa: tca, ansiedad o depresion",
        )
    return normalizado


def _normalizar_severidad(severidad: str) -> str:
    """Normaliza severidad clínica del caso."""
    normalizado = severidad.strip().lower()
    if normalizado not in SEVERIDADES_CLINICAS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Severidad inválida. Usa: leve, moderado o severo",
        )
    return normalizado


def _normalizar_objetivo_riesgo_plan(objetivo: str, riesgo: str) -> tuple[str, str]:
    """Valida catálogos de objetivo nutricional y riesgo metabólico."""
    objetivo_norm = objetivo.strip().lower()
    riesgo_norm = riesgo.strip().lower()

    if objetivo_norm not in OBJETIVOS_NUTRICIONALES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "objetivo_clinico inválido. Usa: perdida_grasa, mantenimiento, "
                "ganancia_muscular, recomposicion o recuperacion_clinica"
            ),
        )
    if riesgo_norm not in RIESGOS_METABOLICOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="riesgo_metabolico inválido. Usa: bajo, medio o alto",
        )
    return objetivo_norm, riesgo_norm


def _validar_coherencia_plan_nutricional(payload: PlanNutricionalUpsertRequest) -> None:
    """Valida coherencia clínica básica entre kcal, macros, objetivo y riesgo."""
    objetivo, riesgo = _normalizar_objetivo_riesgo_plan(
        payload.objetivo_clinico,
        payload.riesgo_metabolico,
    )

    kcal_macros = (payload.proteinas_g * 4) + (payload.carbohidratos_g * 4) + (payload.grasas_g * 9)
    if payload.calorias_objetivo <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="calorias_objetivo inválido")

    desviacion = abs(kcal_macros - payload.calorias_objetivo) / payload.calorias_objetivo
    if desviacion > 0.15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las calorías no son coherentes con los macros (desviación > 15%)",
        )

    pct_prot = (payload.proteinas_g * 4) / payload.calorias_objetivo
    pct_carb = (payload.carbohidratos_g * 4) / payload.calorias_objetivo
    pct_fat = (payload.grasas_g * 9) / payload.calorias_objetivo

    if not (0.10 <= pct_prot <= 0.40 and 0.20 <= pct_carb <= 0.65 and 0.15 <= pct_fat <= 0.40):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Distribución de macros fuera de rango clínico seguro",
        )

    if objetivo == "perdida_grasa" and pct_prot < 0.20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para pérdida de grasa se requiere al menos 20% de proteínas",
        )
    if objetivo == "ganancia_muscular" and (pct_prot < 0.18 or pct_carb < 0.35):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Para ganancia muscular se recomienda proteína >=18% y carbohidratos >=35%",
        )

    if riesgo == "alto":
        if payload.calorias_objetivo > 3000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Riesgo alto: objetivo calórico no debe superar 3000 kcal/día",
            )
        if not (0.18 <= pct_prot <= 0.35 and 0.20 <= pct_fat <= 0.35):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Riesgo alto: ajustar proteína (18-35%) y grasa (20-35%)",
            )


def _asegurar_protocolos_hospitalarios_base(db: Session) -> None:
    """Carga protocolos base hospitalarios si no existen en el entorno."""
    existentes = db.query(ProtocoloHospitalario).count()
    if existentes > 0:
        return

    for item in PROTOCOLS_BASE:
        db.add(
            ProtocoloHospitalario(
                trastorno=item["trastorno"],
                severidad=item["severidad"],
                especialidad=item["especialidad"],
                titulo=item["titulo"],
                checklist_json=json.dumps(item["checklist"], ensure_ascii=False),
                ruta_escalado=item["ruta_escalado"],
                activo=True,
                fecha_actualizacion=datetime.utcnow(),
            )
        )
    db.commit()


def _asegurar_recursos_clinicos_base(db: Session) -> None:
    """Carga recursos clínicos base sin duplicar, incluso en bases ya inicializadas."""
    insertados = 0
    for item in CLINICAL_RESOURCES_BASE:
        existe = (
            db.query(RecursoClinico)
            .filter(RecursoClinico.trastorno == item["trastorno"])
            .filter(RecursoClinico.especialidad == item["especialidad"])
            .filter(RecursoClinico.titulo == item["titulo"])
            .first()
        )
        if existe:
            continue

        db.add(
            RecursoClinico(
                trastorno=item["trastorno"],
                especialidad=item["especialidad"],
                titulo=item["titulo"],
                descripcion=item["descripcion"],
                url=item["url"],
                nivel_evidencia=item["nivel_evidencia"],
                activo=True,
                fecha_actualizacion=datetime.utcnow(),
            )
        )
        insertados += 1

    if insertados:
        db.commit()


def _normalizar_estado_derivacion(estado: str) -> str:
    """Normaliza estados permitidos para el flujo de derivaciones."""
    e = estado.strip().lower()
    permitidos = {"pendiente", "aceptada", "en_seguimiento", "cerrada", "rechazada"}
    if e not in permitidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado invalido. Usa: pendiente, aceptada, en_seguimiento, cerrada o rechazada",
        )
    return e


def _clasificar_imc(imc: float) -> str:
    """Devuelve un rango corto para mostrar estado de IMC en frontend."""
    if imc < 18.5:
        return "aviso"
    if imc < 25:
        return "normal"
    if imc < 30:
        return "sobrepeso"
    return "aviso"


def _serializar_evaluacion_ia(evaluacion: EvaluacionIA) -> EvaluacionIAResponse:
    """Convierte persistencia de evaluación IA a esquema de salida."""
    respuestas: Dict[str, str] = {}
    try:
        parsed = json.loads(evaluacion.respuestas_json)
        if isinstance(parsed, dict):
            respuestas = {str(k): str(v) for k, v in parsed.items()}
    except Exception:
        respuestas = {}

    return EvaluacionIAResponse(
        seccion=evaluacion.seccion,
        respuestas=respuestas,
        plan_ia=evaluacion.plan_ia,
        fecha_actualizacion=evaluacion.fecha_actualizacion.isoformat(),
    )


def _serializar_mensaje_chat(mensaje: MensajeChat) -> ChatHistorialItemResponse:
    """Convierte mensaje persistido de chat a esquema de salida."""
    activos_premium: List[Dict[str, str]] = []
    if mensaje.activos_premium_json:
        try:
            parsed = json.loads(mensaje.activos_premium_json)
            if isinstance(parsed, list):
                activos_premium = [
                    {str(k): str(v) for k, v in item.items()}
                    for item in parsed
                    if isinstance(item, dict)
                ]
        except Exception:
            activos_premium = []

    return ChatHistorialItemResponse(
        id=mensaje.id,
        emisor=mensaje.emisor,
        texto=mensaje.texto,
        peso_registrado=float(mensaje.peso_registrado) if mensaje.peso_registrado is not None else None,
        imc_calculado=float(mensaje.imc_calculado) if mensaje.imc_calculado is not None else None,
        imc_rango=mensaje.imc_rango,
        solicitar_altura=bool(mensaje.solicitar_altura),
        activos_premium=activos_premium,
        fecha=mensaje.fecha_creacion.isoformat(),
        conversation_id=mensaje.conversation_id,
        conversation_title=mensaje.conversation_title,
        conversation_pinned=bool(mensaje.conversation_pinned),
    )


def _resumir_titulo_conversacion(texto: str) -> str:
    """Genera un título corto y legible a partir del primer mensaje del usuario."""
    base = re.sub(r"\s+", " ", (texto or "").strip())
    if not base:
        return "Nuevo chat"
    return f"{base[:57]}..." if len(base) > 60 else base


def _conversation_id_chat(payload: ChatRequest, sender_limpio: str) -> str:
    """Resuelve conversation_id reutilizable sin requerir tabla adicional."""
    raw = (payload.conversation_id or "").strip()
    if raw:
        return raw[:80]
    return f"chat-{sender_limpio}-{int(datetime.utcnow().timestamp())}"


def _obtener_metadata_conversacion(
    db: Session,
    usuario_id: int,
    conversation_id: str,
    titulo_sugerido: str,
) -> Dict[str, Any]:
    """Recupera metadata persistida de una conversación para no pisar renombres o fijados."""
    ultimo = (
        db.query(MensajeChat)
        .filter(
            MensajeChat.usuario_id == usuario_id,
            MensajeChat.conversation_id == conversation_id,
        )
        .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
        .first()
    )
    if ultimo is None:
        return {"titulo": titulo_sugerido, "fijada": False}
    titulo = (ultimo.conversation_title or "").strip() or titulo_sugerido
    return {"titulo": titulo, "fijada": bool(ultimo.conversation_pinned)}


def _listar_conversaciones_usuario(
    db: Session,
    usuario_id: int,
    q: Optional[str] = None,
) -> List[ChatConversationResponse]:
    """Agrupa mensajes por conversación para el sidebar del chat."""
    mensajes = (
        db.query(MensajeChat)
        .filter(MensajeChat.usuario_id == usuario_id)
        .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
        .all()
    )

    agrupadas: Dict[str, Dict[str, Any]] = {}
    filtro = (q or "").strip().lower()
    for mensaje in mensajes:
        conversation_id = (mensaje.conversation_id or f"legacy-{usuario_id}").strip()
        item = agrupadas.get(conversation_id)
        if item is None:
            titulo = (mensaje.conversation_title or "").strip() or _resumir_titulo_conversacion(mensaje.texto)
            ultimo = (mensaje.texto or "").strip()
            if filtro and filtro not in titulo.lower() and filtro not in ultimo.lower():
                continue
            agrupadas[conversation_id] = {
                "conversation_id": conversation_id,
                "titulo": titulo,
                "ultimo_mensaje": ultimo,
                "fecha_ultimo_mensaje": mensaje.fecha_creacion.isoformat(),
                "total_mensajes": 1,
                "fijada": bool(mensaje.conversation_pinned),
            }
            continue
        item["total_mensajes"] += 1

    items = [ChatConversationResponse(**item) for item in agrupadas.values()]
    items.sort(
        key=lambda item: (
            not item.fijada,
            -(datetime.fromisoformat(item.fecha_ultimo_mensaje).timestamp()),
        )
    )
    return items


def _serializar_medicacion(medicacion: MedicacionAsignada) -> MedicacionResponse:
    """Convierte medicación persistida en respuesta para frontend."""
    return MedicacionResponse(
        id=medicacion.id,
        paciente_id=medicacion.paciente_id,
        profesional_id=medicacion.profesional_id,
        profesional_nombre=(
            medicacion.profesional.nombre
            if medicacion.profesional is not None
            else f"Profesional {medicacion.profesional_id}"
        ),
        medicamento=medicacion.medicamento,
        dosis=medicacion.dosis,
        frecuencia=medicacion.frecuencia,
        instrucciones=medicacion.instrucciones,
        activa=bool(medicacion.activa),
        fecha_inicio=medicacion.fecha_inicio.isoformat(),
        fecha_actualizacion=medicacion.fecha_actualizacion.isoformat(),
    )


def _extraer_titulo_nota_clinica(texto: str) -> str:
    """Extrae título de nota clínica persistida en formato [NOTA_CLINICA] Título\ncontenido."""
    raw = (texto or "").strip()
    if not raw.startswith("[NOTA_CLINICA]"):
        return "Nota clínica"
    linea = raw.splitlines()[0]
    titulo = linea.replace("[NOTA_CLINICA]", "").strip()
    return titulo or "Nota clínica"


def _extraer_cuerpo_nota_clinica(texto: str) -> str:
    """Extrae el cuerpo de la nota clínica desde el mensaje persistido."""
    raw = (texto or "").strip()
    if "\n" not in raw:
        return ""
    return raw.split("\n", 1)[1].strip()


def _serializar_nota_clinica(mensaje: MensajeChat, paciente_id: int) -> NotaClinicaResponse:
    """Convierte mensaje de tipo profesional en nota clínica estructurada."""
    return NotaClinicaResponse(
        id=mensaje.id,
        paciente_id=paciente_id,
        profesional_id=mensaje.usuario_id,
        profesional_nombre=(mensaje.usuario.nombre if mensaje.usuario is not None else f"Profesional {mensaje.usuario_id}"),
        titulo=_extraer_titulo_nota_clinica(mensaje.texto),
        contenido=_extraer_cuerpo_nota_clinica(mensaje.texto),
        fecha_creacion=mensaje.fecha_creacion.isoformat(),
    )


def _serializar_plan_nutricional(plan: PlanNutricionalClinico) -> PlanNutricionalResponse:
    """Convierte plan nutricional persistido para panel clínico."""
    return PlanNutricionalResponse(
        id=plan.id,
        paciente_id=plan.paciente_id,
        profesional_id=plan.profesional_id,
        profesional_nombre=(
            plan.profesional.nombre
            if plan.profesional is not None
            else f"Profesional {plan.profesional_id}"
        ),
        calorias_objetivo=int(plan.calorias_objetivo),
        proteinas_g=int(plan.proteinas_g),
        carbohidratos_g=int(plan.carbohidratos_g),
        grasas_g=int(plan.grasas_g),
        objetivo_clinico=plan.objetivo_clinico,
        riesgo_metabolico=plan.riesgo_metabolico,
        observaciones=plan.observaciones,
        activo=bool(plan.activo),
        fecha_actualizacion=plan.fecha_actualizacion.isoformat(),
    )


def _parsear_checklist_json(checklist_json: str) -> List[str]:
    """Recupera checklist almacenado como JSON de texto."""
    try:
        data = json.loads(checklist_json)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def _serializar_protocolo_hospitalario(item: ProtocoloHospitalario) -> ProtocoloHospitalarioResponse:
    """Convierte plantilla de protocolo a respuesta API."""
    return ProtocoloHospitalarioResponse(
        id=item.id,
        trastorno=item.trastorno,
        severidad=item.severidad,
        especialidad=item.especialidad,
        titulo=item.titulo,
        checklist=_parsear_checklist_json(item.checklist_json),
        ruta_escalado=item.ruta_escalado,
        activo=bool(item.activo),
        fecha_actualizacion=item.fecha_actualizacion.isoformat(),
    )


def _serializar_checklist_clinico(item: ChecklistClinicoPaciente) -> ChecklistClinicoResponse:
    """Convierte checklist clínico persistido de paciente."""
    return ChecklistClinicoResponse(
        id=item.id,
        paciente_id=item.paciente_id,
        profesional_id=item.profesional_id,
        profesional_nombre=(
            item.profesional.nombre
            if item.profesional is not None
            else f"Profesional {item.profesional_id}"
        ),
        trastorno=item.trastorno,
        severidad=item.severidad,
        especialidad=item.especialidad,
        checklist=_parsear_checklist_json(item.checklist_json),
        requiere_escalado=bool(item.requiere_escalado),
        ruta_escalado_aplicada=item.ruta_escalado_aplicada,
        observaciones=item.observaciones,
        fecha_actualizacion=item.fecha_actualizacion.isoformat(),
    )


def _serializar_checklist_historial(item: ChecklistClinicoHistorial) -> ChecklistClinicoHistorialItemResponse:
    """Convierte evento de auditoría de checklist clínico para timeline."""
    return ChecklistClinicoHistorialItemResponse(
        id=item.id,
        checklist_id=item.checklist_id,
        paciente_id=item.paciente_id,
        profesional_id=item.profesional_id,
        version=item.version,
        checklist=_parsear_checklist_json(item.checklist_json),
        requiere_escalado=bool(item.requiere_escalado),
        ruta_escalado_aplicada=item.ruta_escalado_aplicada,
        observaciones=item.observaciones,
        fecha_evento=item.fecha_evento.isoformat(),
    )


def _sugerir_severidad_desde_kpis(kpis: PacienteKpisResponse) -> SeveridadSugeridaResponse:
    """Calcula severidad sugerida combinando riesgo emocional, estrés y adherencia."""
    score = 0
    motivos: List[str] = []

    if kpis.riesgo_emocional == "alto":
        score += 3
        motivos.append("Riesgo emocional alto")
    elif kpis.riesgo_emocional == "medio":
        score += 2
        motivos.append("Riesgo emocional medio")

    if kpis.promedio_estres_7d is not None and kpis.promedio_estres_7d >= 7:
        score += 2
        motivos.append("Estrés promedio elevado")
    if kpis.promedio_animo_7d is not None and kpis.promedio_animo_7d <= 4:
        score += 2
        motivos.append("Ánimo promedio bajo")

    if kpis.derivaciones_abiertas >= 2:
        score += 1
        motivos.append("Múltiples derivaciones abiertas")
    if kpis.farmacos_activos >= 2:
        score += 1
        motivos.append("Polifarmacia activa")

    if kpis.adherencia_nutricional_pct is not None and kpis.adherencia_nutricional_pct < 40:
        score += 1
        motivos.append("Adherencia nutricional baja")
    if kpis.adherencia_habitos_pct is not None and kpis.adherencia_habitos_pct < 40:
        score += 1
        motivos.append("Adherencia de hábitos baja")

    if score >= 6:
        severidad = "severo"
    elif score >= 3:
        severidad = "moderado"
    else:
        severidad = "leve"

    if not motivos:
        motivos.append("Sin alertas clínicas relevantes en la ventana analizada")

    return SeveridadSugeridaResponse(
        paciente_id=kpis.paciente_id,
        severidad_sugerida=severidad,
        puntuacion_riesgo=score,
        motivos=motivos,
    )


def _serializar_recurso_clinico(item: RecursoClinico) -> RecursoClinicoResponse:
    """Convierte recurso clínico de repositorio hospitalario."""
    url = (item.url or "").strip()
    if not url:
        # Fallback estable para evitar tarjetas vacías en recursos.
        query = quote_plus(f"{item.trastorno} {item.especialidad} guia clinica")
        url = f"https://www.google.com/search?q={query}"

    return RecursoClinicoResponse(
        id=item.id,
        trastorno=item.trastorno,
        especialidad=item.especialidad,
        titulo=item.titulo,
        descripcion=item.descripcion,
        url=url,
        nivel_evidencia=item.nivel_evidencia,
        activo=bool(item.activo),
        fecha_actualizacion=item.fecha_actualizacion.isoformat(),
    )


def _calcular_rachas(fechas: List[datetime.date]) -> Dict[str, Any]:
    """Calcula racha actual y mejor racha de dias consecutivos."""
    if not fechas:
        return {"actual": 0, "mejor": 0, "ultima": None}

    unicas = sorted(set(fechas))
    mejor = 1
    actual_segmento = 1
    for i in range(1, len(unicas)):
        if (unicas[i] - unicas[i - 1]).days == 1:
            actual_segmento += 1
        else:
            actual_segmento = 1
        if actual_segmento > mejor:
            mejor = actual_segmento

    hoy = datetime.utcnow().date()
    racha_actual = 0
    cursor = hoy
    while cursor in set(unicas):
        racha_actual += 1
        cursor = cursor - timedelta(days=1)

    ultima = unicas[-1].isoformat() if unicas else None
    return {"actual": racha_actual, "mejor": mejor, "ultima": ultima}


def _serializar_derivacion(der: Derivacion) -> DerivacionResponse:
    """Convierte modelo Derivacion en esquema de salida."""
    return DerivacionResponse(
        id=der.id,
        paciente_id=der.paciente_id,
        paciente_nombre=der.paciente.nombre if der.paciente else f"Paciente {der.paciente_id}",
        origen_profesional_id=der.origen_profesional_id,
        origen_profesional_nombre=(
            der.origen_profesional.nombre
            if der.origen_profesional
            else f"Profesional {der.origen_profesional_id}"
        ),
        destino_profesional_id=der.destino_profesional_id,
        destino_profesional_nombre=(
            der.destino_profesional.nombre
            if der.destino_profesional
            else f"Profesional {der.destino_profesional_id}"
        ),
        especialidad_destino=der.especialidad_destino,
        motivo=der.motivo,
        nota_paciente=der.nota_paciente,
        estado=der.estado,
        leida_paciente=bool(der.leida_paciente),
        fecha_creacion=der.fecha_creacion.isoformat(),
    )


def _parse_iso_datetime(valor: str, campo: str) -> datetime:
    """Parsea una fecha ISO y lanza un error HTTP 400 si es inválida."""
    try:
        texto = (valor or "").strip()
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato inválido para '{campo}'. Usa ISO-8601, por ejemplo 2026-04-20T10:30:00",
        ) from e


def _serializar_cita_disponible(cita: CitaDisponible) -> CitaDisponibleResponse:
    """Convierte un hueco de agenda en respuesta de API."""
    return CitaDisponibleResponse(
        id=cita.id,
        especialista_id=cita.especialista_id,
        especialista_nombre=(
            cita.especialista.nombre
            if cita.especialista is not None
            else f"Especialista {cita.especialista_id}"
        ),
        especialidad=cita.especialidad,
        inicio=cita.inicio.isoformat(),
        fin=cita.fin.isoformat(),
        estado=cita.estado,
        notas=cita.notas,
    )


def _serializar_cita_reservada(cita: CitaReservada) -> CitaReservadaResponse:
    """Convierte una cita reservada en respuesta de API."""
    return CitaReservadaResponse(
        id=cita.id,
        cita_disponible_id=cita.cita_disponible_id,
        paciente_id=cita.paciente_id,
        paciente_nombre=(
            cita.paciente.nombre
            if cita.paciente is not None
            else f"Paciente {cita.paciente_id}"
        ),
        especialista_id=cita.especialista_id,
        especialista_nombre=(
            cita.especialista.nombre
            if cita.especialista is not None
            else f"Especialista {cita.especialista_id}"
        ),
        especialidad=cita.especialidad,
        inicio=cita.inicio.isoformat(),
        fin=cita.fin.isoformat(),
        motivo=cita.motivo,
        prioridad_ia=cita.prioridad_ia,
        puntuacion_prioridad=int(cita.puntuacion_prioridad),
        justificacion_ia=cita.justificacion_ia or "",
        estado=cita.estado,
        fecha_creacion=cita.fecha_creacion.isoformat(),
    )


def _clasificar_prioridad_cita_ia(
    especialidad_destino: str,
    motivo: str,
    formulario: CitaFormularioTriageRequest,
) -> TriajeCitaIAResponse:
    """Triage local asistido por reglas clínicas para decidir preferencia de cita."""
    texto = _normalizar_ascii(f"{motivo} {' '.join(formulario.sintomas_clave)} {(formulario.riesgo_psicologico or '')}")
    score = 0
    razones: List[str] = []

    if formulario.nivel_dolor >= 8:
        score += 3
        razones.append("dolor intenso")
    elif formulario.nivel_dolor >= 6:
        score += 2
        razones.append("dolor moderado-alto")

    if formulario.ansiedad_actual >= 8:
        score += 3
        razones.append("ansiedad muy alta")
    elif formulario.ansiedad_actual >= 6:
        score += 2
        razones.append("ansiedad relevante")

    if formulario.horas_sueno < 4:
        score += 2
        razones.append("sueño muy reducido")
    elif formulario.horas_sueno < 6:
        score += 1
        razones.append("sueño insuficiente")

    impacto = _normalizar_ascii(formulario.impacto_funcional)
    if impacto in {"severo", "alto", "grave"}:
        score += 3
        razones.append("alto impacto funcional")
    elif impacto in {"moderado", "medio"}:
        score += 1
        razones.append("impacto funcional moderado")

    if formulario.duracion_dias >= 30:
        score += 1
        razones.append("problema persistente")

    banderas_rojas = [
        "autolesion",
        "suicid",
        "purga",
        "atracon",
        "desmayo",
        "sangrado",
        "dolor torac",
        "fiebre alta",
        "crisis de panico",
        "no puedo respirar",
    ]
    if any(k in texto for k in banderas_rojas):
        score += 4
        razones.append("bandera roja detectada")

    if _normalizar_ascii(especialidad_destino) in {"psicologia", "salud_mental", "psicologo"}:
        if any(k in texto for k in ("obsesion", "toc", "rumiacion", "depres", "ansiedad", "panico")):
            score += 1
            razones.append("sintomatología psicológica activa")

    prioridad = "normal"
    max_horas = 168
    if score >= 7:
        prioridad = "preferente"
        max_horas = 24
    elif score >= 4:
        prioridad = "preferente"
        max_horas = 72

    justificacion = ", ".join(razones) if razones else "sin indicadores clínicos de urgencia"
    return TriajeCitaIAResponse(
        prioridad=prioridad,
        puntuacion=score,
        preferente=(prioridad == "preferente"),
        max_horas_recomendadas=max_horas,
        justificacion=justificacion,
    )


def _serializar_habito_agenda(habito: HabitoAgenda) -> HabitoAgendaResponse:
    """Convierte un habito persistido en su esquema de salida."""
    return HabitoAgendaResponse(
        id=habito.id,
        usuario_id=habito.usuario_id,
        dia_semana=habito.dia_semana,
        titulo=habito.titulo,
        subtitulo=habito.subtitulo,
        franja=habito.franja,
        color_hex=habito.color_hex,
        orden=habito.orden,
        completado=bool(habito.completado),
        ultima_actualizacion=habito.ultima_actualizacion.isoformat() if habito.ultima_actualizacion else None,
    )


def _calcular_kpis_paciente(db: Session, paciente_id: int) -> PacienteKpisResponse:
    """Calcula KPIs clínicos de 7 días para consumo del panel profesional."""
    hoy = datetime.utcnow().date()
    inicio = hoy - timedelta(days=6)

    registros = (
        db.query(RegistroDiario)
        .filter(
            RegistroDiario.usuario_id == paciente_id,
            RegistroDiario.fecha >= inicio,
            RegistroDiario.fecha <= hoy,
        )
        .order_by(RegistroDiario.fecha.asc(), RegistroDiario.id.asc())
        .all()
    )

    checkins = []
    estreses = []
    analisis_nutricional = 0
    consecutivos_riesgo = 0
    max_consecutivos_riesgo = 0

    for r in registros:
        if r.analisis_nutricional_ia:
            analisis_nutricional += 1

        sentimiento = (r.sentimiento_detectado_ia or "").strip().lower()
        if sentimiento in {"ansiedad", "triste", "malestar", "estres", "estrés"}:
            consecutivos_riesgo += 1
            if consecutivos_riesgo > max_consecutivos_riesgo:
                max_consecutivos_riesgo = consecutivos_riesgo
        else:
            consecutivos_riesgo = 0

        parsed = _parsear_nota_checkin(r.notas_diario)
        if parsed and r.estado_animo_puntuacion is not None:
            checkins.append(int(r.estado_animo_puntuacion))
            try:
                estreses.append(int(parsed.get("estres", "0")))
            except ValueError:
                pass

    promedio_animo = round(sum(checkins) / len(checkins), 2) if checkins else None
    promedio_estres = round(sum(estreses) / len(estreses), 2) if estreses else None

    # Proxy de adherencia nutricional: días con análisis nutricional IA útil en ventana de 7 días.
    adherencia_nutricional = round((analisis_nutricional / 7) * 100, 2)

    habitos = (
        db.query(HabitoAgenda)
        .filter(
            HabitoAgenda.usuario_id == paciente_id,
            HabitoAgenda.ultima_actualizacion >= datetime.combine(inicio, time.min),
        )
        .all()
    )
    if habitos:
        completados = len([h for h in habitos if bool(h.completado)])
        adherencia_habitos = round((completados / len(habitos)) * 100, 2)
    else:
        adherencia_habitos = None

    farmacos_activos = (
        db.query(MedicacionAsignada)
        .filter(MedicacionAsignada.paciente_id == paciente_id, MedicacionAsignada.activa == True)
        .count()
    )

    derivaciones = (
        db.query(Derivacion)
        .filter(Derivacion.paciente_id == paciente_id)
        .filter(Derivacion.estado.in_(["pendiente", "aceptada", "en_seguimiento"]))
        .all()
    )
    derivaciones_abiertas = len(derivaciones)
    coordinacion_especialistas = len({d.destino_profesional_id for d in derivaciones})

    if max_consecutivos_riesgo >= 3 or (promedio_animo is not None and promedio_animo <= 3):
        riesgo_emocional = "alto"
    elif (promedio_animo is not None and promedio_animo <= 5) or (promedio_estres is not None and promedio_estres >= 7):
        riesgo_emocional = "medio"
    elif promedio_animo is None:
        riesgo_emocional = "sin_datos"
    else:
        riesgo_emocional = "bajo"

    return PacienteKpisResponse(
        paciente_id=paciente_id,
        checkins_7d=len(checkins),
        promedio_animo_7d=promedio_animo,
        promedio_estres_7d=promedio_estres,
        adherencia_nutricional_pct=adherencia_nutricional,
        adherencia_habitos_pct=adherencia_habitos,
        riesgo_emocional=riesgo_emocional,
        farmacos_activos=farmacos_activos,
        derivaciones_abiertas=derivaciones_abiertas,
        coordinacion_especialistas=coordinacion_especialistas,
    )


def _parsear_color_hex(color_hex: str) -> str:
    """Normaliza un color hexadecimal para la agenda."""
    color = color_hex.strip()
    if not color.startswith("#"):
        color = f"#{color}"
    return color


def _semilla_habitos_base(usuario_id: int, dia_semana: int) -> List[HabitoAgenda]:
    """Genera la agenda base para un usuario y dia concretos."""
    return [
        HabitoAgenda(
            usuario_id=usuario_id,
            dia_semana=dia_semana,
            titulo=item["titulo"],
            subtitulo=item["subtitulo"],
            franja=item["franja"],
            color_hex=_parsear_color_hex(item["color_hex"]),
            orden=item["orden"],
            completado=False,
        )
        for item in HABITOS_BASE
    ]


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


def _calcular_rango_imc(imc: float) -> str:
    """Determina el rango de IMC: 'normal', 'sobrepeso' o 'aviso'."""
    if imc < 18.5:
        return "aviso"  # Bajo peso
    elif imc < 25:
        return "normal"  # Peso normal
    elif imc < 30:
        return "sobrepeso"  # Sobrepeso
    else:
        return "aviso"  # Obesidad


def _normalizar_sentimiento(texto: str) -> Optional[str]:
    """Detecta y normaliza sentimiento principal desde texto libre."""
    t = texto.lower()

    if any(k in t for k in ["ansied", "ansioso", "ansiosa", "malestar", "estres", "estrés"]):
        return "ansiedad"
    if any(k in t for k in ["triste", "deprim", "desanim", "mal", "fatal"]):
        return "triste"
    if any(k in t for k in ["feliz", "bien", "motivad", "genial", "positivo", "contento", "contenta"]):
        return "feliz"
    return None


def _sentimiento_a_valor(sentimiento: str) -> int:
    """Mapea sentimientos a valores numericos para graficas."""
    s = (sentimiento or "").strip().lower()
    if s in ["feliz", "motivacion", "motivación", "bien", "positivo"]:
        return 3
    if s in ["ansiedad", "ansioso", "ansiosa", "malestar", "estres", "estrés"]:
        return 2
    if s in ["triste", "deprimido", "deprimida", "tristeza"]:
        return 1
    return 2


def _extraer_imcs_desde_notas(registros: List[RegistroDiario]) -> List[Dict[str, Any]]:
    """Extrae historial de IMC desde notas_diario en formato 'IMC: <valor>'."""
    resultados: List[Dict[str, Any]] = []
    patron = re.compile(r"imc\s*:\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)

    for r in registros:
        if not r.notas_diario:
            continue
        m = patron.search(r.notas_diario)
        if m:
            try:
                valor = float(m.group(1).replace(",", "."))
                resultados.append({"fecha": r.fecha.isoformat(), "imc": round(valor, 2)})
            except ValueError:
                continue

    return resultados


def _calcular_alerta_profesional(series: List[AnimoDiaResponse]) -> bool:
    """Activa alerta si hay 3 dias seguidos de ansiedad o malestar."""
    consecutivos = 0
    for punto in series:
        sentimiento = punto.sentimiento.lower()
        if sentimiento in ["ansiedad", "malestar", "ansioso", "ansiosa", "estres", "estrés"]:
            consecutivos += 1
            if consecutivos >= 3:
                return True
        else:
            consecutivos = 0
    return False


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


@app.get("/chat/provider", response_model=ChatProviderResponse)
def get_chat_provider(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> ChatProviderResponse:
    """Devuelve proveedor IA activo. Solo profesionales."""
    rol_nombre = (usuario_actual.rol.nombre if usuario_actual.rol else "").strip().lower()
    if rol_nombre not in ROLES_PROFESIONALES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar proveedor IA",
        )

    provider = (settings.IA_PROVIDER or "gemini").strip().lower()
    aliases = {"qwen3": "qwen"}
    provider = aliases.get(provider, provider)
    if provider not in {"gemini", "qwen"}:
        provider = "gemini"

    return ChatProviderResponse(ok=True, provider=provider)


@app.put("/chat/provider", response_model=ChatProviderResponse)
def set_chat_provider(
    payload: ChatProviderUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> ChatProviderResponse:
    """Permite cambiar proveedor IA activo. Solo administrador."""
    rol_nombre = (usuario_actual.rol.nombre if usuario_actual.rol else "").strip().lower()
    if rol_nombre != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administrador puede cambiar proveedor IA",
        )

    provider = (payload.provider or "").strip().lower()
    aliases = {"qwen3": "qwen"}
    provider = aliases.get(provider, provider)
    if provider not in {"gemini", "qwen"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="provider debe ser: gemini o qwen",
        )

    settings.IA_PROVIDER = provider
    logger.info("Proveedor IA actualizado en caliente: %s", provider)
    return ChatProviderResponse(ok=True, provider=provider)

def _generar_peticion_analisis_multimedia(adjuntos: List[Dict[str, Any]]) -> str:
    """Genera automáticamente una petición de análisis cuando se sube multimedia sin pregunta."""
    tipos = {
        "image/jpeg": "imagen JPEG",
        "image/png": "imagen PNG",
        "image/webp": "imagen WEBP",
        "image/gif": "imagen animada",
        "image/bmp": "imagen BMP",
        "image/tiff": "imagen TIFF",
        "image/heic": "imagen HEIC",
        "image/heif": "imagen HEIF",
        "video/mp4": "video MP4",
        "video/quicktime": "video MOV",
        "video/webm": "video WEBM",
        "video/x-matroska": "video MKV",
        "application/pdf": "documento PDF",
    }
    
    descripciones = []
    for adjunto in adjuntos:
        mime = str(adjunto.get("mime_type") or "").lower()
        desc = tipos.get(mime, "archivo")
        descripciones.append(desc)
    
    archivos_str = " y ".join(descripciones) if descripciones else "archivo adjunto"
    return f"Analiza detalladamente el {archivos_str} que adjunto. Describe qué contiene, explica los puntos principales, y resume el contenido de forma clara."


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Orquesta respuesta de chat priorizando RASA y fallback robusto con IA."""
    sender_limpio = payload.sender.strip()
    conversation_id = _conversation_id_chat(payload, sender_limpio)
    mensaje_limpio = _normalizar_mensaje_chat(payload.mensaje)
    conversation_title = _resumir_titulo_conversacion(mensaje_limpio)
    conversation_pinned = False

    area = _detectar_area_chat(mensaje_limpio)
    lugar_entrenamiento = _detectar_lugar_entrenamiento(mensaje_limpio)
    adjuntos_normalizados = _normalizar_adjuntos_chat(payload.adjuntos)
    tiene_multimedia = bool(adjuntos_normalizados)
    es_solicitud_experta = _es_solicitud_experta(mensaje_limpio)
    
    # Si hay multimedia pero NO hay pregunta → generar automáticamente petición de análisis
    if tiene_multimedia and not mensaje_limpio.strip():
        mensaje_limpio = _generar_peticion_analisis_multimedia(adjuntos_normalizados)
    
    texto_pdf_extraido = _extraer_texto_pdf_adjuntos(adjuntos_normalizados)
    mensaje_para_ia = mensaje_limpio
    if texto_pdf_extraido:
        mensaje_para_ia = (
            f"{mensaje_limpio}\n\n"
            "[TEXTO EXTRAIDO AUTOMATICAMENTE DE PDF ADJUNTO]\n"
            f"{texto_pdf_extraido}"
        )

    plan_visual_semanal = []
    respuesta_ia = ""
    motor_respuesta = "fallback_local"

    usuario_chat = None
    contexto_ia = {}
    historial_chat: List[Dict[str, Any]] = []

    # Contexto de usuario opcional (si sender es ID numérico)
    try:
        user_id = int(sender_limpio)
        usuario_chat = db.query(Usuario).filter(Usuario.id == user_id).first()
    except ValueError:
        usuario_chat = None

    if usuario_chat is not None:
        metadata_conversacion = _obtener_metadata_conversacion(
            db,
            usuario_chat.id,
            conversation_id,
            conversation_title,
        )
        conversation_title = str(metadata_conversacion.get("titulo") or conversation_title)
        conversation_pinned = bool(metadata_conversacion.get("fijada"))
        try:
            contexto_ia = _contexto_usuario_para_ia(db, usuario_chat)
        except Exception:
            logger.exception("Error al construir contexto IA del usuario")
            contexto_ia = {}

        try:
            historial_chat = _historial_para_consulta_ia(db, usuario_chat.id, conversation_id=conversation_id)
        except Exception:
            logger.exception("Error al cargar historial de chat para IA")
            historial_chat = []

    # Mantenemos plan visual solo para consultas de entrenamiento sin multimedia.
    if area == "entrenamiento" and not tiene_multimedia:
        try:
            plan_visual_semanal = _generar_plan_visual_semanal_entrenamiento(mensaje_limpio)
        except Exception:
            logger.exception("No se pudo generar plan visual semanal")
            plan_visual_semanal = []

    # 1) Intento RASA para consultas simples, salvo casos expertos/multimedia.
    usar_rasa = debe_priorizar_rasa(
        mensaje_limpio,
        area_detectada=area,
        tiene_multimedia=tiene_multimedia,
        es_solicitud_experta=es_solicitud_experta,
    ) and not _debe_priorizar_ia_avanzada(mensaje_limpio)

    try:
        if usar_rasa:
            analisis_rasa = analizar_mensaje_con_rasa(sender_limpio, mensaje_limpio)
            intent = (analisis_rasa.get("intent") or {}).get("name", "")
            confianza = float((analisis_rasa.get("intent") or {}).get("confidence") or 0.0)

            if es_intento_rasa_confiable(intent, confianza):
                respuestas_rasa = enviar_mensaje_a_rasa(sender_limpio, mensaje_limpio)
                textos = [
                    str(item.get("text", "")).strip()
                    for item in respuestas_rasa
                    if isinstance(item, dict)
                ]
                candidata_rasa = "\n".join([t for t in textos if t])
                if candidata_rasa and not _es_respuesta_rasa_generica(candidata_rasa):
                    respuesta_ia = candidata_rasa
                    motor_respuesta = "rasa"
    except Exception:
        logger.exception("Error al intentar respuesta con RASA")

    # 2) Fallback principal a IA (Gemini/Qwen/local), incluyendo multimedia.
    if not respuesta_ia:
        try:
            resultado_ia = consultar_ia(
                mensaje_usuario=mensaje_para_ia,
                historial_chat=historial_chat,
                imagenes=adjuntos_normalizados,
                contexto_adicional=contexto_ia,
                tiene_multimedia=tiene_multimedia,
                provider_override=(payload.provider or "").strip().lower() or None,
                model_override=(payload.model or "").strip() or None,
            )
            respuesta_ia = str(resultado_ia.get("respuesta") or "").strip()
            motor_respuesta = str(
                resultado_ia.get("origen")
                or resultado_ia.get("modelo")
                or "ia"
            )
        except Exception:
            logger.exception("Error al consultar proveedor IA")
            respuesta_ia = obtener_respuesta_local_segura(
                mensaje_usuario=mensaje_para_ia,
                historial_chat=historial_chat,
                imagenes=adjuntos_normalizados,
                contexto_adicional=contexto_ia,
                tiene_multimedia=tiene_multimedia,
            )
            motor_respuesta = "fallback_local"

    if not respuesta_ia:
        respuesta_ia = obtener_respuesta_local_segura(
            mensaje_usuario=mensaje_para_ia,
            historial_chat=historial_chat,
            imagenes=adjuntos_normalizados,
            contexto_adicional=contexto_ia,
            tiene_multimedia=tiene_multimedia,
        )
        motor_respuesta = "fallback_local"

    preguntas_precision = _preguntas_precision_por_area(area)
    plan_accion = _plan_accion_base(area, mensaje_limpio)
    recursos_multimedia = _recursos_multimedia_por_area(area)

    if _debe_anexar_bloque_utilidad(respuesta_ia, motor_respuesta):
        respuesta_ia = _anexar_bloque_utilidad_chat(
            respuesta_base=respuesta_ia,
            preguntas=preguntas_precision,
            plan=plan_accion,
            recursos=recursos_multimedia,
        )

    # PERSISTENCIA BD (Guardar mensajes)
    if usuario_chat:
        try:
            db.add(MensajeChat(
                usuario_id=usuario_chat.id,
                conversation_id=conversation_id,
                conversation_title=conversation_title,
                conversation_pinned=conversation_pinned,
                emisor="user",
                texto=mensaje_limpio,
            ))
            db.add(MensajeChat(
                usuario_id=usuario_chat.id,
                conversation_id=conversation_id,
                conversation_title=conversation_title,
                conversation_pinned=conversation_pinned,
                emisor="ia",
                texto=respuesta_ia,
            ))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("No se pudo persistir historial de chat")

    # AUTO-GUARDADO DE PLAN: si la IA generó un plan completo, persistirlo en planes_ia
    tipo_plan = {
        "dieta": "nutricion",
        "nutricion": "nutricion",
        "entrenamiento": "entrenamiento",
        "psicologia": "psicologia",
    }.get(area)
    if usuario_chat and tipo_plan:
        try:
            _auto_guardar_plan_ia(db, usuario_chat.id, tipo_plan, mensaje_limpio, respuesta_ia, contexto_ia)
        except Exception:
            logger.exception("No se pudo auto-guardar plan IA")

    return ChatResponse(
        ok=True,
        sender=sender_limpio,
        respuesta_ia=respuesta_ia,
        motor_respuesta=motor_respuesta,
        area_detectada=area,
        preguntas_precision=preguntas_precision,
        plan_accion=plan_accion,
        recursos_multimedia=recursos_multimedia,
        plan_visual_semanal=plan_visual_semanal,
        lugar_entrenamiento=lugar_entrenamiento,
        adjuntos_recibidos=len(adjuntos_normalizados),
        memoria_activa=bool(contexto_ia.get("memoria_activa")),
        memoria_tema=contexto_ia.get("memoria_tema"),
        respuestas_memoria=contexto_ia.get("memoria_respuestas") or {},
        conversation_id=conversation_id,
    )

@app.get("/chat/historial", response_model=List[ChatHistorialItemResponse])
def obtener_historial_chat(
    limit: int = Query(default=80, ge=1, le=300),
    conversation_id: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[ChatHistorialItemResponse]:
    """Devuelve historial de chat persistido para hidratar conversación tras reinicio."""
    query = db.query(MensajeChat).filter(MensajeChat.usuario_id == usuario_actual.id)
    if conversation_id:
        query = query.filter(MensajeChat.conversation_id == conversation_id)
    mensajes = query.order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc()).limit(limit).all()
    mensajes.reverse()
    return [_serializar_mensaje_chat(m) for m in mensajes]


@app.get("/chat/conversations", response_model=List[ChatConversationResponse])
def listar_conversaciones_chat(
    q: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[ChatConversationResponse]:
    """Lista conversaciones del usuario para navegación estilo GPT."""
    return _listar_conversaciones_usuario(db, usuario_actual.id, q=q)


@app.patch("/chat/conversations/{conversation_id}", response_model=ChatConversationResponse)
def actualizar_conversacion_chat(
    conversation_id: str,
    payload: ChatConversationUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> ChatConversationResponse:
    """Permite renombrar o fijar una conversación existente."""
    mensajes = (
        db.query(MensajeChat)
        .filter(
            MensajeChat.usuario_id == usuario_actual.id,
            MensajeChat.conversation_id == conversation_id,
        )
        .all()
    )
    if not mensajes:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    nuevo_titulo = None
    if payload.titulo is not None:
        nuevo_titulo = payload.titulo.strip() or "Nuevo chat"

    for mensaje in mensajes:
        if nuevo_titulo is not None:
            mensaje.conversation_title = nuevo_titulo[:160]
        if payload.fijada is not None:
            mensaje.conversation_pinned = bool(payload.fijada)

    db.commit()
    conversaciones = _listar_conversaciones_usuario(db, usuario_actual.id)
    for item in conversaciones:
        if item.conversation_id == conversation_id:
            return item
    raise HTTPException(status_code=404, detail="Conversación actualizada pero no encontrada")


@app.delete("/chat/historial")
def limpiar_historial_chat(
    conversation_id: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Elimina historial persistido de chat del usuario autenticado."""
    query = db.query(MensajeChat).filter(MensajeChat.usuario_id == usuario_actual.id)
    if conversation_id:
        query = query.filter(MensajeChat.conversation_id == conversation_id)
    query.delete(synchronize_session=False)
    db.commit()
    return {"ok": "true"}


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
        hoy = datetime.utcnow().date()

        if not perfil:
            perfil = PerfilSalud(usuario_id=usuario_actual.id)
            db.add(perfil)
        elif (
            perfil.ultima_actualizacion_metricas is not None
            and perfil.ultima_actualizacion_metricas.date() == hoy
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El perfil solo puede completarse una vez al dia",
            )

        perfil.peso_actual = payload.peso
        perfil.altura = payload.altura
        perfil.imc_actual = imc
        perfil.frecuencia_gym = payload.frecuencia_gym
        perfil.hora_desayuno = payload.hora_desayuno
        perfil.hora_comida = payload.hora_comida
        perfil.hora_cena = payload.hora_cena
        perfil.momento_critico_picoteo = payload.momento_picoteo
        perfil.percepcion_corporal = payload.percepcion_corporal.strip()
        perfil.ultima_actualizacion_metricas = datetime.utcnow()

        db.commit()
        db.refresh(perfil)
    except HTTPException:
        db.rollback()
        raise
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


@app.patch("/perfil/metricas-imc", response_model=PerfilMetricasIMCResponse)
def actualizar_metricas_imc(
    payload: PerfilMetricasIMCRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PerfilMetricasIMCResponse:
    """Actualiza peso y altura del usuario y recalcula IMC en un flujo rapido."""
    altura_m = payload.altura / 100
    imc = round(payload.peso / (altura_m * altura_m), 2)
    rango = _clasificar_imc(imc)
    hoy = datetime.utcnow().date()

    try:
        perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario_actual.id).first()
        perfil_existia = perfil is not None

        if not perfil:
            perfil = PerfilSalud(usuario_id=usuario_actual.id)
            db.add(perfil)
        elif (
            perfil.ultima_actualizacion_metricas is not None
            and perfil.ultima_actualizacion_metricas.date() == hoy
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Las metricas solo pueden actualizarse una vez al dia",
            )

        perfil.peso_actual = payload.peso
        perfil.altura = payload.altura
        perfil.imc_actual = imc
        perfil.ultima_actualizacion_metricas = datetime.utcnow()

        db.commit()
        db.refresh(perfil)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error actualizando metricas de IMC")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudieron actualizar las metricas de IMC",
        ) from e

    mensaje = "Métricas actualizadas" if perfil_existia else "Métricas guardadas por primera vez"

    return PerfilMetricasIMCResponse(
        usuario_id=usuario_actual.id,
        peso_actual=float(payload.peso),
        altura_cm=int(payload.altura),
        imc_calculado=float(imc),
        imc_rango=rango,
        ultima_actualizacion_metricas=perfil.ultima_actualizacion_metricas.isoformat() if perfil.ultima_actualizacion_metricas else None,
        actualizacion_permitida_hoy=False,
        mensaje=mensaje,
    )


@app.get("/perfil/resumen", response_model=PerfilResumenResponse)
def obtener_perfil_resumen(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PerfilResumenResponse:
    """Devuelve métricas persistidas para rehidratar UI tras reinicio."""
    perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario_actual.id).first()
    hoy = datetime.utcnow().date()
    if not perfil:
        return PerfilResumenResponse(usuario_id=usuario_actual.id)

    imc = float(perfil.imc_actual) if perfil.imc_actual is not None else None
    deslices_hoy = []
    restricciones_alimentarias = []
    if perfil.deslices_fecha == hoy:
        deslices_hoy = _leer_json_seguro(perfil.deslices_hoy_json, [])
        if not isinstance(deslices_hoy, list):
            deslices_hoy = []
    restricciones_raw = _leer_json_seguro(perfil.restricciones_alimentarias_json, [])
    if isinstance(restricciones_raw, list):
        restricciones_alimentarias = [str(item) for item in restricciones_raw if str(item).strip()]

    return PerfilResumenResponse(
        usuario_id=usuario_actual.id,
        peso_actual=float(perfil.peso_actual) if perfil.peso_actual is not None else None,
        altura_cm=perfil.altura,
        imc_actual=imc,
        imc_rango=_clasificar_imc(imc) if imc is not None else None,
        objetivo_principal=(perfil.objetivo_principal or "perder_grasa"),
        deslices_hoy=[str(item) for item in deslices_hoy if str(item).strip()],
        restricciones_alimentarias=restricciones_alimentarias,
        ultima_actualizacion_metricas=perfil.ultima_actualizacion_metricas.isoformat() if perfil.ultima_actualizacion_metricas else None,
    )


@app.get("/perfil/plan-diario", response_model=PerfilPlanDiarioResponse)
def obtener_perfil_plan_diario(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PerfilPlanDiarioResponse:
    """Devuelve el plan diario persistido para objetivo y deslices del dia."""
    perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario_actual.id).first()
    hoy = datetime.utcnow().date()

    # Verificar si el usuario puede actualizar metrics hoy
    puede_actualizar_metricas_hoy = True
    ultima_actualizacion_metricas = None
    if perfil and perfil.ultima_actualizacion_metricas is not None and perfil.ultima_actualizacion_metricas.date() == hoy:
        puede_actualizar_metricas_hoy = False
        ultima_actualizacion_metricas = perfil.ultima_actualizacion_metricas.isoformat()

    if not perfil:
        return PerfilPlanDiarioResponse(
            usuario_id=usuario_actual.id,
            objetivo_principal="perder_grasa",
            deslices_hoy=[],
            restricciones_alimentarias=[],
            fecha_deslices=hoy.isoformat(),
            puede_actualizar_metricas_hoy=puede_actualizar_metricas_hoy,
            ultima_actualizacion_metricas=ultima_actualizacion_metricas,
        )

    deslices_hoy = []
    if perfil.deslices_fecha == hoy:
        parsed = _leer_json_seguro(perfil.deslices_hoy_json, [])
        if isinstance(parsed, list):
            deslices_hoy = [str(item) for item in parsed if str(item).strip()]
    restricciones_alimentarias = []
    restricciones_raw = _leer_json_seguro(perfil.restricciones_alimentarias_json, [])
    if isinstance(restricciones_raw, list):
        restricciones_alimentarias = [str(item) for item in restricciones_raw if str(item).strip()]

    return PerfilPlanDiarioResponse(
        usuario_id=usuario_actual.id,
        objetivo_principal=(perfil.objetivo_principal or "perder_grasa"),
        deslices_hoy=deslices_hoy,
        restricciones_alimentarias=restricciones_alimentarias,
        fecha_deslices=hoy.isoformat(),
        puede_actualizar_metricas_hoy=puede_actualizar_metricas_hoy,
        ultima_actualizacion_metricas=ultima_actualizacion_metricas,
    )


@app.put("/perfil/plan-diario", response_model=PerfilPlanDiarioResponse)
def actualizar_perfil_plan_diario(
    payload: PerfilPlanDiarioUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PerfilPlanDiarioResponse:
    """Persiste objetivo principal y deslices de comida del dia."""
    hoy = datetime.utcnow().date()
    perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario_actual.id).first()

    if not perfil:
        perfil = PerfilSalud(usuario_id=usuario_actual.id)
        db.add(perfil)

    if payload.objetivo_principal is not None:
        perfil.objetivo_principal = payload.objetivo_principal

    if payload.deslices_hoy is not None:
        deslices_normalizados = [item.strip() for item in payload.deslices_hoy if isinstance(item, str) and item.strip()]
        perfil.deslices_hoy_json = json.dumps(deslices_normalizados, ensure_ascii=False)
        perfil.deslices_fecha = hoy

    if payload.restricciones_alimentarias is not None:
        restricciones = [
            item.strip() for item in payload.restricciones_alimentarias if isinstance(item, str) and item.strip()
        ]
        perfil.restricciones_alimentarias_json = json.dumps(restricciones, ensure_ascii=False)

    db.commit()
    db.refresh(perfil)

    deslices_hoy = []
    if perfil.deslices_fecha == hoy:
        parsed = _leer_json_seguro(perfil.deslices_hoy_json, [])
        if isinstance(parsed, list):
            deslices_hoy = [str(item) for item in parsed if str(item).strip()]
    restricciones_alimentarias = []
    restricciones_raw = _leer_json_seguro(perfil.restricciones_alimentarias_json, [])
    if isinstance(restricciones_raw, list):
        restricciones_alimentarias = [str(item) for item in restricciones_raw if str(item).strip()]

    return PerfilPlanDiarioResponse(
        usuario_id=usuario_actual.id,
        objetivo_principal=(perfil.objetivo_principal or "perder_grasa"),
        deslices_hoy=deslices_hoy,
        restricciones_alimentarias=restricciones_alimentarias,
        fecha_deslices=hoy.isoformat(),
    )


@app.get("/evaluaciones/ia", response_model=List[EvaluacionIAResponse])
def listar_evaluaciones_ia(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[EvaluacionIAResponse]:
    """Lista todas las evaluaciones IA persistidas del usuario."""
    evaluaciones = (
        db.query(EvaluacionIA)
        .filter(EvaluacionIA.usuario_id == usuario_actual.id)
        .order_by(EvaluacionIA.fecha_actualizacion.desc(), EvaluacionIA.id.desc())
        .all()
    )
    return [_serializar_evaluacion_ia(e) for e in evaluaciones]


@app.put("/evaluaciones/ia/{seccion}", response_model=EvaluacionIAResponse)
def guardar_evaluacion_ia(
    seccion: str,
    payload: EvaluacionIAGuardadoRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> EvaluacionIAResponse:
    """Crea o actualiza evaluación IA de una sección."""
    clave = seccion.strip().lower()
    if not clave:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sección inválida")

    evaluacion = (
        db.query(EvaluacionIA)
        .filter(EvaluacionIA.usuario_id == usuario_actual.id, EvaluacionIA.seccion == clave)
        .first()
    )

    respuestas_json = json.dumps(payload.respuestas, ensure_ascii=False)
    hoy = datetime.utcnow().date()

    if not evaluacion:
        evaluacion = EvaluacionIA(
            usuario_id=usuario_actual.id,
            seccion=clave,
            respuestas_json=respuestas_json,
            plan_ia=payload.plan_ia,
            fecha_actualizacion=datetime.utcnow(),
        )
        db.add(evaluacion)
    else:
        if evaluacion.fecha_actualizacion and evaluacion.fecha_actualizacion.date() == hoy:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Esta evaluación ya se completó hoy. Puedes volver a enviarla mañana.",
            )
        evaluacion.respuestas_json = respuestas_json
        evaluacion.plan_ia = payload.plan_ia
        evaluacion.fecha_actualizacion = datetime.utcnow()

    db.commit()
    db.refresh(evaluacion)
    return _serializar_evaluacion_ia(evaluacion)


@app.delete("/evaluaciones/ia/{seccion}")
def eliminar_evaluacion_ia(
    seccion: str,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Elimina evaluación IA de una sección para forzar nuevo cuestionario."""
    clave = seccion.strip().lower()
    evaluacion = (
        db.query(EvaluacionIA)
        .filter(EvaluacionIA.usuario_id == usuario_actual.id, EvaluacionIA.seccion == clave)
        .first()
    )
    if evaluacion:
        db.delete(evaluacion)
        db.commit()
    return {"ok": "true"}


@app.get("/usuarios/grafica-animo", response_model=GraficaAnimoResponse)
def obtener_grafica_animo(
    usuario_id: int = Query(..., gt=0),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> GraficaAnimoResponse:
    """
    Devuelve los ultimos 7 dias de sentimientos para graficar en frontend.

    Regla de alerta: si existen 3 dias consecutivos de ansiedad/malestar,
    se devuelve alerta_profesional=true.
    """
    _assert_permitido_ver_usuario(usuario_actual, usuario_id)

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    hoy = datetime.utcnow().date()
    inicio = hoy - timedelta(days=6)

    registros = (
        db.query(RegistroDiario)
        .filter(
            RegistroDiario.usuario_id == usuario_id,
            RegistroDiario.fecha >= inicio,
            RegistroDiario.fecha <= hoy,
        )
        .order_by(RegistroDiario.fecha.asc(), RegistroDiario.id.asc())
        .all()
    )

    # Ultimo registro por dia.
    ultimo_por_dia: Dict[str, RegistroDiario] = {}
    for r in registros:
        ultimo_por_dia[r.fecha.isoformat()] = r

    datos: List[AnimoDiaResponse] = []
    for offset in range(7):
        fecha = inicio + timedelta(days=offset)
        key = fecha.isoformat()
        reg = ultimo_por_dia.get(key)

        if reg and reg.sentimiento_detectado_ia:
            sentimiento = reg.sentimiento_detectado_ia.strip().lower()
            valor = _sentimiento_a_valor(sentimiento)
        else:
            sentimiento = "sin_dato"
            valor = 0

        datos.append(
            AnimoDiaResponse(
                fecha=key,
                sentimiento=sentimiento,
                valor=valor,
            )
        )

    alerta = _calcular_alerta_profesional(datos)

    return GraficaAnimoResponse(
        usuario_id=usuario_id,
        datos=datos,
        alerta_profesional=alerta,
    )


@app.get("/usuarios/informe-pdf")
def descargar_informe_pdf(
    usuario_id: int = Query(..., gt=0),
    token: Optional[str] = Query(default=None),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> Response:
    """Genera y descarga un informe PDF mensual para uso clinico."""
    def _to_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def _pdf_safe(value: Any) -> str:
        """Asegura texto compatible con fuentes base de FPDF (latin-1)."""
        text = str(value or "")
        reemplazos = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u2022": "-",
            "\u2026": "...",
            "\u00a0": " ",
        }
        for original, reemplazo in reemplazos.items():
            text = text.replace(original, reemplazo)
        return text.encode("latin-1", "replace").decode("latin-1")

    usuario_actual: Optional[Usuario] = None
    if authorization:
        try:
            token_bearer = _extraer_token_bearer(authorization)
            usuario_actual = obtener_usuario_por_token(db, token_bearer)
        except HTTPException:
            usuario_actual = None

    if not usuario_actual and token:
        usuario_actual = obtener_usuario_por_token(db, token)

    if not usuario_actual:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o expirado",
        )

    _assert_permitido_ver_usuario(usuario_actual, usuario_id)

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == usuario_id).first()
    registros = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_id)
        .order_by(RegistroDiario.fecha.desc(), RegistroDiario.id.desc())
        .limit(60)
        .all()
    )

    # Consejos de IA recientes (filtrando frases de fallback y ruido genérico).
    bloqueados = (
        "incidencia temporal",
        "he recibido tu mensaje",
        "puedo ayudarte",
        "en este momento",
    )
    consejos: List[str] = []
    vistos = set()
    for r in registros:
        if not r.analisis_nutricional_ia:
            continue
        txt = r.analisis_nutricional_ia.strip().replace("\n", " ")
        if not txt:
            continue
        txt_norm = txt.lower()
        if any(k in txt_norm for k in bloqueados):
            continue
        if txt in vistos:
            continue
        consejos.append(txt)
        vistos.add(txt)
        if len(consejos) >= 6:
            break

    kpis = _calcular_kpis_paciente(db, usuario_id)
    plan_nutri = (
        db.query(PlanNutricionalClinico)
        .filter(PlanNutricionalClinico.paciente_id == usuario_id)
        .filter(PlanNutricionalClinico.activo == True)
        .order_by(PlanNutricionalClinico.fecha_actualizacion.desc(), PlanNutricionalClinico.id.desc())
        .first()
    )
    meds_activas = (
        db.query(MedicacionAsignada)
        .filter(MedicacionAsignada.paciente_id == usuario_id)
        .filter(MedicacionAsignada.activa == True)
        .order_by(MedicacionAsignada.fecha_actualizacion.desc(), MedicacionAsignada.id.desc())
        .limit(8)
        .all()
    )
    derivaciones_abiertas = (
        db.query(Derivacion)
        .filter(Derivacion.paciente_id == usuario_id)
        .filter(Derivacion.estado.in_(["pendiente", "aceptada", "en_seguimiento"]))
        .order_by(Derivacion.fecha_creacion.desc(), Derivacion.id.desc())
        .limit(8)
        .all()
    )
    notas_clinicas = (
        db.query(MensajeChat)
        .filter(MensajeChat.usuario_id == usuario_id)
        .filter(MensajeChat.emisor == "profesional")
        .filter(MensajeChat.texto.like("[NOTA_CLINICA]%"))
        .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
        .limit(6)
        .all()
    )

    def _linea_clinica(txt: str, max_chars: int = 140) -> str:
        limpio = (txt or "").replace("\n", " ").strip()
        if len(limpio) <= max_chars:
            return _pdf_safe(limpio)
        return _pdf_safe(limpio[: max_chars - 3].rstrip() + "...")

    historial_imc = _extraer_imcs_desde_notas(registros)
    if not historial_imc and perfil and perfil.imc_actual:
        historial_imc = [{
            "fecha": datetime.utcnow().date().isoformat(),
            "imc": float(perfil.imc_actual),
        }]

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_draw_color(44, 110, 188)
    pdf.set_fill_color(238, 245, 255)

    def _section_title(text: str) -> None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(18, 53, 106)
        pdf.set_fill_color(238, 245, 255)
        pdf.cell(0, 9, _pdf_safe(text), ln=True, fill=True)
        pdf.set_text_color(20, 26, 38)
        pdf.set_font("Helvetica", "", 11)

    # Logo de AuraFit AI (si existe en proyecto).
    logo_path = Path(__file__).resolve().parent.parent / "frontend" / "web" / "favicon.png"
    if logo_path.exists():
        try:
            pdf.image(str(logo_path), x=10, y=8, w=14, h=14)
        except Exception:
            pass

    pdf.set_fill_color(238, 245, 255)
    pdf.rect(8, 8, 194, 28, style="F")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(18, 53, 106)
    pdf.cell(0, 10, "AuraFit AI - Informe Mensual", ln=True)
    pdf.set_text_color(20, 26, 38)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, _pdf_safe(f"Paciente: {usuario.nombre}"), ln=True)
    pdf.cell(0, 8, _pdf_safe(f"Email: {usuario.email}"), ln=True)
    pdf.cell(0, 8, f"Fecha de generacion: {datetime.utcnow().date().isoformat()}", ln=True)
    pdf.ln(4)

    _section_title("1) Resumen de perfil y diagnostico metabolico")
    if perfil:
        peso_actual = _to_float(perfil.peso_actual)
        imc_actual = _to_float(perfil.imc_actual)
        pdf.cell(0, 7, _pdf_safe(f"Peso actual: {peso_actual if peso_actual is not None else 'N/D'} kg"), ln=True)
        pdf.cell(0, 7, _pdf_safe(f"Altura: {perfil.altura if perfil.altura else 'N/D'} cm"), ln=True)
        pdf.cell(0, 7, _pdf_safe(f"IMC actual: {imc_actual if imc_actual is not None else 'N/D'}"), ln=True)
        if imc_actual is not None:
            imc_val = imc_actual
            if imc_val >= 30:
                diagnostico = "IMC elevado: priorizar bajo impacto articular y déficit moderado con proteína alta."
            elif imc_val < 18.5:
                diagnostico = "IMC bajo: priorizar ganancia de masa magra y estabilidad energética."
            else:
                diagnostico = "IMC en rango intermedio: foco en recomposición y adherencia técnica."
            pdf.multi_cell(0, 7, _pdf_safe(f"Diagnóstico metabólico: {diagnostico}"))
    else:
        pdf.cell(0, 7, "Sin perfil de salud registrado", ln=True)

    pdf.cell(0, 7, _pdf_safe(f"Riesgo emocional 7d: {kpis.riesgo_emocional}"), ln=True)
    pdf.cell(0, 7, _pdf_safe(f"Adherencia nutricional 7d: {kpis.adherencia_nutricional_pct if kpis.adherencia_nutricional_pct is not None else 'N/D'}%"), ln=True)
    pdf.cell(0, 7, _pdf_safe(f"Adherencia hábitos 7d: {kpis.adherencia_habitos_pct if kpis.adherencia_habitos_pct is not None else 'N/D'}%"), ln=True)

    pdf.ln(3)
    _section_title("2) Evolucion del IMC")
    if historial_imc:
        for p in sorted(historial_imc, key=lambda x: x["fecha"])[-10:]:
            pdf.cell(0, 7, _pdf_safe(f"{p['fecha']}: IMC {p['imc']}"), ln=True)
    else:
        pdf.cell(0, 7, "No hay datos historicos de IMC disponibles", ln=True)

    pdf.ln(3)
    _section_title("3) Plan nutricional clinico activo")
    if plan_nutri is not None:
        kcal_obj = _to_int(plan_nutri.calorias_objetivo)
        prot = _to_int(plan_nutri.proteinas_g)
        carb = _to_int(plan_nutri.carbohidratos_g)
        grasa = _to_int(plan_nutri.grasas_g)
        kcal_txt = f"{kcal_obj} kcal" if kcal_obj is not None else "N/D"
        prot_txt = f"{prot}g" if prot is not None else "N/D"
        carb_txt = f"{carb}g" if carb is not None else "N/D"
        grasa_txt = f"{grasa}g" if grasa is not None else "N/D"
        pdf.cell(0, 7, _pdf_safe(f"Kcal objetivo: {kcal_txt}"), ln=True)
        pdf.cell(0, 7, _pdf_safe(f"Macros: P {prot_txt} | C {carb_txt} | G {grasa_txt}"), ln=True)
        pdf.cell(0, 7, _pdf_safe(f"Objetivo: {plan_nutri.objetivo_clinico} | Riesgo metabólico: {plan_nutri.riesgo_metabolico}"), ln=True)
        if plan_nutri.observaciones:
            pdf.multi_cell(0, 6, f"Observaciones: {_linea_clinica(plan_nutri.observaciones, 300)}")
    else:
        pdf.cell(0, 7, "No hay plan nutricional clínico activo", ln=True)

    pdf.ln(3)
    _section_title("4) Medicacion activa")
    if meds_activas:
        for med in meds_activas:
            pdf.multi_cell(
                0,
                6,
                _pdf_safe(
                    f"- {med.medicamento} | {med.dosis} | {med.frecuencia}"
                    + (f" | {_linea_clinica(med.instrucciones, 120)}" if med.instrucciones else "")
                ),
            )
    else:
        pdf.cell(0, 7, "Sin medicación activa registrada", ln=True)

    pdf.ln(3)
    _section_title("5) Derivaciones y coordinacion")
    if derivaciones_abiertas:
        for d in derivaciones_abiertas:
            destino = (d.especialidad_destino or "especialidad").strip()
            pdf.multi_cell(0, 6, _pdf_safe(f"- {destino.upper()} [{d.estado}] | {_linea_clinica(d.motivo, 150)}"))
    else:
        pdf.cell(0, 7, "No hay derivaciones abiertas en este periodo", ln=True)

    pdf.ln(3)
    _section_title("6) Notas clinicas del especialista")
    if notas_clinicas:
        for n in notas_clinicas:
            titulo = _extraer_titulo_nota_clinica(n.texto)
            cuerpo = _extraer_cuerpo_nota_clinica(n.texto)
            fecha = n.fecha_creacion.date().isoformat() if n.fecha_creacion else "N/D"
            pdf.multi_cell(0, 6, _pdf_safe(f"- [{fecha}] {titulo}: {_linea_clinica(cuerpo, 220)}"))
    else:
        pdf.cell(0, 7, "No hay notas clínicas recientes", ln=True)

    pdf.ln(3)
    _section_title("7) Resumen de consejos de IA (curado)")
    if consejos:
        for idx, consejo in enumerate(consejos, start=1):
            pdf.multi_cell(0, 6, _pdf_safe(f"{idx}. {_linea_clinica(consejo, 320)}"))
            pdf.ln(1)
    else:
        pdf.cell(0, 7, "No hay recomendaciones IA clínicas válidas en este periodo", ln=True)

    pdf_raw = pdf.output(dest="S")
    if isinstance(pdf_raw, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_raw)
    elif isinstance(pdf_raw, str):
        pdf_bytes = pdf_raw.encode("latin-1", "replace")
    else:
        pdf_bytes = str(pdf_raw).encode("latin-1", "replace")
    filename = f"informe_mensual_usuario_{usuario_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/profesionales/pacientes", response_model=List[PacienteResumenResponse])
def listar_pacientes_para_profesional(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[PacienteResumenResponse]:
    """Lista pacientes para panel de profesionales; bloqueado para rol cliente."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden ver listado de pacientes",
        )

    pacientes = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == "cliente")
        .order_by(Usuario.nombre.asc())
        .all()
    )

    resultados: List[PacienteResumenResponse] = []
    for paciente in pacientes:
        perfil = db.query(PerfilSalud).filter(PerfilSalud.usuario_id == paciente.id).first()
        ultimo_registro = (
            db.query(RegistroDiario)
            .filter(RegistroDiario.usuario_id == paciente.id)
            .order_by(RegistroDiario.fecha.desc(), RegistroDiario.id.desc())
            .first()
        )
        ultima_comida_msg = (
            db.query(MensajeChat)
            .filter(MensajeChat.usuario_id == paciente.id)
            .filter(MensajeChat.emisor == "meal_log")
            .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
            .first()
        )
        meal_data = _parsear_meal_log(ultima_comida_msg.texto if ultima_comida_msg else None)
        if meal_data:
            tipo = str(meal_data.get("tipo") or "comida").capitalize()
            descripcion = str(meal_data.get("descripcion") or "").strip()
            hora = str(meal_data.get("hora") or "").strip()
            ultima_comida = f"{tipo}: {descripcion}" if not hora else f"{tipo} {hora}: {descripcion}"
        else:
            ultima_comida = "Sin registro reciente"

        resultados.append(
            PacienteResumenResponse(
                usuario_id=paciente.id,
                nombre=paciente.nombre,
                email=paciente.email,
                ultimo_imc=float(perfil.imc_actual) if perfil and perfil.imc_actual else None,
                sentimiento_detectado=(
                    ultimo_registro.sentimiento_detectado_ia
                    if ultimo_registro and ultimo_registro.sentimiento_detectado_ia
                    else None
                ),
                ultima_comida=ultima_comida,
                ultima_actualizacion=(
                    ultimo_registro.fecha.isoformat() if ultimo_registro else None
                ),
            )
        )

    return resultados


@app.get("/profesionales/pacientes/{paciente_id}/kpis", response_model=PacienteKpisResponse)
def obtener_kpis_paciente_profesional(
    paciente_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PacienteKpisResponse:
    """KPIs clínicos de paciente para vistas de especialidad del profesional."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar KPIs clínicos",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    return _calcular_kpis_paciente(db, paciente_id)


@app.get("/profesionales/pacientes/{paciente_id}/medicacion", response_model=List[MedicacionResponse])
def listar_medicacion_paciente(
    paciente_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[MedicacionResponse]:
    """Lista medicaciones de un paciente para panel profesional."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden ver medicacion",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    items = (
        db.query(MedicacionAsignada)
        .filter(MedicacionAsignada.paciente_id == paciente_id)
        .order_by(MedicacionAsignada.fecha_actualizacion.desc(), MedicacionAsignada.id.desc())
        .all()
    )
    return [_serializar_medicacion(m) for m in items]


@app.get(
    "/profesionales/catalogos/medicamentos",
    response_model=List[MedicamentoCatalogoResponse],
)
def obtener_catalogo_medicamentos(
    seccion: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> List[MedicamentoCatalogoResponse]:
    """Catálogo farmacológico para apoyo clínico por secciones e indicaciones."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar el catalogo de medicamentos",
        )

    items = _catalogo_medicamentos_filtrado(seccion=seccion, q=q, limit=limit)
    return [
        MedicamentoCatalogoResponse(
            seccion=item["seccion"],
            nombre=item["nombre"],
            para_que_sirve=item["para_que_sirve"],
            requiere_supervision_medica=True,
        )
        for item in items
    ]


@app.post(
    "/profesionales/pacientes/{paciente_id}/medicacion",
    response_model=MedicacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def asignar_medicacion_paciente(
    paciente_id: int,
    payload: MedicacionCreateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> MedicacionResponse:
    """Asigna medicacion (medico/admin) a un paciente."""
    if not _puede_prescribir_medicacion(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo medico o administrador pueden asignar medicacion",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    med = MedicacionAsignada(
        paciente_id=paciente_id,
        profesional_id=usuario_actual.id,
        medicamento=payload.medicamento.strip(),
        dosis=payload.dosis.strip(),
        frecuencia=payload.frecuencia.strip(),
        instrucciones=(payload.instrucciones or "").strip() or None,
        activa=True,
        fecha_actualizacion=datetime.utcnow(),
    )
    db.add(med)
    db.commit()
    db.refresh(med)
    return _serializar_medicacion(med)


@app.patch("/profesionales/medicacion/{medicacion_id}/estado", response_model=MedicacionResponse)
def actualizar_estado_medicacion(
    medicacion_id: int,
    payload: MedicacionEstadoRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> MedicacionResponse:
    """Permite activar/desactivar medicacion de un paciente."""
    if not _puede_prescribir_medicacion(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo medico o administrador pueden modificar medicacion",
        )

    med = db.query(MedicacionAsignada).filter(MedicacionAsignada.id == medicacion_id).first()
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicacion no encontrada")

    med.activa = payload.activa
    med.fecha_actualizacion = datetime.utcnow()
    db.commit()
    db.refresh(med)
    return _serializar_medicacion(med)


@app.get(
    "/profesionales/pacientes/{paciente_id}/notas-clinicas",
    response_model=List[NotaClinicaResponse],
)
def listar_notas_clinicas_paciente(
    paciente_id: int,
    limit: int = Query(default=30, ge=1, le=200),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[NotaClinicaResponse]:
    """Lista notas clínicas escritas por especialistas para el paciente."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar notas clínicas",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    notas = (
        db.query(MensajeChat)
        .filter(MensajeChat.usuario_id == paciente_id)
        .filter(MensajeChat.emisor == "profesional")
        .filter(MensajeChat.texto.like("[NOTA_CLINICA]%"))
        .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
        .limit(limit)
        .all()
    )
    return [_serializar_nota_clinica(n, paciente_id) for n in notas]


@app.post(
    "/profesionales/pacientes/{paciente_id}/notas-clinicas",
    response_model=NotaClinicaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_nota_clinica_paciente(
    paciente_id: int,
    payload: NotaClinicaCreateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> NotaClinicaResponse:
    """Permite al especialista registrar una nota clínica estructurada en el historial del paciente."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden registrar notas clínicas",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    titulo = payload.titulo.strip()
    contenido = payload.contenido.strip()
    texto = f"[NOTA_CLINICA] {titulo}\n{contenido}"

    nota = MensajeChat(
        usuario_id=paciente_id,
        emisor="profesional",
        texto=texto,
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return _serializar_nota_clinica(nota, paciente_id)


@app.get(
    "/profesionales/catalogos/ejercicios",
    response_model=List[EjercicioCatalogoResponse],
)
def obtener_catalogo_ejercicios(
    condicion: Optional[str] = Query(default=None),
    objetivo: Optional[str] = Query(default=None),
    nivel: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> List[EjercicioCatalogoResponse]:
    """Catálogo de ejercicios por condición, objetivo y niveles de dificultad."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar catálogo de ejercicios",
        )

    items = EJERCICIOS_CATALOGO_BASE
    if condicion:
        condicion_norm = condicion.strip().lower()
        items = [e for e in items if e["condicion"] == condicion_norm]
    if objetivo:
        objetivo_norm = objetivo.strip().lower()
        items = [e for e in items if e["objetivo"] == objetivo_norm]
    if nivel:
        nivel_norm = nivel.strip().lower()
        items = [e for e in items if e["nivel"] == nivel_norm]
    if q:
        q_norm = q.strip().lower()
        items = [
            e
            for e in items
            if (
                q_norm in e["nombre"].lower()
                or q_norm in e["que_es"].lower()
                or q_norm in e["para_que_sirve"].lower()
            )
        ]

    items = items[: max(1, min(limit, 1000))]
    return [
        EjercicioCatalogoResponse(
            condicion=item["condicion"],
            objetivo=item["objetivo"],
            nombre=item["nombre"],
            que_es=item["que_es"],
            para_que_sirve=item["para_que_sirve"],
            series=item["series"],
            repeticiones=item["repeticiones"],
            duracion=item["duracion"],
            nivel=item["nivel"],
            imagen_referencia=item["imagen_referencia"],
        )
        for item in items
    ]


@app.get(
    "/profesionales/catalogos/dietas-clinicas",
    response_model=List[DietaClinicaCatalogoResponse],
)
def obtener_catalogo_dietas_clinicas(
    condicion: Optional[str] = Query(default=None),
    alergeno: Optional[str] = Query(default=None),
    objetivo: Optional[str] = Query(default=None),
    especialidad: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> List[DietaClinicaCatalogoResponse]:
    """Catálogo clínico de dietas y alergias para uso de especialistas."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar catálogo de dietas clínicas",
        )

    items = _catalogo_dietas_clinicas_filtrado(
        condicion=condicion,
        alergeno=alergeno,
        objetivo=objetivo,
        especialidad=especialidad,
        q=q,
        limit=limit,
    )
    return [DietaClinicaCatalogoResponse(**item) for item in items]


@app.get(
    "/pacientes/dietas/recomendadas",
    response_model=List[DietaClinicaPacienteResponse],
)
def obtener_dietas_recomendadas_paciente(
    condicion: Optional[str] = Query(default=None),
    alergeno: Optional[str] = Query(default=None),
    objetivo: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> List[DietaClinicaPacienteResponse]:
    """Devuelve recomendaciones nutricionales accionables en lenguaje para paciente."""
    rol_nombre = _rol_actual(usuario_actual)
    if rol_nombre != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pacientes pueden consultar recomendaciones de dieta",
        )

    items = _catalogo_dietas_clinicas_filtrado(
        condicion=condicion,
        alergeno=alergeno,
        objetivo=objetivo,
        especialidad=None,
        q=q,
        limit=limit,
    )

    resultados: List[DietaClinicaPacienteResponse] = []
    for item in items:
        pasos_hoy: List[str] = []
        if item["alimentos_evitar"]:
            pasos_hoy.append(f"Evita hoy: {', '.join(item['alimentos_evitar'][:3])}")
        if item["alimentos_priorizar"]:
            pasos_hoy.append(f"Prioriza hoy: {', '.join(item['alimentos_priorizar'][:3])}")
        if item["ejemplo_menu_1_dia"]:
            pasos_hoy.append(item["ejemplo_menu_1_dia"][0])

        resultados.append(
            DietaClinicaPacienteResponse(
                condicion=item["condicion"],
                objetivo=item["objetivo"],
                titulo=item["titulo"],
                resumen_paciente=f"{item['titulo']}. {item['para_quien']}",
                alimentos_evitar=item["alimentos_evitar"],
                alimentos_priorizar=item["alimentos_priorizar"],
                pasos_hoy=pasos_hoy,
                cuando_pedir_ayuda=item["red_flags"],
                especialistas_recomendados=item["especialistas_recomendados"],
            )
        )

    return resultados


@app.get(
    "/profesionales/biblioteca-clinica",
    response_model=BibliotecaClinicaResponse,
)
def obtener_biblioteca_clinica(
    trastorno: str = Query(...),
    severidad: Optional[str] = Query(default=None),
    especialidad: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> BibliotecaClinicaResponse:
    """Biblioteca unificada: protocolos + recursos por trastorno y severidad."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar biblioteca clínica",
        )

    trastorno_norm = _normalizar_trastorno(trastorno)

    proto_query = db.query(ProtocoloHospitalario).filter(
        ProtocoloHospitalario.trastorno == trastorno_norm,
        ProtocoloHospitalario.activo == True,
    )
    if severidad:
        severidad_norm = _normalizar_severidad(severidad)
        proto_query = proto_query.filter(ProtocoloHospitalario.severidad == severidad_norm)
    if especialidad:
        proto_query = proto_query.filter(
            ProtocoloHospitalario.especialidad == especialidad.strip().lower()
        )

    protocolos = proto_query.order_by(ProtocoloHospitalario.fecha_actualizacion.desc()).all()

    recurso_query = db.query(RecursoClinico).filter(
        RecursoClinico.trastorno == trastorno_norm,
        RecursoClinico.activo == True,
    )
    if especialidad:
        recurso_query = recurso_query.filter(
            RecursoClinico.especialidad == especialidad.strip().lower()
        )

    recursos = recurso_query.order_by(RecursoClinico.fecha_actualizacion.desc()).all()

    return BibliotecaClinicaResponse(
        trastorno=trastorno_norm,
        severidad=severidad or None,
        especialidad=especialidad or None,
        protocolos=[_serializar_protocolo_hospitalario(p) for p in protocolos],
        recursos=[_serializar_recurso_clinico(r) for r in recursos],
    )


@app.get(
    "/profesionales/pacientes/{paciente_id}/resumen-clinico-breve",
    response_model=ResumenClinicoPacienteResponse,
)
def obtener_resumen_clinico_breve(
    paciente_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> ResumenClinicoPacienteResponse:
    """Resumen ultra-breve para médico: qué sé, qué no sé, qué alerta hay."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar resumen clínico",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")

    # Últimos 5 mensajes (para idea rápida de qué le preocupa).
    mensajes = (
        db.query(MensajeChat)
        .filter(MensajeChat.usuario_id == paciente_id)
        .order_by(MensajeChat.fecha_creacion.desc())
        .limit(5)
        .all()
    )
    mensajes.reverse()
    mensajes_recientes = [m.texto[:120] for m in mensajes if m.emisor == "user"]

    # KPIs.
    kpis = _calcular_kpis_paciente(db, paciente_id)

    # Problema probable.
    objetivo_probable = "adherencia" if kpis.adherencia_nutricional_pct is not None and kpis.adherencia_nutricional_pct < 50 else "evaluación"

    problemas_probables: List[str] = []
    if kpis.riesgo_emocional == "alto":
        problemas_probables.append("Riesgo emocional elevado (ansiedad/estado de ánimo bajo)")
    if kpis.promedio_estres_7d and kpis.promedio_estres_7d >= 8:
        problemas_probables.append("Estrés elevado sostenido")
    if kpis.adherencia_nutricional_pct and kpis.adherencia_nutricional_pct < 30:
        problemas_probables.append("Adherencia nutricional muy baja")
    if kpis.farmacos_activos >= 3:
        problemas_probables.append("Polifarmacia activa (revisar interacciones)")

    # Señales de alarma.
    senales_riesgo: List[str] = []
    if kpis.riesgo_emocional == "alto" and kpis.derivaciones_abiertas == 0:
        senales_riesgo.append("Posible depresión/ansiedad sin derivación activa")
    if kpis.promedio_animo_7d is not None and kpis.promedio_animo_7d <= 2:
        senales_riesgo.append("Ánimo muy bajo - considerar valoración urgente")
    if any("vomito" in m.lower() or "no como" in m.lower() for m in [msg.texto.lower() for msg in mensajes]):
        senales_riesgo.append("Mención de conductas de riesgo TCA")

    # Faltan datos.
    faltan_datos: List[str] = []
    if kpis.promedio_animo_7d is None:
        faltan_datos.append("Registro de ánimo/emociones")
    if kpis.adherencia_nutricional_pct is None:
        faltan_datos.append("Histórico de adherencia nutricional")
    if kpis.coordinacion_especialistas == 0 and kpis.riesgo_emocional in {"medio", "alto"}:
        faltan_datos.append("Coordinación multidisciplinar para riesgo emocional")

    # Evidencia sugerida.
    evidencia = "moderada" if kpis.promedio_animo_7d is not None else "baja"
    if kpis.coordinacion_especialistas >= 2:
        evidencia = "alta (coordinación activa)"

    # Resumen breve.
    ultima_act = (
        mensajes[-1].fecha_creacion.isoformat() if mensajes else "sin datos"
    )
    resumen_breve = (
        f"{paciente.nombre}: "
        f"riesgo emocional {kpis.riesgo_emocional}, "
        f"adherencia nutricional {kpis.adherencia_nutricional_pct or 0:.0f}%, "
        f"{kpis.coordinacion_especialistas} especialista(s) coordinado(s). "
    )
    if senales_riesgo:
        resumen_breve += f"⚠️ Alerta: {senales_riesgo[0]}"

    return ResumenClinicoPacienteResponse(
        paciente_id=paciente_id,
        nombre=paciente.nombre,
        ultima_actividad=ultima_act,
        objetivo_probable=objetivo_probable,
        problemas_probables=problemas_probables,
        señales_riesgo=senales_riesgo,
        faltan_datos=faltan_datos,
        evidencia_sugerida=evidencia,
        resumen_breve=resumen_breve,
        mensajes_recientes=mensajes_recientes,
    )


@app.get(
    "/profesionales/pacientes/{paciente_id}/plan-nutricional",
    response_model=Optional[PlanNutricionalResponse],
)
def obtener_plan_nutricional_paciente(
    paciente_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> Optional[PlanNutricionalResponse]:
    """Obtiene plan nutricional clínico activo del paciente (solo profesionales)."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar plan nutricional",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    plan = (
        db.query(PlanNutricionalClinico)
        .filter(
            PlanNutricionalClinico.paciente_id == paciente_id,
            PlanNutricionalClinico.activo == True,
        )
        .order_by(PlanNutricionalClinico.fecha_actualizacion.desc(), PlanNutricionalClinico.id.desc())
        .first()
    )
    if not plan:
        return None

    return _serializar_plan_nutricional(plan)


@app.put(
    "/profesionales/pacientes/{paciente_id}/plan-nutricional",
    response_model=PlanNutricionalResponse,
)
def guardar_plan_nutricional_paciente(
    paciente_id: int,
    payload: PlanNutricionalUpsertRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PlanNutricionalResponse:
    """Crea/actualiza plan nutricional clínico con objetivo calórico y macros."""
    if not _puede_editar_plan_nutricional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo nutricionista, medico o administrador pueden editar plan nutricional",
        )

    _validar_coherencia_plan_nutricional(payload)
    objetivo_clinico, riesgo_metabolico = _normalizar_objetivo_riesgo_plan(
        payload.objetivo_clinico,
        payload.riesgo_metabolico,
    )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    plan = (
        db.query(PlanNutricionalClinico)
        .filter(
            PlanNutricionalClinico.paciente_id == paciente_id,
            PlanNutricionalClinico.activo == True,
        )
        .order_by(PlanNutricionalClinico.fecha_actualizacion.desc(), PlanNutricionalClinico.id.desc())
        .first()
    )

    if not plan:
        plan = PlanNutricionalClinico(
            paciente_id=paciente_id,
            profesional_id=usuario_actual.id,
            calorias_objetivo=payload.calorias_objetivo,
            proteinas_g=payload.proteinas_g,
            carbohidratos_g=payload.carbohidratos_g,
            grasas_g=payload.grasas_g,
            objetivo_clinico=objetivo_clinico,
            riesgo_metabolico=riesgo_metabolico,
            observaciones=(payload.observaciones or "").strip() or None,
            activo=True,
            fecha_actualizacion=datetime.utcnow(),
        )
        db.add(plan)
    else:
        plan.profesional_id = usuario_actual.id
        plan.calorias_objetivo = payload.calorias_objetivo
        plan.proteinas_g = payload.proteinas_g
        plan.carbohidratos_g = payload.carbohidratos_g
        plan.grasas_g = payload.grasas_g
        plan.objetivo_clinico = objetivo_clinico
        plan.riesgo_metabolico = riesgo_metabolico
        plan.observaciones = (payload.observaciones or "").strip() or None
        plan.fecha_actualizacion = datetime.utcnow()

    db.commit()
    db.refresh(plan)
    return _serializar_plan_nutricional(plan)


@app.get(
    "/profesionales/protocolos-hospitalarios",
    response_model=List[ProtocoloHospitalarioResponse],
)
def listar_protocolos_hospitalarios(
    trastorno: Optional[str] = Query(default=None),
    severidad: Optional[str] = Query(default=None),
    especialidad: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[ProtocoloHospitalarioResponse]:
    """Devuelve protocolos clínicos por trastorno/severidad para panel hospitalario."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar protocolos hospitalarios",
        )

    query = db.query(ProtocoloHospitalario).filter(ProtocoloHospitalario.activo == True)
    if trastorno:
        query = query.filter(ProtocoloHospitalario.trastorno == _normalizar_trastorno(trastorno))
    if severidad:
        query = query.filter(ProtocoloHospitalario.severidad == _normalizar_severidad(severidad))
    if especialidad:
        query = query.filter(ProtocoloHospitalario.especialidad == especialidad.strip().lower())

    items = query.order_by(ProtocoloHospitalario.fecha_actualizacion.desc()).all()
    return [_serializar_protocolo_hospitalario(item) for item in items]


@app.put(
    "/profesionales/protocolos-hospitalarios",
    response_model=ProtocoloHospitalarioResponse,
)
def guardar_protocolo_hospitalario(
    payload: ProtocoloHospitalarioUpsertRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> ProtocoloHospitalarioResponse:
    """Crea o actualiza protocolos hospitalarios con checklist por severidad."""
    if not _puede_editar_protocolo_hospitalario(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo psicologo, medico o administrador pueden editar protocolos",
        )

    trastorno = _normalizar_trastorno(payload.trastorno)
    severidad = _normalizar_severidad(payload.severidad)
    especialidad = payload.especialidad.strip().lower()
    checklist = [c.strip() for c in payload.checklist if c.strip()]
    if not checklist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checklist vacío")

    item = (
        db.query(ProtocoloHospitalario)
        .filter(
            ProtocoloHospitalario.trastorno == trastorno,
            ProtocoloHospitalario.severidad == severidad,
            ProtocoloHospitalario.especialidad == especialidad,
            ProtocoloHospitalario.activo == True,
        )
        .first()
    )

    if item is None:
        item = ProtocoloHospitalario(
            trastorno=trastorno,
            severidad=severidad,
            especialidad=especialidad,
            titulo=payload.titulo.strip(),
            checklist_json=json.dumps(checklist, ensure_ascii=False),
            ruta_escalado=payload.ruta_escalado.strip(),
            activo=True,
            fecha_actualizacion=datetime.utcnow(),
        )
        db.add(item)
    else:
        item.titulo = payload.titulo.strip()
        item.checklist_json = json.dumps(checklist, ensure_ascii=False)
        item.ruta_escalado = payload.ruta_escalado.strip()
        item.fecha_actualizacion = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return _serializar_protocolo_hospitalario(item)


@app.get(
    "/profesionales/pacientes/{paciente_id}/checklist-clinico",
    response_model=Optional[ChecklistClinicoResponse],
)
def obtener_checklist_clinico_paciente(
    paciente_id: int,
    trastorno: str = Query(...),
    severidad: str = Query(...),
    especialidad: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> Optional[ChecklistClinicoResponse]:
    """Obtiene checklist clínico más reciente del paciente para un trastorno/severidad."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar checklist clínico",
        )

    trastorno_norm = _normalizar_trastorno(trastorno)
    severidad_norm = _normalizar_severidad(severidad)

    query = db.query(ChecklistClinicoPaciente).filter(
        ChecklistClinicoPaciente.paciente_id == paciente_id,
        ChecklistClinicoPaciente.trastorno == trastorno_norm,
        ChecklistClinicoPaciente.severidad == severidad_norm,
    )
    if especialidad:
        query = query.filter(ChecklistClinicoPaciente.especialidad == especialidad.strip().lower())

    item = query.order_by(ChecklistClinicoPaciente.fecha_actualizacion.desc()).first()
    if item is None:
        return None
    return _serializar_checklist_clinico(item)


@app.put(
    "/profesionales/pacientes/{paciente_id}/checklist-clinico",
    response_model=ChecklistClinicoResponse,
)
def guardar_checklist_clinico_paciente(
    paciente_id: int,
    payload: ChecklistClinicoUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> ChecklistClinicoResponse:
    """Guarda checklist clínico hospitalario por severidad con ruta de escalado."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden editar checklist clínico",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    trastorno_norm = _normalizar_trastorno(payload.trastorno)
    severidad_norm = _normalizar_severidad(payload.severidad)
    checklist = [c.strip() for c in payload.checklist if c.strip()]
    if not checklist:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Checklist vacío")

    item = (
        db.query(ChecklistClinicoPaciente)
        .filter(
            ChecklistClinicoPaciente.paciente_id == paciente_id,
            ChecklistClinicoPaciente.trastorno == trastorno_norm,
            ChecklistClinicoPaciente.severidad == severidad_norm,
            ChecklistClinicoPaciente.especialidad == payload.especialidad.strip().lower(),
        )
        .order_by(ChecklistClinicoPaciente.fecha_actualizacion.desc())
        .first()
    )

    checklist_json = json.dumps(checklist, ensure_ascii=False)

    if item is None:
        item = ChecklistClinicoPaciente(
            paciente_id=paciente_id,
            profesional_id=usuario_actual.id,
            trastorno=trastorno_norm,
            severidad=severidad_norm,
            especialidad=payload.especialidad.strip().lower(),
            checklist_json=checklist_json,
            requiere_escalado=payload.requiere_escalado,
            ruta_escalado_aplicada=(payload.ruta_escalado_aplicada or "").strip() or None,
            observaciones=(payload.observaciones or "").strip() or None,
            fecha_actualizacion=datetime.utcnow(),
        )
        db.add(item)
        db.flush()
    else:
        item.profesional_id = usuario_actual.id
        item.checklist_json = checklist_json
        item.requiere_escalado = payload.requiere_escalado
        item.ruta_escalado_aplicada = (payload.ruta_escalado_aplicada or "").strip() or None
        item.observaciones = (payload.observaciones or "").strip() or None
        item.fecha_actualizacion = datetime.utcnow()

    version = (
        db.query(ChecklistClinicoHistorial)
        .filter(ChecklistClinicoHistorial.checklist_id == item.id)
        .count()
    ) + 1
    db.add(
        ChecklistClinicoHistorial(
            checklist_id=item.id,
            paciente_id=paciente_id,
            profesional_id=usuario_actual.id,
            version=version,
            checklist_json=checklist_json,
            requiere_escalado=payload.requiere_escalado,
            ruta_escalado_aplicada=(payload.ruta_escalado_aplicada or "").strip() or None,
            observaciones=(payload.observaciones or "").strip() or None,
            fecha_evento=datetime.utcnow(),
        )
    )

    db.commit()
    db.refresh(item)
    return _serializar_checklist_clinico(item)


@app.get(
    "/profesionales/pacientes/{paciente_id}/checklist-clinico/auditoria",
    response_model=List[ChecklistClinicoHistorialItemResponse],
)
def obtener_auditoria_checklist_clinico(
    paciente_id: int,
    trastorno: Optional[str] = Query(default=None),
    severidad: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[ChecklistClinicoHistorialItemResponse]:
    """Devuelve historial temporal de cambios de checklist clínico por paciente."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar auditoría clínica",
        )

    query = db.query(ChecklistClinicoHistorial).filter(ChecklistClinicoHistorial.paciente_id == paciente_id)
    if trastorno or severidad:
        query = query.join(
            ChecklistClinicoPaciente,
            ChecklistClinicoPaciente.id == ChecklistClinicoHistorial.checklist_id,
        )
    if trastorno:
        trastorno_norm = _normalizar_trastorno(trastorno)
        query = query.filter(ChecklistClinicoPaciente.trastorno == trastorno_norm)
    if severidad:
        severidad_norm = _normalizar_severidad(severidad)
        query = query.filter(ChecklistClinicoPaciente.severidad == severidad_norm)

    items = query.order_by(ChecklistClinicoHistorial.fecha_evento.desc()).all()
    return [_serializar_checklist_historial(item) for item in items]


@app.get(
    "/profesionales/pacientes/{paciente_id}/severidad-sugerida",
    response_model=SeveridadSugeridaResponse,
)
def obtener_severidad_sugerida_paciente(
    paciente_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeveridadSugeridaResponse:
    """Calcula severidad automática sugerida por IA usando KPIs clínicos."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar severidad sugerida",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    kpis = _calcular_kpis_paciente(db, paciente_id)
    return _sugerir_severidad_desde_kpis(kpis)


@app.get("/profesionales/pacientes/{paciente_id}/informe-hospitalario-pdf")
def descargar_informe_hospitalario_pdf(
    paciente_id: int,
    trastorno: str = Query(...),
    severidad: str = Query(...),
    especialidad: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> Response:
    """Genera PDF hospitalario con protocolo activo, checklist y ruta de escalado."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden descargar informe hospitalario",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    trastorno_norm = _normalizar_trastorno(trastorno)
    severidad_norm = _normalizar_severidad(severidad)

    protocolo_query = db.query(ProtocoloHospitalario).filter(
        ProtocoloHospitalario.trastorno == trastorno_norm,
        ProtocoloHospitalario.severidad == severidad_norm,
        ProtocoloHospitalario.activo == True,
    )
    if especialidad:
        protocolo_query = protocolo_query.filter(ProtocoloHospitalario.especialidad == especialidad.strip().lower())
    protocolo = protocolo_query.order_by(ProtocoloHospitalario.fecha_actualizacion.desc()).first()

    checklist_query = db.query(ChecklistClinicoPaciente).filter(
        ChecklistClinicoPaciente.paciente_id == paciente_id,
        ChecklistClinicoPaciente.trastorno == trastorno_norm,
        ChecklistClinicoPaciente.severidad == severidad_norm,
    )
    if especialidad:
        checklist_query = checklist_query.filter(ChecklistClinicoPaciente.especialidad == especialidad.strip().lower())
    checklist = checklist_query.order_by(ChecklistClinicoPaciente.fecha_actualizacion.desc()).first()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "AuraFit AI - Informe Hospitalario", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Paciente: {paciente.nombre}", ln=True)
    pdf.cell(0, 8, f"Email: {paciente.email}", ln=True)
    pdf.cell(0, 8, f"Trastorno: {trastorno_norm} | Severidad: {severidad_norm}", ln=True)
    pdf.cell(0, 8, f"Generado: {datetime.utcnow().date().isoformat()}", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Protocolo activo", ln=True)
    pdf.set_font("Helvetica", "", 11)
    if protocolo is None:
        pdf.cell(0, 7, "No hay protocolo activo para este filtro.", ln=True)
    else:
        pdf.multi_cell(0, 6, f"Titulo: {protocolo.titulo}")
        pdf.ln(1)
        for idx, item in enumerate(_parsear_checklist_json(protocolo.checklist_json), start=1):
            pdf.multi_cell(0, 6, f"{idx}. {item}")
        pdf.ln(1)
        pdf.multi_cell(0, 6, f"Ruta de escalado: {protocolo.ruta_escalado}")

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Checklist aplicado", ln=True)
    pdf.set_font("Helvetica", "", 11)
    if checklist is None:
        pdf.cell(0, 7, "No hay checklist aplicado para este filtro.", ln=True)
    else:
        for idx, item in enumerate(_parsear_checklist_json(checklist.checklist_json), start=1):
            pdf.multi_cell(0, 6, f"{idx}. {item}")
        pdf.ln(1)
        pdf.multi_cell(
            0,
            6,
            f"Escalado requerido: {'Si' if checklist.requiere_escalado else 'No'}",
        )
        if checklist.ruta_escalado_aplicada:
            pdf.multi_cell(0, 6, f"Ruta aplicada: {checklist.ruta_escalado_aplicada}")
        if checklist.observaciones:
            pdf.multi_cell(0, 6, f"Observaciones: {checklist.observaciones}")

    filename = f"informe_hospitalario_{paciente_id}_{trastorno_norm}_{severidad_norm}.pdf"
    pdf_raw = pdf.output(dest="S")
    if isinstance(pdf_raw, (bytes, bytearray)):
        pdf_bytes = bytes(pdf_raw)
    elif isinstance(pdf_raw, str):
        pdf_bytes = pdf_raw.encode("latin-1", "replace")
    else:
        pdf_bytes = str(pdf_raw).encode("latin-1", "replace")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get(
    "/profesionales/recursos-clinicos",
    response_model=List[RecursoClinicoResponse],
)
def listar_recursos_clinicos(
    trastorno: Optional[str] = Query(default=None),
    especialidad: Optional[str] = Query(default=None),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[RecursoClinicoResponse]:
    """Consulta repositorio persistente de recursos clínicos por área."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar recursos clínicos",
        )

    query = db.query(RecursoClinico).filter(RecursoClinico.activo == True)
    if trastorno:
        query = query.filter(RecursoClinico.trastorno == _normalizar_trastorno(trastorno))
    if especialidad:
        query = query.filter(RecursoClinico.especialidad == especialidad.strip().lower())

    items = query.order_by(RecursoClinico.fecha_actualizacion.desc()).all()
    return [_serializar_recurso_clinico(item) for item in items]


@app.post(
    "/profesionales/recursos-clinicos",
    response_model=RecursoClinicoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_recurso_clinico(
    payload: RecursoClinicoCreateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> RecursoClinicoResponse:
    """Inserta recurso clínico en el repositorio hospitalario persistente."""
    if not _puede_editar_recursos_clinicos(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para crear recursos clínicos",
        )

    item = RecursoClinico(
        trastorno=_normalizar_trastorno(payload.trastorno),
        especialidad=payload.especialidad.strip().lower(),
        titulo=payload.titulo.strip(),
        descripcion=payload.descripcion.strip(),
        url=(payload.url or "").strip() or None,
        nivel_evidencia=(payload.nivel_evidencia or "").strip() or None,
        activo=True,
        fecha_actualizacion=datetime.utcnow(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _serializar_recurso_clinico(item)


@app.get("/profesionales/asignado", response_model=ProfesionalAsignadoResponse)
def obtener_profesional_asignado(
    especialidad: str = Query(..., description="nutricion, gym o salud_mental"),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> ProfesionalAsignadoResponse:
    """Devuelve un profesional de referencia segun especialidad para contacto."""
    _ = usuario_actual  # Solo se usa para exigir autenticacion.
    rol_objetivo = _rol_objetivo_por_especialidad(especialidad)

    profesional = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == rol_objetivo)
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )

    if not profesional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay profesionales disponibles para '{especialidad}'",
        )

    return ProfesionalAsignadoResponse(
        usuario_id=profesional.id,
        nombre=profesional.nombre,
        email=profesional.email,
        rol=rol_objetivo,
        especialidad=especialidad,
    )


@app.post("/profesionales/derivaciones", response_model=DerivacionResponse, status_code=status.HTTP_201_CREATED)
def crear_derivacion_profesional(
    payload: DerivacionCreateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> DerivacionResponse:
    """Permite a un profesional derivar un paciente a otra especialidad."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden crear derivaciones",
        )

    rol_origen = _rol_actual(usuario_actual)

    paciente = db.query(Usuario).filter(Usuario.id == payload.paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    rol_paciente = (paciente.rol.nombre if paciente.rol else "").strip().lower()
    if rol_paciente != "cliente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario indicado no es un paciente",
        )

    rol_destino = _rol_objetivo_por_especialidad(payload.especialidad_destino)
    destinos_permitidos = _roles_destino_permitidos_derivacion(rol_origen)
    if rol_destino not in destinos_permitidos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No puedes derivar a esa especialidad desde tu rol. "
                f"Rol actual: {rol_origen}, destino solicitado: {rol_destino}"
            ),
        )

    destino = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == rol_destino)
        .filter(Usuario.id != usuario_actual.id)
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )
    if not destino:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay especialista disponible para '{payload.especialidad_destino}'",
        )

    derivacion = Derivacion(
        paciente_id=paciente.id,
        origen_profesional_id=usuario_actual.id,
        destino_profesional_id=destino.id,
        especialidad_destino=payload.especialidad_destino.strip().lower(),
        motivo=payload.motivo.strip(),
        nota_paciente=(payload.nota_paciente or "").strip() or None,
        estado="pendiente",
        leida_paciente=0,
    )
    db.add(derivacion)
    db.commit()
    db.refresh(derivacion)

    return _serializar_derivacion(derivacion)


@app.post("/pacientes/solicitar-cita-nutricion", response_model=DerivacionResponse, status_code=status.HTTP_201_CREATED)
def solicitar_cita_nutricion_paciente(
    payload: SolicitarCitaNutricionRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> DerivacionResponse:
    """Permite al paciente solicitar cita de nutrición desde su panel."""
    rol_nombre = (usuario_actual.rol.nombre if usuario_actual.rol else "").strip().lower()
    if rol_nombre != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pacientes pueden solicitar cita de nutricion",
        )

    abierta = (
        db.query(Derivacion)
        .filter(Derivacion.paciente_id == usuario_actual.id)
        .filter(Derivacion.especialidad_destino == "nutricion")
        .filter(Derivacion.estado.in_(["pendiente", "aceptada", "en_seguimiento"]))
        .order_by(Derivacion.fecha_creacion.desc(), Derivacion.id.desc())
        .first()
    )
    if abierta:
        return _serializar_derivacion(abierta)

    nutricionista = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == "nutricionista")
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )
    if not nutricionista:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay nutricionistas disponibles",
        )

    origen = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == "administrador")
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )

    derivacion = Derivacion(
        paciente_id=usuario_actual.id,
        origen_profesional_id=(origen.id if origen else nutricionista.id),
        destino_profesional_id=nutricionista.id,
        especialidad_destino="nutricion",
        motivo=payload.motivo.strip(),
        nota_paciente="Solicitud creada desde tarjeta IMC del paciente",
        estado="pendiente",
        leida_paciente=1,
    )
    db.add(derivacion)
    db.commit()
    db.refresh(derivacion)
    return _serializar_derivacion(derivacion)


@app.post("/pacientes/contactar-especialista", response_model=DerivacionResponse, status_code=status.HTTP_201_CREATED)
def contactar_especialista_paciente(
    payload: SolicitarContactoEspecialistaRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> DerivacionResponse:
    """Crea una derivación directa para que el paciente contacte con un especialista."""
    rol_nombre = (usuario_actual.rol.nombre if usuario_actual.rol else "").strip().lower()
    if rol_nombre != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pacientes pueden contactar con especialistas",
        )

    rol_destino = _rol_objetivo_por_especialidad(payload.especialidad_destino)

    abierta = (
        db.query(Derivacion)
        .filter(Derivacion.paciente_id == usuario_actual.id)
        .filter(Derivacion.especialidad_destino == payload.especialidad_destino.strip().lower())
        .filter(Derivacion.estado.in_(["pendiente", "aceptada", "en_seguimiento"]))
        .order_by(Derivacion.fecha_creacion.desc(), Derivacion.id.desc())
        .first()
    )
    if abierta:
        return _serializar_derivacion(abierta)

    destino = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == rol_destino)
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )
    if not destino:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No hay especialistas disponibles para '{payload.especialidad_destino}'",
        )

    origen = (
        db.query(Usuario)
        .join(Rol, Usuario.rol_id == Rol.id)
        .filter(Rol.nombre == "administrador")
        .order_by(Usuario.fecha_registro.asc(), Usuario.id.asc())
        .first()
    )

    derivacion = Derivacion(
        paciente_id=usuario_actual.id,
        origen_profesional_id=(origen.id if origen else destino.id),
        destino_profesional_id=destino.id,
        especialidad_destino=payload.especialidad_destino.strip().lower(),
        motivo=payload.motivo.strip(),
        nota_paciente=(payload.nota_paciente or "").strip() or None,
        estado="pendiente",
        leida_paciente=0,
    )
    db.add(derivacion)
    db.commit()
    db.refresh(derivacion)
    return _serializar_derivacion(derivacion)


@app.get("/pacientes/derivaciones", response_model=List[DerivacionResponse])
def listar_derivaciones_paciente(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[DerivacionResponse]:
    """Lista derivaciones del paciente autenticado para notificaciones y seguimiento."""
    rol_nombre = (usuario_actual.rol.nombre if usuario_actual.rol else "").strip().lower()
    if rol_nombre != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pacientes pueden consultar sus derivaciones",
        )

    derivaciones = (
        db.query(Derivacion)
        .filter(Derivacion.paciente_id == usuario_actual.id)
        .order_by(Derivacion.fecha_creacion.desc(), Derivacion.id.desc())
        .all()
    )
    return [_serializar_derivacion(d) for d in derivaciones]


@app.patch("/pacientes/derivaciones/{derivacion_id}/leida", response_model=DerivacionResponse)
def marcar_derivacion_como_leida(
    derivacion_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> DerivacionResponse:
    """Permite al paciente marcar una derivacion como leida."""
    rol_nombre = (usuario_actual.rol.nombre if usuario_actual.rol else "").strip().lower()
    if rol_nombre != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pacientes pueden marcar derivaciones",
        )

    derivacion = (
        db.query(Derivacion)
        .filter(Derivacion.id == derivacion_id)
        .filter(Derivacion.paciente_id == usuario_actual.id)
        .first()
    )
    if not derivacion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Derivacion no encontrada")

    derivacion.leida_paciente = 1
    db.commit()
    db.refresh(derivacion)
    return _serializar_derivacion(derivacion)


@app.post("/seguimiento/checkin", response_model=SeguimientoCheckinResponse)
def registrar_checkin_diario(
    payload: SeguimientoCheckinRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeguimientoCheckinResponse:
    """Guarda o actualiza el check-in diario de bienestar del paciente autenticado."""
    hoy = datetime.utcnow().date()
    sentimiento = _sentimiento_desde_animo(payload.estado_animo, payload.estres)
    nota = _construir_nota_checkin(
        energia=payload.energia,
        estres=payload.estres,
        horas_sueno=payload.horas_sueno,
        notas=payload.notas,
    )

    registro = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_actual.id)
        .filter(RegistroDiario.fecha == hoy)
        .order_by(RegistroDiario.id.desc())
        .first()
    )

    if registro and _parsear_nota_checkin(registro.notas_diario):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El check-in diario ya fue registrado hoy. Podrás repetirlo mañana.",
        )

    if not registro:
        registro = RegistroDiario(
            usuario_id=usuario_actual.id,
            fecha=hoy,
        )
        db.add(registro)

    registro.estado_animo_puntuacion = payload.estado_animo
    registro.sentimiento_detectado_ia = sentimiento
    registro.notas_diario = nota

    db.commit()
    db.refresh(registro)

    return SeguimientoCheckinResponse(
        usuario_id=usuario_actual.id,
        fecha=hoy.isoformat(),
        estado_animo=payload.estado_animo,
        energia=payload.energia,
        estres=payload.estres,
        horas_sueno=payload.horas_sueno,
        sentimiento=sentimiento,
        mensaje="Check-in diario guardado correctamente",
    )


@app.post("/seguimiento/comidas", response_model=SeguimientoComidaItemResponse)
def registrar_comida_diaria(
    payload: SeguimientoComidaRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeguimientoComidaItemResponse:
    """Permite al paciente registrar comidas para seguimiento nutricional profesional."""
    hora = (payload.hora or "").strip()
    if hora and not re.match(r"^(?:[01]?\d|2[0-3]):[0-5]\d$", hora):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="hora debe tener formato HH:MM",
        )

    texto = _texto_meal_log(payload.tipo, payload.descripcion, hora or None)
    item = MensajeChat(
        usuario_id=usuario_actual.id,
        emisor="meal_log",
        texto=texto,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    parsed = _parsear_meal_log(item.texto) or {}
    return SeguimientoComidaItemResponse(
        id=item.id,
        usuario_id=usuario_actual.id,
        tipo=str(parsed.get("tipo") or "comida"),
        descripcion=str(parsed.get("descripcion") or payload.descripcion),
        hora=(parsed.get("hora") if parsed.get("hora") is not None else None),
        fecha=(item.fecha_creacion.date().isoformat() if item.fecha_creacion else datetime.utcnow().date().isoformat()),
        fecha_creacion=(item.fecha_creacion.isoformat() if item.fecha_creacion else datetime.utcnow().isoformat()),
    )


@app.get("/seguimiento/comidas", response_model=List[SeguimientoComidaItemResponse])
def listar_comidas_diarias(
    dias: int = Query(default=14, ge=1, le=60),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[SeguimientoComidaItemResponse]:
    """Lista comidas registradas por el paciente para su panel nutricional."""
    desde = datetime.utcnow() - timedelta(days=dias)
    rows = (
        db.query(MensajeChat)
        .filter(MensajeChat.usuario_id == usuario_actual.id, MensajeChat.emisor == "meal_log")
        .filter(MensajeChat.fecha_creacion >= desde)
        .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
        .all()
    )

    salida: List[SeguimientoComidaItemResponse] = []
    for row in rows:
        parsed = _parsear_meal_log(row.texto)
        if not parsed:
            continue
        salida.append(
            SeguimientoComidaItemResponse(
                id=row.id,
                usuario_id=usuario_actual.id,
                tipo=str(parsed.get("tipo") or "comida"),
                descripcion=str(parsed.get("descripcion") or "").strip(),
                hora=(parsed.get("hora") if parsed.get("hora") is not None else None),
                fecha=(row.fecha_creacion.date().isoformat() if row.fecha_creacion else datetime.utcnow().date().isoformat()),
                fecha_creacion=(row.fecha_creacion.isoformat() if row.fecha_creacion else datetime.utcnow().isoformat()),
            )
        )
    return salida


@app.get(
    "/profesionales/pacientes/{paciente_id}/comidas",
    response_model=List[SeguimientoComidaItemResponse],
)
def listar_comidas_paciente_profesional(
    paciente_id: int,
    dias: int = Query(default=14, ge=1, le=90),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[SeguimientoComidaItemResponse]:
    """Permite a profesionales ver comidas registradas por paciente (nutrición y medicina incluidas)."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar comidas de pacientes",
        )

    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    desde = datetime.utcnow() - timedelta(days=dias)
    rows = (
        db.query(MensajeChat)
        .filter(MensajeChat.usuario_id == paciente_id, MensajeChat.emisor == "meal_log")
        .filter(MensajeChat.fecha_creacion >= desde)
        .order_by(MensajeChat.fecha_creacion.desc(), MensajeChat.id.desc())
        .all()
    )

    salida: List[SeguimientoComidaItemResponse] = []
    for row in rows:
        parsed = _parsear_meal_log(row.texto)
        if not parsed:
            continue
        salida.append(
            SeguimientoComidaItemResponse(
                id=row.id,
                usuario_id=paciente_id,
                tipo=str(parsed.get("tipo") or "comida"),
                descripcion=str(parsed.get("descripcion") or "").strip(),
                hora=(parsed.get("hora") if parsed.get("hora") is not None else None),
                fecha=(row.fecha_creacion.date().isoformat() if row.fecha_creacion else datetime.utcnow().date().isoformat()),
                fecha_creacion=(row.fecha_creacion.isoformat() if row.fecha_creacion else datetime.utcnow().isoformat()),
            )
        )
    return salida


@app.get("/seguimiento/resumen-semanal", response_model=SeguimientoResumenSemanalResponse)
def obtener_resumen_semanal(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeguimientoResumenSemanalResponse:
    """Devuelve resumen de 7 dias a partir de check-ins guardados en registros diarios."""
    hoy = datetime.utcnow().date()
    inicio = hoy - timedelta(days=6)

    registros = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_actual.id)
        .filter(RegistroDiario.fecha >= inicio)
        .filter(RegistroDiario.fecha <= hoy)
        .order_by(RegistroDiario.fecha.asc(), RegistroDiario.id.asc())
        .all()
    )

    animos: List[int] = []
    energias: List[int] = []
    estreses: List[int] = []
    suenos: List[float] = []

    for r in registros:
        if r.estado_animo_puntuacion is None:
            continue
        data = _parsear_nota_checkin(r.notas_diario)
        if not data:
            continue
        try:
            energia = int(data.get("energia", "0"))
            estres = int(data.get("estres", "0"))
            sueno = float(data.get("sueno", "0"))
        except ValueError:
            continue

        animos.append(int(r.estado_animo_puntuacion))
        energias.append(energia)
        estreses.append(estres)
        suenos.append(sueno)

    if not animos:
        return SeguimientoResumenSemanalResponse(
            usuario_id=usuario_actual.id,
            dias_registrados=0,
            promedio_animo=0,
            promedio_energia=0,
            promedio_estres=0,
            promedio_sueno=0,
            ultima_actualizacion=None,
        )

    return SeguimientoResumenSemanalResponse(
        usuario_id=usuario_actual.id,
        dias_registrados=len(animos),
        promedio_animo=round(sum(animos) / len(animos), 2),
        promedio_energia=round(sum(energias) / len(energias), 2),
        promedio_estres=round(sum(estreses) / len(estreses), 2),
        promedio_sueno=round(sum(suenos) / len(suenos), 2),
        ultima_actualizacion=(
            registros[-1].fecha.isoformat() if registros else None
        ),
    )


@app.get("/seguimiento/historico", response_model=List[SeguimientoHistoricoItemResponse])
def obtener_historico_seguimiento(
    dias: int = Query(default=14, ge=3, le=60),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[SeguimientoHistoricoItemResponse]:
    """Devuelve los ultimos check-ins del paciente para graficas y paneles."""
    hoy = datetime.utcnow().date()
    inicio = hoy - timedelta(days=dias - 1)

    registros = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_actual.id)
        .filter(RegistroDiario.fecha >= inicio)
        .filter(RegistroDiario.fecha <= hoy)
        .order_by(RegistroDiario.fecha.asc(), RegistroDiario.id.asc())
        .all()
    )

    puntos: List[SeguimientoHistoricoItemResponse] = []
    for registro in registros:
        data = _parsear_nota_checkin(registro.notas_diario)
        if not data or registro.estado_animo_puntuacion is None:
            continue

        try:
            energia = int(data.get("energia", "0"))
            estres = int(data.get("estres", "0"))
            sueno = float(data.get("sueno", "0"))
        except ValueError:
            continue

        puntos.append(
            SeguimientoHistoricoItemResponse(
                fecha=registro.fecha.isoformat(),
                estado_animo=int(registro.estado_animo_puntuacion),
                energia=energia,
                estres=estres,
                horas_sueno=sueno,
                sentimiento=registro.sentimiento_detectado_ia or "neutral",
            )
        )

    return puntos


@app.get("/seguimiento/racha", response_model=SeguimientoRachaResponse)
def obtener_racha_seguimiento(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeguimientoRachaResponse:
    """Devuelve racha actual y mejor racha de check-ins del paciente."""
    registros = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_actual.id)
        .order_by(RegistroDiario.fecha.asc(), RegistroDiario.id.asc())
        .all()
    )
    fechas = [r.fecha for r in registros if _parsear_nota_checkin(r.notas_diario)]
    rachas = _calcular_rachas(fechas)

    return SeguimientoRachaResponse(
        usuario_id=usuario_actual.id,
        racha_actual=rachas["actual"],
        mejor_racha=rachas["mejor"],
        ultimo_checkin=rachas["ultima"],
    )


@app.get("/seguimiento/estado-actual", response_model=SeguimientoEstadoActualResponse)
def obtener_estado_actual(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeguimientoEstadoActualResponse:
    """Devuelve estado diario (bien/regular/mal) y pasos accionables inmediatos."""
    hoy = datetime.utcnow().date()
    registro = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_actual.id)
        .filter(RegistroDiario.fecha == hoy)
        .order_by(RegistroDiario.id.desc())
        .first()
    )

    parsed = _parsear_nota_checkin(registro.notas_diario if registro else None)
    animo = int(registro.estado_animo_puntuacion) if registro and registro.estado_animo_puntuacion is not None else None
    estado = _estado_bienestar_desde_checkin(parsed, animo)

    return SeguimientoEstadoActualResponse(
        fecha=hoy.isoformat(),
        estado=estado["estado"],
        score_bienestar=int(estado["score"]),
        checkin_realizado_hoy=parsed is not None,
        mensaje=estado["mensaje"],
        pasos_recomendados=_pasos_por_estado(estado["estado"]),
    )


@app.get("/seguimiento/cumplimiento-diario", response_model=SeguimientoCumplimientoDiarioResponse)
def obtener_cumplimiento_diario(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeguimientoCumplimientoDiarioResponse:
    """Calcula cumplimiento diario por secciones y progreso de comidas."""
    hoy = datetime.utcnow().date()
    dia = hoy.weekday()

    habitos = (
        db.query(HabitoAgenda)
        .filter(HabitoAgenda.usuario_id == usuario_actual.id, HabitoAgenda.dia_semana == dia)
        .order_by(HabitoAgenda.orden.asc(), HabitoAgenda.id.asc())
        .all()
    )

    if not habitos:
        habitos = _semilla_habitos_base(usuario_actual.id, dia)
        db.add_all(habitos)
        db.commit()
        for h in habitos:
            db.refresh(h)

    total = len(habitos)
    completados = len([h for h in habitos if bool(h.completado)])
    cumplimiento = round((completados / total) * 100, 2) if total else 0.0

    nutri = [h for h in habitos if _es_habito_nutricion(h)]
    gym = [h for h in habitos if _es_habito_gym(h)]
    mental = [h for h in habitos if _es_habito_mental(h)]

    def pct(items: List[HabitoAgenda]) -> float:
        if not items:
            return 0.0
        done = len([i for i in items if bool(i.completado)])
        return round((done / len(items)) * 100, 2)

    comidas = [h for h in habitos if _normalizar_ascii(h.titulo).startswith("comida")]
    comidas_objetivo = len(comidas)
    comidas_marcadas = len([c for c in comidas if bool(c.completado)])

    registro_hoy = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_actual.id)
        .filter(RegistroDiario.fecha == hoy)
        .order_by(RegistroDiario.id.desc())
        .first()
    )
    checkin_hoy = _parsear_nota_checkin(registro_hoy.notas_diario if registro_hoy else None) is not None

    return SeguimientoCumplimientoDiarioResponse(
        fecha=hoy.isoformat(),
        total_tareas=total,
        tareas_completadas=completados,
        cumplimiento_pct=cumplimiento,
        comidas_objetivo=comidas_objetivo,
        comidas_marcadas=comidas_marcadas,
        cumplimiento_nutricion_pct=pct(nutri),
        cumplimiento_gym_pct=pct(gym),
        cumplimiento_salud_mental_pct=pct(mental),
        checkin_realizado_hoy=checkin_hoy,
    )


@app.get("/seguimiento/recursos-personalizados", response_model=SeguimientoRecursosPersonalizadosResponse)
def obtener_recursos_personalizados(
    seccion: str = Query(default="salud_mental"),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> SeguimientoRecursosPersonalizadosResponse:
    """Devuelve recursos dinámicos por sección según estado actual del usuario."""
    hoy = datetime.utcnow().date()
    registro = (
        db.query(RegistroDiario)
        .filter(RegistroDiario.usuario_id == usuario_actual.id)
        .order_by(RegistroDiario.fecha.desc(), RegistroDiario.id.desc())
        .first()
    )

    parsed = _parsear_nota_checkin(registro.notas_diario if registro else None)
    animo = int(registro.estado_animo_puntuacion) if registro and registro.estado_animo_puntuacion is not None else None
    estado = _estado_bienestar_desde_checkin(parsed, animo)["estado"]
    seccion_norm = _normalizar_seccion_recurso(seccion)

    return SeguimientoRecursosPersonalizadosResponse(
        fecha=hoy.isoformat(),
        seccion=seccion_norm,
        estado=estado,
        recursos=_recursos_personalizados_por_seccion(seccion_norm, estado, registro),
    )


@app.get("/usuarios/preferencias-recursos", response_model=PreferenciasRecursosResponse)
def obtener_preferencias_recursos_usuario(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PreferenciasRecursosResponse:
    """Devuelve preferencias persistidas de la pantalla de recursos por usuario."""
    pref = _cargar_preferencias_recursos_usuario(db, usuario_actual.id)
    return PreferenciasRecursosResponse(
        area_seleccionada=pref["area_seleccionada"],
        auto_area=bool(pref["auto_area"]),
        actualizado_en=pref.get("actualizado_en"),
    )


@app.put("/usuarios/preferencias-recursos", response_model=PreferenciasRecursosResponse)
def actualizar_preferencias_recursos_usuario(
    payload: PreferenciasRecursosRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PreferenciasRecursosResponse:
    """Persiste área seleccionada y modo auto-recomendación para recursos."""
    pref = _guardar_preferencias_recursos_usuario(
        db,
        usuario_actual.id,
        payload.area_seleccionada,
        payload.auto_area,
    )
    return PreferenciasRecursosResponse(
        area_seleccionada=pref["area_seleccionada"],
        auto_area=bool(pref["auto_area"]),
        actualizado_en=pref.get("actualizado_en"),
    )


@app.get("/seguimiento/inteligencia-recursos", response_model=InteligenciaRecursosResponse)
def obtener_inteligencia_recursos(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> InteligenciaRecursosResponse:
    """
    Recomienda el área más relevante y devuelve semáforo de riesgo por área
    para personalizar dinámicamente la pantalla de recursos.
    """
    data = _calcular_inteligencia_recursos(db, usuario_actual.id)
    return InteligenciaRecursosResponse(
        area_recomendada=str(data["area_recomendada"]),
        motivo=str(data["motivo"]),
        riesgo_por_area=dict(data["riesgo_por_area"]),
        score_por_area=dict(data["score_por_area"]),
        semaforo_global=str(data["semaforo_global"]),
        actualizado_en=str(data["actualizado_en"]),
    )


@app.get("/estadisticas/graficos")
def obtener_graficos_estadisticas(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Devuelve gráficos y estadísticas de 7 días para dashboard.
    
    Incluye:
    - Línea de ánimo, energía, estrés, sueño
    - Radar de bienestar (multidimensional)
    - Barras comparativas
    - Resumen con estado general y tendencias
    """
    try:
        from services.estadisticas_service import (
            _calcular_estadisticas_7dias,
            generar_gráfico_lineal,
            generar_gráfico_radar,
            generar_gráfico_barras_comparativa,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de estadísticas no disponible",
        )

    datos_7dias = _calcular_estadisticas_7dias(db, usuario_actual.id)

    return {
        "ok": True,
        "usuario_id": usuario_actual.id,
        "periodo": "7 días",
        "resumen": {
            "dias_registrados": datos_7dias["dias_registrados"],
            "racha_actual": datos_7dias["racha_actual"],
            "estado_general": datos_7dias["estado_general"],
            "color_estado": datos_7dias["color_estado"],
            "promedio_animo": datos_7dias["promedio_animo"],
            "promedio_energia": datos_7dias["promedio_energia"],
            "promedio_estres": datos_7dias["promedio_estres"],
            "promedio_sueno": datos_7dias["promedio_sueno"],
            "tendencia_animo": datos_7dias["tendencia_animo"],
            "tendencia_energia": datos_7dias["tendencia_energia"],
            "tendencia_estres": datos_7dias["tendencia_estres"],
        },
        "graficos": [
            generar_gráfico_lineal(
                "Ánimo (últimos 7 días)",
                datos_7dias["datos_diarios"],
                "Puntuación (1-10)",
                "animo",
                "#3b82f6",
            ),
            generar_gráfico_lineal(
                "Energía (últimos 7 días)",
                datos_7dias["datos_diarios"],
                "Energía (1-10)",
                "energia",
                "#10b981",
            ),
            generar_gráfico_lineal(
                "Estrés (últimos 7 días) - Menos es mejor",
                datos_7dias["datos_diarios"],
                "Estrés (1-10)",
                "estres",
                "#f59e0b",
            ),
            generar_gráfico_lineal(
                "Horas de sueño (últimos 7 días)",
                datos_7dias["datos_diarios"],
                "Horas",
                "sueno",
                "#8b5cf6",
            ),
            generar_gráfico_lineal(
                "Score de bienestar (últimos 7 días)",
                datos_7dias["datos_diarios"],
                "Score (0-100)",
                "score_bienestar",
                "#06b6d4",
            ),
            generar_gráfico_radar(
                "Bienestar multidimensional",
                datos_7dias["promedio_animo"],
                datos_7dias["promedio_energia"],
                datos_7dias["promedio_estres"],
                datos_7dias["promedio_sueno"],
            ),
            generar_gráfico_barras_comparativa(
                "Comparativa de indicadores",
                datos_7dias,
            ),
        ],
        "datos_diarios": datos_7dias["datos_diarios"],
        "fecha_actualizacion": datos_7dias["fecha_actualizacion"],
    }


@app.get("/habitos/agenda", response_model=List[HabitoAgendaResponse])
def listar_habitos_agenda(
    dia_semana: Optional[int] = Query(default=None, ge=0, le=6),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[HabitoAgendaResponse]:
    """Devuelve la agenda persistida del usuario para un dia concreto."""
    dia_normalizado = datetime.utcnow().weekday() if dia_semana is None else int(dia_semana)
    habitos = (
        db.query(HabitoAgenda)
        .filter(HabitoAgenda.usuario_id == usuario_actual.id, HabitoAgenda.dia_semana == dia_normalizado)
        .order_by(HabitoAgenda.orden.asc(), HabitoAgenda.id.asc())
        .all()
    )

    if not habitos:
        habitos = _semilla_habitos_base(usuario_actual.id, dia_normalizado)
        db.add_all(habitos)
        db.commit()
        for habito in habitos:
            db.refresh(habito)
    else:
        existentes = {h.titulo.strip().lower() for h in habitos}
        nuevos: List[HabitoAgenda] = []
        for item in HABITOS_BASE:
            clave = item["titulo"].strip().lower()
            if clave in existentes:
                continue
            nuevos.append(
                HabitoAgenda(
                    usuario_id=usuario_actual.id,
                    dia_semana=dia_normalizado,
                    titulo=item["titulo"],
                    subtitulo=item["subtitulo"],
                    franja=item["franja"],
                    color_hex=_parsear_color_hex(item["color_hex"]),
                    orden=item["orden"],
                    completado=False,
                )
            )
        if nuevos:
            db.add_all(nuevos)
            db.commit()
            habitos = (
                db.query(HabitoAgenda)
                .filter(HabitoAgenda.usuario_id == usuario_actual.id, HabitoAgenda.dia_semana == dia_normalizado)
                .order_by(HabitoAgenda.orden.asc(), HabitoAgenda.id.asc())
                .all()
            )

    hoy = datetime.utcnow().date()
    if dia_normalizado == hoy.weekday():
        requiere_reset = [h for h in habitos if h.ultima_actualizacion and h.ultima_actualizacion.date() < hoy and h.completado]
        if requiere_reset:
            for h in requiere_reset:
                h.completado = False
                h.ultima_actualizacion = datetime.utcnow()
            db.commit()
            habitos = (
                db.query(HabitoAgenda)
                .filter(HabitoAgenda.usuario_id == usuario_actual.id, HabitoAgenda.dia_semana == dia_normalizado)
                .order_by(HabitoAgenda.orden.asc(), HabitoAgenda.id.asc())
                .all()
            )

    return [_serializar_habito_agenda(h) for h in habitos]


@app.patch("/habitos/agenda/{habito_id}", response_model=HabitoAgendaResponse)
def actualizar_habito_agenda(
    habito_id: int,
    payload: HabitoAgendaUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> HabitoAgendaResponse:
    """Actualiza el estado de completado de un habito concreto."""
    habito = db.query(HabitoAgenda).filter(HabitoAgenda.id == habito_id).first()
    if not habito:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habito no encontrado")

    if habito.usuario_id != usuario_actual.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes editar este habito")

    hoy = datetime.utcnow().date()
    if (
        payload.completado
        and habito.completado
        and habito.ultima_actualizacion is not None
        and habito.ultima_actualizacion.date() == hoy
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este habito ya se completo hoy. Puedes repetirlo manana.",
        )

    habito.completado = payload.completado
    habito.ultima_actualizacion = datetime.utcnow()
    db.commit()
    db.refresh(habito)
    return _serializar_habito_agenda(habito)


@app.get("/profesionales/derivaciones/recibidas", response_model=List[DerivacionResponse])
def listar_derivaciones_recibidas(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[DerivacionResponse]:
    """Bandeja del especialista destino con derivaciones pendientes/activas."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden ver derivaciones recibidas",
        )

    derivaciones = (
        db.query(Derivacion)
        .filter(Derivacion.destino_profesional_id == usuario_actual.id)
        .order_by(Derivacion.fecha_creacion.desc(), Derivacion.id.desc())
        .all()
    )
    return [_serializar_derivacion(d) for d in derivaciones]


@app.patch("/profesionales/derivaciones/{derivacion_id}/estado", response_model=DerivacionResponse)
def actualizar_estado_derivacion(
    derivacion_id: int,
    payload: DerivacionEstadoUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> DerivacionResponse:
    """Permite al especialista destino actualizar el estado de una derivacion."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden actualizar derivaciones",
        )

    derivacion = db.query(Derivacion).filter(Derivacion.id == derivacion_id).first()
    if not derivacion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Derivacion no encontrada")

    if derivacion.destino_profesional_id != usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el especialista destino puede actualizar esta derivacion",
        )

    derivacion.estado = _normalizar_estado_derivacion(payload.estado)
    db.commit()
    db.refresh(derivacion)
    return _serializar_derivacion(derivacion)


@app.post("/profesionales/agenda/huecos", response_model=CitaDisponibleResponse, status_code=status.HTTP_201_CREATED)
def publicar_hueco_agenda(
    payload: CitaDisponibleCreateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> CitaDisponibleResponse:
    """Permite a un profesional publicar huecos disponibles en su agenda."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden publicar huecos de agenda",
        )

    inicio = _parse_iso_datetime(payload.inicio, "inicio")
    fin = _parse_iso_datetime(payload.fin, "fin")
    if fin <= inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fecha de fin debe ser posterior al inicio",
        )

    if inicio < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden publicar huecos en el pasado",
        )

    especialidad = _normalizar_ascii(payload.especialidad)
    rol_objetivo = _rol_objetivo_por_especialidad(especialidad)
    if _rol_actual(usuario_actual) != rol_objetivo and _rol_actual(usuario_actual) != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tu rol no coincide con la especialidad '{especialidad}'",
        )

    solape = (
        db.query(CitaDisponible)
        .filter(CitaDisponible.especialista_id == usuario_actual.id)
        .filter(CitaDisponible.estado == "disponible")
        .filter(CitaDisponible.inicio < fin)
        .filter(CitaDisponible.fin > inicio)
        .first()
    )
    if solape:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un hueco disponible que se solapa con ese horario",
        )

    hueco = CitaDisponible(
        especialista_id=usuario_actual.id,
        especialidad=especialidad,
        inicio=inicio,
        fin=fin,
        estado="disponible",
        notas=(payload.notas or "").strip() or None,
    )
    db.add(hueco)
    db.commit()
    db.refresh(hueco)
    return _serializar_cita_disponible(hueco)


@app.get("/citas/disponibles", response_model=List[CitaDisponibleResponse])
def listar_citas_disponibles(
    especialidad: Optional[str] = Query(default=None),
    desde: Optional[str] = Query(default=None),
    hasta: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[CitaDisponibleResponse]:
    """Lista huecos disponibles con filtros de especialidad y rango temporal."""
    query = db.query(CitaDisponible).filter(CitaDisponible.estado == "disponible")

    if especialidad:
        query = query.filter(CitaDisponible.especialidad == _normalizar_ascii(especialidad))
    if desde:
        query = query.filter(CitaDisponible.inicio >= _parse_iso_datetime(desde, "desde"))
    if hasta:
        query = query.filter(CitaDisponible.inicio <= _parse_iso_datetime(hasta, "hasta"))

    huecos = query.order_by(CitaDisponible.inicio.asc(), CitaDisponible.id.asc()).limit(300).all()
    return [_serializar_cita_disponible(h) for h in huecos]


@app.post("/pacientes/citas/reservar", response_model=CitaReservaConTriageResponse)
def reservar_cita_con_triaje_ia(
    payload: CitaReservarRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> CitaReservaConTriageResponse:
    """Reserva cita para paciente y aplica triaje IA para prioridad preferente/no preferente."""
    if _rol_actual(usuario_actual) != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pacientes pueden reservar citas",
        )

    especialidad = _normalizar_ascii(payload.especialidad_destino)
    _rol_objetivo_por_especialidad(especialidad)

    hueco_query = (
        db.query(CitaDisponible)
        .filter(CitaDisponible.estado == "disponible")
        .filter(CitaDisponible.especialidad == especialidad)
    )
    if payload.cita_disponible_id is not None:
        hueco_query = hueco_query.filter(CitaDisponible.id == payload.cita_disponible_id)

    hueco = hueco_query.order_by(CitaDisponible.inicio.asc(), CitaDisponible.id.asc()).first()
    if not hueco:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay huecos disponibles para esa especialidad",
        )

    triaje = _clasificar_prioridad_cita_ia(
        especialidad_destino=especialidad,
        motivo=payload.motivo,
        formulario=payload.formulario,
    )

    conflicto = (
        db.query(CitaReservada)
        .filter(CitaReservada.paciente_id == usuario_actual.id)
        .filter(CitaReservada.estado.in_(["pendiente", "confirmada"]))
        .filter(CitaReservada.inicio < hueco.fin)
        .filter(CitaReservada.fin > hueco.inicio)
        .first()
    )
    if conflicto:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya tienes una cita que se solapa con ese horario",
        )

    reserva = CitaReservada(
        cita_disponible_id=hueco.id,
        paciente_id=usuario_actual.id,
        especialista_id=hueco.especialista_id,
        especialidad=hueco.especialidad,
        inicio=hueco.inicio,
        fin=hueco.fin,
        motivo=(payload.motivo or "").strip(),
        prioridad_ia=triaje.prioridad,
        puntuacion_prioridad=triaje.puntuacion,
        justificacion_ia=triaje.justificacion,
        estado="pendiente" if triaje.preferente else "confirmada",
    )
    hueco.estado = "reservada"
    db.add(reserva)
    db.commit()
    db.refresh(reserva)

    return CitaReservaConTriageResponse(
        cita=_serializar_cita_reservada(reserva),
        triaje=triaje,
    )


@app.get("/pacientes/mis-citas", response_model=List[CitaReservadaResponse])
def listar_mis_citas(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[CitaReservadaResponse]:
    """Devuelve las citas reservadas por el paciente autenticado."""
    if _rol_actual(usuario_actual) != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pacientes pueden consultar sus citas",
        )

    citas = (
        db.query(CitaReservada)
        .filter(CitaReservada.paciente_id == usuario_actual.id)
        .order_by(CitaReservada.inicio.asc(), CitaReservada.id.asc())
        .all()
    )
    return [_serializar_cita_reservada(c) for c in citas]


@app.get("/profesionales/mis-citas", response_model=List[CitaReservadaResponse])
def listar_citas_profesional(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[CitaReservadaResponse]:
    """Devuelve las citas reservadas al profesional autenticado."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar su agenda reservada",
        )

    citas = (
        db.query(CitaReservada)
        .filter(CitaReservada.especialista_id == usuario_actual.id)
        .order_by(CitaReservada.inicio.asc(), CitaReservada.id.asc())
        .all()
    )
    return [_serializar_cita_reservada(c) for c in citas]

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


# ---------------------------------------------------------------------------
# PLANES IA – Gestión de planes con duración y notificaciones de vencimiento
# ---------------------------------------------------------------------------

class PlanIACreateRequest(BaseModel):
    tipo: str  # nutricion | entrenamiento | psicologia
    objetivo: Optional[str] = None
    contenido: str
    duracion_dias: int = 7


class PlanIAResponse(BaseModel):
    id: int
    tipo: str
    objetivo: Optional[str]
    contenido: str
    duracion_dias: int
    fecha_inicio: str
    fecha_fin: str
    activo: bool
    dias_restantes: int
    vence_pronto: bool  # True si quedan <=2 días


class NotificacionPlanResponse(BaseModel):
    plan_id: int
    tipo: str
    mensaje: str
    dias_restantes: int
    urgente: bool


class PlanIAProfesionalUpdateRequest(BaseModel):
    objetivo: Optional[str] = None
    contenido: Optional[str] = None
    duracion_dias: Optional[int] = None
    activo: Optional[bool] = None


def _tipos_plan_validos() -> set[str]:
    return {"nutricion", "entrenamiento", "psicologia"}


def _roles_permitidos_por_tipo_plan(tipo: str) -> set[str]:
    mapa = {
        "nutricion": {"nutricionista", "medico", "administrador"},
        "entrenamiento": {"coach", "medico", "administrador"},
        "psicologia": {"psicologo", "medico", "administrador"},
    }
    return mapa.get(tipo, {"administrador"})


def _assert_permiso_plan_por_tipo(usuario: Usuario, tipo: str) -> None:
    rol = _rol_actual(usuario)
    if rol not in _roles_permitidos_por_tipo_plan(tipo):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar este tipo de rutina",
        )


def _assert_paciente_existente(db: Session, paciente_id: int) -> Usuario:
    paciente = db.query(Usuario).filter(Usuario.id == paciente_id).first()
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado",
        )
    return paciente


def _serializar_plan_ia(plan: PlanIA) -> PlanIAResponse:
    hoy = datetime.utcnow()
    dias_restantes = max(0, (plan.fecha_fin - hoy).days)
    return PlanIAResponse(
        id=plan.id,
        tipo=plan.tipo,
        objetivo=plan.objetivo,
        contenido=plan.contenido,
        duracion_dias=plan.duracion_dias,
        fecha_inicio=plan.fecha_inicio.isoformat(),
        fecha_fin=plan.fecha_fin.isoformat(),
        activo=plan.activo,
        dias_restantes=dias_restantes,
        vence_pronto=dias_restantes <= 2 and plan.activo,
    )


@app.post("/planes", response_model=PlanIAResponse, status_code=status.HTTP_201_CREATED)
def crear_plan_ia(
    payload: PlanIACreateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PlanIAResponse:
    """Guarda un plan generado por la IA con fecha de inicio y fin calculada."""
    if payload.duracion_dias < 1 or payload.duracion_dias > 365:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="duracion_dias debe estar entre 1 y 365",
        )
    tipos_validos = _tipos_plan_validos()
    if payload.tipo not in tipos_validos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tipo debe ser uno de: {', '.join(tipos_validos)}",
        )

    ahora = datetime.utcnow()
    # Desactivar planes activos del mismo tipo para este usuario
    db.query(PlanIA).filter(
        PlanIA.usuario_id == usuario_actual.id,
        PlanIA.tipo == payload.tipo,
        PlanIA.activo == True,  # noqa: E712
    ).update({"activo": False})

    plan = PlanIA(
        usuario_id=usuario_actual.id,
        tipo=payload.tipo,
        objetivo=payload.objetivo,
        contenido=payload.contenido,
        duracion_dias=payload.duracion_dias,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=payload.duracion_dias),
        activo=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serializar_plan_ia(plan)


@app.get("/profesionales/pacientes/{paciente_id}/planes", response_model=List[PlanIAResponse])
def listar_planes_paciente_profesional(
    paciente_id: int,
    activo: Optional[bool] = None,
    tipo: Optional[str] = None,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[PlanIAResponse]:
    """Permite a profesionales listar rutinas IA de un paciente."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden consultar planes de pacientes",
        )

    _assert_paciente_existente(db, paciente_id)
    q = db.query(PlanIA).filter(PlanIA.usuario_id == paciente_id)

    tipo_norm = None
    if tipo:
        tipo_norm = tipo.strip().lower()
        if tipo_norm not in _tipos_plan_validos():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tipo invalido para plan",
            )
        _assert_permiso_plan_por_tipo(usuario_actual, tipo_norm)
        q = q.filter(PlanIA.tipo == tipo_norm)

    if activo is not None:
        q = q.filter(PlanIA.activo == activo)

    planes = q.order_by(PlanIA.fecha_inicio.desc()).all()
    if tipo_norm is None:
        rol_actual = _rol_actual(usuario_actual)
        planes = [p for p in planes if rol_actual in _roles_permitidos_por_tipo_plan(p.tipo)]
    return [_serializar_plan_ia(p) for p in planes]


@app.post(
    "/profesionales/pacientes/{paciente_id}/planes",
    response_model=PlanIAResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_plan_paciente_profesional(
    paciente_id: int,
    payload: PlanIACreateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PlanIAResponse:
    """Crea o reemplaza una rutina IA de paciente desde rol profesional."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden crear rutinas de pacientes",
        )

    tipo_norm = payload.tipo.strip().lower()
    if payload.duracion_dias < 1 or payload.duracion_dias > 365:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="duracion_dias debe estar entre 1 y 365",
        )
    if tipo_norm not in _tipos_plan_validos():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tipo invalido para plan",
        )
    _assert_permiso_plan_por_tipo(usuario_actual, tipo_norm)
    _assert_paciente_existente(db, paciente_id)

    ahora = datetime.utcnow()
    db.query(PlanIA).filter(
        PlanIA.usuario_id == paciente_id,
        PlanIA.tipo == tipo_norm,
        PlanIA.activo == True,  # noqa: E712
    ).update({"activo": False})

    plan = PlanIA(
        usuario_id=paciente_id,
        tipo=tipo_norm,
        objetivo=payload.objetivo,
        contenido=payload.contenido,
        duracion_dias=payload.duracion_dias,
        fecha_inicio=ahora,
        fecha_fin=ahora + timedelta(days=payload.duracion_dias),
        activo=True,
        notificacion_enviada=False,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serializar_plan_ia(plan)


@app.put(
    "/profesionales/pacientes/{paciente_id}/planes/{plan_id}",
    response_model=PlanIAResponse,
)
def actualizar_plan_paciente_profesional(
    paciente_id: int,
    plan_id: int,
    payload: PlanIAProfesionalUpdateRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> PlanIAResponse:
    """Permite editar una rutina existente de paciente (contenido, objetivo, duración, estado)."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden editar rutinas de pacientes",
        )

    _assert_paciente_existente(db, paciente_id)
    plan = db.query(PlanIA).filter(PlanIA.id == plan_id, PlanIA.usuario_id == paciente_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan no encontrado",
        )

    _assert_permiso_plan_por_tipo(usuario_actual, plan.tipo)

    if payload.duracion_dias is not None:
        if payload.duracion_dias < 1 or payload.duracion_dias > 365:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="duracion_dias debe estar entre 1 y 365",
            )
        plan.duracion_dias = payload.duracion_dias
        plan.fecha_fin = plan.fecha_inicio + timedelta(days=payload.duracion_dias)
        plan.notificacion_enviada = False

    if payload.objetivo is not None:
        plan.objetivo = payload.objetivo
    if payload.contenido is not None and payload.contenido.strip():
        plan.contenido = payload.contenido

    if payload.activo is not None:
        if payload.activo:
            db.query(PlanIA).filter(
                PlanIA.usuario_id == paciente_id,
                PlanIA.tipo == plan.tipo,
                PlanIA.id != plan.id,
                PlanIA.activo == True,  # noqa: E712
            ).update({"activo": False})
        plan.activo = payload.activo

    db.commit()
    db.refresh(plan)
    return _serializar_plan_ia(plan)


@app.delete(
    "/profesionales/pacientes/{paciente_id}/planes/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def desactivar_plan_paciente_profesional(
    paciente_id: int,
    plan_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> None:
    """Permite a profesional desactivar una rutina de un paciente."""
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo profesionales pueden eliminar rutinas de pacientes",
        )

    _assert_paciente_existente(db, paciente_id)
    plan = db.query(PlanIA).filter(PlanIA.id == plan_id, PlanIA.usuario_id == paciente_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan no encontrado",
        )

    _assert_permiso_plan_por_tipo(usuario_actual, plan.tipo)
    plan.activo = False
    db.commit()


@app.get("/planes", response_model=List[PlanIAResponse])
def listar_planes_ia(
    activo: Optional[bool] = None,
    tipo: Optional[str] = None,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[PlanIAResponse]:
    """Lista todos los planes del usuario autenticado, con filtro opcional por activo/tipo."""
    q = db.query(PlanIA).filter(PlanIA.usuario_id == usuario_actual.id)
    if activo is not None:
        q = q.filter(PlanIA.activo == activo)
    if tipo:
        q = q.filter(PlanIA.tipo == tipo)
    planes = q.order_by(PlanIA.fecha_inicio.desc()).all()
    return [_serializar_plan_ia(p) for p in planes]


@app.get("/planes/activos", response_model=List[PlanIAResponse])
def listar_planes_activos(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[PlanIAResponse]:
    """Devuelve los planes activos del usuario (un plan por tipo como máximo)."""
    planes = (
        db.query(PlanIA)
        .filter(PlanIA.usuario_id == usuario_actual.id, PlanIA.activo == True)  # noqa: E712
        .order_by(PlanIA.tipo.asc())
        .all()
    )
    # Marcar automáticamente como inactivos los planes vencidos
    ahora = datetime.utcnow()
    actualizados = False
    for plan in planes:
        if plan.fecha_fin < ahora:
            plan.activo = False
            actualizados = True
    if actualizados:
        db.commit()
    planes_activos = [p for p in planes if p.activo]
    return [_serializar_plan_ia(p) for p in planes_activos]


@app.delete("/planes/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_plan_ia(
    plan_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> None:
    """Cancela (desactiva) un plan activo del usuario."""
    plan = db.query(PlanIA).filter(
        PlanIA.id == plan_id,
        PlanIA.usuario_id == usuario_actual.id,
    ).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    plan.activo = False
    db.commit()


@app.get("/notificaciones/planes", response_model=List[NotificacionPlanResponse])
def notificaciones_planes(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[NotificacionPlanResponse]:
    """
    Devuelve alertas para planes que vencen en <=2 días o ya han vencido.
    El frontend muestra estas notificaciones como banners o badges.
    """
    ahora = datetime.utcnow()
    planes = (
        db.query(PlanIA)
        .filter(PlanIA.usuario_id == usuario_actual.id)
        .all()
    )

    notificaciones: List[NotificacionPlanResponse] = []
    tipos_nombre = {
        "nutricion": "Nutrición",
        "entrenamiento": "Entrenamiento",
        "psicologia": "Psicología",
    }

    cambios = False
    for plan in planes:
        dias_restantes = (plan.fecha_fin - ahora).days
        tipo_legible = tipos_nombre.get(plan.tipo, plan.tipo.capitalize())

        if plan.fecha_fin < ahora and plan.activo:
            # Plan vencido: se desactiva automáticamente.
            plan.activo = False
            cambios = True

        if plan.fecha_fin < ahora and not plan.notificacion_enviada:
            notificaciones.append(NotificacionPlanResponse(
                plan_id=plan.id,
                tipo=plan.tipo,
                mensaje=f"Tu plan de {tipo_legible} ha terminado. ¿Quieres que te genere uno nuevo personalizado?",
                dias_restantes=0,
                urgente=True,
            ))
            plan.notificacion_enviada = True
            cambios = True
        elif plan.activo and dias_restantes <= 2:
            dias_txt = "mañana" if dias_restantes <= 1 else f"en {dias_restantes} días"
            notificaciones.append(NotificacionPlanResponse(
                plan_id=plan.id,
                tipo=plan.tipo,
                mensaje=f"Tu plan de {tipo_legible} vence {dias_txt}. ¡Renuévalo para no perder continuidad!",
                dias_restantes=max(0, dias_restantes),
                urgente=dias_restantes <= 1,
            ))

    if cambios:
        db.commit()

    return notificaciones


# ---------------------------------------------------------------------------
# RESUMEN CLÍNICO IA — Especialistas obtienen análisis integral de un paciente
# ---------------------------------------------------------------------------

class ResumenClinicoIAResponse(BaseModel):
    usuario_id: int
    nombre_paciente: str
    rol_solicitante: str
    resumen_ia: str
    alertas: List[str]
    fecha_generacion: str


def _detectar_alertas_clinicas(contexto: Dict[str, Any]) -> List[str]:
    """Extrae alertas clínicas automáticas del contexto del paciente."""
    alertas: List[str] = []
    animo = contexto.get("animo_reciente")
    imc = contexto.get("imc_actual")
    if isinstance(animo, (int, float)):
        if animo <= 3:
            alertas.append(f"🔴 Ánimo muy bajo ({animo}/10) — posible riesgo emocional")
        elif animo <= 5:
            alertas.append(f"🟡 Ánimo moderado-bajo ({animo}/10) — seguimiento recomendado")
    if isinstance(imc, (int, float)):
        if imc >= 35:
            alertas.append(f"🔴 IMC elevado ({imc}) — riesgo metabólico, valorar derivación médica")
        elif imc >= 30:
            alertas.append(f"🟡 IMC en rango obesidad I ({imc}) — ajuste de entrenamiento y nutrición")
        elif imc < 18.5:
            alertas.append(f"🔴 IMC bajo ({imc}) — riesgo nutricional, vigilar TCA")
    ultimo_reg = contexto.get("fecha_ultimo_registro")
    if ultimo_reg:
        try:
            dias_sin_reg = (datetime.utcnow().date() - datetime.fromisoformat(str(ultimo_reg)).date()).days
            if dias_sin_reg > 7:
                alertas.append(f"🟡 Sin registro desde hace {dias_sin_reg} días — baja adherencia")
        except Exception:
            pass
    return alertas


@app.get("/pacientes/{usuario_id}/resumen-ia", response_model=ResumenClinicoIAResponse)
def resumen_clinico_ia_paciente(
    usuario_id: int,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> ResumenClinicoIAResponse:
    """
    Genera un resumen clínico IA personalizado de un paciente para el especialista.
    Solo accesible por profesionales (nutricionista, psicólogo, coach, médico, administrador).
    Incluye: estado actual, alertas automáticas, recomendación de próxima intervención.
    """
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo especialistas pueden acceder al resumen clínico IA de un paciente",
        )
    paciente = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    contexto = _contexto_usuario_para_ia(db, paciente)
    alertas = _detectar_alertas_clinicas(contexto)
    rol_solicitante = str(getattr(getattr(usuario_actual, "rol", None), "nombre", "especialista") or "especialista")

    # Construir query específica para el rol del especialista
    enfoque = {
        "nutricionista": "diagnóstico nutricional, adherencia, riesgo de TCA, ajuste de macros y plan de intervención",
        "psicologo": "estado emocional, técnicas recomendadas, riesgo psicológico, tareas terapéuticas y criterios de escalado",
        "coach": "capacidad de entrenamiento, progresión, recuperación, fatiga y ajuste de carga",
        "medico": "riesgos metabólicos, biométricas críticas, indicadores de derivación y seguridad clínica",
        "administrador": "visión global: estado físico, emocional y nutricional con recomendación de coordinación interdisciplinar",
    }.get(rol_solicitante, "estado general del paciente con recomendaciones de mejora en las 3 áreas")

    query_ia = (
        f"Genera un RESUMEN CLÍNICO BREVE de este paciente para un especialista en {rol_solicitante}. "
        f"Enfoque: {enfoque}. "
        "Incluye: 1) Estado actual resumido, 2) Punto crítico que merece atención inmediata, "
        "3) Próxima intervención recomendada, 4) Coherencia entre las 3 áreas (nutrición, entrenamiento, psicología). "
        "Máximo 300 palabras. Lenguaje clínico conciso."
    )

    try:
        resultado = consultar_ia(
            mensaje_usuario=query_ia,
            historial_chat=[],
            imagenes=[],
            contexto_adicional=contexto,
            tiene_multimedia=False,
        )
        resumen = str(resultado.get("respuesta") or "").strip()
    except Exception:
        logger.exception("Error al generar resumen clínico IA")
        resumen = (
            f"Paciente: {paciente.nombre} | "
            f"IMC: {contexto.get('imc_actual', 'N/D')} | "
            f"Ánimo: {contexto.get('animo_reciente', 'N/D')}/10. "
            "No fue posible generar análisis IA en este momento. Consulta la ficha clínica directamente."
        )

    return ResumenClinicoIAResponse(
        usuario_id=usuario_id,
        nombre_paciente=paciente.nombre,
        rol_solicitante=rol_solicitante,
        resumen_ia=resumen,
        alertas=alertas,
        fecha_generacion=datetime.utcnow().isoformat(),
    )


@app.get("/mis-pacientes/alertas", response_model=List[Dict[str, Any]])
def alertas_todos_mis_pacientes(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Devuelve resumen de alertas clínicas automáticas para TODOS los pacientes
    del especialista autenticado (basado en las derivaciones activas hacia él).
    Ideal para dashboard de especialista: ver de un vistazo qué pacientes necesitan atención.
    """
    if not _es_profesional(usuario_actual):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo especialistas pueden consultar alertas de pacientes",
        )

    # Obtener IDs de pacientes que tienen derivaciones activas hacia este especialista
    derivaciones = (
        db.query(Derivacion)
        .filter(
            Derivacion.especialista_id == usuario_actual.id,
            Derivacion.estado.in_(["pendiente", "aceptada"]),
        )
        .all()
    )
    paciente_ids = list({d.paciente_id for d in derivaciones if d.paciente_id})

    resultado: List[Dict[str, Any]] = []
    for pid in paciente_ids:
        paciente = db.query(Usuario).filter(Usuario.id == pid).first()
        if not paciente:
            continue
        ctx = _contexto_usuario_para_ia(db, paciente)
        alertas = _detectar_alertas_clinicas(ctx)
        resultado.append({
            "usuario_id": pid,
            "nombre": paciente.nombre,
            "imc": ctx.get("imc_actual"),
            "animo": ctx.get("animo_reciente"),
            "alertas": alertas,
            "num_alertas": len(alertas),
            "prioridad": "alta" if any("🔴" in a for a in alertas) else ("media" if alertas else "normal"),
        })

    # Ordenar por prioridad: alta → media → normal
    prioridad_orden = {"alta": 0, "media": 1, "normal": 2}
    resultado.sort(key=lambda x: prioridad_orden.get(str(x.get("prioridad")), 2))
    return resultado


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )

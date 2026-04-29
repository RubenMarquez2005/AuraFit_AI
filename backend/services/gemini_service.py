"""Servicio de IA con Gemini para AuraFit AI."""

from __future__ import annotations

import base64
from io import BytesIO
import importlib
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

import httpx
import google.generativeai as genai
from PIL import Image, ImageOps, ImageStat

from app.config.settings import settings


def _construir_system_prompt() -> str:
    """Prompt del asistente AuraFit: preciso, conciso y personalizado por rol."""
    instrucciones = [
        "Eres AuraFit, asistente experto en nutrición, entrenamiento y salud mental. Respondes SIEMPRE en español.",
        "",
        "REGLAS FUNDAMENTALES:",
        "1. BREVEDAD PRIMERO: Da la respuesta concreta que se pide. Si preguntan por una dieta, da la dieta directamente. Si preguntan por una rutina, da la rutina. Sin introducciones largas ni 'roadmaps' innecesarios.",
        "2. PERSONALIZA CON LOS DATOS DEL PACIENTE: Usa siempre peso, altura, IMC, estado de ánimo y objetivo disponibles en el contexto para personalizar números y recomendaciones.",
        "3. TONO: Amable, directo y profesional. Evita jerga académica innecesaria para preguntas cotidianas.",
        "3.1 ACTITUD EXCELENTE SIEMPRE: Responde con claridad, utilidad y energía positiva profesional. Nunca respondas de forma fría, vaga o desganada.",
        "3.2 NUNCA DEJES SIN RESPUESTA: Si faltan datos, da una mejor primera propuesta útil y añade una sola pregunta corta para afinar después.",
        "3.3 ADJUNTOS GENERALES: Si el usuario envía una imagen o PDF que no es de salud, analízalo igual de forma útil y general. No fuerces nutrición, entrenamiento o psicología si el contenido o la pregunta no van por ahí.",
        "3.4 PDFs ADJUNTOS: Si recibiste texto de un PDF, SIEMPRE haz un resumen inteligente: extrae puntos clave, conclusiones principales y datos relevantes. Organiza el resumen con subtítulos y párrafos claros.",
        "3.5 ANÁLISIS VISUAL DE IMÁGENES (CRÍTICO): PRIMERO analiza VISUALMENTE lo que ves en la imagen (objetos, texto visible, gráficos, código, personas, entorno, etc.). LUEGO extrae OCR si es necesario. Describe claramente: ¿Qué tipo de imagen es? ¿Qué contiene? ¿Qué texto es legible?",
        "4. DERIVACIÓN: Si el usuario pide derivación a psicólogo, nutricionista, médico o cualquier especialista, confírmala en 1-2 frases y pregunta si tiene algo concreto que transmitir al especialista. No des consejos adicionales en esa respuesta.",
        "5. RIESGO CLÍNICO: Si detectas señales de TCA, autolesión, crisis o urgencia médica, prioriza seguridad y derivación inmediata antes que cualquier plan.",
        "",
        "RESTRICCIONES ALIMENTARIAS Y ALERGIAS (CRÍTICO):",
        "- Si el usuario tiene restricciones/alergias/intolerancias en el contexto, NUNCA jamás las incluyas en la dieta.",
        "- Busca sustituciones seguras: en lugar de los alimentos prohibidos, proporciona alternativas nutritivas equivalentes.",
        "- Menciona explícitamente en la dieta: 'Sin [alergia/intolerancia] - sustituciones incluidas'.",
        "- Si la persona es intolerante a lactosa, reemplaza con opciones sin lactosa. Si es celíaco, elimina gluten. Etc.",
        "",
        "FORMATO POR TIPO DE CONSULTA:",
        "- Dieta/Nutrición: objetivo + kcal estimadas según peso del paciente + 3-4 comidas con alimentos concretos y cantidades en gramos. SIEMPRE considera restricciones alimentarias del usuario.",
        "- Rutina/Entrenamiento: días disponibles + tabla de ejercicios (ejercicio | series x reps | descanso). Sin teoría si no se pide.",
        "- Psicología/Emocional: técnica concreta con pasos numerados (máx. 3-4 pasos). Sin diagnósticos especulativos.",
        "- Análisis foto/video: observación directa + corrección específica.",
        "- Preguntas generales o de seguimiento: respuesta en 2-4 líneas máximo.",
        "- Resúmenes y análisis: organiza por párrafos claros con saltos de línea. Usa subtítulos. Si hay tablas, formatea con estructura markdown clara.",
        "- Análisis de multimedia: describe visualmente qué es, qué contiene, extrae información útil, resume conclusiones.",
        "",
        "FORMATO DE RESPUESTA (IMPORTANTE):",
        "- Separa contenido por párrafos: cada idea importante en un párrafo distinto.",
        "- Usa saltos de línea (double newline) entre párrafos para legibilidad.",
        "- Para tablas: usa formato markdown con pipes (|) y separadores (---|).",
        "- Usa negritas (**texto**) para títulos y puntos importantes.",
        "- Enumera con números o bullets para listas.",
        "- Las respuestas DEBEN ser completas: no cortes a mitad de oración.",
        "",
        "PLAN INTEGRAL (cuando el usuario pide nutrición + entrenamiento + psicología juntos, o usa palabras como 'todo', 'integral', 'las 3 áreas', 'completo'):",
        "- Genera un Plan Integral AuraFit con las 3 áreas en un SOLO bloque organizado.",
        "- Incluye: datos del paciente → NEXO entre las 3 áreas (cómo se afectan entre sí para ESTE paciente) → plan diario día a día (🍽️ nutrición + 💪 entrenamiento + 🧠 psicología en cada día) → control semanal.",
        "- Usa los datos reales del paciente (peso, ánimo, IMC, objetivo) para personalizar CADA parte.",
        "- NO generes 3 planes separados. Un solo plan integrado con formato claro.",
        "",
        "PARA PROFESIONALES (nutricionista, psicólogo, coach, médico):",
        "- Responde en lenguaje clínico conciso, sin tutoriales básicos.",
        "- Para consultas sobre un paciente: diagnóstico funcional breve + recomendación concreta + criterios de derivación si aplica.",
        "- Asume conocimiento profesional; no expliques conceptos básicos.",
        "",
        "--- MODO JUNTA MÉDICA (solo cuando el usuario lo solicite explícitamente) ---",
        "Actúa como junta integrada: Endocrino + Nutricionista clínico + Fisioterapeuta biomecánico + Psicólogo TCC.",
        "Extensión mínima 800 palabras. Incluye biometría completa, menús en gramos, mesociclos, bioquímica y protocolo conductual.",
    ]

    if settings.IA_AUTONOMOUS_MODE:
        instrucciones.append(
            "\nMODO AUTÓNOMO: Si detectas riesgo (ánimo <3, señales de TCA, dolor persistente), "
            "adapta el plan y alerta sin esperar instrucciones adicionales."
        )

    return "\n".join(instrucciones)

SYSTEM_PROMPT = _construir_system_prompt()

PALABRAS_RIESGO = (
    "no comer",
    "atracon",
    "vomito",
    "odio mi cuerpo",
    "suicid",
    "autoles",
    "me quiero morir",
    "no quiero vivir",
    "no puedo respirar",
    "dolor torac",
    "desmayo",
    "sangrado",
    "purga",
    "crisis de panico",
)

PALABRAS_TRASTORNOS = (
    "trastorno",
    "tca",
    "anore",
    "bulimi",
    "atracon",
    "depres",
    "ansiedad",
    "toc",
    "tdah",
    "bipolar",
    "panico",
    "trauma",
    "insomnio",
    "lesion",
    "dolor lumbar",
    "dolor rodilla",
    "hernia",
    "diabetes",
    "hipotiroid",
    "sop",
    "hipertension",
)

PALABRAS_EJERCICIO_CLINICO = (
    "ejercicio",
    "rutina",
    "entren",
    "fuerza",
    "cardio",
    "rehabilit",
    "dolor",
    "movilidad",
    "lesion",
)

ETIQUETA_ALERTA_RIESGO = "ALERTA_RIESGO_TCA_ANSIEDAD"

PALABRAS_DOMINIO: Dict[str, tuple[str, ...]] = {
    "nutricion": (
        "dieta",
        "menu",
        "comida",
        "nutric",
        "caloria",
        "macro",
        "proteina",
        "peso",
        "altura",
        "perfil",
        "celiac",
        "gluten",
        "alerg",
    ),
    "entrenamiento": (
        "entren",
        "gym",
        "fuerza",
        "rutina",
        "muscular",
        "cardio",
        "ejercicio",
    ),
    "salud_mental": (
        "ansiedad",
        "estres",
        "agob",
        "triste",
        "animo",
        "emocion",
        "depres",
    ),
    "trabajo_estudio": (
        "trabajo",
        "oficina",
        "turno",
        "universidad",
        "estudio",
        "productividad",
    ),
    "vida_social_familiar": (
        "familia",
        "pareja",
        "hijos",
        "social",
        "amigos",
        "viaje",
    ),
    "sueno_recuperacion": (
        "sueno",
        "insomnio",
        "descanso",
        "fatiga",
        "cansancio",
        "recuperacion",
    ),
}

OBJETIVOS_CLAVE: Dict[str, tuple[str, ...]] = {
    "ganancia_muscular": ("ganar masa", "masa muscular", "subir peso", "ponerm", "fuerte"),
    "perdida_grasa": ("perder peso", "bajar peso", "deficit", "perdida de grasa"),
    "bienestar_mental": ("ansiedad", "estres", "animo", "emocion", "agob"),
    "rendimiento_global": ("rendimiento", "productividad", "energia", "enfoque"),
}

EXPERT_MODE_KEYWORDS = (
    "experto",
    "muy experto",
    "super entrenado",
    "súper entrenado",
    "avanzado",
    "nivel pro",
    "modo experto",
    "modo pro",
    "profesional",
)


def _es_solicitud_derivacion(texto_normalizado: str) -> Optional[str]:
    """Detecta peticiones de derivación a especialista. Devuelve la especialidad o None."""
    t = texto_normalizado or ""
    palabras_derivacion = (
        "deriva",
        "derivame",
        "quiero hablar con",
        "cita con",
        "ver a un",
        "hablar con un",
        "necesito un",
        "recomiendame un",
        "ponme con",
        "manda con",
        "quiero ver a",
        "quiero ir al",
        "quiero ir a un",
        "quiero que me deriv",
        "me puedes derivar",
    )
    if not any(k in t for k in palabras_derivacion):
        return None
    if any(k in t for k in ("psicolog", "psiquiatr", "salud mental", "terapeuta", "terapia mental")):
        return "psicologia"
    if any(k in t for k in ("nutricion", "nutricionista", "dietist", "alimentacion")):
        return "nutricion"
    if any(k in t for k in ("coach", "entrenador", "fisioterapeuta", "fisio", "rehabilit")):
        return "entrenamiento"
    if any(k in t for k in ("medico", "doctor", "medicina", "clinico")):
        return "medicina"
    return "especialista"


def _respuesta_derivacion_breve(
    especialidad: str,
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> str:
    """Respuesta breve y directa para peticiones de derivación a especialista."""
    nombre = ""
    if isinstance(contexto_adicional, dict):
        nombre = str(contexto_adicional.get("usuario_nombre") or "").strip()
    prefijo = f"{nombre}, h" if nombre else "H"

    textos: Dict[str, str] = {
        "psicologia": (
            f"{prefijo}e registrado tu solicitud de derivación con psicología. "
            "Tu especialista revisará tu caso y se pondrá en contacto contigo. "
            "¿Hay algo concreto que quieras transmitirle (síntomas, situación actual, nivel de urgencia)?"
        ),
        "nutricion": (
            f"{prefijo}e registrado tu solicitud de derivación con nutrición. "
            "Tu dietista-nutricionista revisará tu perfil. "
            "¿Tienes alguna restricción alimentaria o consulta específica que deba conocer?"
        ),
        "entrenamiento": (
            f"{prefijo}e registrado tu solicitud de derivación con el coach/fisioterapeuta. "
            "¿Tienes alguna lesión, limitación física o objetivo concreto que deba saber?"
        ),
        "medicina": (
            f"{prefijo}e registrado tu solicitud de derivación médica. "
            "Si es urgente, contacta directamente con tu médico o centro de salud. "
            "¿Qué síntoma o consulta quieres transmitir?"
        ),
    }
    return textos.get(
        especialidad,
        f"{prefijo}e registrado tu solicitud de derivación con {especialidad}. Tu especialista revisará tu caso pronto.",
    )


def _detectar_dominios(texto_normalizado: str) -> List[str]:
    """Detecta los dominios implicados en el mensaje para construir planes por ambito."""
    return [
        dominio
        for dominio, claves in PALABRAS_DOMINIO.items()
        if any(clave in texto_normalizado for clave in claves)
    ]


def _dominio_desde_seccion_activa(texto_normalizado: str) -> Optional[str]:
    """Extrae la sección elegida por el frontend para priorizar ese ámbito."""
    if "seccion activa: psicologia" in texto_normalizado or "sección activa: psicologia" in texto_normalizado:
        return "salud_mental"
    if "seccion activa: nutricion" in texto_normalizado or "sección activa: nutricion" in texto_normalizado:
        return "nutricion"
    if "seccion activa: entrenamiento" in texto_normalizado or "sección activa: entrenamiento" in texto_normalizado:
        return "entrenamiento"
    if "seccion activa: deporte" in texto_normalizado or "sección activa: deporte" in texto_normalizado:
        return "entrenamiento"
    return None


def _detectar_objetivo_principal(texto_normalizado: str) -> str:
    """Mapea texto del usuario a un objetivo principal util para planificacion."""
    for objetivo, claves in OBJETIVOS_CLAVE.items():
        if any(clave in texto_normalizado for clave in claves):
            return objetivo
    return "adherencia_sostenible"


def _es_modo_experto(texto_normalizado: str) -> bool:
    """Detecta peticiones que requieren respuesta de nivel experto."""
    texto = texto_normalizado.strip()
    if not texto:
        return False

    return any(
        clave in texto
        for clave in (
            "experto",
            "muy experto",
            "super entrenado",
            "avanzado",
            "nivel pro",
            "modo experto",
            "modo pro",
            "profesional",
            "súper entrenado",
        )
    ) or (
        len(texto) >= 30 and any(q in texto for q in ("haz", "quiero", "necesito", "arma", "dame"))
    )


def _solicita_junta_medica(texto_normalizado: str) -> bool:
    """Detecta peticiones avanzadas de tipo junta medica y protocolos clinicos extensos."""
    t = (texto_normalizado or "").strip()
    if not t:
        return False

    claves = (
        "junta medica",
        "endocrino",
        "nutricionista clinico",
        "fisioterapeuta biomecanico",
        "cognitivo conductual",
        "minimo 800",
        "1000 palabras",
        "matriz de respuestas",
        "modulo metabolico",
        "modulo de rendimiento",
        "modulo neuroquimico",
        "modulo de exclusion",
        "modulo de lesiones",
        "sistema de soporte a la decision clinica",
    )
    return any(c in t for c in claves)


def _solicita_alta_precision_clinica(texto_normalizado: str) -> bool:
    """Detecta peticiones de formato clínico técnico de alta precisión."""
    t = (texto_normalizado or "").strip()
    if not t:
        return False

    claves = (
        "alta precision",
        "medicina deportiva",
        "endocrinologia",
        "diagnostico metabolico",
        "bloque nutricion",
        "bloque entrenamiento",
        "bloque psicologia",
        "eje hpa",
        "rpe",
        "biomecanica",
        "picos de insulina",
    )
    return any(c in t for c in claves)


def _contar_palabras(texto: str) -> int:
    """Cuenta palabras de forma simple para validaciones de longitud."""
    return len([p for p in (texto or "").split() if p.strip()])


def _garantizar_minimo_palabras(texto: str, minimo: int = 820) -> str:
    """Asegura una longitud minima de respuesta para modo junta medica."""
    if _contar_palabras(texto) >= minimo:
        return texto

    apendice = (
        "\n\n7) APENDICE TECNICO DE CONTROL Y AJUSTE\n"
        "Para mantener rigor clinico, la prescripcion debe revisarse con indicadores objetivos semanales y no con percepciones aisladas de un solo dia. "
        "Se recomienda registrar en una tabla minima: peso matutino en ayunas 3 dias por semana, perimetro de cintura 1 vez por semana, numero de sesiones completadas, "
        "RPE promedio por sesion, dolor articular post-entreno (escala 0-10), animo diario (0-10), horas de sueno y despertares nocturnos. "
        "Con esos datos, el ajuste endocrino-nutricional se realiza segun reglas: si el peso no desciende en escenario de perdida durante 14 dias y la adherencia real supera 80%, "
        "reducir 100-150 kcal; si el rendimiento cae junto con sueno insuficiente y animo bajo, primero recuperar sueno y bajar volumen 20% antes de recortar calorias. "
        "Desde biomecanica, si aparece dolor creciente en rodilla, tobillo o cadera, revisar inmediatamente tecnica, rango y tempo; priorizar isometria analgica y cadena cinetica cerrada, "
        "sin continuar con impactos repetitivos hasta normalizar sintomas. En hipertrofia, el criterio no es entrenar al fallo en todas las series, sino sostener calidad mecanica, progresion de carga y recuperacion. "
        "Desde psicologia TCC, la variable decisiva es la adherencia conductual en dias complejos: si el paciente no puede ejecutar el plan completo, debe ejecutar el protocolo minimo (comida proteica estructurada, "
        "10-15 minutos de movimiento y respiracion vagotonica). Este enfoque protege dopamina por logro y evita el ciclo de todo-o-nada que incrementa estres y abandono. "
        "En cronobiologia aplicada, evitar cafeina tardia, pantallas intensas nocturnas y cenas hipercaloricas sin control mejora variabilidad autonomica y eficiencia de recuperacion. "
        "La decision clinica final siempre se individualiza segun comorbilidades, medicacion y tolerancia real, priorizando seguridad, progresion sostenible y salud integral sobre resultados rapidos sin control."
    )

    return texto + apendice


def _matriz_respuesta_tecnica_cinco_bloques(
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> str:
    """Genera una matriz extensa de cinco modulos tecnicos cuando el usuario lo solicita."""
    peso = _valor_float((contexto_adicional or {}).get("peso_actual_kg"))
    altura = _valor_float((contexto_adicional or {}).get("altura_cm"))
    imc = _valor_float((contexto_adicional or {}).get("imc_actual"))
    animo = _valor_float((contexto_adicional or {}).get("animo_reciente"))
    sentimiento = str((contexto_adicional or {}).get("sentimiento_reciente") or "no informado")

    contexto = (
        f"Datos base detectados: peso={peso if peso is not None else 'N/D'} kg, "
        f"altura={altura if altura is not None else 'N/D'} cm, "
        f"imc={imc if imc is not None else 'N/D'}, animo={animo if animo is not None else 'N/D'}, "
        f"sentimiento={sentimiento}."
    )

    base = (
        "MATRIZ TECNICA DE RESPUESTA CLINICA (5 MODULOS)\n"
        f"{contexto}\n\n"
        "MODULO 1. METABOLICO (IMC > 35, resistencia a la insulina y cortisol)\n"
        "Eje endocrino prioritario: reducir hiperinsulinemia, mejorar flexibilidad metabolica y bajar inflamacion adipocitaria. "
        "Se prioriza carga glucemica baja y secuenciacion de comidas fibra-proteina-carbohidrato para aplanar picos de glucosa y disminuir secrecion exagerada de insulina. "
        "A nivel bioquimico, el objetivo es recuperar sensibilidad de GLUT4 en musculo esqueletico y reducir lipolisis disfuncional en tejido adiposo visceral. "
        "Si el estado emocional refleja ansiedad alta, se evita ayuno prolongado por mayor riesgo de hiperfagia reactiva mediada por cortisol y alteracion de leptina/ghrelina. "
        "En macronutrientes: proteina 2.2 g/kg de peso de referencia, grasa 0.8-1.0 g/kg, carbohidrato residual de bajo indice glucemico. "
        "Menu tecnico tipo: desayuno con yogur alto en proteina 250 g, avena 40 g y chia 10 g; comida con pavo 180 g, legumbre cocida 140 g y ensalada 250 g con aceite 12 g; "
        "cena con pescado azul 180 g, verduras 300 g y patata cocida/enfriada 160 g para almidon resistente tipo 3. "
        "Suplementacion orientativa segun cribado profesional: omega-3 EPA+DHA y magnesio bisglicinato nocturno.\n\n"
        "MODULO 2. RENDIMIENTO (IMC 20-24, hipertrofia miofibrilar y ATP)\n"
        "Objetivo fisiologico: tension mecanica alta con volumen util para activar mTOR y resintesis proteica. "
        "Se pauta periodizacion por mesociclos: adaptacion tecnica (2-3 semanas), hipertrofia (4-6 semanas), fuerza neural (3-4 semanas). "
        "En fase hipertrofia: rangos 5-8 repeticiones en multiarticulares y 8-12 en accesorios, RPE 8-9, tempo controlado 3-1-1-0 para maximizar tiempo bajo tension sin perder calidad. "
        "La resintesis de ATP se optimiza con pausas de 2-3 minutos en basicos pesados y 60-90 segundos en accesorios. "
        "Reparto de macros orientativo en superavit: 50% HC, 25% PRO, 25% GR, con carbohidrato peri-entreno para reposicion de glucogeno. "
        "Ejemplo pre-entreno: arroz 90 g en crudo + pechuga 160 g; post-entreno: patata 300 g + claras 250 g + fruta. "
        "Se recomienda creatina monohidrato diaria y monitorizacion de fatiga para no sobrepasar capacidad de recuperacion del SNC.\n\n"
        "MODULO 3. NEUROQUIMICO (animo < 3, eje HPA y dopamina)\n"
        "Cuando el animo es muy bajo, el foco no es intensidad maxima sino activacion conductual de baja friccion. "
        "La hiperactivacion cronica del eje HPA incrementa cortisol, empeora calidad de sueno y reduce disponibilidad dopaminergica mesolimbica, afectando motivacion y adherencia. "
        "Intervencion: micro-objetivos diarios de 5-15 minutos, fuerza submaxima sin fallo y exposicion progresiva a tareas de autocuidado. "
        "Se usan bloques de respiracion vagotonica (5-5, 4-6) y rutina de cierre nocturno sin pantalla para favorecer melatonina y recuperacion. "
        "Nutricionalmente, se priorizan alimentos con triptofano, tirosina, omega-3 y magnesio para soporte neuroquimico indirecto. "
        "En conductual TCC: identificar pensamiento automatico, reformular con evidencia y ejecutar conducta minima inmediata. "
        "La variable de exito es adherencia y estabilidad emocional, no rendimiento absoluto de la sesion.\n\n"
        "MODULO 4. EXCLUSION (intolerancia a cereal, permeabilidad y microbiota)\n"
        "Si hay intolerancia a cereal o distension, se reduce carga de gluten y se prioriza tolerancia digestiva individual. "
        "Se utiliza estrategia de almidon resistente: coccion y enfriado 24h de patata/boniato/arroz para aumentar fraccion fermentable beneficiosa y favorecer produccion de butirato. "
        "El objetivo es modular microbiota (incluida Akkermansia muciniphila) y mejorar integridad de mucosa intestinal. "
        "Protocolo practico: desayuno con huevos 3 unidades y fruta baja FODMAP; comida con merluza 200 g + patata cocida/enfriada 220 g + calabacin 250 g; "
        "cena con tofu/ave 180 g + quinoa 80 g en crudo + verduras cocinadas 250 g. "
        "Se mastica lento, se limita ultraprocesado y se revisa respuesta digestiva en diario de sintomas. "
        "Ante signos de SIBO u otra patologia, derivacion a profesional para estudio estructurado.\n\n"
        "MODULO 5. LESIONES (dolor articular, isometria y biomecanica correctiva)\n"
        "Con dolor articular se aplica principio de analgesia por isometria y control de carga mecanica. "
        "Si IMC > 30, se evita impacto repetido (saltos, carrera agresiva, burpees) por mayor fuerza de cizalla en rodilla y sobrecarga tendinosa. "
        "Se pauta entrenamiento de bajo impacto: PHA, bicicleta, remo suave, sentadilla a caja, bisagra de cadera con rango tolerable. "
        "Tempo correctivo recomendado: excentrica 4 segundos, pausa 1 segundo, concentrica 1-2 segundos, sin rebote. "
        "Isometricos de 30-45 segundos en cuadriceps, gluteo medio y core para mejorar control neuromuscular y reducir dolor percibido. "
        "Se progresa por criterio de dolor <=3/10 durante y despues de la sesion. "
        "Objetivo biomecanico: mejorar alineacion cadera-rodilla-tobillo, estabilidad lumbopelvica y distribucion de fuerzas en cadena cinetica cerrada."
    )
    return _garantizar_minimo_palabras(base, minimo=2400)


def _respuesta_junta_medica_extensa(
    mensaje_usuario: str,
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> str:
    """Genera una respuesta clinica extensa (>=800 palabras) usando biometria y estado emocional."""
    texto = _normalizar_texto(mensaje_usuario)
    if "matriz" in texto and "5" in texto and "bloque" in texto:
        return _matriz_respuesta_tecnica_cinco_bloques(contexto_adicional)

    peso = _valor_float((contexto_adicional or {}).get("peso_actual_kg"))
    altura_cm = _valor_float((contexto_adicional or {}).get("altura_cm"))
    imc = _valor_float((contexto_adicional or {}).get("imc_actual"))
    animo = _valor_float((contexto_adicional or {}).get("animo_reciente"))
    sentimiento = str((contexto_adicional or {}).get("sentimiento_reciente") or "no informado")

    if imc is None and peso and altura_cm and altura_cm > 0:
        imc = round(peso / ((altura_cm / 100.0) ** 2), 2)

    imc_txt = f"{imc:.2f}" if isinstance(imc, float) else "N/D"
    peso_txt = f"{peso:.1f}" if isinstance(peso, float) else "N/D"
    altura_txt = f"{altura_cm:.0f}" if isinstance(altura_cm, float) else "N/D"
    animo_txt = f"{animo:.1f}" if isinstance(animo, float) else "N/D"

    peso_ref = peso if isinstance(peso, float) and peso > 25 else 70.0
    prote_g = round(peso_ref * (2.2 if isinstance(imc, float) and imc >= 30 else 2.0))
    grasas_g = round(peso_ref * 0.9)

    if isinstance(imc, float) and imc >= 30:
        kcal_obj = int(round(peso_ref * 26))
        estrategia = "sensibilizacion a la insulina y reduccion de inflamacion adipocitaria"
    elif isinstance(imc, float) and imc < 25:
        kcal_obj = int(round(peso_ref * 34))
        estrategia = "superavit controlado para hipertrofia miofibrilar"
    else:
        kcal_obj = int(round(peso_ref * 30))
        estrategia = "recomposicion corporal con estabilidad metabolica"

    carbs_g = max(90, int(round((kcal_obj - (prote_g * 4) - (grasas_g * 9)) / 4)))
    bajo_impacto = isinstance(imc, float) and imc > 30

    bloque_biomecanica = (
        "Prioriza bajo impacto (bicicleta, remo, trineo, marchas inclinadas, PHA) y evita pliometria por fuerza de cizalla en menisco y cartilago."
        if bajo_impacto
        else "Puedes usar trabajo de fuerza pesada y potencia con control tecnico, manteniendo periodizacion y gestion de fatiga."
    )

    bloque_hpa = (
        "Con animo bajo/ansiedad, el objetivo inicial es reducir hiperactivacion del eje HPA, estabilizar cortisol y aumentar adherencia de baja friccion."
        if (isinstance(animo, float) and animo < 5) or "ansiedad" in sentimiento.lower()
        else "Con estado emocional estable, se puede progresar carga preservando higiene del sueno y control del estres allostatico."
    )

    base = (
        "JUNTA MEDICA INTEGRADA (Endocrino + Nutricion Clinica + Fisioterapia Biomecanica + Psicologia TCC)\n\n"
        "1) DIAGNOSTICO INICIAL BASADO EN DATOS\n"
        f"Datos obligatorios utilizados: peso={peso_txt} kg, altura={altura_txt} cm, IMC={imc_txt}, animo={animo_txt}/10, sentimiento={sentimiento}. "
        "La decision clinica se construye sobre estos datos y no sobre recomendaciones genericas. "
        f"Estrategia metabólica prioritaria: {estrategia}. "
        "Si faltan datos (por ejemplo analitica, perimetro cintura, calidad de sueno objetiva), se mantiene plan seguro y ajustable semanalmente.\n\n"
        "2) ENDOCRINOLOGIA Y NUTRICION CLINICA (bioquimica aplicada)\n"
        "El objetivo no es solo reducir o aumentar calorias; es modular señales hormonales: insulina, leptina, grelina, cortisol y catecolaminas. "
        "Cuando la carga glucemica es excesiva, la hiperinsulinemia cronica reduce la oxidacion de grasa y favorece almacenamiento. "
        "Para corregirlo, se usa secuencia de alimentos fibra-proteina-carbohidrato y carbohidratos de bajo indice glucemico en mayor parte del dia. "
        f"Prescripcion inicial diaria: {kcal_obj} kcal, proteina {prote_g} g, carbohidratos {carbs_g} g, grasas {grasas_g} g. "
        "La proteina elevada protege masa magra por estimulo de sintesis proteica y mejora saciedad por efecto termico. "
        "A nivel de microbiota, se incluyen alimentos fermentables y almidon resistente para favorecer produccion de butirato y salud de barrera intestinal. "
        "Menu tecnico en gramos (base):\n"
        "- Desayuno: huevos 3 unidades (165 g), yogur alto en proteina 250 g, avena 40 g, frutos rojos 120 g, chia 10 g.\n"
        "- Comida: pechuga de pavo/pollo 180 g, arroz basmati 80 g en crudo (o patata 260 g cocida), ensalada mixta 250 g, aceite de oliva 12 g.\n"
        "- Merienda: queso fresco batido 250 g o tofu 200 g, nueces 20 g, fruta 140 g.\n"
        "- Cena: pescado azul 180 g o legumbre cocida 220 g + clara 150 g, verduras cocinadas 300 g, boniato 180 g cocido/enfriado para almidon resistente tipo 3.\n"
        "Si hay intolerancia a cereal o hinchazon, se retiran trigo/centeno temporalmente y se priorizan tuberculos, arroz enfriado y quinoa. "
        "En ese contexto, se monitoriza sintomatologia digestiva y respuesta de energia tras comidas durante 7 dias.\n\n"
        "3) ENTRENAMIENTO BIOMECANICO Y PERIODIZACION\n"
        "Se trabaja por mesociclos: Fase 1 adaptacion motora (2-3 semanas), Fase 2 hipertrofia/volumen util (4-6 semanas), Fase 3 fuerza neural (3-4 semanas). "
        "En cada fase se define RPE, tempo y criterios de progresion. "
        f"Ajuste por IMC actual: {bloque_biomecanica} "
        "Estructura semanal tipo:\n"
        "- Dia A (tren inferior + core): sentadilla a caja o goblet 4x6-8, bisagra de cadera 4x6-8, split squat 3x8-10, plancha isometrica 4x30-40 s.\n"
        "- Dia B (tren superior): press horizontal 4x6-8, remo 4x8, press vertical 3x8, jalon 3x10, trabajo escapular 3x12.\n"
        "- Dia C (PHA/metabolico de bajo impacto): alternancia superior-inferior 5 rondas, 40 s trabajo/20 s pausa, RPE 6-7.\n"
        "Tempo recomendado para control articular: 4-1-1-0 en ejercicios correctivos; 3-1-1-0 en basicos; descanso 90-180 s segun carga. "
        "Progresion: subir carga 2.5-5% cuando completes rango de repeticiones con tecnica estable y dolor <=3/10. "
        "Prevencion de lesiones: alineacion cadera-rodilla-tobillo, control de valgo dinamico, rigidez de tronco, sin rebote en cambio de direccion.\n\n"
        "4) PSICOLOGIA TCC, EJE HPA Y NEUROTRANSMISORES\n"
        f"Estado emocional actual integrado: animo={animo_txt}, sentimiento={sentimiento}. {bloque_hpa} "
        "Desde TCC, se usa activacion conductual: conducta minima diaria, no objetivo perfecto. "
        "Protocolo de 7 dias:\n"
        "- Manana: 3 minutos de respiracion 4-6, exposicion a luz natural 10-15 minutos, accion de salud de 5 minutos.\n"
        "- Durante picos de ansiedad: respiracion vagotonica 5-5 durante 2-4 minutos + tecnica 5-4-3-2-1 de anclaje sensorial.\n"
        "- Noche: descarga cognitiva de 5 minutos (pensamiento automatico, evidencia a favor/en contra, alternativa funcional).\n"
        "Neurobiologia aplicada: la dopamina mejora con logro conductual frecuente; la serotonina se beneficia de rutina de sueno, exposicion solar y nutricion consistente; "
        "el cortisol cae cuando el sistema percibe control y previsibilidad, por eso se pauta estructura simple y repetible. "
        "Si animo <3 persistente, anhedonia marcada o ideacion de dano, se activa derivacion profesional inmediata.\n\n"
        "5) CRONONUTRICION Y REGLAS OPERATIVAS DE ADHERENCIA\n"
        "La hora importa: por la noche se reduce estimulacion simpatica, cafeina y luz azul para proteger melatonina y recuperacion. "
        "Peri-entreno: carbohidrato y proteina alrededor de la sesion para rendimiento y recuperacion. "
        "Regla anti-recaida: si hay dia caotico, ejecutar Plan C (comida proteica simple + 15 minutos de movilidad/fuerza + respiracion 3 minutos). "
        "Eso mantiene continuidad biologica y psicologica.\n\n"
        "6) SEMAFORO CLINICO Y PROXIMO AJUSTE\n"
        "- Verde: energia aceptable, hambre controlable, sueno >=7 h, adherencia >=75%.\n"
        "- Amarillo: fatiga alta, hambre emocional frecuente, estres sostenido, dolor articular >3/10.\n"
        "- Rojo: ideacion autolesiva, dolor toracico, desmayo, purgas, restriccion extrema o deterioro funcional severo.\n"
        "Proxima reevaluacion en 7 dias con: peso, perimetro cintura, adherencia, energia, dolor articular, animo y calidad de sueno. "
        "Con esos datos se ajustan calorias, carga mecanica y plan conductual sin improvisacion."
    )
    return _garantizar_minimo_palabras(base, minimo=820)


def _respuesta_alta_precision_clinica(
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> str:
    """Respuesta técnica compacta en formato clínico obligatorio."""
    peso = _valor_float((contexto_adicional or {}).get("peso_actual_kg"))
    altura_cm = _valor_float((contexto_adicional or {}).get("altura_cm"))
    imc = _valor_float((contexto_adicional or {}).get("imc_actual"))
    animo = _valor_float((contexto_adicional or {}).get("animo_reciente"))
    sentimiento = str((contexto_adicional or {}).get("sentimiento_reciente") or "no informado")
    restricciones = str(((contexto_adicional or {}).get("memoria_respuestas") or {}).get("restricciones") or "")

    peso_ref = peso if isinstance(peso, float) and peso > 25 else 70.0
    kcal = int(round(peso_ref * 28))
    prote = int(round(peso_ref * 2.0))
    grasa = int(round(peso_ref * 0.9))
    carb = max(90, int(round((kcal - (prote * 4) - (grasa * 9)) / 4)))

    bajo_impacto = isinstance(imc, float) and imc >= 30
    adaptacion_impacto = (
        "IMC>30: suprimir impactos (saltos/carrera intensa). Priorizar bici, remo, trineo y fuerza técnica en cadena cerrada para proteger menisco y cartílago."
        if bajo_impacto
        else "IMC<30: se permiten cargas progresivas con control de tempo y RPE."
    )

    sustituto = "Usar arroz, patata cocida/enfriada y quinoa como base de almidón resistente."
    if "lactosa" in restricciones.lower():
        sustituto += " Sustituir lácteos por versiones sin lactosa o bebida vegetal fortificada."
    if "gluten" in restricciones.lower() or "celia" in restricciones.lower():
        sustituto += " Eliminar trigo/cebada/centeno y evitar contaminación cruzada."

    return (
        "ANALISIS DE DATOS\n"
        f"Peso={peso if peso is not None else 'N/D'} kg | IMC={imc if imc is not None else 'N/D'} | Animo={animo if animo is not None else 'N/D'}/10 | Sentimiento={sentimiento}. "
        "Se integra riesgo metabólico, carga alostática y tolerancia mecánica para decidir intervención sin plantillas.\n\n"
        "BLOQUE NUTRICION\n"
        f"Objetivo diario: ~{kcal} kcal (P {prote}g / C {carb}g / G {grasa}g). Menú técnico: desayuno (huevo+fruta+avena certificada), comida (proteína magra+arroz/legumbre+verdura), "
        "merienda (lácteo alto en proteína o alternativa), cena (pescado/legumbre+verdura+tubérculo enfriado). "
        "Lógica bioquímica: reducir picos de insulina con secuencia fibra-proteína-carbohidrato, mejorar microbiota con fermentables y butirato, y usar almidón resistente para estabilidad glucémica. "
        f"Sustituciones: {sustituto}\n\n"
        "BLOQUE ENTRENAMIENTO\n"
        "Rutina base 3 días: A) sentadilla/press/remo 4x6-8, B) bisagra/press militar/jalón 4x6-10, C) circuito PHA 5 rondas 40s-20s. "
        "Usar RPE 7-8, tempo 3-1-1-0, descanso 90-180s y progresión de 2.5-5% cuando técnica y recuperación lo permitan. "
        f"Biomecánica: {adaptacion_impacto}\n\n"
        "BLOQUE PSICOLOGIA\n"
        "Si ánimo bajo o ansiedad: eje HPA hiperactivado, cortisol elevado y menor señal dopaminérgica por fatiga conductual. "
        "Protocolo: respiración 4-6 durante 3 minutos, técnica 5-4-3-2-1 en picos de estrés y activación conductual mínima (10-15 min) para preservar adherencia. "
        "Objetivo neuroquímico: bajar cortisol, sostener dopamina por logro pequeño y estabilizar serotonina con rutina de sueño y luz matinal."
    )


def _resumen_contexto(contexto_adicional: Optional[Dict[str, Any]]) -> str:
    """Genera un resumen util del contexto conocido para no dar planes ciegos."""
    if not contexto_adicional:
        return "Contexto disponible: limitado. Se usa plan inicial seguro."

    piezas: List[str] = []
    for clave in (
        "usuario_rol",
        "peso_actual_kg",
        "altura_cm",
        "imc_actual",
        "frecuencia_gym",
        "sentimiento_reciente",
        "animo_reciente",
    ):
        valor = contexto_adicional.get(clave)
        if valor is not None:
            piezas.append(f"{clave}={valor}")

    if not piezas:
        return "Contexto disponible: sin metricas previas relevantes."
    return "Contexto disponible: " + ", ".join(piezas)


def _bloques_avanzados_multiambito(
    dominios: List[str],
    objetivo: str,
    contexto_adicional: Optional[Dict[str, Any]],
) -> str:
    """Construye un plan avanzado por bloques para casos de varios ambitos."""
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios)
    contexto = _resumen_contexto(contexto_adicional)

    return (
        "Diagnostico funcional breve:\n"
        f"- Objetivo principal detectado: {objetivo}.\n"
        f"- Ambitos implicados: {dominios_texto}.\n"
        f"- {contexto}\n\n"
        "Intervencion avanzada por ambitos:\n"
        "1) Nutricion: estructura diaria 3-4 comidas, proteina suficiente y ajustes por objetivo.\n"
        "2) Entrenamiento: fuerza con progresion + recuperacion activa segun energia/sueno.\n"
        "3) Salud mental: protocolo diario anti-estres (respiracion, descarga mental, cierre de dia).\n"
        "4) Trabajo/familia/social: plan minimo viable para dias complejos y decisiones de alta friccion.\n\n"
        "Roadmap 4 semanas:\n"
        "- Semana 1: estabilizacion de rutinas y medicion base.\n"
        "- Semana 2: progresion de carga y mejora de adherencia.\n"
        "- Semana 3: optimizacion segun respuesta real (energia, hambre, estres).\n"
        "- Semana 4: consolidacion y plan de mantenimiento.\n\n"
        "Metricas de control (cada 7 dias):\n"
        "- Adherencia (%), energia (1-10), sueno (horas), estres (1-10), progreso del objetivo.\n\n"
        "Alertas de escalado:\n"
        "- Deterioro funcional sostenido, ansiedad alta persistente, o conducta alimentaria de riesgo.\n"
        "- En ese caso, derivar a profesional (nutricionista/psicologo/medico)."
    )


def _siguiente_accion_autonoma(dominios: List[str], objetivo: str) -> str:
    """Define la mejor siguiente accion inmediata sin depender de un LLM externo."""
    if "salud_mental" in dominios:
        return "Haz 3 minutos de respiracion 4-4-4 y registra tu nivel de estres del 1 al 10."
    if "nutricion" in dominios:
        return "Define tu siguiente comida con proteina + fibra + agua y fijala para la proxima hora."
    if "entrenamiento" in dominios:
        return "Haz una sesion minima de 15 minutos (movilidad + fuerza basica) y anota sensaciones."

    if objetivo == "perdida_grasa":
        return "Planifica hoy un deficit suave (300-450 kcal) y cumple al menos 8.000 pasos."
    if objetivo == "ganancia_muscular":
        return "Asegura una toma de proteina en la proxima comida y programa tu proxima sesion de fuerza."
    if objetivo == "bienestar_mental":
        return "Agenda una rutina de cierre del dia de 10 minutos sin pantalla + respiracion guiada."

    return "Elige una sola accion de salud para hoy y ejecutala en menos de 10 minutos sin negociar."


def _es_mensaje_social_breve(texto_normalizado: str) -> bool:
    """Detecta saludos/interacciones cortas para responder de forma natural."""
    t = (texto_normalizado or "").strip()
    if not t:
        return False

    saludos = {
        "hola",
        "holaa",
        "buenas",
        "buenas tardes",
        "buenos dias",
        "buenas noches",
        "hey",
        "ey",
        "que tal",
        "como estas",
        "como va",
        "gracias",
        "ok",
        "vale",
    }
    if t in saludos:
        return True

    palabras = [p for p in t.split() if p]
    if len(palabras) <= 4 and any(k in t for k in ("hola", "buenas", "hey", "que tal", "gracias")):
        return True
    return False


def _respuesta_social_contextual(
    mensaje_usuario: str,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Genera una respuesta corta y coherente para mensajes sociales o de arranque."""
    t = _normalizar_texto(mensaje_usuario)
    nombre = ""
    if isinstance(contexto_adicional, dict):
        nombre = str(contexto_adicional.get("usuario_nombre") or "").strip()
    prefijo = f"{nombre}, " if nombre else ""

    texto_historial = " ".join(
        _normalizar_texto(str((i or {}).get("mensaje") or ""))
        for i in (historial_chat or [])
        if isinstance(i, dict)
    )
    saludo_repetido = texto_historial.count("hola") >= 2 and ("hola" in t or "buenas" in t)

    if any(k in t for k in ("gracias", "thank")):
        return f"De nada. {prefijo}si quieres, seguimos con algo concreto: nutricion, entrenamiento, estado emocional o analisis de foto/video."

    if saludo_repetido:
        return (
            f"{prefijo}aqui estoy y te leo bien. Para darte una respuesta precisa, dime en una frase que necesitas ahora: "
            "1) plan de comida, 2) rutina, 3) ansiedad/sueno, 4) analisis de imagen/video."
        )

    return (
        f"{prefijo}hola. Te respondo de forma directa y precisa. "
        "Dime que necesitas ahora mismo y te doy una accion concreta en menos de 1 minuto."
    )


def _es_respuesta_ambigua_corta(texto_normalizado: str) -> bool:
    """Detecta respuestas muy cortas que requieren clarificación, no un plan largo."""
    t = (texto_normalizado or "").strip()
    if not t:
        return False
    ambiguas = {
        "no",
        "si",
        "sí",
        "depende",
        "no se",
        "ni idea",
        "quizas",
        "quizá",
        "ok",
        "vale",
        "da igual",
        "normal",
    }
    if t in ambiguas:
        return True
    palabras = [p for p in t.split() if p]
    return len(palabras) <= 3 and all(len(p) <= 8 for p in palabras)


def _respuesta_ambigua_contextual(
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> str:
    """Devuelve una pregunta de desambiguación corta y útil."""
    tema = _normalizar_texto(str((contexto_adicional or {}).get("memoria_tema") or ""))
    if tema in {"dieta", "visual", "nutricion"}:
        return "Para cerrarte una dieta útil ahora mismo, dime solo una cosa: objetivo (masa, perder grasa o mantener)."
    if tema in {"entrenamiento", "gym"}:
        return "Para ajustarte la rutina, dime solo esto: ¿cuántos días reales puedes entrenar esta semana?"
    if tema in {"psicologia", "salud_mental"}:
        return "Para ayudarte bien, dime qué te pesa más ahora: ansiedad, ánimo bajo o sueño."
    return "Para darte una respuesta precisa, elige una: 1) dieta, 2) rutina, 3) ansiedad/sueño, 4) análisis foto/video."


def _valor_float(valor: Any) -> Optional[float]:
    """Convierte valor a float de forma segura."""
    try:
        if valor is None:
            return None
        return float(valor)
    except Exception:
        return None


def _extraer_memoria_respuestas(contexto_adicional: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Recupera respuestas de memoria ya recopiladas en chat."""
    if not isinstance(contexto_adicional, dict):
        return {}
    raw = contexto_adicional.get("memoria_respuestas")
    if isinstance(raw, dict):
        return raw
    return {}


def _objetivo_desde_contexto(
    objetivo_detectado: str,
    contexto_adicional: Optional[Dict[str, Any]],
) -> str:
    """Prioriza objetivo recogido en memoria frente al inferido por keywords."""
    memoria = _extraer_memoria_respuestas(contexto_adicional)
    objetivo_mem = _normalizar_texto(str(memoria.get("objetivo") or ""))
    if any(k in objetivo_mem for k in ("masa", "muscular", "ganar")):
        return "ganancia_muscular"
    if any(k in objetivo_mem for k in ("perder", "grasa", "adelgaz")):
        return "perdida_grasa"
    if any(k in objetivo_mem for k in ("mantener", "mantenimiento")):
        return "adherencia_sostenible"
    return objetivo_detectado


def _detectar_duracion_plan(texto: str) -> int:
    """Extrae duración en días del mensaje del usuario. Por defecto 7 días."""
    if any(k in texto for k in ("mes", "mensual", "4 semanas", "cuatro semanas", "30 dias", "30 días")):
        return 30
    if any(k in texto for k in ("dos semanas", "2 semanas", "14 dias", "14 días", "quincena")):
        return 14
    if any(k in texto for k in ("semana", "7 dias", "7 días")):
        return 7
    if any(k in texto for k in ("3 dias", "3 días", "tres dias")):
        return 3
    return 7


def _detectar_sesiones_entrenamiento(texto: str) -> Optional[int]:
    """Extrae sesiones por semana solicitadas por usuario (rango 2-7)."""
    t = _normalizar_texto(texto or "")
    m = re.search(r"(\d{1,2})\s*(?:sesion(?:es)?|dias?)\s*(?:a la semana|/\s*semana|por semana)?", t)
    if not m:
        return None
    try:
        sesiones = int(m.group(1))
    except (TypeError, ValueError):
        return None
    return max(2, min(7, sesiones))


def _menu_dia_nutricion(dia: int, objetivo: str, prote: Optional[int], carbs: Optional[int], grasa: Optional[int], restricciones: str) -> str:
    """Genera menú para un día concreto rotando alimentos."""
    proteinas_opciones = [
        ("pollo a la plancha", 180),
        ("merluza al horno", 200),
        ("salmón", 180),
        ("pechuga de pavo", 180),
        ("atún en agua", 150),
        ("huevos revueltos", "3 huevos"),
        ("ternera magra", 160),
    ]
    carbos_opciones = [
        ("arroz", "90 g en crudo"),
        ("patata cocida", "200 g"),
        ("pasta integral", "80 g en crudo"),
        ("boniato", "200 g"),
        ("quinoa", "80 g en crudo"),
        ("pan integral", "60 g"),
        ("avena", "60 g"),
    ]
    verduras_opciones = [
        "ensalada mixta", "brócoli al vapor", "espinacas salteadas",
        "judías verdes", "pisto de verduras", "zanahoria y pepino",
        "col lombarda", "coliflor al horno",
    ]
    idx = (dia - 1) % 7
    prot_nombre, prot_cant = proteinas_opciones[idx]
    carb_nombre, carb_cant = carbos_opciones[idx]
    verd = verduras_opciones[idx]

    # Ajuste si hay restricciones (sin gluten: elimina pasta/pan/avena)
    if "celiac" in restricciones or "gluten" in restricciones:
        if "pasta" in carb_nombre or "pan" in carb_nombre or "avena" in carb_nombre:
            carb_nombre, carb_cant = "arroz", "90 g en crudo"

    desayuno_opciones = [
        "3 huevos revueltos + avena 60g + plátano",
        "yogur griego 200g + granola 40g + fresas",
        "tostada integral 60g + aguacate + 2 huevos",
        "batido proteico 250ml + avena 50g + naranja",
        "queso batido 200g + frutos secos 30g + melocotón",
        "2 huevos + tortita avena 60g + arándanos",
        "pavo 80g + pan integral 50g + tomate",
    ]
    desayuno = desayuno_opciones[idx]
    if "celiac" in restricciones or "gluten" in restricciones:
        desayuno = desayuno.replace("avena", "arroz inflado 40g").replace("tostada integral", "tostada sin gluten").replace("pan integral", "pan sin gluten")

    bloque_macros = ""
    if prote and carbs and grasa:
        bloque_macros = f" (~P:{prote}g / C:{carbs}g / G:{grasa}g)"

    return (
        f"\nDía {dia}{bloque_macros if dia == 1 else ''}:"
        f"\n  Desayuno: {desayuno}"
        f"\n  Comida: {prot_nombre} {prot_cant} + {carb_nombre} {carb_cant} + {verd}"
        f"\n  Merienda: yogur alto proteína 150g + fruta de temporada"
        f"\n  Cena: {proteinas_opciones[(idx+2)%7][0]} {proteinas_opciones[(idx+2)%7][1]} + verdura salteada"
    )


def _plan_nutricion_preciso(
    objetivo: str,
    contexto_adicional: Optional[Dict[str, Any]],
    escenarios: List[str],
    texto_usuario: str = "",
) -> str:
    """Entrega plan nutricional completo y personalizado por perfil y duración solicitada."""
    memoria = _extraer_memoria_respuestas(contexto_adicional)
    peso = _valor_float((contexto_adicional or {}).get("peso_actual_kg"))
    altura = _valor_float((contexto_adicional or {}).get("altura_cm"))
    imc = _valor_float((contexto_adicional or {}).get("imc_actual"))
    animo = _valor_float((contexto_adicional or {}).get("animo_reciente"))
    nombre = str((contexto_adicional or {}).get("usuario_nombre") or "").strip()
    horario = str(memoria.get("horario") or "").strip() or "flexible"
    restricciones = _normalizar_texto(str(memoria.get("restricciones") or "ninguna"))
    duracion = _detectar_duracion_plan(_normalizar_texto(texto_usuario))

    # Cálculo de macros personalizado
    kcal = prote = carbs = grasa = None
    if peso and peso > 25:
        tmb = (10 * peso + (6.25 * altura if altura else 0) - 5 * 25 + 5)  # Mifflin estimado
        factor_actividad = 1.55 if "entren" in _normalizar_texto(texto_usuario) else 1.375
        tdee = int(tmb * factor_actividad)

        if objetivo == "ganancia_muscular":
            kcal = tdee + 250
            prote = round(peso * 2.2)
            grasa = round(peso * 1.0)
        elif objetivo == "perdida_grasa":
            kcal = max(1200, tdee - 400)
            prote = round(peso * 2.0)
            grasa = round(peso * 0.8)
        else:
            kcal = tdee
            prote = round(peso * 1.8)
            grasa = round(peso * 0.9)
        kcal_prote = int(prote * 4)
        kcal_grasa = int(grasa * 9)
        carbs = max(80, int(round((kcal - kcal_prote - kcal_grasa) / 4)))

    # Suplementación según objetivo y estado de ánimo
    suplementos = []
    if objetivo == "ganancia_muscular":
        suplementos += ["Creatina monohidrato 5g/día", "Proteína de suero 30g post-entreno"]
    elif objetivo == "perdida_grasa":
        suplementos += ["Cafeína 100-200mg pre-entreno (opcional)", "Omega-3 1g/día"]
    if animo and animo < 5:
        suplementos += ["Magnesio 300mg antes de dormir (ánimo bajo detectado)", "Vitamina D3 2000UI/día"]

    # Ajuste por turnos
    ajuste_turnos = ""
    if "trabajo_por_turnos" in escenarios or "turno" in _normalizar_texto(horario):
        ajuste_turnos = "\n⏰ Ajuste turnos: usa bloques de comida, no horas fijas. Prioriza comida 1 al despertar y comida post-turno."

    # Restricciones alimentarias
    aviso_restricciones = ""
    if restricciones not in {"", "ninguna", "no"}:
        aviso_restricciones = f"\n⚠️ Restricciones activas: {restricciones}. Los alimentos listados son compatibles."

    # Cabecera personalizada
    saludo = f"Plan nutricional para {nombre} — " if nombre else "Plan nutricional — "
    etiqueta_obj = {"ganancia_muscular": "Ganancia muscular", "perdida_grasa": "Pérdida de grasa"}.get(objetivo, "Mantenimiento/adherencia")

    if kcal and prote and carbs and grasa:
        bloque_macros = (
            f"\n📊 Macros diarios objetivo: {kcal} kcal | Proteína: {prote}g | Carbohidratos: {carbs}g | Grasas: {grasa}g"
            f"\n   (Basado en: peso {peso}kg{'  altura ' + str(int(altura)) + 'cm' if altura else ''}{'  IMC ' + str(round(imc,1)) if imc else ''})"
        )
    else:
        bloque_macros = (
            "\n📊 Sin peso registrado → estructura por porciones:"
            "\n   Por ingesta: 1 palma de proteína + 1 puño de carbohidrato complejo + 2 puños de verdura + 1 pulgar de grasa"
        )

    # Generar los días del plan
    dias_texto = ""
    for d in range(1, duracion + 1):
        dias_texto += _menu_dia_nutricion(d, objetivo, prote, carbs, grasa, restricciones)

    # Bloque de control/ajuste según duración
    if duracion >= 30:
        control = (
            "\n\n📅 Control mensual:"
            "\n- Semana 1-2: estabilización de rutina + registro de adherencia"
            "\n- Semana 3: ajuste de kcal según progreso (±150 kcal si no hay cambio en peso)"
            "\n- Semana 4: consolidación + planificación del mes siguiente"
            "\n- Si peso ↓ >1kg/semana en pérdida: sube 100 kcal para evitar pérdida muscular"
            "\n- Si peso ↑ >0.5kg/semana en ganancia: baja 150 kcal para controlar grasa"
        )
    elif duracion >= 14:
        control = (
            "\n\n📅 Control quincenal:"
            "\n- Día 7: revisa energía (1-10) y adherencia. Si <6, simplifica las comidas."
            "\n- Día 14: pesa y mide. Ajusta ±100 kcal según resultado."
        )
    else:
        control = (
            "\n\n📅 Control semanal:"
            "\n- Si no ves cambio en energía o peso al final de la semana: ajusta +/-150 kcal"
            "\n- Si hay hambre excesiva: añade snack de 150-200 kcal proteico"
        )

    bloque_suplementos = ""
    if suplementos:
        bloque_suplementos = "\n\n💊 Suplementación recomendada:\n- " + "\n- ".join(suplementos)

    return (
        f"{saludo}{etiqueta_obj} · {duracion} días"
        f"{bloque_macros}"
        f"{aviso_restricciones}"
        f"{ajuste_turnos}"
        f"\n{'─'*40}"
        f"{dias_texto}"
        f"{control}"
        f"{bloque_suplementos}"
        f"\n\n🔗 Este plan va coordinado con entrenamiento y gestión emocional. Dime si quieres que ajuste algún día específico."
    )


def _plan_entrenamiento_preciso(
    objetivo: str,
    contexto_adicional: Optional[Dict[str, Any]],
    escenarios: List[str],
    texto_usuario: str = "",
) -> str:
    """Entrega rutina completa personalizada con progresión, por días y duración solicitada."""
    frecuencia = (contexto_adicional or {}).get("frecuencia_gym")
    peso = _valor_float((contexto_adicional or {}).get("peso_actual_kg"))
    imc = _valor_float((contexto_adicional or {}).get("imc_actual"))
    animo = _valor_float((contexto_adicional or {}).get("animo_reciente"))
    nombre = str((contexto_adicional or {}).get("usuario_nombre") or "").strip()
    duracion = _detectar_duracion_plan(_normalizar_texto(texto_usuario))

    sesiones_solicitadas = _detectar_sesiones_entrenamiento(texto_usuario)

    # Días por semana (prioridad: petición del paciente > perfil guardado > default)
    if isinstance(sesiones_solicitadas, int):
        dias_semana = sesiones_solicitadas
    elif isinstance(frecuencia, int) and frecuencia >= 5:
        dias_semana = 5
    elif isinstance(frecuencia, int) and frecuencia >= 4:
        dias_semana = 4
    else:
        dias_semana = 3

    # IMC alto → bajo impacto
    bajo_impacto = bool(imc and imc > 30)

    # Foco según objetivo
    foco_map = {
        "ganancia_muscular": "hipertrofia + progresión de carga",
        "perdida_grasa": "fuerza + cardio metabólico",
    }
    foco = foco_map.get(objetivo, "salud funcional y adherencia")

    # Reducción de volumen si ánimo bajo
    volumen_nota = ""
    if animo is not None and animo < 4:
        volumen_nota = "\n⚠️ Ánimo bajo detectado: reduce series en 1 por ejercicio esta semana. Prioriza movimiento sobre rendimiento."

    # Estructura de días según frecuencia y objetivo
    if dias_semana >= 4:
        estructura = [
            ("Día A – Pecho + Hombros + Tríceps", [
                ("Press banca / Press pecho máquina", "4x8-10", "RPE 8", "2'"),
                ("Press militar mancuernas", "3x10-12", "RPE 7", "90\""),
                ("Elevaciones laterales", "3x15", "RPE 7", "60\""),
                ("Fondos en paralelas / Asistido", "3x10", "RPE 8", "90\""),
            ]),
            ("Día B – Espalda + Bíceps", [
                ("Jalón al pecho / Dominadas asistidas", "4x8-10", "RPE 8", "2'"),
                ("Remo con barra / Remo máquina", "4x10", "RPE 8", "2'"),
                ("Curl bíceps mancuernas", "3x12", "RPE 7", "60\""),
                ("Facepulls / Remo en polea", "3x15", "RPE 6", "60\""),
            ]),
            ("Día C – Piernas enfoque cuádriceps", [
                ("Sentadilla libre / Prensa 45°" if not bajo_impacto else "Prensa 45° ángulo bajo", "4x8-10", "RPE 8", "2'30\""),
                ("Extensiones cuádriceps", "3x12-15", "RPE 7", "90\""),
                ("Zancadas andando", "3x10 c/p", "RPE 7", "90\""),
                ("Elevaciones gemelo", "4x15-20", "RPE 7", "60\""),
            ]),
            ("Día D – Piernas enfoque posterior + Core", [
                ("Peso muerto rumano" if not bajo_impacto else "Curl femoral en máquina", "4x10", "RPE 8", "2'"),
                ("Hip thrust / Puente glúteo", "4x12", "RPE 8", "90\""),
                ("Sentadilla sumo o abductores", "3x12", "RPE 7", "90\""),
                ("Plank con variantes", "3x40\"", "RPE 6", "45\""),
            ]),
        ]
    else:
        estructura = [
            ("Día A – Tren superior (empuje + tirón)", [
                ("Press banca / Press pecho máquina", "4x10", "RPE 8", "2'"),
                ("Jalón al pecho / Dominadas asistidas", "4x10", "RPE 8", "2'"),
                ("Press hombros mancuernas", "3x12", "RPE 7", "90\""),
                ("Curl + extensión tríceps en polea", "3x12", "RPE 7", "60\""),
            ]),
            ("Día B – Tren inferior + Core", [
                ("Sentadilla libre / Prensa" if not bajo_impacto else "Prensa 45°", "4x10", "RPE 8", "2'30\""),
                ("Peso muerto rumano" if not bajo_impacto else "Curl femoral", "3x10", "RPE 8", "2'"),
                ("Zancadas andando", "3x10 c/p", "RPE 7", "90\""),
                ("Plank + abdominales", "3x40\"", "RPE 6", "45\""),
            ]),
            ("Día C – Cuerpo completo + Cardio", [
                ("Sentadilla goblet / Peso muerto" if not bajo_impacto else "Sentadilla asistida", "3x12", "RPE 7", "90\""),
                ("Remo con mancuernas", "3x12", "RPE 7", "90\""),
                ("Flexiones / Fondos", "3x10-15", "RPE 7", "90\""),
                ("Cardio zona 2: 20 min bicicleta/elíptica", "1 serie", "FC 120-140 ppm", "—"),
            ]),
        ]

    # Generar texto de la rutina
    saludo = f"Rutina de entrenamiento para {nombre} — " if nombre else "Rutina de entrenamiento — "
    etiqueta_obj = {"ganancia_muscular": "Hipertrofia", "perdida_grasa": "Pérdida de grasa + tonificación"}.get(objetivo, "Salud funcional")

    cuerpo_dias = ""
    for sesion in estructura[:dias_semana]:
        titulo_dia, ejercicios_dia = sesion
        cuerpo_dias += f"\n\n**{titulo_dia}**"
        cuerpo_dias += "\n| Ejercicio | Series×Reps | RPE | Descanso |"
        cuerpo_dias += "\n|-----------|-------------|-----|----------|"
        for ej, sereps, rpe, desc in ejercicios_dia:
            cuerpo_dias += f"\n| {ej} | {sereps} | {rpe} | {desc} |"

    # Cardio complementario
    cardio = ""
    if objetivo == "perdida_grasa":
        cardio = "\n\n🏃 Cardio: 2-3 sesiones adicionales/semana de 20-30 min en zona 2 (FC ~120-140 ppm) o caminar 8.000 pasos/día."
    elif objetivo == "ganancia_muscular":
        cardio = "\n\n🚴 Cardio: 1-2 sesiones de 15-20 min zona 2 para salud cardiovascular sin interferir con recuperación."

    # Progresión según duración
    if duracion >= 30:
        progresion = (
            "\n\n📈 Progresión mensual:"
            "\n- Semana 1-2 (Acumulación): aprende técnica. Objetivo: completar todas las series con RPE indicado."
            "\n- Semana 3 (Intensificación): sube 2.5-5 kg en ejercicios principales si RPE ≤7."
            "\n- Semana 4 (Descarga): reduce volumen un 40%. Recuperación activa."
        )
    elif duracion >= 14:
        progresion = (
            "\n\n📈 Progresión quincenal:"
            "\n- Semana 1: técnica y base. RPE 7 máximo."
            "\n- Semana 2: añade 2.5 kg en ejercicios base si completas todas las series."
        )
    else:
        progresion = (
            "\n\n📈 Progresión semanal:"
            "\n- Si completas todas las series con técnica limpia: sube 2.5-5% de carga la semana siguiente."
            "\n- Si duermes <6h o ánimo <4: reduce volumen un 20% sin culpa."
        )

    ajuste_tiempo = ""
    if "tiempo_limitado" in escenarios:
        ajuste_tiempo = (
            "\n\n⚡ Protocolo express (si tienes <25 min):"
            "\n- 3 rondas de: empuje (10 reps) + tirón (10 reps) + sentadilla (12 reps). Sin descanso entre ejercicios, 90\" entre rondas."
        )

    return (
        f"{saludo}{etiqueta_obj} · {duracion} días · {dias_semana} sesiones/semana"
        f"{volumen_nota}"
        f"{'' if not bajo_impacto else chr(10) + '⚠️ IMC >30: rutina de bajo impacto articular seleccionada.'}"
        f"\n{'─'*40}"
        f"{cuerpo_dias}"
        f"{cardio}"
        f"{progresion}"
        f"{ajuste_tiempo}"
        f"\n\n🔗 Coordínalo con tu nutrición: los días de entrenamiento aumenta los carbohidratos ~30-50g extra."
    )


def _plan_psicologia_preciso(
    contexto_adicional: Optional[Dict[str, Any]],
    escenarios: List[str],
    texto_usuario: str = "",
) -> str:
    """Entrega plan psicológico personalizado con técnicas TCC/ACT y progresión por días."""
    sentimiento = str((contexto_adicional or {}).get("sentimiento_reciente") or "").strip() or "no informado"
    animo = _valor_float((contexto_adicional or {}).get("animo_reciente"))
    nombre = str((contexto_adicional or {}).get("usuario_nombre") or "").strip()
    duracion = _detectar_duracion_plan(_normalizar_texto(texto_usuario))

    saludo = f"Plan psicológico para {nombre} — " if nombre else "Plan psicológico — "

    # Nivel de intensidad según ánimo
    if animo is not None and animo <= 3:
        nivel = "alta_intensidad"
        nivel_txt = "Regulación prioritaria (ánimo crítico detectado)"
    elif animo is not None and animo <= 6:
        nivel = "media"
        nivel_txt = "Estabilización y construcción de recursos"
    else:
        nivel = "mantenimiento"
        nivel_txt = "Optimización y prevención"

    # Técnicas base según nivel
    tecnicas_base = {
        "alta_intensidad": [
            ("Respiración diafragmática 4-4-6", "Inhala 4s por nariz, mantén 4s, exhala 6s por boca. 5 ciclos cada vez que notes tensión."),
            ("Técnica grounding 5-4-3-2-1", "Nombra: 5 cosas que ves, 4 que tocas, 3 que oyes, 2 que hueles, 1 que saboreas. Ancla al presente."),
            ("Defusión cognitiva", "Cuando aparezca un pensamiento angustiante, dite: 'Estoy teniendo el pensamiento de que...' Crea distancia del pensamiento."),
        ],
        "media": [
            ("Registro de pensamientos (TCC)", "Anota: situación → pensamiento automático → emoción (0-10) → pensamiento alternativo más realista."),
            ("Activación conductual", "Elige 1 actividad placentera al día (mínimo 15 min). No negocies. Regístrala y puntúa cómo te sentiste después."),
            ("Higiene del sueño", "Hora fija de dormir/despertar ±30 min. Pantallas off 45 min antes. Temperatura 18-20°C."),
        ],
        "mantenimiento": [
            ("Mindfulness 10 min/día", "Observa pensamientos como nubes que pasan. No los juzgues, no los sigas. App sugerida: Headspace, Calm o YouTube."),
            ("Revisión semanal de valores (ACT)", "Cada domingo: ¿Qué acciones hice esta semana coherentes con lo que más valoro? ¿Cuáles me alejaron?"),
            ("Gratitud activa", "3 cosas concretas por las que estás agradecido/a cada noche. Específicas, no genéricas."),
        ],
    }

    tecnicas = tecnicas_base[nivel]

    # Plan día a día (simplificado para duraciones largas)
    if duracion <= 7:
        dias_plan = []
        tareas_rotacion = [
            "Mañana: respiración 4-4-6 (5 min) + intención del día (1 frase)",
            "Tarde: registro de 1 pensamiento automático",
            "Noche: diario emocional (¿qué sentí hoy?, ¿qué lo generó?, ¿cómo respondí?)",
            "Práctica de defusión ante 1 pensamiento difícil",
            "Activación: 1 actividad placentera elegida (15-30 min)",
            "Higiene sueño: apaga pantallas 45 min antes",
            "Revisión: ¿Qué técnica me ha ayudado más esta semana?",
        ]
        for d in range(1, duracion + 1):
            dias_plan.append(f"\nDía {d}: {tareas_rotacion[(d-1) % len(tareas_rotacion)]}")
        texto_dias = "".join(dias_plan)
    else:
        # Para planes de 14-30 días, estructura semanal
        semanas = (duracion + 6) // 7
        semanas_plan = []
        fases = [
            ("Semana de toma de contacto", "Establece el hábito de registro diario (5 min/día). Sin presión de cambiar, solo observar."),
            ("Semana de intervención", "Aplica 1 técnica por día de forma consistente. Puntúa cada noche el malestar (0-10)."),
            ("Semana de profundización", "Identifica tus 3 disparadores principales. Diseña respuesta alternativa para cada uno."),
            ("Semana de consolidación", "Integra lo aprendido. Define tu protocolo personal mínimo viable para días difíciles."),
        ]
        for s in range(1, min(semanas + 1, 5)):
            titulo_s, desc_s = fases[min(s - 1, 3)]
            semanas_plan.append(f"\nSemana {s} — {titulo_s}: {desc_s}")
        texto_dias = "".join(semanas_plan)

    # Semáforo de acción
    semaforo = (
        "\n\n🚦 Semáforo de acción:"
        "\n- 🟢 Malestar ≤4/10: continúa rutina habitual"
        "\n- 🟡 Malestar 5-7/10: activa grounding + reduce exigencia del día"
        "\n- 🔴 Malestar ≥8/10 o ideas de daño: contacta con profesional hoy"
    )

    # Conexión con nutrición y entrenamiento
    nexo = (
        "\n\n🔗 Conexión cuerpo-mente:"
        "\n- Los días de ánimo bajo, no canceles el entreno: cambia por 20 min de caminar."
        "\n- El eje cortisol-glucosa se regula mejor con proteína en desayuno y descanso activo."
        "\n- Si hay hambre emocional nocturna: técnica grounding antes de ir a la cocina."
    )

    cuerpo_tecnicas = "\n\n🛠️ Técnicas asignadas:"
    for tec_nombre, tec_desc in tecnicas:
        cuerpo_tecnicas += f"\n\n**{tec_nombre}**\n{tec_desc}"

    return (
        f"{saludo}{nivel_txt} · {duracion} días"
        f"\nEstado emocional reciente: {sentimiento}"
        f"\nEscenarios activos: {', '.join(escenarios) if escenarios else 'ninguno detectado'}"
        f"\n{'─'*40}"
        f"{cuerpo_tecnicas}"
        f"\n\n📅 Estructura del plan:"
        f"{texto_dias}"
        f"{semaforo}"
        f"{nexo}"
    )


def _es_solicitud_integral(dominios: List[str], texto: str) -> bool:
    """Detecta si el usuario pide plan combinado de 2 o más áreas simultáneamente."""
    dominios_nucleares = [
        dominio for dominio in dominios if dominio in {"nutricion", "entrenamiento", "salud_mental"}
    ]
    if len(set(dominios_nucleares)) >= 2:
        return True
    palabras_integral = (
        "todo junto", "las 3", "las tres", "integral", "completo",
        "combinado", "todo a la vez", "dieta y rutina", "rutina y dieta",
        "nutricion y entrenamiento", "entrenamiento y nutricion",
        "mental y fisico", "fisico y mental", "mente y cuerpo",
    )
    return any(p in texto for p in palabras_integral)


def _dominio_desde_memoria(contexto_adicional: Optional[Dict[str, Any]]) -> Optional[str]:
    """Infere dominio principal a partir de memoria activa/contexto reciente."""
    if not isinstance(contexto_adicional, dict):
        return None

    tema = _normalizar_texto(str(contexto_adicional.get("memoria_tema") or ""))
    if any(k in tema for k in ("dieta", "nutri", "comida")):
        return "nutricion"
    if any(k in tema for k in ("entren", "rutina", "gym")):
        return "entrenamiento"
    if any(k in tema for k in ("psico", "ansiedad", "sueno", "salud_mental")):
        return "salud_mental"

    respuestas = contexto_adicional.get("memoria_respuestas")
    if isinstance(respuestas, dict):
        objetivo = _normalizar_texto(str(respuestas.get("objetivo") or ""))
        if any(k in objetivo for k in ("masa", "grasa", "peso", "dieta")):
            return "nutricion"
    return None


def _dominio_forzado_por_input_corto(
    texto: str,
    contexto_adicional: Optional[Dict[str, Any]],
) -> Optional[str]:
    """
    Convierte respuestas ultracortas de continuidad en un dominio útil.
    Ejemplos: "1" -> nutrición, "2" -> entrenamiento, "3" -> salud mental,
    "4" -> visual. También maneja frases de duración tipo "para un mes".
    """
    t = _normalizar_texto(texto)

    if t in {"1", "1.", "uno", "opcion 1", "opción 1"}:
        return "nutricion"
    if t in {"2", "2.", "dos", "opcion 2", "opción 2"}:
        return "entrenamiento"
    if t in {"3", "3.", "tres", "opcion 3", "opción 3"}:
        return "salud_mental"
    if t in {"4", "4.", "cuatro", "opcion 4", "opción 4"}:
        return "visual"

    # Si el usuario solo indica duración, mantenemos continuidad por memoria.
    if _detectar_duracion_plan(t) != 7 and not any(
        k in t for k in ("dieta", "nutri", "comida", "rutina", "entren", "ansiedad", "sueno", "psico")
    ):
        return _dominio_desde_memoria(contexto_adicional)

    return None


def _plan_integral_preciso(
    objetivo: str,
    contexto_adicional: Optional[Dict[str, Any]],
    escenarios: List[str],
    texto_usuario: str = "",
) -> str:
    """
    Plan integral AuraFit: nutrición + entrenamiento + psicología interconectados.
    Muestra cómo las 3 áreas se afectan mutuamente y genera un plan diario unificado.
    """
    memoria = _extraer_memoria_respuestas(contexto_adicional)
    peso = _valor_float((contexto_adicional or {}).get("peso_actual_kg"))
    altura = _valor_float((contexto_adicional or {}).get("altura_cm"))
    imc = _valor_float((contexto_adicional or {}).get("imc_actual"))
    animo = _valor_float((contexto_adicional or {}).get("animo_reciente"))
    nombre = str((contexto_adicional or {}).get("usuario_nombre") or "").strip()
    frecuencia = (contexto_adicional or {}).get("frecuencia_gym") or 3
    sentimiento = str((contexto_adicional or {}).get("sentimiento_reciente") or "neutral").strip()
    restricciones = _normalizar_texto(str(memoria.get("restricciones") or "ninguna"))
    duracion = _detectar_duracion_plan(_normalizar_texto(texto_usuario))
    try:
        frecuencia = int(frecuencia)
    except (TypeError, ValueError):
        frecuencia = 3

    saludo = f"## Plan Integral AuraFit — {nombre}\n" if nombre else "## Plan Integral AuraFit\n"

    # ── DATOS BASE ──────────────────────────────────────────────────────────
    kcal = prote = carbs = grasa = None
    if peso and peso > 25:
        tmb = 10 * peso + (6.25 * altura if altura else 0) - 5 * 25 + 5
        factor = 1.55 if frecuencia >= 4 else 1.375
        tdee = int(tmb * factor)
        if objetivo == "ganancia_muscular":
            kcal, prote = tdee + 250, round(peso * 2.2)
            grasa = round(peso * 1.0)
            carbs = round((kcal - prote * 4 - grasa * 9) / 4)
        elif objetivo == "perdida_grasa":
            kcal, prote = max(1200, tdee - 400), round(peso * 2.0)
            grasa = round(peso * 0.8)
            carbs = round((kcal - prote * 4 - grasa * 9) / 4)
        else:
            kcal, prote = tdee, round(peso * 1.8)
            grasa = round(peso * 0.9)
            carbs = round((kcal - prote * 4 - grasa * 9) / 4)
    else:
        calorias_base = {
            "ganancia_muscular": 2400,
            "perdida_grasa": 1800,
            "bienestar_mental": 2000,
            "rendimiento_global": 2200,
            "adherencia_sostenible": 2000,
        }
        kcal = calorias_base.get(objetivo, 2000)
        prote = 140 if objetivo in {"ganancia_muscular", "perdida_grasa"} else 120
        grasa = 65
        carbs = max(160, round((kcal - prote * 4 - grasa * 9) / 4))

    datos_base = "\n### Perfil integrado\n"
    if peso:
        datos_base += f"- Peso: {peso} kg"
        if altura:
            datos_base += f" | Altura: {altura} cm"
        if imc:
            datos_base += f" | IMC: {imc}"
        datos_base += "\n"
    if kcal:
        datos_base += f"- TDEE objetivo: **{kcal} kcal/día** | P: {prote}g · C: {carbs}g · G: {grasa}g\n"
    datos_base += f"- Ánimo reciente: {sentimiento} ({animo}/10)" if animo else f"- Ánimo reciente: {sentimiento}"
    datos_base += f"\n- Objetivo principal: **{objetivo.replace('_', ' ')}** | Duración: {duracion} días"
    if restricciones != "ninguna":
        datos_base += f"\n- ⚠️ Restricciones: {restricciones}"

    # ── NEXO ENTRE LAS 3 ÁREAS ──────────────────────────────────────────────
    nexos: list = []
    if animo is not None and animo <= 5:
        nexos.append("🧠→🍽️ El ánimo bajo eleva el cortisol → aumenta el antojo de azúcar. "
                     "Prioriza proteína en desayuno para estabilizar glucosa y estado de ánimo.")
        nexos.append("🧠→💪 Con ánimo ≤5, reduce intensidad de entrenamiento (-20% RPE). "
                     "Sesión corta de 25-30 min es más efectiva que forzar 60 min.")
    if objetivo == "ganancia_muscular":
        nexos.append("💪→🍽️ El anabolismo muscular requiere superávit calórico y ventana post-entreno: "
                     f"consume {round((prote or 0) * 0.3)}g proteína + hidratos simples en los 45 min post-sesión.")
    if objetivo == "perdida_grasa":
        nexos.append("🍽️→💪 El déficit calórico puede bajar energía en entreno: programa sesiones a las 2-3h de la comida principal.")
        nexos.append("🧠→🍽️ El hambre emocional sabotea el déficit más que ningún otro factor. "
                     "Usa la técnica de pausa de 10 min antes de comer fuera de horario.")
    if "estres" in escenarios or (animo is not None and animo <= 4):
        nexos.append("🧠→💪 El estrés elevado aumenta el cortisol → inhibe la síntesis proteica. "
                     "Añade 5 min de respiración diafragmática post-entreno para cortarlo.")
    if not nexos:
        nexos = [
            "Las 3 áreas forman un ciclo virtuoso: mejor nutrición → más energía en entreno → "
            "endorfinas → mejor estado de ánimo → más adherencia nutricional.",
        ]

    nexo_texto = "\n### 🔗 Cómo se conectan tus 3 áreas\n" + "\n".join(f"- {n}" for n in nexos)

    # ── PLAN DIARIO INTEGRADO ────────────────────────────────────────────────
    dias_entreno = {1, 2, 4, 5, 7} if frecuencia >= 5 else {1, 3, 5, 7} if frecuencia == 4 else {1, 3, 5} if frecuencia == 3 else {1, 4}
    nombres_dia = {1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb", 7: "Dom"}

    splits = {
        1: "Pecho + Hombro + Tríceps",
        2: "Espalda + Bíceps",
        3: "Cuádriceps + Core",
        4: "Isquios + Glúteo + Pantorrilla",
        5: "Full Body (carga moderada)",
        6: "Cardio ligero / movilidad",
        7: "Cardio ligero / movilidad",
    }
    tecnicas_psico_rota = [
        "Respiración 4-4-6 (5 min al despertar)",
        "Registro de pensamientos: situación→emoción→alternativa",
        "Grounding 5-4-3-2-1 si hay tensión",
        "Actividad placentera mínima 15 min",
        "Mindfulness 10 min (app o YouTube)",
        "Revisión de valores ACT (5 min nocturna)",
        "Gratitud activa: 3 cosas concretas antes de dormir",
    ]

    dias_mostrar = min(duracion, 7)
    plan_diario = f"\n\n### 📅 Plan diario integrado ({dias_mostrar} días)\n"
    for dia in range(1, dias_mostrar + 1):
        nombre_dia = nombres_dia.get(dia, f"Día {dia}")
        es_entreno = dia in dias_entreno
        menu = _menu_dia_nutricion(dia, objetivo, prote, carbs, grasa, restricciones)
        split = splits.get(dia, "Descanso activo")
        tecnica = tecnicas_psico_rota[(dia - 1) % len(tecnicas_psico_rota)]
        if animo is not None and animo <= 4:
            rpe_max = "5-6"
            entreno_txt = f"Sesión suave ({split}) — RPE máx {rpe_max}, 20-25 min"
        elif es_entreno:
            entreno_txt = f"{split} — RPE 7-8, 45-55 min"
        else:
            entreno_txt = "Descanso activo: 20-30 min caminata o movilidad"

        plan_diario += (
            f"\n**{nombre_dia} (Día {dia})**\n"
            f"  🍽️ {menu.strip()}\n"
            f"  💪 {entreno_txt}\n"
            f"  🧠 {tecnica}\n"
        )

    if duracion > 7:
        semanas = duracion // 7
        plan_diario += f"\n\n> Semanas 2–{semanas}: repite el ciclo aumentando carga de entrenamiento en +5% cada semana y ajusta kcal según evolución del peso."

    # ── CONTROL Y REVISIÓN ──────────────────────────────────────────────────
    if duracion <= 7:
        control = "\n\n### 📊 Control al final del plan\n- Peso y perímetro abdominal\n- Nivel de ánimo promedio (7 días)\n- Adherencia al entreno: sesiones completadas / sesiones planificadas\n- Si cualquier métrica empeora, dime y ajusto el plan."
    elif duracion <= 14:
        control = "\n\n### 📊 Control semanal\n**Semana 1:** registra peso, energía y ánimo diariamente.\n**Semana 2:** ajuste de carga (+5% entreno) y calorías si el peso no evoluciona como esperado."
    else:
        control = "\n\n### 📊 Control mensual\n- **Semana 1-2:** establecer hábitos base, no buscar resultados aún.\n- **Semana 3:** primera revisión: peso, adherencia, ánimo.\n- **Semana 4:** ajuste de macros y progresión de carga según datos.\n- Al mes, dime los resultados y genero el plan del mes siguiente."

    # ── ALERTA CLÍNICA ───────────────────────────────────────────────────────
    alertas = ""
    if imc and imc >= 30:
        alertas += "\n\n> ⚠️ **IMC elevado:** el entrenamiento es de bajo impacto hasta semana 3. Adapta la intensidad progresivamente."
    if animo is not None and animo <= 3:
        alertas += "\n\n> 🔴 **Ánimo muy bajo detectado:** Si persiste más de 2 semanas, considera derivación a psicología. La parte psicológica del plan es prioritaria esta semana."

    return (
        saludo
        + datos_base
        + nexo_texto
        + plan_diario
        + control
        + alertas
    )


def _respuesta_general_precisa(
    mensaje_usuario: str,
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> str:
    """Respuesta corta y útil para peticiones generales sin dominio claro."""
    texto = _normalizar_texto(mensaje_usuario)
    nombre = ""
    if isinstance(contexto_adicional, dict):
        nombre = str(contexto_adicional.get("usuario_nombre") or "").strip()
    prefijo = f"{nombre}, " if nombre else ""

    if any(k in texto for k in ("dieta", "comer", "menu", "nutric")):
        return f"{prefijo}te hago la dieta ahora. Solo dime objetivo: masa, perder grasa o mantener."
    if any(k in texto for k in ("rutina", "gym", "entren", "ejercicio")):
        return f"{prefijo}te preparo rutina ya. Dime días reales por semana (2, 3, 4 o 5)."
    if any(k in texto for k in ("ansiedad", "estres", "sueño", "sueno", "animo")):
        return f"{prefijo}vamos directo. Dime qué pesa más ahora: ansiedad, ánimo o sueño."

    return (
        f"{prefijo}te respondo exacto a lo que pidas. "
        "Elige una y te lo doy ya: 1) dieta, 2) rutina, 3) ansiedad/sueño, 4) análisis foto/video."
    )


def _respuesta_local_autonoma_gratis(
    mensaje_usuario: str,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    MODO EXPERTO LOCAL: Solo se activa si falla el motor de IA principal.
    Genera prescripciones técnicas basadas en lógica determinista de AuraFit.
    """

    texto = _normalizar_texto(mensaje_usuario)
    dominios = _detectar_dominios(texto)
    dominio_seccion = _dominio_desde_seccion_activa(texto)
    if dominio_seccion:
        dominios = [dominio_seccion] + [dom for dom in dominios if dom != dominio_seccion]
    objetivo = _detectar_objetivo_principal(texto)
    objetivo = _objetivo_desde_contexto(objetivo, contexto_adicional)
    escenarios = _detectar_escenarios(texto)
    trastornos = _detectar_trastornos_probables(texto)

    dominio_forzado = _dominio_forzado_por_input_corto(texto, contexto_adicional)
    if dominio_forzado == "visual":
        return (
            "Perfecto, vamos con análisis visual.\n"
            "Adjunta una imagen, vídeo o PDF y te doy observaciones concretas + correcciones accionables."
        )
    if dominio_forzado and dominio_forzado not in dominios:
        dominios.insert(0, dominio_forzado)

    if "integral" in texto and any(k in texto for k in ("porque", "por que")):
        return (
            "Lo llamo integral porque conecta nutrición, entrenamiento y salud mental en un único plan.\n"
            "Si prefieres, te lo doy por separado por área o en versión mixta por semanas."
        )

    # 0. DERIVACIÓN: respuesta breve y directa sin análisis adicional
    especialidad_derivacion = _es_solicitud_derivacion(texto)
    if especialidad_derivacion:
        return _respuesta_derivacion_breve(especialidad_derivacion, contexto_adicional)

    # Modo junta medica: respuesta extensa y tecnicamente estructurada.
    if _solicita_junta_medica(texto):
        return _respuesta_junta_medica_extensa(mensaje_usuario, contexto_adicional)

    # Modo alta precision clinica: respuesta tecnica compacta con bloques fijos.
    if _solicita_alta_precision_clinica(texto):
        return _respuesta_alta_precision_clinica(contexto_adicional)

    # 1. GESTIÓN DE SALUDOS (Corto y directo)
    if _es_mensaje_social_breve(texto):
        return _respuesta_social_contextual(mensaje_usuario, contexto_adicional, historial_chat)

    # 2. SI PIDE PLAN DIRECTO, RESPONDER CON EL PLAN ANTES QUE CON MARCO CLÍNICO LARGO.
    # Decidimos el dominio prioritario para no ser ambiguos
    dominio_principal = dominios[0] if dominios else "general"

    if _solicita_plan_accionable(texto):
        if dominio_seccion == "nutricion":
            return _plan_nutricion_preciso(objetivo, contexto_adicional, escenarios, texto_usuario=mensaje_usuario)
        if dominio_seccion == "entrenamiento":
            return _plan_entrenamiento_preciso(objetivo, contexto_adicional, escenarios, texto_usuario=mensaje_usuario)
        if dominio_seccion == "salud_mental":
            return _plan_psicologia_preciso(contexto_adicional, escenarios, texto_usuario=mensaje_usuario)
        if _es_solicitud_integral(dominios, texto):
            return _plan_integral_preciso(objetivo, contexto_adicional, escenarios, texto_usuario=mensaje_usuario)
        if dominio_principal == "nutricion" or "dieta" in texto:
            return _plan_nutricion_preciso(objetivo, contexto_adicional, escenarios, texto_usuario=mensaje_usuario)
        if dominio_principal == "entrenamiento" or "rutina" in texto:
            return _plan_entrenamiento_preciso(objetivo, contexto_adicional, escenarios, texto_usuario=mensaje_usuario)
        if dominio_principal == "salud_mental" or "ansiedad" in texto or "estres" in texto:
            return _plan_psicologia_preciso(contexto_adicional, escenarios, texto_usuario=mensaje_usuario)

    # 3. PROTOCOLO CLÍNICO (solo cuando de verdad hace falta ese marco)
    if _requiere_protocolo_clinico(texto, trastornos):
        return _protocolo_trastornos_multiambito(texto, contexto_adicional)

    # 4. GENERACIÓN DE RESPUESTA TÉCNICA LOCAL

    # PLAN INTEGRAL: si el usuario pide 2 o más áreas a la vez
    if _es_solicitud_integral(dominios, texto):
        return _plan_integral_preciso(objetivo, contexto_adicional, escenarios, texto_usuario=mensaje_usuario)

    # RESPUESTA DIRECTA POR DOMINIO: no asumir plan completo salvo petición explícita.
    if dominio_principal in {"nutricion", "entrenamiento", "salud_mental"}:
        return _respuesta_orientativa_por_dominio(dominio_principal, mensaje_usuario, contexto_adicional)

    # 5. FALLBACK GENERAL EXPERTO
    return _respuesta_experta_base(mensaje_usuario, contexto_adicional)

def _preguntas_minimas_expertas(dominios: List[str], objetivo: str) -> str:
    """Define las preguntas mínimas para afinar una respuesta avanzada sin perder utilidad."""
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios) if dominios else "general"
    return (
        "Preguntas minimas para afinar al maximo:\n"
        f"1) Objetivo exacto y prioridad real ahora mismo ({objetivo}).\n"
        f"2) Contexto principal implicado ({dominios_texto}) y horario real.\n"
        "3) Restricciones o riesgos: alergias, celiaquia, ansiedad, medicacion, lesiones.\n"
        "4) Recursos disponibles: tiempo, presupuesto, equipo, apoyo familiar."
    )


def _plan_experto_semanal(
    objetivo: str,
    escenarios: List[str],
    dominios: List[str],
    contexto_adicional: Optional[Dict[str, Any]],
) -> str:
    """Construye una salida experta con plan semanal extremadamente accionable."""
    contexto = _resumen_contexto(contexto_adicional)
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios) if dominios else "general"

    return (
        "Plan experto accionable (7 dias):\n"
        f"- Objetivo principal: {objetivo}.\n"
        f"- Dominios prioritarios: {dominios_texto}.\n"
        f"- {contexto}\n\n"
        "Lunes: definir menu base, ventana de entrenamiento y 3 tareas clave del dia.\n"
        "Martes: ejecucion principal (nutricion + entrenamiento + autocontrol).\n"
        "Miercoles: auditoria de energia, hambre, estres y sueno; ajuste fino.\n"
        "Jueves: segundo bloque fuerte de progreso; reforzar adherencia.\n"
        "Viernes: consolidar, reducir friccion y preparar fin de semana.\n"
        "Sabado: version flexible con estructura minima y decisiones de entorno.\n"
        "Domingo: revision de metricas, aprendizaje y replanificacion.\n\n"
        "Parametros operativos:\n"
        "- Nutricion: 3-4 comidas, proteina por toma, carbohidrato segun gasto y objetivo.\n"
        "- Entrenamiento: 3-5 sesiones/semana o adaptacion equivalente segun turnos.\n"
        "- Salud mental: 10 minutos diarios de regulacion y cierre de dia.\n"
        "- Contexto social/familiar: plan minimo viable para no abandonar por friccion externa.\n\n"
        f"Adaptaciones por escenario:\n{_adaptaciones_por_escenario(escenarios)}\n\n"
        "Metricas a medir cada 7 dias:\n"
        "- Cumplimiento (%), energia (1-10), estres (1-10), sueno (horas), progreso del objetivo.\n"
        "- Si cae adherencia o sube el malestar, reducir complejidad antes de subir exigencia."
    )


def _matriz_decision_experta(
    objetivo: str,
    dominios: List[str],
    escenarios: List[str],
) -> str:
    """Construye una matriz de decision con criterios de ajuste y contingencia."""
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios) if dominios else "general"
    escenarios_texto = ", ".join(escenarios) if escenarios else "sin escenario especial"

    return (
        "Matriz de decision experta:\n"
        f"- Prioridad 1: {objetivo} en {dominios_texto}.\n"
        f"- Escenarios activos: {escenarios_texto}.\n"
        "- Si hay baja energia o poco tiempo -> bajar complejidad, mantener estructura minima.\n"
        "- Si hay alta adherencia y buena energia -> progresar un 5-10% en carga o dificultad.\n"
        "- Si aparece ansiedad, purga, dolor persistente o caida de rendimiento -> parar la progresion y estabilizar.\n"
        "- Si el entorno frena el plan -> pasar a Plan B (adaptado) sin perder continuidad.\n"
    )


def _planes_contingencia_expertos(objetivo: str, dominios: List[str]) -> str:
    """Entrega Plan A/B/C para que la respuesta sea realmente util en escenarios reales."""
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios) if dominios else "general"
    return (
        "Planes de contingencia:\n"
        f"- Plan A (ideal): {objetivo} con {dominios_texto}, rutina completa y seguimiento semanal.\n"
        "- Plan B (realista): misma direccion con menos variables, menos volumen y mas foco en adherencia.\n"
        "- Plan C (critico): minimo viable de salud para no romper continuidad cuando el dia se complica.\n"
    )


def _diagnostico_diferencial_experto(
    objetivo: str,
    dominios: List[str],
    escenarios: List[str],
) -> str:
    """Describe hipotesis alternativas para elevar el nivel de la respuesta."""
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios) if dominios else "general"
    escenarios_texto = ", ".join(escenarios) if escenarios else "sin escenario especial"
    return (
        "Diagnostico diferencial experto:\n"
        f"- Hipotesis principal: {objetivo} en {dominios_texto}.\n"
        f"- Condicionantes de contexto: {escenarios_texto}.\n"
        "- Si el problema real es falta de tiempo -> priorizar Plan B y automatizacion.\n"
        "- Si el problema real es ansiedad/evitacion -> bajar exigencia y estabilizar primero.\n"
        "- Si el problema real es adherencia -> simplificar decisiones y medir cumplimiento real.\n"
        "- Si el problema real es energia/sueno -> corregir recuperacion antes de pedir mas rendimiento.\n"
    )


def _plan_72h_experto(
    objetivo: str,
    dominios: List[str],
    escenarios: List[str],
    contexto_adicional: Optional[Dict[str, Any]],
) -> str:
    """Plan de 72 horas para ejecutar inmediatamente tras la consulta."""
    contexto = _resumen_contexto(contexto_adicional)
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios) if dominios else "general"
    return (
        "Plan de accion 72h:\n"
        f"- Objetivo: {objetivo}.\n"
        f"- Ambito(s): {dominios_texto}.\n"
        f"- {contexto}\n"
        "DIA 1: definir objetivo operativo, eliminar friccion y preparar entorno.\n"
        "DIA 2: ejecutar rutina base completa y registrar energia/estres/adherencia.\n"
        "DIA 3: revisar resultados, corregir el cuello de botella y fijar siguiente paso.\n"
        f"Adaptacion por escenario: {', '.join(escenarios) if escenarios else 'sin ajuste especial'}.\n"
    )


def _plan_diario_experto(objetivo: str, dominios: List[str]) -> str:
    """Devuelve un esquema diario de maxima utilidad."""
    dominios_texto = ", ".join(d.replace("_", "/") for d in dominios) if dominios else "general"
    return (
        "Estructura diaria experta:\n"
        f"- Manana: revisar objetivo, comida 1, y bloque de prioridad en {dominios_texto}.\n"
        "- Mediodia: chequeo de energia, ingesta principal y ajuste de carga.\n"
        "- Tarde: ejecucion clave (entreno, trabajo o intervencion segun contexto).\n"
        "- Noche: cierre de dia, revision de fallos y preparacion del siguiente dia.\n"
        "- Regla de oro: si el dia se rompe, salvar la cadena minima antes de intentar optimizar.\n"
    )


def _detectar_trastornos_probables(texto_normalizado: str) -> List[str]:
    """Detecta grupos de trastorno para activar protocolo de precision y triage."""
    grupos: List[str] = []
    if "trastorn" in texto_normalizado:
        if any(k in texto_normalizado for k in ("aliment", "tca", "comida")):
            grupos.append("conducta_alimentaria")
        if any(k in texto_normalizado for k in ("psico", "mental", "emoc")):
            grupos.append("salud_mental")

    if any(k in texto_normalizado for k in ("trastorno aliment", "anore", "bulimi", "atracon", "tca")):
        if "conducta_alimentaria" not in grupos:
            grupos.append("conducta_alimentaria")
    if any(k in texto_normalizado for k in ("trastorno psic", "ansiedad", "panico", "depres", "toc", "trauma", "estres")):
        if "salud_mental" not in grupos:
            grupos.append("salud_mental")
    if any(k in texto_normalizado for k in ("diabetes", "hipotiroid", "sop", "hipertension")):
        grupos.append("metabolico_hormonal")
    if any(k in texto_normalizado for k in ("lesion", "dolor", "hernia", "rodilla", "lumbar", "rehabilit")):
        grupos.append("musculoesqueletico")
    return grupos


def _solicita_plan_accionable(texto_normalizado: str) -> bool:
    """Detecta peticiones donde el usuario quiere el plan directo y no un marco clínico largo."""
    return any(
        clave in texto_normalizado
        for clave in (
            "plan de",
            "quiero un plan",
            "dame un plan",
            "hazme un plan",
            "quiero una dieta",
            "dame una dieta",
            "hazme una dieta",
            "quiero una rutina",
            "dame una rutina",
            "hazme una rutina",
            "menu",
            "semana por semana",
            "plan diario",
            "respuesta breve",
            "accionable",
            "sin relleno",
            "incluye menu",
        )
    )


def _respuesta_orientativa_por_dominio(
    dominio_principal: str,
    mensaje_usuario: str,
    contexto_adicional: Optional[Dict[str, Any]],
) -> str:
    """Devuelve respuesta útil por dominio sin asumir que el usuario ya pidió un plan completo."""
    contexto = _resumen_contexto(contexto_adicional)

    if dominio_principal == "nutricion":
        return (
            f"Respuesta nutricional directa para tu consulta:\n"
            f"- Contexto útil detectado: {contexto}.\n"
            "- Te respondo a lo que has preguntado sin forzar una dieta completa.\n"
            "- Si tu duda afecta hambre, horarios, digestión, saciedad o elección de comidas, la prioridad es resolver eso primero con una recomendación concreta y realista.\n\n"
            "Si quieres, en el siguiente mensaje te preparo además una dieta adaptada a tus necesidades y horarios."
        )

    if dominio_principal == "entrenamiento":
        return (
            f"Respuesta de entrenamiento directa para tu consulta:\n"
            f"- Contexto útil detectado: {contexto}.\n"
            "- Te respondo a tu duda concreta sin convertirlo todavía en una rutina completa.\n"
            "- La prioridad es aclarar ejecución, progresión, dolor, fatiga o frecuencia antes de ampliar el plan.\n\n"
            "Si quieres, después te monto una rutina completa adaptada a tu nivel y días disponibles."
        )

    if dominio_principal == "salud_mental":
        return (
            f"Respuesta de salud mental directa para tu consulta:\n"
            f"- Contexto útil detectado: {contexto}.\n"
            "- Te respondo a la preocupación concreta sin asumir todavía que quieres una rutina psicológica completa.\n"
            "- La prioridad es darte regulación útil ahora y luego, solo si quieres, estructurarlo en plan diario o semanal.\n\n"
            "Si te encaja, después te preparo una rutina psicológica adaptada a tus necesidades."
        )

    accion = _siguiente_accion_autonoma(["general"], _detectar_objetivo_principal(_normalizar_texto(mensaje_usuario)))
    return (
        f"Respuesta directa: {contexto}.\n\n"
        f"Siguiente acción útil: {accion}\n\n"
        "Si quieres, después te lo convierto en plan completo por nutrición, entrenamiento o salud mental."
    )


def _requiere_protocolo_clinico(texto_normalizado: str, trastornos: List[str]) -> bool:
    """Restringe el modo clínico largo a casos realmente clínicos o de riesgo."""
    if not trastornos:
        return False

    claves_explicitamente_clinicas = (
        "triage",
        "diagnostico",
        "medicacion",
        "contraindic",
        "precision maxima",
        "alta precision",
        "trastorno",
        "lesion",
        "dolor agudo",
        "purga",
        "ideas de dano",
        "sincope",
        "mareo",
    )
    if any(clave in texto_normalizado for clave in claves_explicitamente_clinicas):
        return True

    if _solicita_plan_accionable(texto_normalizado):
        return False

    return True


def _protocolo_trastornos_multiambito(
    texto_normalizado: str,
    contexto_adicional: Optional[Dict[str, Any]],
) -> str:
    """Genera respuesta amplia y segura para casos de trastorno/lesion/consulta compleja."""
    grupos = _detectar_trastornos_probables(texto_normalizado)
    contexto = _resumen_contexto(contexto_adicional)
    grupos_texto = ", ".join(grupos) if grupos else "sin clasificacion inicial"

    return (
        "Modo clinico de alta precision activado.\n"
        f"Contexto: {contexto}\n"
        f"Grupos probables detectados: {grupos_texto}.\n\n"
        "Marco de fiabilidad:\n"
        "- Lo confirmado: sintomas y datos que si has mencionado.\n"
        "- Lo probable: hipotesis iniciales a validar.\n"
        "- Lo no confirmado: diagnostico final (requiere profesional).\n\n"
        "Triage por riesgo:\n"
        "1) Riesgo alto: purgas, restriccion severa, ideas de dano, dolor agudo, mareo/sincope.\n"
        "2) Riesgo medio: deterioro funcional, ansiedad alta sostenida, perdida de peso no intencional, dolor recurrente.\n"
        "3) Riesgo bajo: sintomas leves sin impacto funcional mayor.\n\n"
        "Plan inicial por ambito (72h):\n"
        "- Nutricion: estructura regular, proteina por toma, hidratacion, evitar ayunos reactivos.\n"
        "- Psicologia: regulacion breve diaria + registro de disparadores y pensamientos.\n"
        "- Ejercicio: carga conservadora, tecnica limpia, dolor <=3/10, progresion gradual.\n"
        "- Sueno/estres: horario estable y rutina de cierre nocturno.\n\n"
        "Ejercicio adaptado por situacion:\n"
        "- Ansiedad alta: caminar 20-30 min + fuerza basica submaxima.\n"
        "- Fatiga/sueno pobre: movilidad + fuerza ligera, evitar alta intensidad.\n"
        "- Dolor/lesion: trabajo sin dolor agudo, rango tolerable y supervision profesional si persiste.\n"
        "- Objetivo de composicion corporal: combinar fuerza + pasos diarios + adherencia nutricional.\n\n"
        "Preguntas clinicas clave para precision maxima:\n"
        "1) Diagnostico previo confirmado (si existe) y medicacion actual.\n"
        "2) Intensidad de sintomas (0-10), frecuencia y desde cuando.\n"
        "3) Restricciones medicas, lesiones y contraindicaciones.\n"
        "4) Objetivo principal y tiempo real disponible por dia.\n"
        "5) Senales de alarma recientes (mareo, purga, dolor fuerte, ideas de dano).\n"
    )


def _respuesta_experta_base(
    mensaje_usuario: str,
    contexto_adicional: Optional[Dict[str, Any]],
) -> str:
    """Respuesta experta concisa adaptada al rol y al dominio detectado."""
    texto = _normalizar_texto(mensaje_usuario)
    dominios = _detectar_dominios(texto)
    objetivo = _detectar_objetivo_principal(texto)
    escenarios = _detectar_escenarios(texto)
    rol = _rol_especialista(contexto_adicional)
    trastornos_probables = _detectar_trastornos_probables(texto)

    dominio_forzado = _dominio_forzado_por_input_corto(texto, contexto_adicional)
    if dominio_forzado == "visual":
        return (
            "Perfecto, análisis visual activado.\n"
            "Adjunta imagen, vídeo o PDF y te doy feedback técnico directo."
        )
    if dominio_forzado and dominio_forzado not in dominios:
        dominios.insert(0, dominio_forzado)

    if "integral" in texto and any(k in texto for k in ("porque", "por que")):
        return (
            "Integral significa que el plan no separa áreas: une comida, entreno y regulación emocional para que no se contradigan.\n"
            "Si quieres, ahora mismo te lo convierto en: 1) solo nutrición, 2) solo entreno, 3) solo salud mental."
        )

    if trastornos_probables:
        return _protocolo_trastornos_multiambito(texto, contexto_adicional)

    # Para profesionales: respuesta clínica concisa
    if rol in ("nutricionista", "psicologo", "coach", "medico"):
        return (
            f"{_enfoque_por_rol(rol)}\n\n"
            f"{_workflow_operativo_por_rol(rol)}\n"
            f"Objetivo detectado: {objetivo}. Dominios: {', '.join(dominios) if dominios else 'general'}.\n"
            f"{_resumen_contexto(contexto_adicional)}"
        )

    # Para pacientes: plan accionable directo según dominio
    dominio_principal = dominios[0] if dominios else "general"

    # PLAN INTEGRAL: si el usuario pide 2 o más áreas a la vez
    if _es_solicitud_integral(dominios, texto):
        return _plan_integral_preciso(objetivo, contexto_adicional, escenarios, texto_usuario=mensaje_usuario)

    if dominio_principal in {"nutricion", "entrenamiento", "salud_mental"}:
        return _respuesta_orientativa_por_dominio(dominio_principal, mensaje_usuario, contexto_adicional)

    # Fallback general: resumen conciso + acción inmediata
    accion = _siguiente_accion_autonoma(dominios or ["general"], objetivo)
    return (
        f"Diagnóstico rápido: objetivo {objetivo}.\n"
        f"{_resumen_contexto(contexto_adicional)}\n\n"
        f"Acción inmediata: {accion}\n\n"
        "Dime qué necesitas exactamente (dieta, rutina, regulación emocional o análisis de imagen) y lo resuelvo ahora."
    )


def _rol_especialista(contexto_adicional: Optional[Dict[str, Any]]) -> str:
    """Obtiene rol para adaptar el lenguaje avanzado por especialidad."""
    if not contexto_adicional:
        return "cliente"
    rol = str(contexto_adicional.get("usuario_rol") or "cliente").strip().lower()
    return rol or "cliente"


def _enfoque_por_rol(rol: str) -> str:
    """Define enfoque experto por rol para respuestas de mayor nivel."""
    if rol == "nutricionista":
        return "Enfoque nutricion clinica: adherencia, seguridad alimentaria, macros y derivacion por riesgo."
    if rol == "psicologo":
        return "Enfoque psicologico clinico: regulacion emocional, riesgo, funcionalidad y coordinacion interdisciplinar."
    if rol == "coach":
        return "Enfoque de entrenamiento: progresion de carga, fatiga, recuperacion y adherencia sostenible."
    if rol == "medico":
        return "Enfoque medico: seguridad clinica, criterios de alerta, farmacoterapia y escalado."
    if rol == "administrador":
        return "Enfoque coordinacion clinica: priorizacion de casos, trazabilidad y consistencia entre especialistas."
    return "Enfoque paciente: accion practica, claridad y seguimiento semanal medible."


def _funcionalidades_por_rol(rol: str) -> str:
    """Lista capacidades avanzadas que la IA ofrece segun rol profesional."""
    if rol == "nutricionista":
        return (
            "Funcionalidades IA (nutricionista):\n"
            "- Plan nutricional por objetivo y fase.\n"
            "- Ajuste de macros/kcal por adherencia y respuesta semanal.\n"
            "- Version alergias/celiaquia con control anti-trazas.\n"
            "- Menu A/B/C para continuidad en contexto real.\n"
            "- Criterios de derivacion a psicologia/medicina por riesgo.\n"
        )
    if rol == "psicologo":
        return (
            "Funcionalidades IA (psicologo):\n"
            "- Analisis funcional de disparadores y mantenimiento del problema.\n"
            "- Protocolo de regulacion emocional por intensidad.\n"
            "- Plan semanal de activacion/exposicion/higiene de sueno.\n"
            "- Guion de sesion y tareas entre sesiones.\n"
            "- Criterios de escalado por riesgo clinico.\n"
        )
    if rol == "coach":
        return (
            "Funcionalidades IA (coach):\n"
            "- Periodizacion por bloques con progresion y descarga.\n"
            "- Ajuste de carga por sueno/estres/fatiga.\n"
            "- Alternativa de sesion para turnos y poco tiempo.\n"
            "- Prevencion de lesion y control de tecnica.\n"
            "- Coordinacion con nutricion/psicologia en adherencia.\n"
        )
    if rol == "medico":
        return (
            "Funcionalidades IA (medico):\n"
            "- Triage de riesgo y red flags clinicos.\n"
            "- Plan de seguridad y seguimiento por severidad.\n"
            "- Revision de interacciones generales y adherencia terapeutica.\n"
            "- Criterios de derivacion urgente.\n"
            "- Resumen clinico integrado para coordinacion.\n"
        )
    if rol == "administrador":
        return (
            "Funcionalidades IA (administrador):\n"
            "- Priorizacion de casos por riesgo y demora.\n"
            "- Matriz de coordinacion entre especialistas.\n"
            "- Trazabilidad de decisiones y alertas operativas.\n"
            "- Deteccion de cuellos de botella del circuito clinico.\n"
            "- Resumen ejecutivo semanal de operativa.\n"
        )
    return (
        "Funcionalidades IA (paciente):\n"
        "- Plan personal por objetivo y contexto real.\n"
        "- Ajustes por sueno/estres/tiempo disponible.\n"
        "- Plan A/B/C para no abandonar el proceso.\n"
        "- Seguimiento semanal con metricas accionables.\n"
        "- Sugerencia de derivacion por senales de riesgo.\n"
    )


def _workflow_operativo_por_rol(rol: str) -> str:
    """Secuencia operativa inmediata para aumentar utilidad por especialidad."""
    if rol == "nutricionista":
        return (
            "Workflow operativo (nutricionista):\n"
            "1) Definir objetivo metabolico y adherencia base.\n"
            "2) Prescribir estructura + macros iniciales.\n"
            "3) Revaluar semanal y ajustar.\n"
        )
    if rol == "psicologo":
        return (
            "Workflow operativo (psicologo):\n"
            "1) Medir intensidad de malestar y funcionalidad.\n"
            "2) Ejecutar tecnica regulatoria + tarea concreta.\n"
            "3) Revisar riesgo y decidir escalado.\n"
        )
    if rol == "coach":
        return (
            "Workflow operativo (coach):\n"
            "1) Ajustar carga por recuperacion actual.\n"
            "2) Ejecutar sesion principal + alternativa corta.\n"
            "3) Registrar progreso/fatiga para proxima semana.\n"
        )
    if rol == "medico":
        return (
            "Workflow operativo (medico):\n"
            "1) Triage de riesgo clinico.\n"
            "2) Definir plan de seguridad y seguimiento.\n"
            "3) Coordinar indicaciones con equipo interdisciplinar.\n"
        )
    if rol == "administrador":
        return (
            "Workflow operativo (administrador):\n"
            "1) Priorizar casos por impacto y espera.\n"
            "2) Asignar responsables y tiempos.\n"
            "3) Auditar cumplimiento y desbloquear cuellos de botella.\n"
        )
    return (
        "Workflow operativo (paciente):\n"
        "1) Definir objetivo semanal realista.\n"
        "2) Ejecutar plan minimo viable diario.\n"
        "3) Revisar metricas y pedir ajuste.\n"
    )


def _detectar_escenarios(texto_normalizado: str) -> List[str]:
    """Detecta escenarios de vida real para adaptar recomendaciones."""
    escenarios: List[str] = []
    if any(k in texto_normalizado for k in ("turno", "turnos", "nocturno", "horario")):
        escenarios.append("trabajo_por_turnos")
    if any(k in texto_normalizado for k in ("poco tiempo", "sin tiempo", "agenda", "justo de tiempo", "20 min", "20 minutos", "15 min", "15 minutos", "30 min", "30 minutos")):
        escenarios.append("tiempo_limitado")
    if any(k in texto_normalizado for k in ("familia", "hijos", "pareja", "casa")):
        escenarios.append("carga_familiar")
    if any(k in texto_normalizado for k in ("presupuesto", "dinero", "ahorro", "barato")):
        escenarios.append("presupuesto_ajustado")
    if any(k in texto_normalizado for k in ("viaje", "viajar", "hotel", "fuera de casa")):
        escenarios.append("viajes")
    return escenarios


def _adaptaciones_por_escenario(escenarios: List[str]) -> str:
    """Entrega adaptaciones concretas segun escenarios detectados."""
    if not escenarios:
        return "- Escenario estandar: mantener estructura base con revision semanal."

    lineas: List[str] = []
    for escenario in escenarios:
        if escenario == "trabajo_por_turnos":
            lineas.append("- Turnos: distribuir comidas y sueno por bloques, no por horas fijas.")
        elif escenario == "tiempo_limitado":
            lineas.append("- Tiempo limitado: protocolo 20-30 minutos y menu de 3 preparaciones base.")
        elif escenario == "carga_familiar":
            lineas.append("- Carga familiar: plan minimo viable con acciones cortas y delegables.")
        elif escenario == "presupuesto_ajustado":
            lineas.append("- Presupuesto: cesta base de bajo coste con alta densidad nutricional.")
        elif escenario == "viajes":
            lineas.append("- Viajes: reglas de decision para restaurante, aeropuerto y hotel.")

    return "\n".join(lineas)


def _plan_semanal_detallado(objetivo: str, escenarios: List[str]) -> str:
    """Genera plan semanal de ejecucion para respuestas de nivel experto."""
    foco = {
        "ganancia_muscular": "priorizar superavit suave y progresion de fuerza",
        "perdida_grasa": "priorizar deficit sostenible y alta adherencia",
        "bienestar_mental": "priorizar regulacion emocional y estabilidad conductual",
        "rendimiento_global": "priorizar energia estable y recuperacion",
        "adherencia_sostenible": "priorizar constancia y bajo desgaste mental",
    }.get(objetivo, "priorizar constancia clinicamente segura")

    return (
        "Ejecucion semanal detallada:\n"
        f"- Foco de la semana: {foco}.\n"
        "- Lunes: planificacion semanal + compras + sesiones clave.\n"
        "- Martes: bloque principal de ejecucion (nutricion/entreno/salud mental).\n"
        "- Miercoles: ajuste por energia, sueno y carga laboral/familiar.\n"
        "- Jueves: segunda fase de progresion y chequeo de adherencia.\n"
        "- Viernes: consolidacion y preparacion de fin de semana.\n"
        "- Sabado: version flexible sin perder estructura minima.\n"
        "- Domingo: revision de metricas y replan de la semana siguiente.\n"
        "Adaptaciones por escenario:\n"
        f"{_adaptaciones_por_escenario(escenarios)}"
    )


def _normalizar_texto(texto: str) -> str:
    """Pasa texto a minusculas y sin acentos para detectar riesgos con consistencia."""
    texto_min = texto.lower().strip()
    texto_sin_acentos = "".join(
        ch for ch in unicodedata.normalize("NFKD", texto_min) if not unicodedata.combining(ch)
    )
    return " ".join(texto_sin_acentos.split())


def _texto_usuario_para_alerta(mensaje_usuario: str) -> str:
    """Usa solo la consulta del usuario para alerta de riesgo, no el texto técnico inyectado."""
    marcador = "[TEXTO EXTRAIDO AUTOMATICAMENTE DE PDF ADJUNTO]"
    if marcador in (mensaje_usuario or ""):
        limpio, _, _ = (mensaje_usuario or "").partition(marcador)
        return limpio.strip()
    return (mensaje_usuario or "").strip()


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
    """Prepara partes multimodales para envio de fotos o video a Gemini."""
    partes: List[Dict[str, Any]] = []

    for imagen in imagenes or []:
        if not isinstance(imagen, dict):
            continue

        data = imagen.get("data")
        mime_type = str(imagen.get("mime_type") or imagen.get("mimeType") or "image/jpeg").strip().lower()
        if not (
            mime_type.startswith("image/")
            or mime_type.startswith("video/")
            or mime_type == "application/pdf"
        ):
            continue

        # Formato esperado para Gemini: {"mime_type": "image/jpeg", "data": bytes}
        if data:
            partes.append({"mime_type": mime_type, "data": data})

    return partes


def _generation_config() -> Dict[str, Any]:
    """Centraliza parametros de generacion para mantener calidad de salida consistente."""
    try:
        temperatura = float(settings.GEMINI_TEMPERATURE)
    except Exception:
        temperatura = 0.3
    temperatura = max(0.0, min(1.0, temperatura))

    try:
        max_tokens = int(settings.GEMINI_MAX_OUTPUT_TOKENS)
    except Exception:
        max_tokens = 1800
    max_tokens = max(256, min(8192, max_tokens))

    return {
        "temperature": temperatura,
        "top_p": 0.9,
        "max_output_tokens": max_tokens,
    }


def detectar_alerta_riesgo(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """Detecta riesgo por mensaje actual para evitar falsos positivos por historial antiguo."""
    _ = historial_chat  # Se mantiene firma para compatibilidad.
    texto_actual = _normalizar_texto(_texto_usuario_para_alerta(mensaje_usuario))
    return any(palabra in texto_actual for palabra in PALABRAS_RIESGO)


def _obtener_api_key() -> str:
    """Prioriza Settings y fallback a variable de entorno directa."""
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("No se encontro GEMINI_API_KEY en el entorno")
    return api_key


def _proveedor_ia_actual(provider_override: Optional[str] = None) -> str:
    """Devuelve el proveedor configurado para la IA principal."""
    proveedor = (provider_override or settings.IA_PROVIDER or "gemini").strip().lower()
    proveedor = proveedor or "gemini"
    aliases = {
        "qwen3": "qwen",
        "ollama": "qwen",
        "openai-compatible": "qwen",
    }
    proveedor = aliases.get(proveedor, proveedor)
    if proveedor not in {"gemini", "qwen"}:
        return "gemini"
    return proveedor


def _tiene_video_adjuntos(imagenes: Optional[List[Dict[str, Any]]]) -> bool:
    """Detecta si algun adjunto es video y requiere soporte multimodal real."""
    for imagen in imagenes or []:
        if not isinstance(imagen, dict):
            continue
        mime_type = str(imagen.get("mime_type") or imagen.get("mimeType") or "").lower()
        if mime_type.startswith("video/"):
            return True
    return False


def _configuracion_qwen() -> Dict[str, str]:
    """Obtiene la configuracion necesaria para hablar con un backend OpenAI-compatible."""
    api_key = settings.QWEN_API_KEY or os.getenv("QWEN_API_KEY", "")
    base_url = (settings.QWEN_BASE_URL or os.getenv("QWEN_BASE_URL", "")).rstrip("/")
    model = settings.QWEN_MODEL or os.getenv("QWEN_MODEL", "qwen3-32b-instruct")
    base_url_norm = base_url.lower()
    es_backend_local = any(
        host in base_url_norm
        for host in (
            "http://localhost",
            "http://127.0.0.1",
            "http://host.docker.internal",
        )
    )

    if not api_key and not es_backend_local:
        raise RuntimeError("No se encontro QWEN_API_KEY en el entorno")
    if not base_url:
        raise RuntimeError("No se encontro QWEN_BASE_URL en el entorno")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def _convertir_imagenes_a_partes_openai(
    imagenes: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Convierte adjuntos binarios en partes image_url para APIs OpenAI-compatible."""
    partes: List[Dict[str, Any]] = []
    for imagen in imagenes or []:
        if not isinstance(imagen, dict):
            continue

        mime_type = str(imagen.get("mime_type") or imagen.get("mimeType") or "image/jpeg")
        data = imagen.get("data")
        if not data or mime_type.startswith("video/"):
            continue

        if isinstance(data, bytes):
            data_bytes = data
        elif isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            continue

        data_url = f"data:{mime_type};base64,{base64.b64encode(data_bytes).decode('ascii')}"
        partes.append(
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            }
        )

    return partes


def _construir_mensajes_qwen(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]],
    imagenes: Optional[List[Dict[str, Any]]],
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Construye mensajes compatibles con chat/completions para Qwen/OpenAI-compatible."""
    mensajes: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if contexto_adicional:
        contexto_serializado = []
        for clave, valor in contexto_adicional.items():
            if valor is None:
                continue
            contexto_serializado.append(f"- {clave}: {valor}")
        if contexto_serializado:
            mensajes.append(
                {
                    "role": "user",
                    "content": "Contexto del usuario para personalizar respuesta:\n"
                    + "\n".join(contexto_serializado),
                }
            )

    for item in historial_chat or []:
        if not isinstance(item, dict):
            continue

        rol = item.get("rol") or item.get("role") or "user"
        texto = _extraer_texto_historial(item)
        if not texto:
            continue

        mensajes.append({"role": _mapear_rol(str(rol)), "content": texto})

    contenido_usuario: List[Dict[str, Any]] = [{"type": "text", "text": mensaje_usuario}]
    contenido_usuario.extend(_convertir_imagenes_a_partes_openai(imagenes))
    if len(contenido_usuario) == 1:
        mensajes.append({"role": "user", "content": mensaje_usuario})
    else:
        mensajes.append({"role": "user", "content": contenido_usuario})

    return mensajes


def _consultar_qwen(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
    imagenes: Optional[List[Dict[str, Any]]] = None,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    alerta_riesgo: bool = False,
    etiqueta_alerta: Optional[str] = None,
    tiene_multimedia: bool = False,
    model_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Consulta un modelo Qwen mediante API OpenAI-compatible."""
    config = _configuracion_qwen()

    if imagenes and _tiene_video_adjuntos(imagenes) and not settings.QWEN_SUPPORTS_MULTIMODAL:
        if settings.GEMINI_API_KEY:
            return _consultar_gemini(
                mensaje_usuario=mensaje_usuario,
                historial_chat=historial_chat,
                imagenes=imagenes,
                contexto_adicional=contexto_adicional,
                alerta_riesgo=alerta_riesgo,
                etiqueta_alerta=etiqueta_alerta,
                tiene_multimedia=tiene_multimedia,
            )
        raise RuntimeError(
            "El proveedor Qwen configurado no admite video multimodal. "
            "Activa QWEN_SUPPORTS_MULTIMODAL o usa Gemini para analisis visual."
        )

    mensajes = _construir_mensajes_qwen(
        mensaje_usuario=mensaje_usuario,
        historial_chat=historial_chat,
        imagenes=imagenes if settings.QWEN_SUPPORTS_MULTIMODAL else None,
        contexto_adicional=contexto_adicional,
    )

    generation_cfg = _generation_config()
    payload = {
        "model": (model_override or config["model"]).strip(),
        "messages": mensajes,
        "temperature": generation_cfg["temperature"],
        "max_tokens": generation_cfg["max_output_tokens"],
    }

    headers = {
        "Content-Type": "application/json",
    }
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"

    respuesta = httpx.post(
        f"{config['base_url']}/chat/completions",
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    respuesta.raise_for_status()

    data = respuesta.json()
    choices = data.get("choices") or []
    contenido = ""
    if choices:
        message = choices[0].get("message") or {}
        contenido = (message.get("content") or "").strip()

    if not contenido:
        contenido = "No he podido generar una respuesta en este momento."

    return {
        "respuesta": contenido,
        "etiqueta_alerta": etiqueta_alerta,
        "alerta_riesgo": alerta_riesgo,
        "modelo": (model_override or config["model"]).strip(),
        "origen": "qwen",
    }


def _consultar_gemini(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
    imagenes: Optional[List[Dict[str, Any]]] = None,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    alerta_riesgo: bool = False,
    etiqueta_alerta: Optional[str] = None,
    tiene_multimedia: bool = False,
    model_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Consulta Gemini con contexto conversacional y deteccion de alerta de riesgo."""
    contenido = _construir_contenido(
        mensaje_usuario,
        historial_chat,
        imagenes,
        contexto_adicional,
    )

    api_key = _obtener_api_key()
    genai.configure(api_key=api_key)

    model_name = (model_override or settings.GEMINI_MODEL).strip()
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT,
    )

    respuesta = model.generate_content(
        contenido,
        generation_config=_generation_config(),
    )
    texto_respuesta = (getattr(respuesta, "text", "") or "").strip()

    if not texto_respuesta:
        texto_respuesta = "No he podido generar una respuesta en este momento."

    return {
        "respuesta": texto_respuesta,
        "etiqueta_alerta": etiqueta_alerta,
        "alerta_riesgo": alerta_riesgo,
        "modelo": model_name,
        "origen": "gemini",
    }


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


def _extraer_texto_pdf_inyectado(mensaje_usuario: str) -> str:
    """Recupera el texto de PDF que main.py ya inyecta en el mensaje antes del fallback."""
    marcador = "[TEXTO EXTRAIDO AUTOMATICAMENTE DE PDF ADJUNTO]"
    if marcador not in (mensaje_usuario or ""):
        return ""
    _, _, resto = mensaje_usuario.partition(marcador)
    return resto.strip()


def _mensaje_sin_bloque_pdf(mensaje_usuario: str) -> str:
    """Elimina el bloque técnico de texto PDF para quedarnos con la consulta original."""
    marcador = "[TEXTO EXTRAIDO AUTOMATICAMENTE DE PDF ADJUNTO]"
    if marcador not in (mensaje_usuario or ""):
        return (mensaje_usuario or "").strip()
    limpio, _, _ = mensaje_usuario.partition(marcador)
    return limpio.strip()


def _resumen_texto_plano(texto: str, max_fragmentos: int = 3, max_chars: int = 520) -> str:
    """Genera un resumen corto y estable a partir de texto plano ya extraído."""
    fragmentos: List[str] = []
    acumulado = 0

    candidatos = [
        linea.strip(" -•\t")
        for linea in re.split(r"[\n\r]+", texto or "")
        if linea and linea.strip()
    ]
    if not candidatos:
        candidatos = [
            frag.strip()
            for frag in re.split(r"(?<=[\.!?])\s+", texto or "")
            if frag and frag.strip()
        ]

    for candidato in candidatos:
        if len(candidato) < 20:
            continue
        if candidato.lower().startswith("pagina "):
            continue
        disponible = max_chars - acumulado
        if disponible <= 0:
            break
        recorte = candidato[:disponible].strip()
        if len(recorte) < 20:
            continue
        fragmentos.append(recorte)
        acumulado += len(recorte)
        if len(fragmentos) >= max_fragmentos:
            break

    return "\n".join(f"- {frag}" for frag in fragmentos)


def _consulta_pide_leer_contenido(mensaje_usuario: str) -> bool:
    """Detecta si el usuario quiere leer/extraer contenido del adjunto."""
    texto = _normalizar_texto((mensaje_usuario or "").strip())
    if not texto:
        return False
    return any(
        clave in texto
        for clave in (
            "que hay",
            "que pone",
            "que dice",
            "leer",
            "lee",
            "texto",
            "contenido",
            "analiza",
            "adjunto",
            "imagen",
            "captura",
        )
    )


def _clasificar_documento_general(texto: str) -> str:
    """Clasifica el tipo de documento de forma simple para respuestas genéricas."""
    t = _normalizar_texto(texto)
    reglas = (
        ("documento de contratacion", ("contrato", "contratacion", "arrendamiento", "firmante", "clausula", "vigencia")),
        ("documento de anulación o cancelación", ("anulacion", "cancelacion", "revocacion", "rescision", "deja sin efecto")),
        ("documento administrativo", ("solicitud", "expediente", "resolucion", "administracion", "tramite")),
        ("factura o documento de cobro", ("factura", "iva", "subtotal", "total", "base imponible")),
        ("rutina de entrenamiento", ("series", "repeticiones", "entrenamiento", "rutina", "descanso", "ejercicio")),
        ("plan nutricional", ("calorias", "proteinas", "hidratos", "grasas", "menu", "comida")),
    )
    for etiqueta, claves in reglas:
        if any(clave in t for clave in claves):
            return etiqueta
    return "documento general"


def _analisis_documental_generico(texto: str, consulta: str, origen: str) -> str:
    """Devuelve un análisis neutro para cualquier documento, sea o no de salud."""
    tipo = _clasificar_documento_general(texto)
    resumen = _resumen_texto_plano(texto, max_fragmentos=4, max_chars=700)
    titulo = "He leído el PDF adjunto." if origen == "pdf" else "He leído el texto de la imagen adjunta."
    consulta_norm = _normalizar_texto(consulta)

    if not resumen:
        return (
            f"{titulo} Parece un {tipo}, pero no he podido extraer fragmentos suficientes para resumirlo mejor. "
            "Si quieres, te digo exactamente qué parte revisar si me indicas página o bloque concreto."
        )

    if any(k in consulta_norm for k in ("que es", "de que trata", "analiza", "lee", "resume", "resumen", "que pone", "que dice", "documento")):
        return (
            f"{titulo} Esto parece un {tipo}.\n"
            "Resumen de contenido detectado:\n"
            f"{resumen}\n\n"
            "Si quieres, te lo explico en lenguaje más simple o te extraigo los puntos legales/técnicos clave."
        )

    return (
        f"{titulo} He detectado que es un {tipo}.\n"
        f"Fragmentos clave:\n{resumen}"
    )


def _extraer_texto_ocr_local(data: bytes) -> str:
    """Intenta OCR local de imágenes cuando el proveedor multimodal no está disponible."""
    try:
        pytesseract = importlib.import_module("pytesseract")
    except Exception:
        return ""

    try:
        img = Image.open(BytesIO(bytes(data)))
        img.load()
        if img.mode not in {"RGB", "RGBA", "L"}:
            img = img.convert("RGB")

        base = img.convert("L")
        variantes = [
            base,
            ImageOps.autocontrast(base),
            base.point(lambda px: 255 if px > 165 else 0),
            ImageOps.autocontrast(base).resize((max(1, base.width * 2), max(1, base.height * 2))),
        ]
        configuraciones = (
            "--oem 3 --psm 6",
            "--oem 3 --psm 11",
            "--oem 3 --psm 4",
        )

        mejor_texto = ""
        mejor_puntaje = 0

        for variante in variantes:
            for config in configuraciones:
                try:
                    candidato = pytesseract.image_to_string(variante, lang="spa+eng", config=config)
                except Exception:
                    continue
                candidato_limpio = " ".join((candidato or "").split()).strip()
                if not candidato_limpio:
                    continue
                puntaje = sum(1 for ch in candidato_limpio if ch.isalnum())
                if puntaje > mejor_puntaje:
                    mejor_puntaje = puntaje
                    mejor_texto = candidato_limpio
    except Exception:
        return ""

    return mejor_texto if mejor_puntaje >= 6 else ""


def _respuesta_local_desde_texto_extraido(
    mensaje_usuario: str,
    texto_extraido: str,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
    origen: str = "documento",
) -> str:
    """Reutiliza texto extraído localmente para responder sin depender de visión externa."""
    consulta = _mensaje_sin_bloque_pdf(mensaje_usuario)
    consulta_norm = _normalizar_texto(consulta)
    texto_limpio = " ".join((texto_extraido or "").split()).strip()

    if not texto_limpio:
        if origen == "pdf":
            return (
                "He recibido el PDF, pero no he podido sacar texto legible del archivo. "
                "Si es un PDF escaneado o una foto incrustada, vuelve a enviarlo con más nitidez y lo intento de nuevo."
            )
        return (
            "He recibido la imagen, pero no he podido extraer texto legible en local. "
            "Si es una captura con texto pequeño, envíala con más resolución y la reviso otra vez."
        )

    if any(
        clave in consulta_norm
        for clave in (
            "resume",
            "resumen",
            "que pone",
            "que dice",
            "que hay",
            "leer",
            "lee",
            "contenido",
            "explica",
        )
    ) or len(consulta_norm) < 18:
        return _analisis_documental_generico(texto_limpio, consulta, origen)

    if origen in {"pdf", "imagen"} and any(
        k in consulta_norm
        for k in ("documento", "archivo", "contrato", "anulacion", "cancelacion", "factura", "pdf", "imagen")
    ):
        return _analisis_documental_generico(texto_limpio, consulta, origen)

    prompt_enriquecido = (
        f"{consulta or 'Analiza el contenido adjunto y dime lo importante.'}\n\n"
        f"Contenido extraído del {origen}:\n{texto_limpio[:4000]}"
    )
    respuesta = _respuesta_local_autonoma_gratis(
        mensaje_usuario=prompt_enriquecido,
        contexto_adicional=contexto_adicional,
        historial_chat=historial_chat,
    ).strip()
    prefijo = "He leído el PDF adjunto." if origen == "pdf" else "He leído el texto visible de la imagen adjunta."
    return f"{prefijo}\n{respuesta}" if respuesta else prefijo


def _analisis_visual_local(
    mensaje_usuario: str,
    imagenes: Optional[List[Dict[str, Any]]],
    contexto_adicional: Optional[Dict[str, Any]] = None,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Genera una respuesta local útil cuando no hay visión externa disponible."""
    if not imagenes:
        return (
            "No tengo adjuntos validos para analizar ahora mismo. "
            "Reenvia la imagen/video y dime que quieres evaluar exactamente."
        )

    primer = imagenes[0] if isinstance(imagenes[0], dict) else {}
    mime = str(primer.get("mime_type") or "").strip().lower()
    data = primer.get("data")

    if mime.startswith("video/"):
        return (
            "He recibido un video. En este entorno local no puedo extraer fotogramas automaticamente, "
            "pero si me dices el segundo exacto o el gesto tecnico que quieres revisar, "
            "te doy el checklist de tecnica paso a paso y como corregirlo."
        )

    if mime == "application/pdf":
        return _respuesta_local_desde_texto_extraido(
            mensaje_usuario=mensaje_usuario,
            texto_extraido=_extraer_texto_pdf_inyectado(mensaje_usuario),
            contexto_adicional=contexto_adicional,
            historial_chat=historial_chat,
            origen="pdf",
        )

    if not mime.startswith("image/"):
        return (
            "He recibido un adjunto, pero no parece una imagen compatible para analisis local. "
            "Si lo reenvias como imagen JPG/PNG/WebP, puedo darte una lectura mas util."
        )

    if not isinstance(data, (bytes, bytearray)):
        return (
            "He recibido la imagen pero sin datos binarios legibles para analisis local. "
            "Reenviala y te doy una lectura precisa."
        )

    try:
        img = Image.open(BytesIO(bytes(data)))
        img.load()
        width, height = img.size
        mode = (img.mode or "?").upper()
        texto_ocr = _extraer_texto_ocr_local(bytes(data))

        if len(texto_ocr) >= 8:
            return _respuesta_local_desde_texto_extraido(
                mensaje_usuario=mensaje_usuario,
                texto_extraido=texto_ocr,
                contexto_adicional=contexto_adicional,
                historial_chat=historial_chat,
                origen="imagen",
            )

        if _consulta_pide_leer_contenido(mensaje_usuario):
            return (
                "He recibido la imagen, pero en este intento no he podido leer texto suficiente con OCR local. "
                "Prueba a reenviarla con más contraste (fondo claro, letra más grande) y la analizo de nuevo para decirte exactamente qué pone."
            )

        # Medidas visuales simples y estables para orientar al usuario.
        gray = img.convert("L")
        brillo = float(ImageStat.Stat(gray).mean[0])
        mini = img.convert("RGB").resize((1, 1))
        r, g, b = mini.getpixel((0, 0))

        if width <= 16 and height <= 16:
            return (
                f"Analisis visual local: imagen muy pequena ({width}x{height}, modo {mode}). "
                "No contiene detalle suficiente para identificar objetos o tecnica. "
                "Necesito una imagen mas grande y nitida para decirte exactamente que se ve."
            )

        nivel_luz = "baja" if brillo < 65 else "media" if brillo < 170 else "alta"
        return (
            "Analisis visual local realizado:\n"
            f"- Resolucion: {width}x{height} px\n"
            f"- Formato interno: {mode}\n"
            f"- Iluminacion estimada: {nivel_luz} (brillo medio {brillo:.1f}/255)\n"
            f"- Color dominante aproximado: RGB({r},{g},{b})\n"
            "Con esta lectura base, dime ahora si quieres que evalúe tecnica, comida, postura o riesgo visible, "
            "y te doy una conclusion directa con correcciones concretas."
        )
    except Exception:
        return (
            "No pude decodificar la imagen para analisis local. "
            "Reenviala en JPG o PNG y te devuelvo lectura precisa."
        )


def _respuesta_local_gratis(
    mensaje_usuario: str,
    alerta_riesgo: bool,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    tiene_multimedia: bool = False,
    imagenes: Optional[List[Dict[str, Any]]] = None,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Genera respuesta local estable para no bloquear al usuario cuando falla proveedor externo."""
    if alerta_riesgo:
        return (
            "Gracias por decirlo con claridad. Lo que comentas puede requerir apoyo profesional cuanto antes. "
            "Mientras conectas con ayuda, haz este bloque de seguridad: respiracion 4-4-4 durante 3 minutos, "
            "una comida simple en las proximas 2 horas y aviso hoy a una persona de confianza."
        )

    if tiene_multimedia:
        return _analisis_visual_local(
            mensaje_usuario=mensaje_usuario,
            imagenes=imagenes,
            contexto_adicional=contexto_adicional,
            historial_chat=historial_chat,
        )

    # En fallback local, siempre devolvemos respuesta util y específica.
    return _respuesta_local_autonoma_gratis(
        mensaje_usuario=mensaje_usuario,
        contexto_adicional=contexto_adicional,
        historial_chat=historial_chat,
    )


def obtener_respuesta_local_segura(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
    imagenes: Optional[List[Dict[str, Any]]] = None,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    tiene_multimedia: bool = False,
) -> str:
    """Devuelve una respuesta local útil cuando proveedores externos no están disponibles."""
    alerta_riesgo = detectar_alerta_riesgo(mensaje_usuario, historial_chat)
    return _respuesta_local_gratis(
        mensaje_usuario=mensaje_usuario,
        alerta_riesgo=alerta_riesgo,
        contexto_adicional=contexto_adicional,
        tiene_multimedia=tiene_multimedia or bool(imagenes),
        imagenes=imagenes,
        historial_chat=historial_chat,
    )


def _construir_contenido(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]],
    imagenes: Optional[List[Dict[str, Any]]],
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Construye el payload para Gemini inyectando la ficha clínica 
    como prioridad máxima de procesamiento.
    """
    contenido: List[Dict[str, Any]] = []

    # 1. INYECCIÓN DE FICHA CLÍNICA (Prioridad 1)
    if contexto_adicional:
        # Convertimos el diccionario en una tabla técnica para la IA
        lineas_ficha = [f"[{k.upper()}]: {v}" for k, v in contexto_adicional.items() if v is not None]
        
        if lineas_ficha:
            ficha_clinica = (
                "SISTEMA: CARGA DE FICHA CLÍNICA DEL PACIENTE\n"
                "ATENCIÓN: Los siguientes datos son MANDATORIOS para cualquier cálculo o prescripción:\n"
                + "\n".join(lineas_ficha)
                + "\n\nInstrucción: Cruza estos parámetros con la petición del usuario para garantizar seguridad biológica."
            )
            # Se envía como un mensaje de sistema/usuario inicial para fijar el contexto
            contenido.append({"role": "user", "parts": [ficha_clinica]})
            contenido.append({"role": "model", "parts": ["Ficha clínica cargada y verificada. Analizando métricas para la prescripción..."]})

    # 2. HISTORIAL DE CONVERSACIÓN (Contexto temporal)
    for item in historial_chat or []:
        if not isinstance(item, dict):
            continue

        rol = _mapear_rol(str(item.get("rol") or item.get("role") or "user"))
        texto = _extraer_texto_historial(item)
        if texto:
            contenido.append({"role": rol, "parts": [texto]})

    # 3. MENSAJE ACTUAL + MULTIMEDIA (Input de ejecución)
    # Si hay imágenes/video, Gemini las procesará junto con el texto del usuario
    # IMPORTANTE: Agregamos instrucción explícita de análisis visual si hay imágenes
    partes_mensaje: List[Any] = []
    
    # Si hay imágenes, añadir instrucción de análisis visual primero
    if imagenes:
        # Agregar instrucción de análisis visual ANTES de las imágenes
        instruccion_visual = (
            "ANALIZA VISUALMENTE lo que ves en las imágenes adjuntas. "
            "Describe claramente: tipo de imagen, contenido visible, objetos, texto, gráficos, código, personas, etc. "
            "Luego extrae cualquier OCR si es necesario y proporciona un resumen útil completo."
        )
        partes_mensaje.append(instruccion_visual)
    
    # Agregar el mensaje del usuario
    partes_mensaje.append(mensaje_usuario)
    
    # Agregar las imágenes/multimedia
    partes_mensaje.extend(_preparar_partes_imagenes(imagenes))
    
    contenido.append({"role": "user", "parts": partes_mensaje})

    return contenido


def _validar_respuesta_pertinente(
    respuesta: str,
    mensaje_usuario: str,
    contexto_adicional: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Valida que la respuesta IA sea coherente y pertinente al contexto del usuario.
    
    Retorna dict con:
    - valida: bool
    - puntuacion: 0-100
    - motivos: List[str] = razones de validación o rechazo
    - alerta_incoherencia: bool = si hay contradicción grave
    """
    if contexto_adicional is None:
        return {
            "valida": True,
            "puntuacion": 75,
            "motivos": ["Sin contexto adicional para validar"],
            "alerta_incoherencia": False,
        }

    contexto = contexto_adicional
    respuesta_norm = (respuesta or "").lower().strip()
    mensaje_norm = (mensaje_usuario or "").lower().strip()
    puntuacion = 100
    motivos: List[str] = []
    alerta = False

    # 1. Detección de contradicción peso/objetivo
    if contexto.get("peso_actual_kg") and contexto.get("imc_actual"):
        peso = float(contexto.get("peso_actual_kg", 0))
        imc = float(contexto.get("imc_actual", 0))
        
        # Si el usuario tiene objetivo de "perder peso" pero la respuesta recomienda aumento calórico
        if any(k in mensaje_norm for k in ["bajar peso", "bajar de peso", "perder peso", "perder grasa", "adelgaz"]):
            if any(
                k in respuesta_norm
                for k in ["aumenta calor", "aumentar calor", "come mas", "ganar musculo", "superavit", "superávit"]
            ):
                puntuacion -= 30
                alerta = True
                motivos.append("CONTRADICCIÓN: usuario pide perder peso pero respuesta recomienda aumentar calorías")
        
        # Si el usuario tiene peso bajo (IMC < 18.5) y pide rutina pesada sin proteína
        if imc < 18.5 and any(k in mensaje_norm for k in ["rutina", "entrenamiento", "ejercicio"]):
            if not any(k in respuesta_norm for k in ["proteina", "proteína"]):
                puntuacion -= 15
                motivos.append("ALERTA: usuario con bajo peso solicita entrenamiento pero respuesta no menciona proteína")

    # 2. Detección de contradicción con restricciones/alergias
    restricciones = (contexto.get("memoria_respuestas", {}) or {}).get("restricciones", "") or ""
    if restricciones and restricciones.lower() not in {"no", "ninguna"}:
        restricciones_norm = restricciones.lower()
        # Si el usuario mencionó celiaquía y la respuesta recomienda pan/pasta/gluten
        if "celia" in restricciones_norm and any(k in respuesta_norm for k in ["pan", "pasta", "gluten", "cereales"]):
            puntuacion -= 35
            alerta = True
            motivos.append("CONTRADICCIÓN GRAVE: usuario celíaco pero respuesta incluye gluten")
        # Si mencionó lactosa y la respuesta recomienda productos lácteos sin advertencia
        if "lactosa" in restricciones_norm and any(k in respuesta_norm for k in ["leche", "queso", "yogur", "mantequilla"]):
            if "sin lactosa" not in respuesta_norm and "intolerancia" not in respuesta_norm:
                puntuacion -= 25
                alerta = True
                motivos.append("ALERTA: usuario intolerante a lactosa, respuesta recomienda lácteos sin alternativas")

    # 3. Validación de coherencia con sentimiento/estado reciente
    sentimiento = (contexto.get("sentimiento_reciente") or "").lower()
    if sentimiento in {"triste", "deprimido", "ansiedad", "estres"}:
        # Si el usuario está en ánimo bajo, una respuesta que recomienda ayuno prolongado es incoherente
        if any(k in respuesta_norm for k in ["ayuno", "ayunar", "ayunas", "solo agua", "ayunos intermitentes"]):
            puntuacion -= 35
            alerta = True
            motivos.append("ALERTA: usuario con ánimo bajo recibe recomendación de restricción sin contexto positivo")

    # 4. Revisión de lógica: si la respuesta es demasiado simple para pregunta compleja
    if len(mensaje_norm.split()) > 20 and len(respuesta_norm.split()) < 10:
        puntuacion -= 10
        motivos.append("ALERTA LEVE: respuesta muy breve para pregunta compleja (posible generación incompleta)")

    # 5. Detección de respuesta "plantilla"
    plantillas_detectadas = ["te recomiendo", "suavemente", "tal vez deberías", "si lo deseas", "en mi humilde opinión"]
    if any(p in respuesta_norm for p in plantillas_detectadas):
        puntuacion -= 5
        motivos.append("Detección de lenguaje plantilla (preferimos directo y técnico)")

    # 6. Reglas de salida para modo junta medica (extensión y secciones técnicas).
    if _solicita_junta_medica(mensaje_norm):
        n_palabras = _contar_palabras(respuesta)
        if n_palabras < 800:
            puntuacion -= 35
            alerta = True
            motivos.append("ALERTA: respuesta demasiado corta para modo junta medica (minimo 800 palabras)")

        secciones_clave = ("nutric", "entren", "hpa", "cortisol", "imc")
        if sum(1 for s in secciones_clave if s in respuesta_norm) < 4:
            puntuacion -= 20
            alerta = True
            motivos.append("ALERTA: faltan secciones clinicas clave (nutricion/entrenamiento/HPA/IMC)")

    # 7. Aprobación lógica: si pasa todas las validaciones
    if puntuacion >= 85:
        motivos.append("Respuesta coherente con contexto del usuario")
    
    if not motivos:
        motivos.append("Validación completada sin hallazgos críticos")

    return {
        "valida": puntuacion >= 70,  # Umbral de aprobación
        "puntuacion": max(0, min(100, puntuacion)),
        "motivos": motivos,
        "alerta_incoherencia": alerta,
    }


def consultar_ia(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
    imagenes: Optional[List[Dict[str, Any]]] = None,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    tiene_multimedia: bool = False,
    provider_override: Optional[str] = None,
    model_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Consulta IA con proveedor configurable y deteccion de alerta de riesgo."""
    if not mensaje_usuario or not mensaje_usuario.strip():
        raise ValueError("mensaje_usuario no puede estar vacio")

    alerta_riesgo = detectar_alerta_riesgo(mensaje_usuario, historial_chat)
    etiqueta_alerta = ETIQUETA_ALERTA_RIESGO if alerta_riesgo else None

    # Interceptar derivaciones: respuesta breve local sin llamar al proveedor de IA
    _texto_norm_ia = _normalizar_texto(mensaje_usuario)
    _esp_derivacion = _es_solicitud_derivacion(_texto_norm_ia)
    if _esp_derivacion:
        return {
            "respuesta": _respuesta_derivacion_breve(_esp_derivacion, contexto_adicional),
            "etiqueta_alerta": None,
            "alerta_riesgo": False,
            "modelo": "local_derivacion",
            "origen": "local",
        }

    def _aplicar_validacion(resultado: Dict[str, Any]) -> Dict[str, Any]:
        """Envuelve un resultado con validación de pertinencia."""
        respuesta = resultado.get("respuesta", "")
        validacion = _validar_respuesta_pertinente(
            respuesta,
            mensaje_usuario,
            contexto_adicional=contexto_adicional,
        )
        # Añade info de validación al resultado sin romper la estructura
        resultado["validacion_pertinencia"] = validacion
        if validacion["alerta_incoherencia"]:
            resultado["nota_validacion"] = "ALERTA: Posible incoherencia con contexto del usuario"

        # Auto-reparación: si es petición de junta médica y la salida no cumple, forzar salida clínica local extensa.
        if _solicita_junta_medica(_normalizar_texto(mensaje_usuario)) and not validacion["valida"]:
            resultado["respuesta"] = _respuesta_junta_medica_extensa(
                mensaje_usuario=mensaje_usuario,
                contexto_adicional=contexto_adicional,
            )
            resultado["modelo"] = "fallback_local_junta_medica"
            resultado["origen"] = "fallback_local"
            resultado["validacion_pertinencia"] = {
                "valida": True,
                "puntuacion": 90,
                "motivos": ["Auto-reparacion aplicada: salida clinica extensa en modo junta medica"],
                "alerta_incoherencia": False,
            }
        return resultado

    # En testing mode intentamos IA real si hay credenciales configuradas; si falla,
    # entramos a fallback local fiable para no romper UX.
    if settings.IA_TESTING_MODE:
        proveedor_testing = _proveedor_ia_actual(provider_override)
        try:
            if proveedor_testing == "qwen" and settings.QWEN_API_KEY and settings.QWEN_BASE_URL:
                resultado = _consultar_qwen(
                    mensaje_usuario=mensaje_usuario,
                    historial_chat=historial_chat,
                    imagenes=imagenes,
                    contexto_adicional=contexto_adicional,
                    alerta_riesgo=alerta_riesgo,
                    etiqueta_alerta=etiqueta_alerta,
                    tiene_multimedia=tiene_multimedia,
                    model_override=model_override,
                )
                return _aplicar_validacion(resultado)

            if settings.GEMINI_API_KEY:
                resultado = _consultar_gemini(
                    mensaje_usuario=mensaje_usuario,
                    historial_chat=historial_chat,
                    imagenes=imagenes,
                    contexto_adicional=contexto_adicional,
                    alerta_riesgo=alerta_riesgo,
                    etiqueta_alerta=etiqueta_alerta,
                    tiene_multimedia=tiene_multimedia,
                    model_override=model_override,
                )
                return _aplicar_validacion(resultado)
        except Exception as e:
            if not settings.IA_FALLBACK_LOCAL:
                raise

            return {
                "respuesta": _respuesta_local_gratis(
                    mensaje_usuario,
                    alerta_riesgo,
                    contexto_adicional=contexto_adicional,
                    tiene_multimedia=tiene_multimedia or bool(imagenes),
                    imagenes=imagenes,
                    historial_chat=historial_chat,
                ),
                "etiqueta_alerta": etiqueta_alerta,
                "alerta_riesgo": alerta_riesgo,
                "modelo": "fallback_local",
                "origen": "fallback_local",
                "motivo_fallback": e.__class__.__name__,
            }

        return {
            "respuesta": _respuesta_local_gratis(
                mensaje_usuario,
                alerta_riesgo,
                contexto_adicional=contexto_adicional,
                tiene_multimedia=tiene_multimedia or bool(imagenes),
                imagenes=imagenes,
                historial_chat=historial_chat,
            ),
            "etiqueta_alerta": etiqueta_alerta,
            "alerta_riesgo": alerta_riesgo,
            "modelo": "fallback_local",
            "origen": "fallback_local",
            "motivo_fallback": "testing_mode_without_provider_credentials",
        }

    proveedor = _proveedor_ia_actual(provider_override)

    # Qwen3 es excelente para texto; si el mensaje trae multimedia y el modelo
    # configurado no la soporta, usamos Gemini como ruta visual.
    if proveedor == "qwen":
        try:
            if imagenes and (tiene_multimedia or _tiene_video_adjuntos(imagenes)) and not settings.QWEN_SUPPORTS_MULTIMODAL:
                if settings.GEMINI_API_KEY:
                    resultado = _consultar_gemini(
                        mensaje_usuario=mensaje_usuario,
                        historial_chat=historial_chat,
                        imagenes=imagenes,
                        contexto_adicional=contexto_adicional,
                        alerta_riesgo=alerta_riesgo,
                        etiqueta_alerta=etiqueta_alerta,
                        tiene_multimedia=tiene_multimedia,
                        model_override=model_override,
                    )
                    return _aplicar_validacion(resultado)

            resultado = _consultar_qwen(
                mensaje_usuario=mensaje_usuario,
                historial_chat=historial_chat,
                imagenes=imagenes,
                contexto_adicional=contexto_adicional,
                alerta_riesgo=alerta_riesgo,
                etiqueta_alerta=etiqueta_alerta,
                tiene_multimedia=tiene_multimedia,
                model_override=model_override,
            )
            return _aplicar_validacion(resultado)
        except Exception as e:
            if not settings.IA_FALLBACK_LOCAL:
                raise

            return {
                "respuesta": _respuesta_local_gratis(
                    mensaje_usuario,
                    alerta_riesgo,
                    contexto_adicional=contexto_adicional,
                    tiene_multimedia=tiene_multimedia or bool(imagenes),
                    imagenes=imagenes,
                    historial_chat=historial_chat,
                ),
                "etiqueta_alerta": etiqueta_alerta,
                "alerta_riesgo": alerta_riesgo,
                "modelo": "fallback_local",
                "origen": "fallback_local",
                "motivo_fallback": e.__class__.__name__,
            }

    try:
        resultado = _consultar_gemini(
            mensaje_usuario=mensaje_usuario,
            historial_chat=historial_chat,
            imagenes=imagenes,
            contexto_adicional=contexto_adicional,
            alerta_riesgo=alerta_riesgo,
            etiqueta_alerta=etiqueta_alerta,
            tiene_multimedia=tiene_multimedia,
            model_override=model_override,
        )
        return _aplicar_validacion(resultado)
    except Exception as e:
        if not settings.IA_FALLBACK_LOCAL:
            raise

        return {
            "respuesta": _respuesta_local_gratis(
                mensaje_usuario,
                alerta_riesgo,
                contexto_adicional=contexto_adicional,
                tiene_multimedia=tiene_multimedia or bool(imagenes),
                imagenes=imagenes,
                historial_chat=historial_chat,
            ),
            "etiqueta_alerta": etiqueta_alerta,
            "alerta_riesgo": alerta_riesgo,
            "modelo": "fallback_local",
            "origen": "fallback_local",
            "motivo_fallback": e.__class__.__name__,
        }

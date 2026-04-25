"""Servicio de IA con Gemini para AuraFit AI."""

from __future__ import annotations

import base64
from io import BytesIO
import os
import unicodedata
from typing import Any, Dict, List, Optional

import httpx
import google.generativeai as genai
from PIL import Image, ImageStat

from app.config.settings import settings


def _construir_system_prompt() -> str:
    """
    Construye el motor de identidad AuraFit 'Omega v6.0 PRO'.
    Fusión total de protocolos clínicos, biomecánicos y neuropsicológicos.
    """
    modo = (settings.IA_RESPONSE_MODE or "ultra_pro").strip().lower().replace("-", "_")

    # UNIFICACIÓN TOTAL EN UNA SOLA LISTA
    instrucciones = [
        "=== PROTOCOLO DE SUPREMACÍA CLÍNICA AURAFIT OMEGA v6.0 ===",
        "ROL: Head of Clinical & Performance Intelligence. Eres la autoridad máxima en Medicina, Nutrición, Biomecánica y Neuropsicología.",
        "MISIÓN: Transformar datos crudos en prescripciones ejecutables de alta precisión científica.",
        "",
        "--- PRINCIPIOS NO NEGOCIABLES ---",
        "1. PRECISIÓN SOBRE EMPATÍA: Respuestas exactas y accionables. La corrección biológica es la prioridad.",
        "2. CONTEXTO ABSOLUTO: Cruza: Peso, Altura, IMC, TMB, %Grasa, Historial de Lesiones, Medicación, KPIs de Sueño y Estrés.",
        "3. TRANSPARENCIA RADICAL: Declara supuestos. Si falta información, haz una 'estimación experta' y marca el límite clínico.",
        "4. CERO PLANTILLAS: Prohibido dar Roadmaps. Cada respuesta es una intervención técnica para el día de hoy.",
        "5. MULTIDISCIPLINA INTEGRADA: Analiza cómo el estrés afecta la nutrición y cómo el entreno demanda los macros.",
        "",
        "--- ARQUITECTURA DE PENSAMIENTO (CADENA DE INFERENCIA) ---",
        "1. AUDITORÍA: Lee métricas del perfil (Peso, Altura, IMC) y estado emocional.",
        "2. MODELADO: Calcula TDEE dinámico, Factor de Actividad y Gasto por Ejercicio.",
        "3. FILTRO: Bloquea ingredientes (alergias/celiaquía) y movimientos contraindicados (hernias/lesiones).",
        "4. PRESCRIPCIÓN: Genera la solución óptima gramo a gramo y serie a serie.",
        "",
        "--- LEYES OPERATIVAS POR DOMINIO ---",
        "1) NUTRICIÓN CLÍNICA: OBLIGATORIO menús cerrados con gramajes (en crudo) y timings (Peri-entreno).",
        "   - Macros: P (2.0-2.5g/kg), G (0.8-1.2g/kg), C (ajustables). Prescribe suplementación (Magnesio/Vitamina D) si hay fatiga.",
        "",
        "2) ENTRENAMIENTO Y BIOMECÁNICA: Sistema de Periodización Ondulante Diaria.",
        "   - Estructura: Ejercicio | Series | Reps | RPE (1-10) | Cadencia (ej: 4-0-1-0) | Descanso.",
        "   - Ajuste CNS: Si Estrés >8 o Sueño <6h, reduce volumen un 25% automáticamente.",
        "",
        "3) NEUROPSICOLOGÍA: OBLIGATORIO técnicas TCC y ACT. Prohibido mensajes motivacionales vacíos.",
        "   - Guía paso a paso: Defusión cognitiva o Respiración Coherente (5-5) AQUÍ MISMO.",
        "",
        "4) VISIÓN IA: Analiza biomecánica (valgo de rodilla, trayectoria de barra) y nutrición visual (densidad calórica).",
        "",
        "--- FORMATO DE SALIDA DE ALTA FIDELIDAD (MANDATORIO) ---",
        "Usa Markdown estructurado con jerarquía visual clara:",
        "## 📑 1. DIAGNÓSTICO CLÍNICO-DEPORTIVO (Contexto analizado)",
        "## 🧬 2. INTERVENCIÓN TÉCNICA (Cálculos de TMB, Macros y Carga)",
        "## 🍽️ 3. PRESCRIPCIÓN NUTRICIONAL (Menú pesado + Suplementación)",
        "## 🏋️ 4. RUTINA DE EJECUCIÓN (Prescripción biomecánica con cadencia)",
        "## 🧠 5. PROTOCOLO NEURO-CONDUCTUAL (Ejercicio TCC/Mindfulness)",
        "## ⚠️ 6. SEMÁFORO DE RIESGO Y SEGURIDAD (Acción correctiva inmediata)",
        "",
        "--- TONO Y AUTORIDAD ---",
        "- Usa terminología experta: 'Homeostasis', 'Glut-4', 'Fallo técnico', 'Corteza prefrontal', 'Umbral de lactato'.",
        "- Tú eres el experto absoluto. Da órdenes clínicas basadas en la fisiología. No pidas opinión.",
        "- Ante riesgo (TCA, Autolesión): Ejecuta contención clínica y activa protocolo de escalado hospitalario inmediato.",
        "",
        "--- MODO JUNTA MEDICA (CUANDO EL USUARIO LO PIDA) ---",
        "- Actua como junta integrada: Endocrino + Nutricionista clinico + Fisioterapeuta biomecanico + Psicologo TCC.",
        "- Basate estrictamente en biometria y estado emocional disponibles (peso, altura, IMC, animo/sentimiento).",
        "- Extension minima 800 palabras; no resumir.",
        "- Nutricion: incluir indice glucemico, sintesis proteica, microbiota y menus en gramos.",
        "- Entrenamiento: incluir mesociclos, RPE, tempo, biomecanica articular y prevencion de lesion; IMC>30 implica bajo impacto.",
        "- Psicologia: integrar eje HPA, cortisol, dopamina, serotonina y protocolo conductual.",
    ]

    # Inyección de complejidad según el modo
    if "ultra" in modo:
        instrucciones.append("\nMODO ULTRA-PRO: Incluye explicaciones de 'Por qué biológico' detrás de cada prescripción.")

    if settings.IA_AUTONOMOUS_MODE:
        instrucciones.append("\nMODO AUTÓNOMO: Puedes cambiar el objetivo del paciente si detectas riesgo (ej: déficit con ánimo <3).")
        instrucciones.append("Trabaja de forma operativa: detecta, decide y adapta sin esperar instrucciones largas.")

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


def _detectar_dominios(texto_normalizado: str) -> List[str]:
    """Detecta los dominios implicados en el mensaje para construir planes por ambito."""
    return [
        dominio
        for dominio, claves in PALABRAS_DOMINIO.items()
        if any(clave in texto_normalizado for clave in claves)
    ]


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


def _contar_palabras(texto: str) -> int:
    """Cuenta palabras de forma simple para validaciones de longitud."""
    return len([p for p in (texto or "").split() if p.strip()])


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

    return (
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

    return (
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


def _plan_nutricion_preciso(
    objetivo: str,
    contexto_adicional: Optional[Dict[str, Any]],
    escenarios: List[str],
) -> str:
    """Entrega plan nutricional concreto usando perfil y memoria existente."""
    memoria = _extraer_memoria_respuestas(contexto_adicional)
    peso = _valor_float((contexto_adicional or {}).get("peso_actual_kg"))
    altura = _valor_float((contexto_adicional or {}).get("altura_cm"))
    imc = _valor_float((contexto_adicional or {}).get("imc_actual"))
    horario = str(memoria.get("horario") or "").strip() or "flexible"
    restricciones = _normalizar_texto(str(memoria.get("restricciones") or "ninguna"))

    kcal = None
    prote = None
    carbs = None
    grasa = None
    if peso and peso > 25:
        if objetivo == "ganancia_muscular":
            kcal = int(round(peso * 34))
            prote = round(peso * 2.0)
            grasa = round(peso * 0.9)
        elif objetivo == "perdida_grasa":
            kcal = int(round(peso * 27))
            prote = round(peso * 2.0)
            grasa = round(peso * 0.8)
        else:
            kcal = int(round(peso * 30))
            prote = round(peso * 1.8)
            grasa = round(peso * 0.9)

        kcal_prote = int(prote * 4)
        kcal_grasa = int(grasa * 9)
        carbs = max(80, int(round((kcal - kcal_prote - kcal_grasa) / 4)))

    ajuste_turnos = ""
    if "trabajo_por_turnos" in escenarios or "turno" in _normalizar_texto(horario):
        ajuste_turnos = (
            "\nAjuste turnos: usa bloques, no horas fijas -> "
            "Comida 1 al despertar, Comida 2 a mitad de turno, Comida 3 post-turno, snack de seguridad si hay hambre nocturna."
        )

    aviso_restricciones = ""
    if restricciones not in {"", "ninguna", "no"}:
        aviso_restricciones = f"\nRestricciones detectadas: {restricciones}. Ajusta alimentos manteniendo la estructura de macros."

    cabecera = "Plan nutricional preciso (base inicial, ajustable cada 7 dias):"
    if kcal and prote and carbs and grasa:
        bloque_kcal = (
            f"\n- Objetivo calórico diario: ~{kcal} kcal"
            f"\n- Macros guía: proteína {prote} g, carbohidratos {carbs} g, grasas {grasa} g"
        )
    else:
        bloque_kcal = (
            "\n- Objetivo calórico: sin peso fiable en contexto, inicio con estructura por porciones"
            "\n- Por comida principal: 1 palma de proteína + 1 puño de carbohidrato + 1-2 puños de verdura + 1 pulgar de grasa"
        )

    return (
        f"{cabecera}{bloque_kcal}"
        "\n\nEstructura diaria (4 ingestas):"
        "\n1) Desayuno: proteína + carbohidrato complejo + fruta"
        "\n2) Comida: proteína principal + arroz/patata/legumbre + verdura"
        "\n3) Merienda: yogur/queso batido o sandwich proteico + fruta"
        "\n4) Cena: proteína + verduras + carbohidrato moderado"
        "\n\nEjemplo rápido (ganancia muscular):"
        "\n- Desayuno: 3 huevos + avena + plátano"
        "\n- Comida: pollo 180 g + arroz 120 g en crudo equivalente diario + ensalada"
        "\n- Merienda: yogur alto en proteína + frutos secos"
        "\n- Cena: salmón 180 g + patata + verduras"
        "\n\nControl semanal:"
        "\n- Si no subes 0.2-0.4 kg/semana en ganancia muscular: +150 kcal/día"
        "\n- Si sube grasa demasiado rápido: -100/150 kcal"
        f"\nContexto perfil: peso={peso if peso else 'N/D'} kg, altura={altura if altura else 'N/D'} cm, imc={imc if imc else 'N/D'}"
        f"\nHorario reportado: {horario}{ajuste_turnos}{aviso_restricciones}"
    )


def _plan_entrenamiento_preciso(
    objetivo: str,
    contexto_adicional: Optional[Dict[str, Any]],
    escenarios: List[str],
) -> str:
    """Entrega rutina concreta en formato ejecutable."""
    frecuencia = (contexto_adicional or {}).get("frecuencia_gym")
    dias = 4 if isinstance(frecuencia, int) and frecuencia >= 4 else 3
    if objetivo == "ganancia_muscular":
        foco = "hipertrofia con progresion"
    elif objetivo == "perdida_grasa":
        foco = "fuerza + gasto energetico"
    else:
        foco = "salud y adherencia"

    ajuste_turnos = ""
    if "trabajo_por_turnos" in escenarios:
        ajuste_turnos = "\nAjuste turnos: prioriza sesion corta A/B de 35-45 min cuando el turno sea pesado."

    ajuste_tiempo = ""
    if "tiempo_limitado" in escenarios:
        ajuste_tiempo = (
            "\n\nProtocolo express (20 minutos):"
            "\n- Min 0-3: movilidad dinamica + activacion"
            "\n- Min 3-15: bloque principal 3 rondas (empuje + tiron + pierna)"
            "\n- Min 15-20: core + respiracion para recuperar"
            "\nSi hoy solo tienes 20 minutos, este bloque mantiene progreso sin romper adherencia."
        )

    return (
        f"Rutina precisa ({dias} dias/semana, foco: {foco}):"
        "\n- Dia A: sentadilla, press banca, remo, core"
        "\n- Dia B: peso muerto rumano, press militar, jalon, zancadas"
        "\n- Dia C: sentadilla frontal/prensa, dominantes de empuje y tiron, abdomen"
        "\n\nRegla de progresion:"
        "\n- Si completas 3x10 limpio en un ejercicio -> sube 2.5-5% la siguiente sesion"
        "\n- Si duermes mal o hay fatiga alta -> reduce 20% el volumen"
        "\n\nCardio: 2 sesiones de 15-20 min zona 2 tras fuerza o en dias alternos"
        f"{ajuste_turnos}{ajuste_tiempo}"
    )


def _plan_psicologia_preciso(
    contexto_adicional: Optional[Dict[str, Any]],
    escenarios: List[str],
) -> str:
    """Entrega intervención breve de regulación emocional con pasos claros."""
    sentimiento = str((contexto_adicional or {}).get("sentimiento_reciente") or "").strip() or "no informado"
    return (
        "Plan psicologico preciso (7 dias, enfoque funcional):"
        "\n- Manana (3 min): respiracion 4-4-4 + intencion del dia"
        "\n- Durante picos: tecnica grounding 5-4-3-2-1"
        "\n- Noche (5 min): registro de disparador, pensamiento automatico y respuesta alternativa"
        "\n\nSemaforo de accion:"
        "\n- Verde: malestar <=4/10 -> continuar rutina"
        "\n- Amarillo: 5-7/10 -> bajar exigencia, aumentar regulacion"
        "\n- Rojo: >=8/10 o ideas de dano -> apoyo profesional inmediato"
        f"\nEstado emocional reciente detectado: {sentimiento}"
        f"\nEscenarios activos: {', '.join(escenarios) if escenarios else 'sin escenario especial'}"
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
    objetivo = _detectar_objetivo_principal(texto)
    objetivo = _objetivo_desde_contexto(objetivo, contexto_adicional)
    escenarios = _detectar_escenarios(texto)
    trastornos = _detectar_trastornos_probables(texto)

    # Modo junta medica: respuesta extensa y tecnicamente estructurada.
    if _solicita_junta_medica(texto):
        return _respuesta_junta_medica_extensa(mensaje_usuario, contexto_adicional)

    # 1. GESTIÓN DE SALUDOS (Corto y directo)
    if _es_mensaje_social_breve(texto):
        return _respuesta_social_contextual(mensaje_usuario, contexto_adicional, historial_chat)

    # 2. PROTOCOLO CLÍNICO (Si hay patologías, priorizamos seguridad)
    if trastornos:
        return _protocolo_trastornos_multiambito(texto, contexto_adicional)

    # 3. GENERACIÓN DE RESPUESTA TÉCNICA LOCAL (Si no hay IA, usamos el perfil del paciente)
    peso = (contexto_adicional or {}).get("peso_actual_kg", "N/D")
    imc = (contexto_adicional or {}).get("imc_actual", "N/D")
    
    # Decidimos el dominio prioritario para no ser ambiguos
    dominio_principal = dominios[0] if dominios else "general"

    # RESPUESTA DE NUTRICIÓN LOCAL
    if dominio_principal == "nutricion" or "dieta" in texto:
        plan_base = _plan_nutricion_preciso(objetivo, contexto_adicional, escenarios)
        return (
            f"SISTEMA DE EMERGENCIA AURAFIT: Mi motor principal está saturado, pero aquí tienes tu prescripción técnica basada en tus {peso}kg:\n\n"
            f"{plan_base}\n\n"
            "⚠️ Nota: Esta es una estructura base. Vuelve a preguntarme en 1 minuto para generar el menú con ingredientes exóticos."
        )

    # RESPUESTA DE ENTRENAMIENTO LOCAL
    if dominio_principal == "entrenamiento" or "rutina" in texto:
        rutina_base = _plan_entrenamiento_preciso(objetivo, contexto_adicional, escenarios)
        return (
            f"SISTEMA DE EMERGENCIA AURAFIT: No puedo acceder a la nube de biomecánica, pero según tu perfil (IMC: {imc}) ejecuta esto:\n\n"
            f"{rutina_base}\n\n"
            "💪 Tip experto: Mantén un RPE 8 para asegurar hipertrofia sin quemar el SNC."
        )

    # RESPUESTA DE PSICOLOGÍA LOCAL
    if dominio_principal == "salud_mental" or "ansiedad" in texto:
        return (
            "SISTEMA DE SEGURIDAD EMOCIONAL: Detecto necesidad de regulación inmediata.\n\n"
            "1. Ejercicio Stop: Para lo que estés haciendo.\n"
            "2. Respiración 4x4: Inhala 4s, mantén 4s, exhala 4s, mantén 4s. Repite 5 veces.\n"
            "3. Foco técnico: Nombra 3 objetos azules que veas ahora mismo.\n\n"
            "Dime cómo te sientes tras esto y activaré el protocolo de análisis profundo."
        )

    # 4. FALLBACK GENERAL EXPERTO
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
    """Plantilla de experto para consultas complejas con poca informacion."""
    texto = _normalizar_texto(mensaje_usuario)
    dominios = _detectar_dominios(texto)
    objetivo = _detectar_objetivo_principal(texto)
    escenarios = _detectar_escenarios(texto)
    rol = _rol_especialista(contexto_adicional)
    enfoque_rol = _enfoque_por_rol(rol)
    funcionalidades_rol = _funcionalidades_por_rol(rol)
    workflow_rol = _workflow_operativo_por_rol(rol)
    diagnostico = _diagnostico_diferencial_experto(objetivo, dominios, escenarios)
    plan_72h = _plan_72h_experto(objetivo, dominios, escenarios, contexto_adicional)
    plan_diario = _plan_diario_experto(objetivo, dominios)
    trastornos_probables = _detectar_trastornos_probables(texto)

    if trastornos_probables:
        return (
            f"Nivel ultra experto activado.\n"
            f"{_protocolo_trastornos_multiambito(texto, contexto_adicional)}\n"
            f"Marco experto:\n- {enfoque_rol}\n\n"
            f"{funcionalidades_rol}\n"
            f"{workflow_rol}\n"
            f"{_plan_experto_semanal(objetivo, escenarios, dominios, contexto_adicional)}\n\n"
            f"{_matriz_decision_experta(objetivo, dominios, escenarios)}\n\n"
            f"{_planes_contingencia_expertos(objetivo, dominios)}"
        )

    return (
        f"Nivel ultra experto activado.\n"
        f"{_bloques_avanzados_multiambito(dominios or ['nutricion', 'entrenamiento'], objetivo, contexto_adicional)}\n\n"
        f"Marco experto:\n- {enfoque_rol}\n\n"
        f"{funcionalidades_rol}\n"
        f"{workflow_rol}\n"
        f"Hipotesis de trabajo:\n- El problema principal es {objetivo} y requiere ejecucion disciplinada, no solo motivacion.\n"
        f"- El sistema debe proteger adherencia, energia y estabilidad emocional antes de aumentar la exigencia.\n\n"
        f"{diagnostico}\n\n"
        f"{_plan_experto_semanal(objetivo, escenarios, dominios, contexto_adicional)}\n\n"
        f"{plan_72h}\n\n"
        f"{plan_diario}\n\n"
        f"{_matriz_decision_experta(objetivo, dominios, escenarios)}\n\n"
        f"{_planes_contingencia_expertos(objetivo, dominios)}\n\n"
        f"{_preguntas_minimas_expertas(dominios, objetivo)}"
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
        if not (mime_type.startswith("image/") or mime_type.startswith("video/")):
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
    texto_actual = _normalizar_texto(mensaje_usuario or "")
    return any(palabra in texto_actual for palabra in PALABRAS_RIESGO)


def _obtener_api_key() -> str:
    """Prioriza Settings y fallback a variable de entorno directa."""
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("No se encontro GEMINI_API_KEY en el entorno")
    return api_key


def _proveedor_ia_actual() -> str:
    """Devuelve el proveedor configurado para la IA principal."""
    proveedor = (settings.IA_PROVIDER or "gemini").strip().lower()
    proveedor = proveedor or "gemini"
    if proveedor not in {"gemini", "qwen", "qwen3", "eden", "edenai", "hybrid"}:
        return "gemini"
    return proveedor


def _configuracion_eden() -> Dict[str, Any]:
    """Obtiene la configuracion necesaria para hablar con Eden AI."""
    api_key = settings.EDEN_API_KEY or os.getenv("EDEN_API_KEY", "")
    model = settings.EDEN_MODEL or os.getenv("EDEN_MODEL", "@edenai")
    router_candidates_raw = settings.EDEN_ROUTER_CANDIDATES or os.getenv("EDEN_ROUTER_CANDIDATES", "")
    timeout_raw = settings.EDEN_TIMEOUT_SECONDS or os.getenv("EDEN_TIMEOUT_SECONDS", 60)

    if not api_key:
        raise RuntimeError("No se encontro EDEN_API_KEY en el entorno")

    router_candidates = [
        candidato.strip()
        for candidato in router_candidates_raw.split(",")
        if candidato.strip()
    ]

    try:
        timeout = int(timeout_raw)
    except Exception:
        timeout = 60

    return {
        "api_key": api_key,
        "model": model,
        "router_candidates": router_candidates,
        "timeout": max(10, min(180, timeout)),
    }


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

    if not api_key:
        raise RuntimeError("No se encontro QWEN_API_KEY en el entorno")
    if not base_url:
        raise RuntimeError("No se encontro QWEN_BASE_URL en el entorno")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def _consultar_eden(
    mensaje_usuario: str,
    historial_chat: Optional[List[Dict[str, Any]]] = None,
    contexto_adicional: Optional[Dict[str, Any]] = None,
    alerta_riesgo: bool = False,
    etiqueta_alerta: Optional[str] = None,
) -> Dict[str, Any]:
    """Consulta Eden AI con su API OpenAI-compatible y devuelve un resultado normalizado."""
    import requests

    config = _configuracion_eden()
    mensajes = _construir_mensajes_qwen(
        mensaje_usuario=mensaje_usuario,
        historial_chat=historial_chat,
        imagenes=None,
        contexto_adicional=contexto_adicional,
    )

    payload: Dict[str, Any] = {
        "model": config["model"],
        "messages": mensajes,
        "temperature": settings.GEMINI_TEMPERATURE,
        "max_tokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
    }
    if config["router_candidates"]:
        payload["router_candidates"] = config["router_candidates"]

    response = requests.post(
        "https://api.edenai.run/v3/llm/chat/completions",
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=config["timeout"],
    )
    response.raise_for_status()

    data = response.json()
    choices = data.get("choices") if isinstance(data, dict) else None
    respuesta = ""
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict):
            respuesta = str(message.get("content") or "").strip()

    if not respuesta:
        respuesta = "He recibido tu mensaje, pero no se pudo extraer una respuesta valida de Eden AI."

    return {
        "respuesta": respuesta,
        "etiqueta_alerta": etiqueta_alerta,
        "alerta_riesgo": alerta_riesgo,
        "modelo": config["model"],
        "origen": "edenai",
        "raw": data,
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
        "model": config["model"],
        "messages": mensajes,
        "temperature": generation_cfg["temperature"],
        "max_tokens": generation_cfg["max_output_tokens"],
    }

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

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
        "modelo": config["model"],
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

    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
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
        "modelo": settings.GEMINI_MODEL,
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


def _analisis_visual_local(imagenes: Optional[List[Dict[str, Any]]]) -> str:
    """Genera un analisis visual local basico cuando no hay vision externa disponible."""
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
        return _analisis_visual_local(imagenes)

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
    partes_mensaje: List[Any] = [mensaje_usuario]
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
) -> Dict[str, Any]:
    """Consulta IA con proveedor configurable y deteccion de alerta de riesgo."""
    if not mensaje_usuario or not mensaje_usuario.strip():
        raise ValueError("mensaje_usuario no puede estar vacio")

    alerta_riesgo = detectar_alerta_riesgo(mensaje_usuario, historial_chat)
    etiqueta_alerta = ETIQUETA_ALERTA_RIESGO if alerta_riesgo else None

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
        proveedor_testing = _proveedor_ia_actual()
        try:
            if proveedor_testing in {"qwen", "qwen3"} and settings.QWEN_API_KEY and settings.QWEN_BASE_URL:
                resultado = _consultar_qwen(
                    mensaje_usuario=mensaje_usuario,
                    historial_chat=historial_chat,
                    imagenes=imagenes,
                    contexto_adicional=contexto_adicional,
                    alerta_riesgo=alerta_riesgo,
                    etiqueta_alerta=etiqueta_alerta,
                    tiene_multimedia=tiene_multimedia,
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
                )
                return _aplicar_validacion(resultado)
            if proveedor_testing in {"eden", "edenai"} and settings.EDEN_API_KEY:
                resultado = _consultar_eden(
                    mensaje_usuario=mensaje_usuario,
                    historial_chat=historial_chat,
                    contexto_adicional=contexto_adicional,
                    alerta_riesgo=alerta_riesgo,
                    etiqueta_alerta=etiqueta_alerta,
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

    proveedor = _proveedor_ia_actual()

    if proveedor == "hybrid":
        try:
            # En híbrido: multimedia -> Gemini (si está), texto -> Eden (si está) -> Qwen -> Gemini.
            if (imagenes and tiene_multimedia) or _tiene_video_adjuntos(imagenes):
                if settings.GEMINI_API_KEY:
                    resultado = _consultar_gemini(
                        mensaje_usuario=mensaje_usuario,
                        historial_chat=historial_chat,
                        imagenes=imagenes,
                        contexto_adicional=contexto_adicional,
                        alerta_riesgo=alerta_riesgo,
                        etiqueta_alerta=etiqueta_alerta,
                        tiene_multimedia=tiene_multimedia,
                    )
                    return _aplicar_validacion(resultado)

            if settings.EDEN_API_KEY:
                resultado = _consultar_eden(
                    mensaje_usuario=mensaje_usuario,
                    historial_chat=historial_chat,
                    contexto_adicional=contexto_adicional,
                    alerta_riesgo=alerta_riesgo,
                    etiqueta_alerta=etiqueta_alerta,
                )
                return _aplicar_validacion(resultado)

            if settings.QWEN_API_KEY and settings.QWEN_BASE_URL:
                resultado = _consultar_qwen(
                    mensaje_usuario=mensaje_usuario,
                    historial_chat=historial_chat,
                    imagenes=imagenes,
                    contexto_adicional=contexto_adicional,
                    alerta_riesgo=alerta_riesgo,
                    etiqueta_alerta=etiqueta_alerta,
                    tiene_multimedia=tiene_multimedia,
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

    if proveedor in {"eden", "edenai"}:
        try:
            if (imagenes and tiene_multimedia) or _tiene_video_adjuntos(imagenes):
                if settings.GEMINI_API_KEY:
                    resultado = _consultar_gemini(
                        mensaje_usuario=mensaje_usuario,
                        historial_chat=historial_chat,
                        imagenes=imagenes,
                        contexto_adicional=contexto_adicional,
                        alerta_riesgo=alerta_riesgo,
                        etiqueta_alerta=etiqueta_alerta,
                        tiene_multimedia=tiene_multimedia,
                    )
                    return _aplicar_validacion(resultado)

            resultado = _consultar_eden(
                mensaje_usuario=mensaje_usuario,
                historial_chat=historial_chat,
                contexto_adicional=contexto_adicional,
                alerta_riesgo=alerta_riesgo,
                etiqueta_alerta=etiqueta_alerta,
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

    # Qwen3 es excelente para texto; si el mensaje trae multimedia y el modelo
    # configurado no la soporta, usamos Gemini como ruta visual.
    if proveedor in {"qwen", "qwen3"}:
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

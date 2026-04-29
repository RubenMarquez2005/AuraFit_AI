import sys
import os

# Añadir el path actual para importar módulos
sys.path.append(os.getcwd())

# Importando desde services.gemini_service según vimos en el test
from services.gemini_service import obtener_respuesta_local_segura

prompt = """Sección activa: psicologia.
Datos del usuario:
- Objetivo principal: dormir mejor
- Síntomas o dificultades: ansiedad, estrés
- Contexto: trabajo

Requisitos de salida:
1) Respuesta breve y útil (sin relleno).
2) Plan de 4 semanas, semana por semana.
3) Incluye menú/plan diario por semana según la sección."""

# Ejecutamos la función de respuesta
response = obtener_respuesta_local_segura(prompt)
print("INICIO DE LA RESPUESTA:")
print(response[:500])

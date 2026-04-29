"""Tests de precisión y pertinencia del motor IA mejorado."""

from io import BytesIO

import pytest
from PIL import Image
from services.gemini_service import (
    _configuracion_qwen,
    _proveedor_ia_actual,
    _validar_respuesta_pertinente,
    obtener_respuesta_local_segura,
)
from app.config.settings import settings
from services.chat_router import debe_priorizar_rasa, es_intento_rasa_confiable


class TestValidacionPertinencia:
    """Validación de coherencia entre respuesta IA y contexto del usuario."""

    def test_detecta_contradiccion_peso_objetivo(self):
        """Debe detectar si respuesta contradice objetivo de pérdida de peso."""
        contexto = {
            "peso_actual_kg": 85.0,
            "imc_actual": 28.5,
        }
        respuesta = "Te recomiendo aumentar calorías significativamente para ganar músculo rápido."
        mensaje = "Quiero bajar de peso, tengo 85kg y 1.75m"

        validacion = _validar_respuesta_pertinente(
            respuesta=respuesta,
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        assert not validacion["valida"], "Debe detectar contradicción peso/calorías"
        assert validacion["puntuacion"] < 75
        assert validacion["alerta_incoherencia"]

    def test_detecta_contradiccion_celiquia_gluten(self):
        """Debe detectar si respuesta incluye gluten sin advertencia para celíaco."""
        contexto = {
            "memoria_respuestas": {
                "restricciones": "Celiaco, no puedo comer gluten",
            }
        }
        respuesta = "Come pan integral en cada comida para mejor saciedad."
        mensaje = "Soy celíaco, ¿qué puedo desayunar?"

        validacion = _validar_respuesta_pertinente(
            respuesta=respuesta,
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        assert not validacion["valida"], "Debe detectar alerta de gluten"
        assert validacion["alerta_incoherencia"]
        assert any("gluten" in m.lower() for m in validacion["motivos"])

    def test_detecta_respuesta_coherente(self):
        """Respuesta coherente debe pasar validación."""
        contexto = {
            "peso_actual_kg": 85.0,
            "imc_actual": 28.5,
            "usuario_nombre": "Juan",
        }
        respuesta = (
            "Con 85kg e IMC 28.5, un déficit de 500kcal diarias es razonable. "
            "Objetivo: 1.5-2kg/mes. Aumenta proteína a 150g/día "
            "para preservar músculo durante pérdida de grasa."
        )
        mensaje = "Quiero bajar de peso en 3 meses"

        validacion = _validar_respuesta_pertinente(
            respuesta=respuesta,
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        assert validacion["valida"], "Respuesta coherente debe ser válida"
        assert validacion["puntuacion"] >= 75

    def test_detecta_respuesta_plantilla(self):
        """Detecta lenguaje de plantilla no deseable."""
        contexto = {}
        respuesta = (
            "Te recomiendo suavemente que intentes hacer ejercicio. "
            "Si lo deseas, puedes también mejorar tu dieta."
        )
        mensaje = "Tengo sobrepeso"

        validacion = _validar_respuesta_pertinente(
            respuesta=respuesta,
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        # Debe penalizar lenguaje plantilla
        assert validacion["puntuacion"] < 100
        assert any("plantilla" in m.lower() for m in validacion["motivos"])

    def test_detecta_respuesta_breve_para_pregunta_compleja(self):
        """Detecta respuestas muy breves para preguntas complejas."""
        contexto = {}
        respuesta = "Haz ejercicio."
        mensaje = (
            "Tengo 85kg con IMC 28.5, quiero perder grasa en 3 meses "
            "pero tengo lesión de rodilla. ¿Qué debo cambiar en mi dieta, "
            "rutina de entrenamiento y cómo manejo mi ánimo?"
        )

        validacion = _validar_respuesta_pertinente(
            respuesta=respuesta,
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        # Debe penalizar respuestas muy breves
        assert validacion["puntuacion"] < 100
        assert any("breve" in m.lower() for m in validacion["motivos"])

    def test_sin_contexto_es_valido(self):
        """Sin contexto adicional, respuesta es válida (permite uso general)."""
        validacion = _validar_respuesta_pertinente(
            respuesta="Aquí está mi respuesta",
            mensaje_usuario="Hola",
            contexto_adicional=None,
        )

        assert validacion["valida"]
        assert validacion["puntuacion"] >= 70


class TestCasosTotalesIntegracion:
    """Casos de uso integrales para validar especialista senior."""

    def test_caso_usuario_ansiedad_ponderar_ejercicio(self):
        """Usuario con ansiedad no debe recibir recomendación agresiva de ejercicio."""
        contexto = {
            "sentimiento_reciente": "ansiedad",
            "usuario_nombre": "Maria",
            "imc_actual": 22.0,
        }
        respuesta = (
            "Tu ánimo está bajo debido a ansiedad. "
            "Te recomiendo ayunar y hacer ayunos intermitentes para regular cortisol."
        )
        mensaje = "Me siento con mucha ansiedad y no duermo bien"

        validacion = _validar_respuesta_pertinente(
            respuesta=respuesta,
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        assert not validacion["valida"], "No debe recomendar ayuno a persona con ansiedad"
        assert validacion["alerta_incoherencia"]

    def test_caso_usuario_bajo_peso_con_proteina(self):
        """Usuario con bajo peso debe recibir énfasis en proteína."""
        contexto = {
            "peso_actual_kg": 55.0,
            "altura_cm": 165,
            "imc_actual": 20.2,  # Normal pero en el límite bajo
        }
        respuesta = (
            "Aunque tienes peso normal, con IMC 20.2 y queriendo entrenar, "
            "prioriza 150-160g de proteína diaria para preservar y ganar masa magra."
        )
        mensaje = "Quiero empezar a entrenar fuerza"

        validacion = _validar_respuesta_pertinente(
            respuesta=respuesta,
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        # Buena respuesta que menciona proteína
        assert validacion["valida"]
        assert validacion["puntuacion"] >= 75


class TestRouterEdenRasa:
    def test_rasa_para_intentos_cortos(self):
        assert debe_priorizar_rasa("Quiero plan nutricion", area_detectada="nutricion")

    def test_no_rasa_para_caso_experto(self):
        assert not debe_priorizar_rasa(
            "Analiza esta imagen y dame un plan experto completo",
            area_detectada="nutricion",
            tiene_multimedia=True,
            es_solicitud_experta=True,
        )

    def test_intento_rasa_confiable(self):
        assert es_intento_rasa_confiable("pedir_plan_nutricion", 0.9)


class TestFallbackMultimodalLocal:
    def test_reutiliza_texto_pdf_extraido_en_fallback_local(self):
        mensaje = (
            "Lee este PDF y dime que pone\n\n"
            "[TEXTO EXTRAIDO AUTOMATICAMENTE DE PDF ADJUNTO]\n"
            "Plan semanal de nutricion. Desayuno: yogur natural con avena y fruta. "
            "Comida: arroz con pollo y verduras. Cena: salmon con ensalada."
        )

        respuesta = obtener_respuesta_local_segura(
            mensaje_usuario=mensaje,
            imagenes=[{"mime_type": "application/pdf", "data": b"pdf-simulado"}],
            tiene_multimedia=True,
        )

        assert "no puedo extraer su texto" not in respuesta.lower()
        assert "he leído el pdf adjunto" in respuesta.lower()
        assert any(clave in respuesta.lower() for clave in ("yogur", "avena", "salmon", "pollo"))

    def test_imagen_con_ocr_prioriza_lectura_texto(self, monkeypatch):
        monkeypatch.setattr(
            "services.gemini_service._extraer_texto_ocr_local",
            lambda _data: "Paciente: Juan Perez. Diagnostico: ansiedad moderada.",
        )

        img = Image.new("RGB", (120, 80), color=(255, 255, 255))
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        data = buffer.getvalue()

        respuesta = obtener_respuesta_local_segura(
            mensaje_usuario="lee lo que hay dentro de la imagen",
            imagenes=[{"mime_type": "image/png", "data": data}],
            tiene_multimedia=True,
        )

        assert "he leído el texto de la imagen adjunta" in respuesta.lower()
        assert "analisis visual local realizado" not in respuesta.lower()

    def test_pdf_no_salud_se_analiza_como_documento_generico(self):
        mensaje = (
            "léeme ese documento\n\n"
            "[TEXTO EXTRAIDO AUTOMATICAMENTE DE PDF ADJUNTO]\n"
            "Contrato de arrendamiento entre las partes firmantes. "
            "La cláusula tercera establece vigencia de 12 meses y cancelación anticipada con preaviso."
        )

        respuesta = obtener_respuesta_local_segura(
            mensaje_usuario=mensaje,
            imagenes=[{"mime_type": "application/pdf", "data": b"pdf-simulado"}],
            tiene_multimedia=True,
        )

        assert "esto parece un documento de contratacion" in respuesta.lower()
        assert "resumen de contenido detectado" in respuesta.lower()

    def test_pdf_con_palabras_riesgo_inyectadas_no_dispara_bloque_crisis(self):
        mensaje = (
            "léeme este pdf legal\n\n"
            "[TEXTO EXTRAIDO AUTOMATICAMENTE DE PDF ADJUNTO]\n"
            "Anexo con frase de ejemplo: me quiero morir. "
            "Este texto aparece como cita dentro del documento, no como petición del usuario."
        )

        respuesta = obtener_respuesta_local_segura(
            mensaje_usuario=mensaje,
            imagenes=[{"mime_type": "application/pdf", "data": b"pdf-simulado"}],
            tiene_multimedia=True,
        )

        assert "bloque de seguridad" not in respuesta.lower()
        assert "he leído el pdf adjunto" in respuesta.lower()


class TestProveedorLocalGratis:
    def test_alias_ollama_mapea_a_backend_openai_compatible(self):
        assert _proveedor_ia_actual("ollama") == "qwen"

    def test_configuracion_local_sin_api_key_es_valida(self, monkeypatch):
        monkeypatch.setattr(settings, "QWEN_API_KEY", "")
        monkeypatch.setattr(settings, "QWEN_BASE_URL", "http://host.docker.internal:11434/v1")
        monkeypatch.setattr(settings, "QWEN_MODEL", "qwen2.5vl:7b")

        config = _configuracion_qwen()

        assert config["api_key"] == ""
        assert config["base_url"] == "http://host.docker.internal:11434/v1"
        assert config["model"] == "qwen2.5vl:7b"


class TestPrioridadPlanFrenteAModoClinico:
    def test_plan_breve_psicologia_no_devuelve_bloque_clinico_largo(self):
        mensaje = """
Modo clínico breve y accionable.
Sección activa: psicologia.
Datos del usuario:
- Objetivo principal: dormir mejor
- Síntomas o dificultades: ansiedad, estrés
- Contexto: trabajo

Requisitos de salida:
1) Respuesta breve y útil (sin relleno).
2) Plan de 4 semanas, semana por semana.
3) Incluye menú/plan diario por semana según la sección.
"""
        contexto = {
            "usuario_rol": "cliente",
            "peso_actual_kg": 72.5,
            "altura_cm": 174,
            "imc_actual": 23.95,
            "sentimiento_reciente": "neutral",
            "animo_reciente": 6,
        }

        respuesta = obtener_respuesta_local_segura(
            mensaje_usuario=mensaje,
            contexto_adicional=contexto,
        )

        assert "modo clinico de alta precision activado" not in respuesta.lower()
        assert "plan psicologico" in respuesta.lower() or "plan psicológico" in respuesta.lower()

    def test_peticion_clinica_explicita_si_devuelve_marco_clinico(self):
        mensaje = "Necesito triage, diagnostico probable, medicacion actual y contraindicaciones por ansiedad y lesion"

        respuesta = obtener_respuesta_local_segura(
            mensaje_usuario=mensaje,
            contexto_adicional={"animo_reciente": 4},
        )

        assert "modo clinico de alta precision activado" in respuesta.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

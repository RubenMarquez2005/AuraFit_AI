"""Tests del enrutado entre RASA y la IA generativa."""

from services.chat_router import debe_priorizar_rasa, es_intento_rasa_confiable


def test_prioriza_rasa_para_mensajes_simple_nutricion() -> None:
    assert debe_priorizar_rasa("Quiero un plan de dieta para hoy", area_detectada="nutricion")


def test_no_prioriza_rasa_para_multimedia() -> None:
    assert not debe_priorizar_rasa(
        "Analiza esta foto",
        area_detectada="nutricion",
        tiene_multimedia=True,
    )


def test_no_prioriza_rasa_para_urgencia() -> None:
    assert not debe_priorizar_rasa("No quiero vivir", area_detectada="salud_mental")


def test_intento_rasa_confiable() -> None:
    assert es_intento_rasa_confiable("pedir_plan_nutricion", 0.91)


def test_intento_rasa_debiles_no_pasan() -> None:
    assert not es_intento_rasa_confiable("pedir_plan_nutricion", 0.4)
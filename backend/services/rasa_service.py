"""Cliente HTTP para comunicacion con servidor RASA."""

from __future__ import annotations

from typing import Any, Dict, List

import requests

from app.config.settings import settings


def enviar_mensaje_a_rasa(sender: str, mensaje: str) -> List[Dict[str, Any]]:
    """Envia un mensaje al webhook REST de RASA y devuelve la lista de respuestas."""
    payload = {
        "sender": sender,
        "message": mensaje,
    }

    response = requests.post(
        settings.RASA_WEBHOOK_URL,
        json=payload,
        timeout=settings.RASA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list):
        raise ValueError("RASA devolvio un formato no esperado")

    return data

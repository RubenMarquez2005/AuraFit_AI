"""Cliente HTTP para comunicacion con servidor RASA."""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse, urlunparse

import requests

from app.config.settings import settings


def _obtener_url_parse_rasa() -> str:
    """Deriva la URL del endpoint de parseo a partir del webhook REST."""
    webhook_url = (settings.RASA_WEBHOOK_URL or "").rstrip("/")
    if webhook_url.endswith("/webhooks/rest/webhook"):
        return webhook_url[: -len("/webhooks/rest/webhook")] + "/model/parse"

    parsed = urlparse(webhook_url)
    if parsed.scheme and parsed.netloc:
        return urlunparse(parsed._replace(path="/model/parse", params="", query="", fragment=""))

    return webhook_url + "/model/parse"


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


def analizar_mensaje_con_rasa(sender: str, mensaje: str) -> Dict[str, Any]:
    """Pide a RASA el intent y entidades del mensaje antes de responder."""
    payload = {
        "sender": sender,
        "text": mensaje,
    }

    response = requests.post(
        _obtener_url_parse_rasa(),
        json=payload,
        timeout=settings.RASA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("RASA devolvio un formato no esperado en parseo")

    return data

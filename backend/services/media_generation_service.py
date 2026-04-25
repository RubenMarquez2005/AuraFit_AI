"""Servicio premium para generacion real de imagen y video con proveedores externos."""

from __future__ import annotations

import time
from typing import Dict, Any, List
from urllib.parse import quote_plus

import httpx

from app.config.settings import settings


def _result(estado: str, proveedor: str, prompt: str, url: str = "", detalle: str = "") -> Dict[str, str]:
    """Estandariza resultados de generacion para respuesta de chat."""
    return {
        "estado": estado,
        "proveedor": proveedor,
        "prompt": prompt,
        "url_generada": url,
        "detalle": detalle,
    }


def _result_modelo(
    estado: str,
    proveedor: str,
    prompt: str,
    modelo: str,
    url: str = "",
    detalle: str = "",
) -> Dict[str, str]:
    """Respuesta estandar con modelo usado para facilitar auditoria."""
    data = _result(estado=estado, proveedor=proveedor, prompt=prompt, url=url, detalle=detalle)
    data["modelo"] = modelo
    return data


def generar_imagen_premium(prompt: str) -> Dict[str, str]:
    """Genera imagen real con proveedor premium configurado."""
    model = (settings.OPENAI_IMAGE_MODEL or "gpt-image-1").strip()
    if not settings.PREMIUM_MEDIA_ENABLED:
        return _result_modelo("deshabilitado", "none", prompt, model, detalle="PREMIUM_MEDIA_ENABLED=False")

    provider = (settings.PREMIUM_IMAGE_PROVIDER or "openai").strip().lower()

    # Modo demo gratuito: devuelve una URL de placeholder estable sin coste.
    if provider == "mock":
        text = quote_plus((prompt or "imagen premium").strip()[:120])
        demo_url = f"https://placehold.co/1024x1024/png?text={text}"
        return _result_modelo("ok", "mock", prompt, "mock-image-v1", url=demo_url, detalle="Generacion demo local sin coste")

    if provider != "openai":
        return _result_modelo("no_soportado", provider, prompt, model, detalle="Proveedor de imagen no soportado")

    if not settings.OPENAI_API_KEY:
        return _result_modelo("no_configurado", "openai", prompt, model, detalle="Falta OPENAI_API_KEY")

    payload = {
        "model": model,
        "prompt": prompt,
        "size": settings.OPENAI_IMAGE_SIZE,
    }
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    retries = max(1, int(settings.PREMIUM_IMAGE_RETRIES))
    last_error = ""
    for intento in range(1, retries + 1):
        try:
            resp = httpx.post(
                "https://api.openai.com/v1/images/generations",
                json=payload,
                headers=headers,
                timeout=90.0,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data") or []
            if not items:
                last_error = "Sin datos de imagen en respuesta"
                continue

            first = items[0] or {}
            image_url = (first.get("url") or "").strip()
            if image_url:
                return _result_modelo("ok", "openai", prompt, model, url=image_url)

            b64 = (first.get("b64_json") or "").strip()
            if b64:
                data_url = f"data:image/png;base64,{b64}"
                return _result_modelo("ok", "openai", prompt, model, url=data_url)

            last_error = "Respuesta sin url ni b64_json"
        except Exception as exc:
            last_error = str(exc)
            if intento < retries:
                time.sleep(1)

    return _result_modelo("error", "openai", prompt, model, detalle=last_error or "Fallo desconocido en imagen")


def _parse_replicate_output(output: Any) -> str:
    """Extrae URL util desde la salida de Replicate."""
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.strip():
                return item.strip()
    if isinstance(output, dict):
        for key in ("video", "url", "output"):
            value = output.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _modelos_video_replicate() -> List[str]:
    """Lista ordenada de modelos de video: principal + fallback sin duplicados."""
    primary = (settings.REPLICATE_VIDEO_MODEL or "").strip()
    fallback_raw = settings.REPLICATE_VIDEO_FALLBACK_MODELS or ""
    fallback = [item.strip() for item in fallback_raw.split(",") if item.strip()]

    modelos: List[str] = []
    for model in [primary, *fallback]:
        if model and model not in modelos:
            modelos.append(model)

    return modelos


def _generar_video_replicate_modelo(prompt: str, model: str) -> Dict[str, str]:
    """Lanza prediccion en Replicate para un modelo concreto y espera resultado."""
    headers = {
        "Authorization": f"Token {settings.REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    create_payload = {
        "model": model,
        "input": {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "duration": 5,
        },
    }

    create_resp = httpx.post(
        "https://api.replicate.com/v1/predictions",
        json=create_payload,
        headers=headers,
        timeout=30.0,
    )
    create_resp.raise_for_status()
    pred = create_resp.json()

    pred_id = str(pred.get("id") or "").strip()
    if not pred_id:
        return _result_modelo("error", "replicate", prompt, model, detalle="No se recibio id de prediccion")

    timeout_seconds = max(20, int(settings.PREMIUM_VIDEO_TIMEOUT_SECONDS))
    poll_seconds = max(0.5, float(settings.PREMIUM_VIDEO_POLL_SECONDS))
    deadline = time.time() + timeout_seconds

    last_status = str(pred.get("status") or "starting")
    output_url = _parse_replicate_output(pred.get("output"))

    while time.time() < deadline and last_status not in {"succeeded", "failed", "canceled"}:
        poll = httpx.get(
            f"https://api.replicate.com/v1/predictions/{pred_id}",
            headers=headers,
            timeout=20.0,
        )
        poll.raise_for_status()
        pred = poll.json()
        last_status = str(pred.get("status") or last_status)
        output_url = _parse_replicate_output(pred.get("output"))
        if output_url and last_status == "succeeded":
            break
        time.sleep(poll_seconds)

    if output_url:
        return _result_modelo("ok", "replicate", prompt, model, url=output_url)

    error_txt = str(pred.get("error") or "")
    if last_status in {"failed", "canceled"}:
        return _result_modelo("error", "replicate", prompt, model, detalle=f"{last_status}: {error_txt}")

    return _result_modelo("timeout", "replicate", prompt, model, detalle="Tiempo de espera agotado")


def generar_video_premium(prompt: str) -> Dict[str, str]:
    """Genera video real con proveedor premium configurado."""
    if not settings.PREMIUM_MEDIA_ENABLED:
        return _result("deshabilitado", "none", prompt, detalle="PREMIUM_MEDIA_ENABLED=False")

    provider = (settings.PREMIUM_VIDEO_PROVIDER or "replicate").strip().lower()

    # Modo demo gratuito: usa un clip de muestra publico para pruebas de flujo.
    if provider == "mock":
        demo_video_url = "https://samplelib.com/lib/preview/mp4/sample-5s.mp4"
        return _result_modelo(
            "ok",
            "mock",
            prompt,
            "mock-video-v1",
            url=demo_video_url,
            detalle="Generacion demo sin coste",
        )

    if provider != "replicate":
        return _result("no_soportado", provider, prompt, detalle="Proveedor de video no soportado")

    if not settings.REPLICATE_API_TOKEN:
        return _result("no_configurado", "replicate", prompt, detalle="Falta REPLICATE_API_TOKEN")

    modelos = _modelos_video_replicate()
    if not modelos:
        return _result("no_configurado", "replicate", prompt, detalle="No hay modelos de video configurados")

    retries = max(1, int(settings.PREMIUM_VIDEO_RETRIES))
    errores: List[str] = []

    for model in modelos:
        for intento in range(1, retries + 1):
            try:
                resultado = _generar_video_replicate_modelo(prompt=prompt, model=model)
                if resultado.get("estado") == "ok":
                    return resultado

                detalle = resultado.get("detalle") or "sin detalle"
                errores.append(f"{model} intento {intento}: {detalle}")
            except Exception as exc:
                errores.append(f"{model} intento {intento}: {exc}")

            if intento < retries:
                time.sleep(1)

    return _result(
        "error",
        "replicate",
        prompt,
        detalle=" | ".join(errores[:10]) or "Fallo desconocido en video",
    )

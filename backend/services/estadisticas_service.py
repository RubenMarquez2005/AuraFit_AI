"""Servicio para generar gráficos y estadísticas de bienestar del usuario."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models import RegistroDiario, Usuario


def _calcular_estadisticas_7dias(db: Session, usuario_id: int) -> Dict[str, Any]:
    """Calcula estadísticas completas de 7 días para gráficos."""
    hoy = datetime.utcnow().date()
    inicio = hoy - timedelta(days=6)

    registros = (
        db.query(RegistroDiario)
        .filter(
            RegistroDiario.usuario_id == usuario_id,
            RegistroDiario.fecha >= inicio,
            RegistroDiario.fecha <= hoy,
        )
        .order_by(RegistroDiario.fecha.asc())
        .all()
    )

    # Datos para gráficos
    datos_diarios: List[Dict[str, Any]] = []
    animos = []
    energias = []
    estreses = []
    suenos = []

    for r in registros:
        parsed = _parsear_nota_checkin(r.notas_diario)
        if parsed is None:
            parsed = {}

        try:
            animo = int(r.estado_animo_puntuacion) if r.estado_animo_puntuacion else 5
            energia = int(parsed.get("energia", "5"))
            estres = int(parsed.get("estres", "5"))
            sueno = float(parsed.get("sueno", "7"))
        except (ValueError, TypeError):
            animo, energia, estres, sueno = 5, 5, 5, 7

        animos.append(animo)
        energias.append(energia)
        estreses.append(estres)
        suenos.append(sueno)

        # Score de bienestar diario
        score_diario = (animo * 10) + (energia * 7) - (estres * 5) + (sueno * 2)
        score_diario = max(0, min(100, score_diario))

        datos_diarios.append({
            "fecha": r.fecha.strftime("%a %d/%m"),  # "Mon 01/01"
            "fecha_iso": r.fecha.isoformat(),
            "animo": animo,
            "energia": energia,
            "estres": estres,
            "sueno": round(sueno, 1),
            "score_bienestar": round(score_diario, 1),
            "sentimiento": r.sentimiento_detectado_ia or "neutral",
        })

    # Promedios
    promedio_animo = round(sum(animos) / len(animos), 1) if animos else 5.0
    promedio_energia = round(sum(energias) / len(energias), 1) if energias else 5.0
    promedio_estres = round(sum(estreses) / len(estreses), 1) if estreses else 5.0
    promedio_calma = round(max(0.0, min(10.0, 10 - promedio_estres)), 1)
    promedio_sueno = round(sum(suenos) / len(suenos), 1) if suenos else 7.0

    # Tendencias (comparar primeros 3 días vs últimos 3 días)
    if len(animos) >= 6:
        tendencia_animo = "↑" if promedio_animo > (sum(animos[:3]) / 3) else ("↓" if promedio_animo < (sum(animos[:3]) / 3) else "→")
        tendencia_energia = "↑" if promedio_energia > (sum(energias[:3]) / 3) else ("↓" if promedio_energia < (sum(energias[:3]) / 3) else "→")
        tendencia_estres = "↓" if promedio_estres < (sum(estreses[:3]) / 3) else ("↑" if promedio_estres > (sum(estreses[:3]) / 3) else "→")
    else:
        tendencia_animo = "→"
        tendencia_energia = "→"
        tendencia_estres = "→"

    # Racha de cumplimiento
    racha_actual = 0
    for r in registros[::-1]:  # Desde hoy hacia atrás
        if r.estado_animo_puntuacion is not None:
            racha_actual += 1
        else:
            break

    # Clasificación de estado general (incluye calma para respetar que menos estrés = mejor).
    indice_general = (promedio_animo * 0.45) + (promedio_energia * 0.35) + (promedio_calma * 0.20)
    if indice_general >= 7:
        estado_general = "Excelente"
        color = "#10b981"  # Verde
    elif indice_general >= 6:
        estado_general = "Bueno"
        color = "#3b82f6"  # Azul
    elif indice_general >= 4:
        estado_general = "Regular"
        color = "#f59e0b"  # Ámbar
    else:
        estado_general = "Bajo"
        color = "#ef4444"  # Rojo

    return {
        "dias_registrados": len(datos_diarios),
        "racha_actual": racha_actual,
        "promedio_animo": promedio_animo,
        "promedio_energia": promedio_energia,
        "promedio_estres": promedio_estres,
        "promedio_calma": promedio_calma,
        "promedio_sueno": promedio_sueno,
        "tendencia_animo": tendencia_animo,
        "tendencia_energia": tendencia_energia,
        "tendencia_estres": tendencia_estres,
        "estado_general": estado_general,
        "color_estado": color,
        "datos_diarios": datos_diarios,
        "fecha_actualizacion": datetime.utcnow().isoformat(),
    }


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


def generar_gráfico_lineal(
    titulo: str,
    datos: List[Dict[str, Any]],
    etiqueta_eje_y: str,
    campo_valor: str,
    color: str = "#3b82f6",
) -> Dict[str, Any]:
    """Genera estructura de gráfico lineal para frontend."""
    return {
        "tipo": "lineal",
        "titulo": titulo,
        "etiqueta_eje_y": etiqueta_eje_y,
        "color": color,
        "datos": [
            {
                "fecha": d.get("fecha", ""),
                "valor": d.get(campo_valor, 0),
            }
            for d in datos
        ],
    }


def generar_gráfico_radar(
    titulo: str,
    promedio_animo: float,
    promedio_energia: float,
    promedio_estres: float,
    promedio_sueno: float,
) -> Dict[str, Any]:
    """Genera gráfico radar de bienestar multidimensional."""
    return {
        "tipo": "radar",
        "titulo": titulo,
        "dimensiones": [
            {
                "nombre": "Ánimo",
                "valor": min(10, max(0, promedio_animo)),  # 0-10
                "color": "#3b82f6",
            },
            {
                "nombre": "Energía",
                "valor": min(10, max(0, promedio_energia)),
                "color": "#10b981",
            },
            {
                "nombre": "Estrés (inverso)",
                "valor": min(10, max(0, 10 - promedio_estres)),  # Invertido (menos estrés = mejor)
                "color": "#f59e0b",
            },
            {
                "nombre": "Sueño",
                "valor": min(10, max(0, (promedio_sueno / 12) * 10)),  # Normalizar a 0-10
                "color": "#8b5cf6",
            },
        ],
    }


def generar_gráfico_barras_comparativa(
    titulo: str,
    datos_7dias: Dict[str, Any],
) -> Dict[str, Any]:
    """Genera gráfico de barras comparando ánimo, energía y estrés."""
    return {
        "tipo": "barras",
        "titulo": titulo,
        "categorias": ["Ánimo", "Energía", "Estrés (inverso, más alto = mejor)"],
        "valores": [
            datos_7dias.get("promedio_animo", 5),
            datos_7dias.get("promedio_energia", 5),
            10 - datos_7dias.get("promedio_estres", 5),  # Invertido
        ],
        "colores": ["#3b82f6", "#10b981", "#f59e0b"],
    }

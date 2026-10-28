"""Guías ciudadanas paso a paso por materia (contenido en data/guias.json) con personalización laboral."""
from __future__ import annotations

import copy
from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _base() -> dict:
    return config.cargar_json_datos("guias.json")


def _dinero(x: float) -> str:
    return f"${x:,.2f} MXN"


SUBTIPOS = {"danos_en_trabajo": "Daños en el trabajo (sin contrato o por propinas)"}


def obtener_guia(categoria: str, datos: dict | None = None, resultado=None, oferta: float = 0.0, plazo: dict | None = None,
                 subtipo: str | None = None) -> dict:
    """Devuelve una copia de la guía de la categoría (o la de «Indeterminado»), personalizada si aplica.
    Si se indica un subtipo conocido, usa su guía específica."""
    guias = _base()
    clave_sub = SUBTIPOS.get(subtipo or "")
    if clave_sub and clave_sub in guias:
        return copy.deepcopy(guias[clave_sub])
    guia = copy.deepcopy(guias.get(categoria) or guias["Indeterminado"])
    if categoria == "Casos Laborales":
        _personalizar_laboral(guia, datos or {}, resultado, oferta, plazo)
    guia.pop("radiografia_template", None)
    return guia


def _personalizar_laboral(guia: dict, datos: dict, resultado, oferta: float, plazo: dict | None) -> None:
    sueldo_txt = ""
    if datos.get("salario_monto") and datos.get("periodicidad"):
        sueldo_txt = (
            f"ganabas **{_dinero(datos['salario_monto'])} ({datos['periodicidad'].lower()})**"
            + (f" (≈ {_dinero(datos['salario_diario'] * 30)} al mes)" if datos.get("salario_diario") else "")
            + "; "
        )
    if sueldo_txt or resultado is not None:
        partes = [sueldo_txt or "con los datos que indicaste, "]
        if datos.get("dias_sueldo_pendientes"):
            partes.append(f"te deben **{datos['dias_sueldo_pendientes']} días de sueldo** ya trabajado; ")
        if resultado is not None and oferta and oferta < resultado.total_liquidacion:
            partes.append(
                f"te ofrecen {_dinero(oferta)}, pero la estimación de lo que marca la ley es de **{_dinero(resultado.total_liquidacion)}**. "
            )
        elif resultado is not None:
            partes.append(f"la estimación de lo que marca la ley es de **{_dinero(resultado.total_liquidacion)}**. ")
        guia["radiografia"] = guia["radiografia_template"].format(sueldo_txt="".join(partes), oferta_txt="") if "radiografia_template" in guia else guia["radiografia"]

    extras = []
    if datos.get("sin_contrato") or datos.get("sin_imss"):
        extras.append(
            "🔹 **Sin contrato o sin IMSS:** la falta de alta en el IMSS y de contrato es responsabilidad del patrón, "
            "no una razón para negarte derechos. Pide a la PROFEDET que valore tu caso."
        )
    if datos.get("jornada_larga"):
        extras.append("🔹 **Jornadas muy largas:** podrían generar pago de horas extra (Art. 66 a 68 LFT). Anota tus horarios reales y guarda pruebas.")
    guia["explicacion_sencilla"].extend(extras)

    if plazo and plazo.get("estado") in ("urgente", "vencido"):
        guia["fase_1_hoy"].insert(0, f"**⏰ {plazo['mensaje']}**")

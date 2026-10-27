"""Cotizador de honorarios (referencia) para el despacho. Los valores salen de data/tabulador.json."""
from __future__ import annotations

from . import config


def tabulador_rama(categoria: str) -> dict:
    ramas = config.tabulador()["ramas"]
    return ramas.get(categoria) or ramas["Casos Laborales"]


def calcular_cotizacion(
    monto_en_disputa: float,
    costo_asesoria: float = 1000.0,
    anticipo_fijo: float = 0.0,
    pct_litis: float = 25.0,
    gastos_periciales: float = 1000.0,
    horas_invertidas: float = 35.0,
    costo_hora_despacho: float | None = None,
) -> dict:
    if costo_hora_despacho is None:
        costo_hora_despacho = float(config.tabulador().get("costo_hora_despacho", 350))
    for nombre, valor in (
        ("monto", monto_en_disputa), ("asesoría", costo_asesoria), ("anticipo", anticipo_fijo),
        ("gastos", gastos_periciales), ("horas", horas_invertidas), ("costo por hora", costo_hora_despacho),
    ):
        if valor is None or valor < 0:
            raise ValueError(f"El valor de {nombre} no puede ser negativo")
    if not (0 <= pct_litis <= 50):
        raise ValueError("La cuota litis debe estar entre 0% y 50%")

    comision = round(monto_en_disputa * pct_litis / 100.0, 2)
    honorarios = round(costo_asesoria + anticipo_fijo + comision, 2)
    desembolso = round(honorarios + gastos_periciales, 2)
    neto = round(max(0.0, monto_en_disputa - desembolso), 2)
    costo_interno = round(horas_invertidas * costo_hora_despacho, 2)
    pct_hon = round(100 * honorarios / monto_en_disputa, 1) if monto_en_disputa > 0 else 0.0

    advertencias = []
    if monto_en_disputa > 0 and desembolso >= monto_en_disputa:
        advertencias.append("Los honorarios y gastos igualan o superan el monto en disputa: el cliente no recibiría nada.")
    elif pct_hon > 40:
        advertencias.append("Los honorarios superan el 40% del monto en disputa: revisa si es razonable para el cliente.")
    if pct_litis > 0:
        advertencias.append("La cuota litis debe pactarse por escrito, con el porcentaje y la base de cálculo claros.")

    return {
        "comision_exito": comision,
        "honorarios_totales_abogado": honorarios,
        "desembolso_total_cliente": desembolso,
        "monto_neto_libre_ciudadano": neto,
        "pct_honorarios_sobre_monto": pct_hon,
        "costo_interno_despacho": costo_interno,
        "utilidad_neta_abogado": round(honorarios - costo_interno, 2),
        "advertencias": advertencias,
    }


def texto_propuesta(materia: str, asesoria: float, anticipo: float, pct: float) -> str:
    return (
        f"Estimado(a) cliente, respecto a su asunto de {materia}, la propuesta de honorarios es la siguiente:\n"
        f"- Asesoría inicial: ${asesoria:,.2f} MXN\n"
        f"- Anticipo inicial para gestiones: ${anticipo:,.2f} MXN\n"
        f"- Cuota por éxito (cuota litis): {pct:g}% sobre lo efectivamente recuperado.\n"
        "Los honorarios se formalizarán en un contrato de prestación de servicios por escrito. "
        "Quedamos a sus órdenes para iniciar la defensa jurídica."
    )

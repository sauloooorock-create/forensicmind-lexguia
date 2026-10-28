"""Cálculo de finiquito, liquidación e indemnización según la Ley Federal del Trabajo (LFT).

Todos los valores legales provienen de ``data/leyes.json``. Las cifras son ESTIMACIONES
informativas: el monto final lo determina el convenio ratificado o la autoridad laboral.
"""
from __future__ import annotations

import calendar
import math
from dataclasses import dataclass, field
from datetime import date

from . import config

PERIODOS_DIAS = {"Semanal": 7, "Quincenal": 15, "Mensual": 30, "Diario": 1}
MOTIVOS = {
    "despido": "Despido injustificado (me corrieron)",
    "rescision_patron": "Rescisión por causa del patrón (no me pagan sueldo, maltrato, etc.)",
    "renuncia": "Renuncia voluntaria (yo decidí salirme)",
}


def salario_diario(monto: float, periodicidad: str) -> float:
    """Convierte un sueldo por periodo a salario diario."""
    dias = PERIODOS_DIAS.get(periodicidad)
    if dias is None:
        raise ValueError(f"Periodicidad desconocida: {periodicidad!r}")
    if monto is None or monto < 0:
        raise ValueError("El sueldo no puede ser negativo")
    return round(float(monto) / dias, 2)


def dias_vacaciones(anio_servicio: int) -> int:
    """Días de vacaciones que corresponden en el año de servicio indicado (1, 2, 3...)."""
    anio = max(1, int(anio_servicio))
    tabla = config.leyes()["vacaciones_dias"]
    for tramo in tabla:
        if tramo["desde"] <= anio <= tramo["hasta"]:
            return int(tramo["dias"])
    # Después del último tramo de la tabla (art. 76 LFT reformado): +2 días cada 5 años.
    ultimo = tabla[-1]
    extra = 2 * math.ceil((anio - int(ultimo["hasta"])) / 5)
    return int(ultimo["dias"]) + extra


def vacaciones_no_gozadas_sugeridas(anios_completos: int) -> int:
    """Suma de días de vacaciones de los años completos (si NUNCA gozó vacaciones)."""
    return sum(dias_vacaciones(a) for a in range(1, max(0, int(anios_completos)) + 1))


def factor_integracion(dias_vac: int) -> float:
    ley = config.leyes()
    aguinaldo = float(ley["aguinaldo_dias_minimos"])
    prima = float(ley["prima_vacacional_pct"]) / 100.0
    return 1.0 + aguinaldo / 365.0 + (dias_vac * prima) / 365.0


def agregar_meses(f: date, meses: int) -> date:
    m = f.month - 1 + meses
    anio = f.year + m // 12
    mes = m % 12 + 1
    dia = min(f.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def plazo_reclamo(fecha_separacion: date, hoy: date | None = None) -> dict:
    """Plazo para reclamar un despido injustificado (2 meses, Art. 518 LFT)."""
    hoy = hoy or date.today()
    pres = config.leyes()["prescripcion"]
    limite = agregar_meses(fecha_separacion, int(pres["despido_meses"]))
    restantes = (limite - hoy).days
    transcurridos = (hoy - fecha_separacion).days
    if transcurridos < 0:
        estado, msg = "futuro", "La fecha de separación está en el futuro: revísala."
    elif restantes < 0:
        estado = "vencido"
        msg = (
            f"Pasaron {transcurridos} días desde la separación y el plazo de 2 meses ya venció "
            f"({-restantes} días). Aun así acude cuanto antes a la PROFEDET: pueden existir otras acciones "
            "(por ejemplo, pago de prestaciones, que prescriben en 1 año) y la autoridad valora tu caso."
        )
    elif restantes <= int(pres["aviso_por_vencer_dias"]):
        estado = "urgente"
        msg = f"⚠️ ¡URGENTE! Te quedan solo {restantes} días (hasta el {limite.strftime('%d/%m/%Y')}) para iniciar la conciliación."
    else:
        estado = "vigente"
        msg = f"Te quedan {restantes} días (hasta el {limite.strftime('%d/%m/%Y')}) para iniciar la conciliación por despido."
    return {
        "estado": estado, "mensaje": msg, "fecha_limite": limite,
        "dias_restantes": restantes, "dias_transcurridos": transcurridos,
    }


@dataclass
class DatosLaborales:
    salario_diario: float
    anios: int = 0
    meses: int = 0
    motivo: str = "despido"
    fecha_separacion: date | None = None
    dias_sueldo_pendientes: float = 0.0
    dias_vacaciones_vencidas: float = 0.0
    dias_descanso_trabajados: float = 0.0
    zona_frontera: bool = False
    meses_juicio: int = 12
    tiempo_indeterminado: bool = True


@dataclass
class ResultadoLFT:
    salario_diario: float
    sdi: float
    antiguedad: float
    dias_vacaciones_anio: int
    conceptos: list = field(default_factory=list)
    subtotal_finiquito: float = 0.0
    subtotal_indemnizacion: float = 0.0
    prima_antiguedad: float = 0.0
    total_liquidacion: float = 0.0
    salarios_vencidos_max: float = 0.0
    total_con_salarios_vencidos: float = 0.0
    es_despido: bool = False
    isr_pago_separacion: float = 0.0
    isr_tope_exento: float = 0.0
    isr_gravable_estimado: float = 0.0
    notas: list = field(default_factory=list)

    @property
    def gran_total_bruto(self) -> float:  # compatibilidad con el nombre usado en v10
        return self.total_liquidacion


def _r(x: float) -> float:
    return round(float(x), 2)


def calcular_liquidacion(d: DatosLaborales, hoy: date | None = None) -> ResultadoLFT:
    if d.salario_diario is None or d.salario_diario <= 0:
        raise ValueError("El salario diario debe ser mayor a cero")
    if d.motivo not in MOTIVOS:
        raise ValueError(f"Motivo desconocido: {d.motivo!r}")
    if not (0 <= d.meses <= 11):
        raise ValueError("Los meses adicionales deben estar entre 0 y 11")
    if d.anios < 0:
        raise ValueError("Los años no pueden ser negativos")
    for nombre in ("dias_sueldo_pendientes", "dias_vacaciones_vencidas", "dias_descanso_trabajados"):
        if getattr(d, nombre) < 0:
            raise ValueError(f"{nombre} no puede ser negativo")

    ley = config.leyes()
    ind = ley["indemnizacion"]
    hoy = hoy or date.today()
    fs = d.fecha_separacion or hoy

    sd = float(d.salario_diario)
    antig = d.anios + d.meses / 12.0
    idx_anio = d.anios + 1
    dias_vac_anio = dias_vacaciones(idx_anio)
    sdi = _r(sd * factor_integracion(dias_vac_anio))
    es_despido = d.motivo in ("despido", "rescision_patron")
    minimo = float(ley["salario_minimo"]["frontera_norte" if d.zona_frontera else "general"])
    notas: list[str] = []

    # ---- Finiquito (corresponde siempre, incluso si renuncias) -----------------------
    m_sueldo = _r(d.dias_sueldo_pendientes * sd)

    dias_en_anio = min((fs - date(fs.year, 1, 1)).days + 1, round(antig * 365))
    dias_en_anio = max(0, dias_en_anio)
    m_aguinaldo = _r(float(ley["aguinaldo_dias_minimos"]) * sd * dias_en_anio / 365.0)

    dias_vac_prop = dias_vac_anio * (d.meses / 12.0)
    dias_vac_total = dias_vac_prop + d.dias_vacaciones_vencidas
    m_vacaciones = _r(dias_vac_total * sd)
    m_prima_vac = _r(m_vacaciones * float(ley["prima_vacacional_pct"]) / 100.0)

    extra = float(ley["descanso_trabajado_pago_extra_veces"])
    m_descansos = _r(d.dias_descanso_trabajados * sd * extra)

    conceptos = [
        {"grupo": "Finiquito", "concepto": "Sueldo ya trabajado y no pagado", "fundamento": "Art. 82 y 88 LFT", "monto": m_sueldo,
         "nota": f"{d.dias_sueldo_pendientes:g} días × ${sd:,.2f}"},
        {"grupo": "Finiquito", "concepto": "Aguinaldo proporcional", "fundamento": "Art. 87 LFT", "monto": m_aguinaldo,
         "nota": f"{ley['aguinaldo_dias_minimos']} días/año × {dias_en_anio} días trabajados del año"},
        {"grupo": "Finiquito", "concepto": "Vacaciones (proporcionales + no gozadas)", "fundamento": "Art. 76, 79 LFT", "monto": m_vacaciones,
         "nota": f"{dias_vac_total:.1f} días × ${sd:,.2f}"},
        {"grupo": "Finiquito", "concepto": "Prima vacacional (25%)", "fundamento": "Art. 80 LFT", "monto": m_prima_vac,
         "nota": "25% sobre las vacaciones anteriores"},
        {"grupo": "Finiquito", "concepto": "Descansos trabajados sin pago extra", "fundamento": "Art. 73 LFT", "monto": m_descansos,
         "nota": f"{d.dias_descanso_trabajados:g} días × 2 × ${sd:,.2f} (el día ya va en tu sueldo; se reclama el pago doble)"},
    ]
    subtotal_finiquito = _r(m_sueldo + m_aguinaldo + m_vacaciones + m_prima_vac + m_descansos)

    # ---- Indemnización y prima de antigüedad ----------------------------------------
    m_90 = m_20 = m_prima_ant = 0.0
    tope_sal_prima = min(sd, float(ind["prima_antiguedad_tope_veces_minimo"]) * minimo)
    if es_despido:
        m_90 = _r(float(ind["dias_constitucional"]) * sdi)
        conceptos.append({"grupo": "Indemnización", "concepto": "Indemnización constitucional (3 meses = 90 días)",
                          "fundamento": "Art. 123 Const., Art. 48 y 50 LFT", "monto": m_90,
                          "nota": f"90 días × SDI ${sdi:,.2f}"})
        if d.tiempo_indeterminado:
            m_20 = _r(float(ind["dias_por_anio_art50"]) * antig * sdi)
            conceptos.append({"grupo": "Indemnización", "concepto": "20 días de salario por cada año de servicios",
                              "fundamento": "Art. 50 fr. II LFT", "monto": m_20,
                              "nota": f"20 días × {antig:.2f} años × SDI ${sdi:,.2f}"})
        else:
            notas.append("Para contratos por tiempo determinado el Art. 50 fr. I calcula la indemnización distinto: consulta a la PROFEDET.")
        m_prima_ant = _r(float(ind["prima_antiguedad_dias_por_anio"]) * antig * tope_sal_prima)
        conceptos.append({"grupo": "Indemnización", "concepto": "Prima de antigüedad (12 días por año)",
                          "fundamento": "Art. 162 LFT", "monto": m_prima_ant,
                          "nota": f"12 días × {antig:.2f} años × ${tope_sal_prima:,.2f} (salario topado a 2× mínimo)"})
    else:
        if antig >= float(ind["prima_antiguedad_renuncia_min_anios"]):
            m_prima_ant = _r(float(ind["prima_antiguedad_dias_por_anio"]) * antig * tope_sal_prima)
            conceptos.append({"grupo": "Indemnización", "concepto": "Prima de antigüedad (renuncia con 15+ años)",
                              "fundamento": "Art. 162 fr. III LFT", "monto": m_prima_ant, "nota": "Aplica por tener 15 años o más"})
        notas.append("Con renuncia voluntaria corresponde solo el finiquito (y prima de antigüedad con 15+ años). "
                     "Si te presionaron para renunciar o te retuvieron el sueldo, podría ser un despido encubierto: consulta a la PROFEDET.")

    subtotal_indemnizacion = _r(m_90 + m_20)
    total_liquidacion = _r(subtotal_finiquito + subtotal_indemnizacion + m_prima_ant)

    # ---- Salarios vencidos (solo si hay juicio por despido) --------------------------
    sal_venc = 0.0
    if es_despido:
        meses = max(0, min(int(d.meses_juicio), int(ind["salarios_vencidos_max_meses"])))
        sal_venc = _r(sdi * 30 * meses)
        notas.append(
            f"Salarios vencidos (Art. 48 LFT): hasta {ind['salarios_vencidos_max_meses']} meses desde el despido ≈ ${sal_venc:,.2f}. "
            "Solo se generan si el caso llega a juicio y se gana; en conciliación suele negociarse un convenio."
        )
    if d.anios == 0 and d.meses < 3:
        notas.append("Con menos de 3 meses de antigüedad los montos de indemnización pueden variar; consulta a la PROFEDET.")

    # ---- ISR (informativo) -------------------------------------------------------------
    pago_sep = _r(subtotal_indemnizacion + m_prima_ant)
    anios_isr = max(1, d.anios + (1 if d.meses > 6 else 0))
    tope_exento = _r(float(ley["isr"]["exento_uma_por_anio_servicio"]) * float(ley["uma"]["diaria"]) * anios_isr)
    gravable = _r(max(0.0, pago_sep - tope_exento))

    return ResultadoLFT(
        salario_diario=sd, sdi=sdi, antiguedad=_r(antig), dias_vacaciones_anio=dias_vac_anio,
        conceptos=conceptos, subtotal_finiquito=subtotal_finiquito, subtotal_indemnizacion=subtotal_indemnizacion,
        prima_antiguedad=m_prima_ant, total_liquidacion=total_liquidacion, salarios_vencidos_max=sal_venc,
        total_con_salarios_vencidos=_r(total_liquidacion + sal_venc), es_despido=es_despido,
        isr_pago_separacion=pago_sep, isr_tope_exento=tope_exento, isr_gravable_estimado=gravable, notas=notas,
    )


def comparar_oferta(total_ley: float, oferta: float) -> dict:
    """Compara lo que ofrece el patrón contra lo que marca la ley."""
    oferta = max(0.0, float(oferta or 0))
    diferencia = _r(max(0.0, total_ley - oferta))
    pct = _r(100 * oferta / total_ley) if total_ley > 0 else 0.0
    return {"oferta": oferta, "diferencia": diferencia, "pct_de_lo_legal": pct, "oferta_menor": oferta > 0 and oferta < total_ley}

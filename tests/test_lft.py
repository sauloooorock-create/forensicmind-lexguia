"""Pruebas del cálculo de la LFT con valores calculados a mano.

Ejecutar con pytest:  python -m pytest tests -q
o directamente:       python tests/test_lft.py
"""

import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from forensicmind import lft  # noqa: E402


def _monto(res, nombre_inicia):
    for c in res.conceptos:
        if c["concepto"].startswith(nombre_inicia):
            return c["monto"]
    return None


# ---------------------------------------------------------------------
# Vacaciones (art. 76 LFT): tabla y extensión después del último tramo
# ---------------------------------------------------------------------
def test_vacaciones_por_tramo():
    casos = {1: 12, 2: 14, 5: 20, 6: 22, 10: 22, 11: 24, 46: 38, 50: 38}
    for anios, dias in casos.items():
        assert lft.dias_vacaciones(anios) == dias, anios


def test_vacaciones_mas_de_50_anios_suman_2_cada_5():
    # 51–55 → 40, 56–60 → 42 (antes devolvía 38 para todos los años > 50)
    casos = {51: 40, 55: 40, 56: 42, 60: 42, 61: 44}
    for anios, dias in casos.items():
        assert lft.dias_vacaciones(anios) == dias, anios


# ---------------------------------------------------------------------
# Fechas y periodicidad
# ---------------------------------------------------------------------
def test_agregar_meses_respeta_fin_de_mes():
    assert lft.agregar_meses(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert lft.agregar_meses(date(2025, 1, 31), 1) == date(2025, 2, 28)


def test_salario_diario_por_periodicidad():
    assert lft.salario_diario(3000, "Quincenal") == 200.0
    assert lft.salario_diario(3000, "Mensual") == 100.0
    assert lft.salario_diario(700, "Semanal") == 100.0


# ---------------------------------------------------------------------
# Liquidación con cifras verificadas a mano
# ---------------------------------------------------------------------
def test_aguinaldo_proporcional_renuncia():
    # Separación el 30-jun-2026 (día 181 del año). Aguinaldo = 15 × 100 × 181 / 365 = 743.84
    d = lft.DatosLaborales(salario_diario=100.0, anios=2, meses=0, motivo="renuncia",
                           fecha_separacion=date(2026, 6, 30))
    res = lft.calcular_liquidacion(d, hoy=date(2026, 6, 30))
    assert _monto(res, "Aguinaldo proporcional") == 743.84


def test_renuncia_no_paga_indemnizacion_constitucional():
    d = lft.DatosLaborales(salario_diario=100.0, anios=2, meses=0, motivo="renuncia",
                           fecha_separacion=date(2026, 6, 30))
    res = lft.calcular_liquidacion(d, hoy=date(2026, 6, 30))
    assert _monto(res, "Indemnización constitucional") is None


def test_despido_indemnizacion_constitucional_y_20_dias():
    # SDI = 100 × (1 + 15/365 + 16×0.25/365) = 105.2054… → 105.21
    # 90 días × 105.21 = 9468.90 ; 20 días × 2 años × 105.21 = 4208.40
    d = lft.DatosLaborales(salario_diario=100.0, anios=2, meses=0, motivo="despido",
                           fecha_separacion=date(2026, 6, 30), tiempo_indeterminado=True)
    res = lft.calcular_liquidacion(d, hoy=date(2026, 6, 30))
    assert _monto(res, "Indemnización constitucional") == 9468.90
    assert _monto(res, "20 días de salario") == 4208.40


if __name__ == "__main__":
    fallos = 0
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"✅ {nombre}")
            except Exception as exc:  # noqa: BLE001
                fallos += 1
                print(f"❌ {nombre}: {exc!r}")
    print("Todas las pruebas pasaron." if not fallos else f"{fallos} prueba(s) fallaron.")
    sys.exit(1 if fallos else 0)

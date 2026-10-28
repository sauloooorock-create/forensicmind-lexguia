"""Pruebas del control de administración: ajustes legales, edición de casos y respaldo.

Usan una base y un archivo de ajustes temporales; nunca tocan los datos reales.
Ejecutar con pytest:  python -m pytest tests -q
o directamente:       python tests/test_admin.py
"""

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

_TMP = tempfile.mkdtemp(prefix="fm_test_")
os.environ["FM_DB_PATH"] = os.path.join(_TMP, "prueba.db")
os.environ["FM_AJUSTES_PATH"] = os.path.join(_TMP, "ajustes_legales.json")

from forensicmind import config, db  # noqa: E402


def _limpiar():
    ruta = config._ruta_ajustes()
    if ruta.exists():
        ruta.unlink()
    config.leyes.cache_clear()


def _anio() -> int:
    return date.today().year


# ---------------------------------------------------------------------
# Cifras legales
# ---------------------------------------------------------------------
def test_cambio_valido_se_aplica_y_conserva_el_resto():
    _limpiar()
    base = config.leyes_base()
    problemas = config.guardar_ajustes_legales({"salario_minimo": {"general": 330.0}, "vigencia_anio": _anio()})
    assert problemas == []
    efectivo = config.leyes()
    assert efectivo["salario_minimo"]["general"] == 330.0
    assert efectivo["salario_minimo"]["frontera_norte"] == base["salario_minimo"]["frontera_norte"]
    assert config.leyes_base()["salario_minimo"]["general"] == base["salario_minimo"]["general"]
    _limpiar()


def test_cambio_invalido_no_se_guarda():
    _limpiar()
    problemas = config.guardar_ajustes_legales({"salario_minimo": {"general": -5.0}, "vigencia_anio": _anio()})
    assert problemas
    assert not config._ruta_ajustes().exists()
    _limpiar()


def test_tabla_de_vacaciones_con_hueco_se_rechaza():
    _limpiar()
    tabla = [{"desde": 1, "hasta": 1, "dias": 12}, {"desde": 3, "hasta": 5, "dias": 16}]
    problemas = config.guardar_ajustes_legales({"vacaciones_dias": tabla, "vigencia_anio": _anio()})
    assert any("huecos" in p for p in problemas)
    _limpiar()


def test_restablecer_vuelve_a_leyes_json():
    _limpiar()
    config.guardar_ajustes_legales({"uma": {"diaria": 120.0}, "vigencia_anio": _anio()})
    assert config.leyes()["uma"]["diaria"] == 120.0
    config.restablecer_ajustes_legales()
    assert config.leyes()["uma"]["diaria"] == config.leyes_base()["uma"]["diaria"]
    _limpiar()


# ---------------------------------------------------------------------
# Casos, memoria y buzón
# ---------------------------------------------------------------------
def test_editar_y_borrar_caso():
    db.init_db()
    casos = db.listar_casos()
    assert casos, "la semilla debe traer casos"
    id_caso = casos[0]["id"]
    ok = db.actualizar_caso(id_caso, {"titulo": "Título editado", "origen": "hackeado",
                                      "evidencia_logs": "Contacto: juan@correo.com y 55 1234 5678"})
    assert ok
    editado = db.obtener_caso(id_caso)
    assert editado["titulo"] == "Título editado"
    assert editado["origen"] != "hackeado", "campos fuera de la lista permitida no se editan"
    assert "juan@correo.com" not in (editado["evidencia_logs"] or ""), "el texto libre se anonimiza"
    assert db.eliminar_caso(id_caso) is True
    assert db.obtener_caso(id_caso) is None


def test_respaldo_incluye_y_restaura_ajustes_legales():
    _limpiar()
    db.init_db()
    config.guardar_ajustes_legales({"aguinaldo_dias_minimos": 20, "vigencia_anio": _anio()})
    respaldo = db.exportar_respaldo()
    assert respaldo["ajustes_legales"]["aguinaldo_dias_minimos"] == 20

    config.restablecer_ajustes_legales()
    assert config.leyes()["aguinaldo_dias_minimos"] == config.leyes_base()["aguinaldo_dias_minimos"]

    nuevos = db.importar_respaldo(respaldo)
    assert nuevos["ajustes_legales"] is True
    assert config.leyes()["aguinaldo_dias_minimos"] == 20
    _limpiar()


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

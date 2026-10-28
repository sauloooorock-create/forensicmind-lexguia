"""Pruebas básicas: datos legales vigentes y seguridad de enlaces.

Ejecutar con pytest:  python -m pytest tests -q
o directamente:       python tests/test_basico.py
"""

import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def test_leyes_vigentes_al_dia_actual():
    """Si cambia el año y no se actualiza data/leyes.json, esta prueba falla."""
    leyes = json.loads((RAIZ / "data" / "leyes.json").read_text(encoding="utf-8"))
    assert leyes["vigencia_anio"] == date.today().year, (
        "Actualiza data/leyes.json (salario mínimo, UMA, vigencia_anio y version)."
    )


def test_datos_json_son_validos():
    for ruta in (RAIZ / "data").glob("*.json"):
        json.loads(ruta.read_text(encoding="utf-8"))


def test_url_segura_bloquea_esquemas_peligrosos():
    from forensicmind.security import url_segura

    assert url_segura("javascript:alert(1)") == "#"
    assert url_segura("data:text/html,hola") == "#"
    assert url_segura("https://www.gob.mx/profeco") == "https://www.gob.mx/profeco"


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

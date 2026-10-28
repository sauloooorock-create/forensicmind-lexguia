"""Pruebas de las guías: la guía de daños en el trabajo y que el resto no cambia.

Ejecutar con pytest:  python -m pytest tests -q
o directamente:       python tests/test_guias.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from forensicmind import guias  # noqa: E402


def _texto(g: dict) -> str:
    partes = []
    for v in g.values():
        partes.extend(v if isinstance(v, list) else [str(v)])
    return " ".join(partes)


def test_guia_danos_tiene_que_hacer_y_que_no_hacer():
    g = guias.obtener_guia("Casos Laborales", subtipo="danos_en_trabajo")
    texto = _texto(g)
    assert "No pagues" in texto
    assert "No firmes" in texto
    assert "PROFEDET" in texto
    assert "Borrar mensajes" in texto  # error fatal


def test_guia_danos_no_menciona_liquidacion_de_despido():
    g = guias.obtener_guia("Casos Laborales", subtipo="danos_en_trabajo")
    assert "liquidación" not in " ".join(g["fase_1_hoy"]).lower()


def test_guia_laboral_normal_no_cambia_con_el_subtipo_nuevo():
    normal = guias.obtener_guia("Casos Laborales")
    assert "No pagues" not in _texto(normal)
    assert normal["abogado_req"] != guias.obtener_guia("Casos Laborales", subtipo="danos_en_trabajo")["abogado_req"]


def test_guia_danos_incluye_seguridad_y_propuesta_de_solucion():
    g = guias.obtener_guia("Casos Laborales", subtipo="danos_en_trabajo")
    texto = _texto(g)
    assert "Tu seguridad va primero" in texto or "Tu seguridad primero" in texto
    assert "Propuesta de solución" in texto
    assert "aseguradora" in texto
    assert "peritaje independiente" in texto
    assert "Si el cliente te amenaza" in texto


def test_guia_danos_explica_despido_sin_contrato():
    texto = _texto(guias.obtener_guia("Casos Laborales", subtipo="danos_en_trabajo"))
    assert "Art. 47" in texto
    assert "Art. 48" in texto
    assert "Art. 784" in texto
    assert "Plazo de 2 meses" in texto


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

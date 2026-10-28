"""Pruebas de la IA de respaldo con respuestas simuladas (sin red).

Ejecutar con pytest:  python -m pytest tests -q
o directamente:       python tests/test_ia.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from forensicmind import ia_respaldo  # noqa: E402

_original = ia_respaldo._llamar


def _simular(respuesta: dict):
    ia_respaldo._llamar = lambda *a, **k: respuesta


def _restaurar():
    ia_respaldo._llamar = _original


def test_sin_clave_no_llama_a_la_api():
    _restaurar()
    assert ia_respaldo.clasificar_indeterminado("texto", "", "modelo") == {}
    assert ia_respaldo.proponer_caso("texto", "", "modelo") == {}


def test_clasificacion_valida_se_acepta():
    _simular({"categoria": "Casos Laborales", "motivo": "Daño en el trabajo"})
    r = ia_respaldo.clasificar_indeterminado("relato", "clave", "modelo")
    assert r["categoria"] == "Casos Laborales"
    _restaurar()


def test_categoria_inventada_se_descarta():
    _simular({"categoria": "Casos Espaciales", "motivo": "x"})
    assert ia_respaldo.clasificar_indeterminado("relato", "clave", "modelo") == {}
    _restaurar()


def test_propuesta_con_resultado_invalido_se_descarta():
    _simular({"titulo": "Caso", "categoria_caso": "Casos Laborales", "resultado": "EMPATE"})
    assert ia_respaldo.proponer_caso("relato", "clave", "modelo") == {}
    _restaurar()


def test_propuesta_valida_se_anonimiza_y_queda_ilustrativa():
    _simular({
        "titulo": "Daño en el trabajo", "categoria_caso": "Casos Laborales", "resultado": "GANADO",
        "evidencia_logs": "Contacto: juan@correo.com y 55 1234 5678",
        "estrategia_ganadora": "Pedir reporte por escrito", "que_hacer_ciudadano": "Guardar pruebas",
        "que_no_hacer_ciudadano": "No firmar",
    })
    p = ia_respaldo.proponer_caso("relato", "clave", "modelo")
    assert p["ilustrativo"] == 1
    assert "juan@correo.com" not in p["evidencia_logs"]
    _restaurar()


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

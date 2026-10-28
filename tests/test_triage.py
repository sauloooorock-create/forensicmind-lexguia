"""Pruebas del triage: casos laborales por daños en el trabajo y control de no laborales.

Ejecutar con pytest:  python -m pytest tests -q
o directamente:       python tests/test_triage.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from forensicmind import triage  # noqa: E402

CASO_DANOS_EN_TRABAJO = (
    "Trabajo en una bodega de autoservicio como acomodador. Iba bajando con el diablito un refrigerador muy grande "
    "por la rampa y se me cayo. El cliente ya se quiere cobrar 15 mil de los danos del refrigerador. Fue a gerencia "
    "y me dijeron que me arregle con el cliente. Que hago?"
)


def test_danos_en_el_trabajo_se_clasifican_como_laboral():
    assert triage.diagnosticar(CASO_DANOS_EN_TRABAJO)["categoria"] == "Casos Laborales"


def test_descuento_de_sueldo_por_danos_es_laboral():
    texto = "Me quieren descontar 15 mil de mi sueldo por un producto que se dano en la tienda donde trabajo."
    assert triage.diagnosticar(texto)["categoria"] == "Casos Laborales"


def test_cargo_no_reconocido_no_se_vuelve_laboral():
    texto = "Me cobraron un cargo no reconocido en mi tarjeta y el banco no responde."
    assert triage.diagnosticar(texto)["categoria"] != "Casos Laborales"


def test_subtipo_danos_en_trabajo_se_detecta():
    assert triage.subtipo_laboral(CASO_DANOS_EN_TRABAJO) == "danos_en_trabajo"


def test_despido_no_usa_el_subtipo_de_danos():
    assert triage.subtipo_laboral("Me despidieron sin pagarme finiquito ni vacaciones.") is None


def test_amenaza_de_golpes_del_cliente_activa_alerta():
    tipos = [a["tipo"] for a in triage.detectar_alertas("El cliente me quiere pegar y dice que me va a demandar")]
    assert "agresion_cliente" in tipos


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

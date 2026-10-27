"""Fundamentos legales en lenguaje sencillo (paráfrasis con artículo de referencia)."""
from __future__ import annotations

from functools import lru_cache

from . import config


@lru_cache(maxsize=1)
def _cargar() -> dict:
    return config.cargar_json_datos("base_legal.json")


def aviso() -> str:
    return _cargar()["aviso"]


def fundamentos_para(categorias: list[str] | str) -> list[dict]:
    """Fundamentos relevantes para una o varias categorías, sin repetir."""
    if isinstance(categorias, str):
        categorias = [categorias]
    vistos, salida = set(), []
    for f in _cargar()["fundamentos"]:
        if any(c in f["categorias"] for c in categorias) and f["id"] not in vistos:
            vistos.add(f["id"])
            salida.append(f)
    return salida

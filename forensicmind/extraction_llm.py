"""Extracción opcional con un LLM (Anthropic API). OPT-IN: solo si hay API key y el usuario lo autoriza.

Privacidad: el texto se anonimiza ANTES de enviarse. Si falla la red o la respuesta es inválida,
se ignora y se usa la extracción local (regex).
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import date

from .security import anonimizar

API_URL = "https://api.anthropic.com/v1/messages"
PERIODOS_VALIDOS = {"Semanal", "Quincenal", "Mensual", "Diario"}

PROMPT = """Extrae datos laborales del siguiente relato de una persona en México.
Responde ÚNICAMENTE con un objeto JSON (sin texto adicional) con estas claves; usa null si el dato no aparece
explícitamente (no inventes):
{{"salario_monto": numero|null, "periodicidad": "Semanal"|"Quincenal"|"Mensual"|"Diario"|null,
  "oferta_patronal": numero|null, "dias_sueldo_pendientes": numero|null,
  "anios": entero|null, "meses": entero|null, "fecha_separacion": "AAAA-MM-DD"|null}}
La fecha de hoy es {hoy}. Relato:
<<<
{relato}
>>>"""


def validar(d: dict, hoy: date | None = None) -> dict:
    """Filtra y valida la respuesta del LLM; descarta campos fuera de rango."""
    hoy = hoy or date.today()
    out: dict = {}
    if not isinstance(d, dict):
        return out

    def num(k, lo, hi):
        v = d.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        return float(v) if lo <= v <= hi else None

    s = num("salario_monto", 50, 10_000_000)
    if s is not None:
        out["salario_monto"] = s
    if d.get("periodicidad") in PERIODOS_VALIDOS:
        out["periodicidad"] = d["periodicidad"]
    o = num("oferta_patronal", 0, 100_000_000)
    if o is not None:
        out["oferta_patronal"] = o
    p = num("dias_sueldo_pendientes", 0, 720)
    if p is not None:
        out["dias_sueldo_pendientes"] = int(p)
    a = num("anios", 0, 60)
    if a is not None:
        out["anios"] = int(a)
    m = num("meses", 0, 11)
    if m is not None:
        out["meses"] = int(m)
    f = d.get("fecha_separacion")
    if isinstance(f, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", f):
        try:
            fecha = date.fromisoformat(f)
            if date(hoy.year - 3, 1, 1) <= fecha <= hoy:
                out["fecha_separacion"] = fecha
        except ValueError:
            pass
    return out


def extraer_con_llm(relato: str, api_key: str, modelo: str, timeout: float = 20.0, hoy: date | None = None) -> dict:
    """Llama a la API. Devuelve {} ante cualquier problema."""
    if not api_key or not relato.strip():
        return {}
    hoy = hoy or date.today()
    cuerpo = {
        "model": modelo, "max_tokens": 400,
        "messages": [{"role": "user", "content": PROMPT.format(hoy=hoy.isoformat(), relato=anonimizar(relato)[:4000])}],
    }
    req = urllib.request.Request(
        API_URL, data=json.dumps(cuerpo).encode("utf-8"), method="POST",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        texto = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", texto, re.S)
        return validar(json.loads(m.group(0)), hoy) if m else {}
    except (urllib.error.URLError, ValueError, KeyError, TypeError, OSError):
        return {}


def fusionar(datos_regex: dict, datos_llm: dict) -> dict:
    """El LLM solo rellena lo que la extracción local dejó vacío (la extracción local manda)."""
    res = dict(datos_regex)
    for k, v in datos_llm.items():
        vacio = res.get(k) in (None, 0, 0.0, "")
        if vacio:
            res[k] = v
    if res.get("salario_monto") and res.get("periodicidad") and not res.get("salario_diario"):
        from .lft import salario_diario
        res["salario_diario"] = salario_diario(res["salario_monto"], res["periodicidad"])
    res["faltan_datos"] = [
        x for x in res.get("faltan_datos", [])
        if not (
            (x == "sueldo" and res.get("salario_monto")) or (x == "periodicidad del sueldo" and res.get("periodicidad"))
            or (x == "antigüedad" and res.get("anios") is not None) or (x == "fecha del despido" and res.get("fecha_separacion"))
        )
    ]
    return res

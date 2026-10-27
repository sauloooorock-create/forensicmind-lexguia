"""Consulta de información pública en internet (Wikipedia y Google Noticias) con caché y tiempos límite."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .security import url_segura

UA = {"User-Agent": "ForensicMindBot/11.0 (+orientacion-legal)"}
MAX_BYTES = 600_000
TTL_SEG = 3600
_CACHE: dict[str, tuple[float, dict]] = {}


def _get(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_BYTES)


def _limpiar_html(texto: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", texto or "")).strip()


def buscar_wikipedia(consulta: str, limite: int = 2, timeout: float = 3.5) -> list[dict]:
    url = (
        "https://es.wikipedia.org/w/api.php?action=query&list=search"
        f"&srsearch={urllib.parse.quote(consulta)}&utf8=&format=json&srlimit={int(limite)}"
    )
    try:
        data = json.loads(_get(url, timeout).decode("utf-8"))
    except Exception:
        return []
    salida = []
    for item in data.get("query", {}).get("search", [])[:limite]:
        titulo = str(item.get("title", "")).strip()
        if not titulo:
            continue
        salida.append({
            "fuente": "📖 Enciclopedia (Wikipedia)",
            "titulo": titulo,
            "resumen": _limpiar_html(item.get("snippet", "")),
            "url": f"https://es.wikipedia.org/wiki/{urllib.parse.quote(titulo.replace(' ', '_'))}",
        })
    return salida


def buscar_noticias(consulta: str, limite: int = 3, timeout: float = 4.0) -> list[dict]:
    url = (
        "https://news.google.com/rss/search?"
        f"q={urllib.parse.quote(consulta)}&hl=es-419&gl=MX&ceid=MX:es-419"
    )
    try:
        raiz = ET.fromstring(_get(url, timeout))
    except Exception:
        return []
    salida = []
    for it in raiz.findall(".//item")[:limite]:
        titulo = _limpiar_html(it.findtext("title") or "")
        enlace = (it.findtext("link") or "").strip()
        if not titulo or url_segura(enlace) == "#":
            continue
        salida.append({
            "fuente": "🌐 Noticias recientes (Google Noticias México)",
            "titulo": titulo,
            "resumen": f"Nota publicada el {_limpiar_html(it.findtext('pubDate') or 'fecha no disponible')}.",
            "url": enlace,
        })
    return salida


CONSULTAS_NOTICIAS = {
    "Casos Laborales": "despido injustificado liquidación PROFEDET Ley Federal del Trabajo México",
    "Tránsito y Abuso Policial": "abuso policial extorsión corralón Asuntos Internos México",
    "Acoso de Cobranza y Deudas": "despachos de cobranza amenazas embargo CONDUSEF México",
    "Casos Penales y Fraudes": "robo de identidad fraude bancario CONDUSEF México",
    "Casos Familiares": "pensión alimenticia derechos México",
    "Casos Civiles y Mercantiles": "arrendamiento pagaré juicio México",
}


def buscar_informacion(categoria: str, tipo: str) -> list[dict]:
    """Resultados web para una materia (con caché de 1 hora). Nunca lanza excepciones."""
    clave = f"{categoria}|{tipo}"
    ahora = time.time()
    if clave in _CACHE and ahora - _CACHE[clave][0] < TTL_SEG:
        return _CACHE[clave][1]["resultados"]
    resultados = buscar_wikipedia(f"{tipo} México") + buscar_noticias(CONSULTAS_NOTICIAS.get(categoria, f"{tipo} derechos México"))
    _CACHE[clave] = (ahora, {"resultados": resultados})
    return resultados

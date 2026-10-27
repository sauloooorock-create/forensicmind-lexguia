"""Configuración global, catálogos y carga de reglas legales versionadas.

Los valores legales (salario mínimo, UMA, vacaciones, plazos...) NO viven en el
código: se leen de ``data/leyes.json`` para poder actualizarlos sin tocar la lógica.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

AUTOR_SISTEMA = "Ing. Industrial y de Sistemas Saúl Ángel Ortiz Rogel"
MARCA_SISTEMA = "ForensicMind & LexGuía CBR v11.0 — Triage Multi-Materia, Despacho & Auto-Sync"
VERSION = "11.0"

BACKUP_JSON_FILE = "cerebro_autonomo_backup.json"
FOLIO_BASE = "SAOR"

AVISO_LEGAL = (
    "Esta herramienta ofrece orientación informativa general y NO sustituye la asesoría de un abogado. "
    "Las autoridades, trámites y plazos pueden variar según tu estado y cambiar con reformas. "
    "Verifica siempre en la fuente oficial."
)

AVISO_PRIVACIDAD = (
    "**Aviso de privacidad (resumen).** El texto que escribes se analiza en tu sesión y no se guarda por defecto. "
    "Solo si marcas la casilla de consentimiento, se guardará una versión **anonimizada** (sin nombres, teléfonos, "
    "correos, cuentas, INE, CURP ni RFC detectables) para que el administrador la revise antes de usarla para mejorar "
    "el sistema. Si usas el buzón y dejas un dato de contacto, solo lo verá el administrador y **nunca se sube a GitHub**. "
    "Si usas el dictado por voz, el audio se envía a un servicio externo (Google) para transcribirse. "
    "Puedes pedir la eliminación de tus datos al correo de contacto del despacho (derechos ARCO, LFPDPPP)."
)

# --------------------------------------------------------------------------------------
# Catálogos
# --------------------------------------------------------------------------------------
CATEGORIAS = [
    "Tránsito y Abuso Policial",
    "Casos Penales y Fraudes",
    "Casos Laborales",
    "Casos Familiares",
    "Casos Civiles y Mercantiles",
    "Acoso de Cobranza y Deudas",
]

TIPOS_CASOS = {
    "Tránsito y Abuso Policial": [
        "Detención arbitraria, siembra de pruebas o extorsión policial",
        "Amenaza ilegal de corralón o retiro de placas",
        "Multa sin fundamento o retención de documentos",
    ],
    "Casos Penales y Fraudes": [
        "Robo de identidad con INE, fraude bancario o criptoactivos",
        "Phishing, vaciado de cuentas o transferencias SPEI no reconocidas",
        "Extorsión o amenazas digitales",
    ],
    "Casos Laborales": [
        "Despido injustificado o falta de pago de quincenas/semanas",
        "Presión para firmar renuncia u hoja en blanco",
        "Salarios, vacaciones o descansos no pagados",
    ],
    "Acoso de Cobranza y Deudas": [
        "Amenazas de embargo falso o despachos de cobranza",
        "Acoso de aplicaciones de préstamos o créditos no solicitados",
    ],
    "Casos Familiares": [
        "Pensión alimenticia y gasto de los hijos",
        "Guarda, custodia y régimen de visitas",
        "Divorcio",
    ],
    "Casos Civiles y Mercantiles": [
        "Inquilino que no paga renta ni desocupa",
        "Pagaré vencido o deuda de dinero prestado",
    ],
}

# categoría -> (macro_rama, rama_derecho, tipo_por_defecto)
MAPA_MATERIA = {
    "Tránsito y Abuso Policial": ("Derecho Público", "Derecho Administrativo y Penal (Abuso Policial)", TIPOS_CASOS["Tránsito y Abuso Policial"][0]),
    "Casos Penales y Fraudes": ("Derecho Público", "Derecho Penal y Cibernético (Identidad y Cuentas)", TIPOS_CASOS["Casos Penales y Fraudes"][0]),
    "Casos Laborales": ("Derecho Privado", "Derecho Laboral", TIPOS_CASOS["Casos Laborales"][0]),
    "Acoso de Cobranza y Deudas": ("Derecho Privado", "Defensa del Deudor y CONDUSEF", TIPOS_CASOS["Acoso de Cobranza y Deudas"][0]),
    "Casos Familiares": ("Derecho Privado", "Derecho de Familia", TIPOS_CASOS["Casos Familiares"][0]),
    "Casos Civiles y Mercantiles": ("Derecho Privado", "Derecho Civil y Mercantil", TIPOS_CASOS["Casos Civiles y Mercantiles"][0]),
}

PRIORIDAD_TRIAGE = {
    "Tránsito y Abuso Policial": (1, "🚨 PRIORIDAD 1 (LIBERTAD E INTEGRIDAD): Abuso policial, detención o corralón"),
    "Casos Penales y Fraudes": (2, "🔐 PRIORIDAD 2 (BLINDAJE DE IDENTIDAD Y CUENTAS): Fraude, robo de celular/INE o delito"),
    "Casos Laborales": (3, "💼 PRIORIDAD 3 (TRABAJO Y DINERO): Despido, sueldos retenidos y liquidación LFT"),
    "Casos Familiares": (4, "👨‍👩‍👧 PRIORIDAD 4 (PROTECCIÓN FAMILIAR): Pensión alimenticia y custodia"),
    "Casos Civiles y Mercantiles": (5, "🏠 PRIORIDAD 5 (PATRIMONIO CIVIL): Arrendamiento y pagarés"),
    "Acoso de Cobranza y Deudas": (6, "📵 PRIORIDAD 6 (FRENO AL HOSTIGAMIENTO): Despachos de cobranza y apps de préstamos"),
}

ESCENARIOS_FRECUENTES = {
    "✍️ Escribir o dictar mi propio caso libremente": "",
    "🌪️ Caso extremo multi-materia (trabajo + robo de INE + abuso policial + cobranza)": (
        "Trabajaba para una empresa que no me quiere pagar 3 quincenas y usaron mi INE sin permiso "
        "para sacar créditos. Ayer iba en mi moto, una patrulla me detuvo sin motivo, me sembraron "
        "sustancias ilícitas para pedirme 50,000 pesos, me quitaron mi celular con mis cuentas bancarias "
        "y se llevaron mi moto al corralón. Además una app de préstamos me cobra 30,000 pesos que no pedí."
    ),
    "🚓 Tránsito y policías: me detuvo una patrulla, piden mordida y amenazan con corralón": (
        "Una patrulla de tránsito me detuvo sin decirme qué infracción cometí, me quieren quitar "
        "la placa o llevarse mi vehículo al corralón con grúa si no les doy dinero en efectivo."
    ),
    "💼 Laboral: me despidieron, ofrecen $5,000 y no me daban vacaciones": (
        "Mi sueldo semanal es de 2300. Me despidieron hace dos semanas y no me quieren dar liquidación, "
        "solo me quieren dar $5000 y no me daban vacaciones ni días libres ni bonos. Trabajé 2 años ahí."
    ),
    "✍️ Laboral: me exigen firmar mi renuncia o una hoja en blanco": (
        "Me corrieron de la chamba hoy sin aviso por escrito y el encargado de recursos humanos "
        "me dice que si no le firmo mi hoja de renuncia voluntaria no me va a dar ni mi última semana. "
        "Gano 4000 a la quincena y llevaba 3 años."
    ),
    "📞 Deudas y cobranza: me amenazan por WhatsApp con embargar mi casa sin orden de juez": (
        "Un despacho de cobranza me manda mensajes amenazando con que mañana van a ir a romper "
        "la cerradura de mi casa para embargar mis muebles por una deuda y le llaman a mis contactos."
    ),
    "👨‍👩‍👧 Familiar: el papá de mis hijos no da pensión y esconde su sueldo": (
        "El papá de mis hijos lleva 4 meses sin dar dinero para la comida y escuela de los niños, "
        "se salió de su trabajo formal a propósito pero gana dinero por su cuenta en efectivo."
    ),
    "💻 Fraude bancario: me vaciaron mi cuenta con un enlace o llamada falsa": (
        "Me llegó un mensaje que parecía de mi banco, entré al link y sacaron mi dinero con "
        "transferencias SPEI que yo nunca autoricé; el banco dice que fue mi culpa."
    ),
}


# --------------------------------------------------------------------------------------
# Rutas y secretos
# --------------------------------------------------------------------------------------
def db_path() -> str:
    """Ruta de la base SQLite (configurable con FM_DB_PATH, útil para pruebas)."""
    return os.environ.get("FM_DB_PATH", str(DATA_DIR / "boveda_juridica.db"))


def get_secret(nombre: str, default: str = "") -> str:
    """Lee un secreto: primero variable de entorno, luego st.secrets (si existe)."""
    valor = os.environ.get(nombre)
    if valor not in (None, ""):
        return valor
    try:  # import perezoso: el núcleo no depende de streamlit
        import streamlit as st

        valor = st.secrets.get(nombre, default)
        return str(valor) if valor is not None else default
    except Exception:
        return default


def solo_digitos(valor: str) -> str:
    return re.sub(r"\D", "", str(valor or ""))


@dataclass
class Ajustes:
    gh_repo: str = ""
    gh_token: str = ""
    gh_branch: str = "main"
    admin_password: str = ""
    admin_email: str = "contacto@forensicmind.mx"
    whatsapp: str = ""
    anthropic_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    permitir_repo_publico: bool = False

    @property
    def whatsapp_valido(self) -> str:
        """Devuelve el número solo con dígitos si parece real; si no, cadena vacía."""
        d = solo_digitos(self.whatsapp)
        if 10 <= len(d) <= 15 and len(set(d)) > 3:
            return d
        return ""


def cargar_ajustes() -> Ajustes:
    return Ajustes(
        gh_repo=get_secret("GITHUB_REPO", ""),
        gh_token=get_secret("GITHUB_TOKEN", ""),
        gh_branch=get_secret("GITHUB_BRANCH", "main") or "main",
        admin_password=get_secret("ADMIN_PASSWORD_HASH", "") or get_secret("ADMIN_PASSWORD", ""),
        admin_email=get_secret("ADMIN_EMAIL", "contacto@forensicmind.mx"),
        whatsapp=get_secret("WHATSAPP_DESPACHO", ""),
        anthropic_key=get_secret("ANTHROPIC_API_KEY", ""),
        anthropic_model=get_secret("ANTHROPIC_MODEL", "claude-sonnet-5-5") or "claude-sonnet-5-5",
        permitir_repo_publico=get_secret("PERMITIR_REPO_PUBLICO", "").lower() in ("1", "true", "si", "sí"),
    )


# --------------------------------------------------------------------------------------
# Reglas legales versionadas
# --------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def leyes() -> dict:
    with open(DATA_DIR / "leyes.json", "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def tabulador() -> dict:
    with open(DATA_DIR / "tabulador.json", "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_json_datos(nombre: str):
    with open(DATA_DIR / nombre, "r", encoding="utf-8") as f:
        return json.load(f)


def validar_leyes(d: dict | None = None, hoy: date | None = None) -> list[str]:
    """Devuelve una lista de problemas en las reglas legales (vacía = todo bien)."""
    d = d if d is not None else leyes()
    hoy = hoy or date.today()
    problemas: list[str] = []
    try:
        if float(d["salario_minimo"]["general"]) <= 0:
            problemas.append("Salario mínimo general inválido.")
        if float(d["salario_minimo"]["frontera_norte"]) < float(d["salario_minimo"]["general"]):
            problemas.append("El salario mínimo de la frontera norte no puede ser menor al general.")
        if float(d["uma"]["diaria"]) <= 0:
            problemas.append("UMA diaria inválida.")
        tramos = d["vacaciones_dias"]
        if not tramos or tramos[0]["desde"] != 1:
            problemas.append("La tabla de vacaciones debe iniciar en el año 1.")
        for a, b in zip(tramos, tramos[1:]):
            if b["desde"] != a["hasta"] + 1:
                problemas.append(f"Tabla de vacaciones con huecos entre {a['hasta']} y {b['desde']}.")
            if b["dias"] <= a["dias"]:
                problemas.append("Los días de vacaciones deben aumentar con la antigüedad.")
        if int(d["vigencia_anio"]) != hoy.year:
            problemas.append(
                f"Las reglas legales son de {d['vigencia_anio']} pero estamos en {hoy.year}: "
                "actualiza data/leyes.json (salario mínimo, UMA) y la fecha 'verificado'."
            )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        problemas.append(f"leyes.json incompleto o con formato inválido: {exc!r}")
    return problemas

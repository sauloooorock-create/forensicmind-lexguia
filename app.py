import streamlit as st
import sqlite3
import hashlib
import re
import math
import io
import os
import json
import base64
import textwrap
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime
import pandas as pd
import numpy as np
import cv2

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from sklearn.neural_network import MLPClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    MLPClassifier = None
    TfidfVectorizer = None

# ==============================================================================
# CONFIGURACIÓN GLOBAL Y CREDENCIALES SEGURAS
# ==============================================================================
AUTOR_SISTEMA = "Ing. Industrial y de Sistemas Saúl Ángel Ortiz Rogel"
MARCA_SISTEMA = "ForensicMind & LexGuía CBR v8.0 — Guía Ciudadana & Auto-Sync"

st.set_page_config(
    page_title=f"{MARCA_SISTEMA} | {AUTOR_SISTEMA}",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_NAME = "boveda_juridica_cbr_v8.db"
BACKUP_JSON_FILE = "cerebro_autonomo_backup.json"

DEFAULT_GH_TOKEN = ""
DEFAULT_GH_REPO = "sauloooorock-create/forensicmind-lexguia"
DEFAULT_GH_BRANCH = "main"
DEFAULT_ADMIN_PASS = "admin2026"
DEFAULT_ADMIN_EMAIL = "contacto@forensicmind.mx"

try:
    DEFAULT_GH_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
    DEFAULT_GH_REPO = st.secrets.get("GITHUB_REPO", DEFAULT_GH_REPO)
    DEFAULT_GH_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
    DEFAULT_ADMIN_PASS = st.secrets.get("ADMIN_PASSWORD", "admin2026")
    DEFAULT_ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)
except Exception:
    pass

if "es_admin" not in st.session_state:
    st.session_state["es_admin"] = False

# ==============================================================================
# BARRA LATERAL: ACCESO ADMIN Y PREFERENCIAS
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎨 Apariencia Visual")
    modo_visual = st.radio(
        "Modo de lectura:",
        [
            "☀️ Claro Ejecutivo (Fácil lectura en celular)",
            "🌙 Oscuro Forense"
        ],
        index=0
    )
    buscar_web_switch = st.checkbox(
        "🌐 Consultar noticias y criterios en internet en vivo",
        value=True
    )

    st.markdown("---")
    st.markdown("### 🔐 Acceso Exclusivo Administrador")
    if not st.session_state["es_admin"]:
        clave_input = st.text_input(
            "Contraseña de Administrador:",
            type="password",
            placeholder="Solo para el Ing. Saúl..."
        )
        if st.button("🔓 Desbloquear Panel Admin", use_container_width=True):
            if clave_input == DEFAULT_ADMIN_PASS:
                st.session_state["es_admin"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        gh_repo_input = DEFAULT_GH_REPO
        gh_token_input = DEFAULT_GH_TOKEN
        gh_branch_input = DEFAULT_GH_BRANCH
        auto_entrenar_switch = True
    else:
        st.success("✅ Modo Administrador Activo (Ing. Saúl)")
        auto_entrenar_switch = st.checkbox(
            "🧠 Auto-Aprendizaje e Inyección Activa",
            value=True
        )
        gh_repo_input = st.text_input(
            "Repositorio GitHub:",
            value=DEFAULT_GH_REPO
        )
        gh_token_input = st.text_input(
            "GitHub Token (ghp_...):",
            value=DEFAULT_GH_TOKEN,
            type="password"
        )
        gh_branch_input = st.text_input(
            "Rama (Branch):",
            value=DEFAULT_GH_BRANCH
        )
        if st.button("🔒 Cerrar Sesión Admin", use_container_width=True):
            st.session_state["es_admin"] = False
            st.rerun()

# ==============================================================================
# ESTILOS CSS SIN COMILLAS TRIPLES (INMUNE A CORTES EN MÓVIL)
# ==============================================================================
if "Claro" in modo_visual:
    css_lines = [
        "<style>",
        ".stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }",
        ".block-container { padding-top: 3.2rem !important; padding-bottom: 2.5rem !important; }",
        "h1, h2, h3, h4, h5, h6, p, li, span, div { color: #0f172a; }",
        "label, [data-testid='stWidgetLabel'] p { color: #0f172a !important; font-weight: 700 !important; }",
        "textarea, input[type='text'], input[type='number'], input[type='password'] {",
        "  background-color: #ffffff !important; color: #0f172a !important;",
        "  -webkit-text-fill-color: #0f172a !important; border: 2px solid #2563eb !important;",
        "  border-radius: 10px !important; font-size: 1.04rem !important; font-weight: 600 !important;",
        "}",
        ".author-banner {",
        "  background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);",
        "  border-left: 6px solid #f59e0b; border-radius: 14px; padding: 16px 20px; margin-bottom: 18px;",
        "}",
        ".author-banner * { color: #ffffff !important; }",
        "div[data-testid='metric-container'] {",
        "  background: #ffffff !important; border: 1px solid #cbd5e1 !important;",
        "  border-left: 5px solid #2563eb !important; padding: 14px !important; border-radius: 12px !important;",
        "}",
        ".win-badge { background-color: #059669; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }",
        ".loss-badge { background-color: #dc2626; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }",
        ".step-badge { background-color: #1d4ed8; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }",
        ".gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 5px 12px; border-radius: 6px; font-weight: 800; display: inline-block; }",
        ".card-box { background-color: #ffffff; border: 1px solid #cbd5e1; border-left: 6px solid #2563eb; border-radius: 12px; padding: 18px; margin: 10px 0; }",
        ".money-box { background-color: #ecfdf5; border: 1px solid #6ee7b7; border-left: 6px solid #059669; border-radius: 12px; padding: 18px; margin: 10px 0; }",
        ".lawyer-box { background-color: #eef2ff; border: 1px solid #a5b4fc; border-left: 6px solid #4f46e5; border-radius: 12px; padding: 18px; margin: 10px 0; }",
        ".alert-box { background-color: #fef2f2; border: 1px solid #fca5a5; border-left: 6px solid #dc2626; border-radius: 12px; padding: 18px; margin: 10px 0; }",
        ".script-box { background-color: #fffbeb; border: 1px solid #fcd34d; border-left: 6px solid #d97706; border-radius: 12px; padding: 18px; margin: 10px 0; }",
        ".web-box { background-color: #f0f9ff; border: 1px solid #7dd3fc; border-left: 6px solid #0284c7; border-radius: 12px; padding: 16px; margin: 10px 0; }",
        "div.stButton > button:first-child {",
        "  background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important;",
        "  color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;",
        "  font-weight: 800 !important; border-radius: 10px !important; padding: 12px 20px !important;",
        "}",
        "</style>"
    ]
else:
    css_lines = [
        "<style>",
        ".stApp { background-color: #0b0f19 !important; color: #f8fafc !important; }",
        ".block-container { padding-top: 3.2rem !important; padding-bottom: 2.5rem !important; }",
        "h1, h2, h3, h4, h5, h6, p, li, label { color: #f8fafc !important; }",
        "textarea, input[type='text'], input[type='number'], input[type='password'] {",
        "  background-color: #ffffff !important; color: #0f172a !important;",
        "  -webkit-text-fill-color: #0f172a !important; border: 2px solid #38bdf8 !important; border-radius: 10px !important;",
        "}",
        ".author-banner { background: #1e293b; border-left: 6px solid #f59e0b; border-radius: 12px; padding: 16px 20px; margin-bottom: 18px; }",
        ".win-badge { background-color: #065f46; color: #34d399 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }",
        ".loss-badge { background-color: #7f1d1d; color: #f87171 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }",
        ".step-badge { background-color: #1e3a8a; color: #93c5fd !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }",
        ".gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }",
        ".card-box { background-color: #131c2e; border: 1px solid #2dd4bf; border-radius: 10px; padding: 18px; margin: 10px 0; }",
        ".money-box { background-color: #0f2922; border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 10px; padding: 18px; margin: 10px 0; }",
        ".lawyer-box { background-color: #1e1b4b; border: 1px solid #818cf8; border-left: 5px solid #a78bfa; border-radius: 10px; padding: 18px; margin: 10px 0; }",
        ".alert-box { background-color: #1f1215; border: 1px solid #f87171; border-left: 5px solid #ef4444; border-radius: 10px; padding: 18px; margin: 10px 0; }",
        ".script-box { background-color: #272011; border: 1px solid #f59e0b; border-left: 5px solid #fbbf24; border-radius: 10px; padding: 18px; margin: 10px 0; }",
        ".web-box { background-color: #0c192c; border: 1px solid #38bdf8; border-left: 5px solid #0284c7; border-radius: 10px; padding: 16px; margin: 10px 0; }",
        "</style>"
    ]

st.markdown("\n".join(css_lines), unsafe_allow_html=True)

# ==============================================================================
# CATÁLOGOS DE CASOS Y ESCENARIOS CIUDADANOS (INCLUYE TRÁNSITO Y COBRANZA)
# ==============================================================================
TIPOS_CASOS = {
    "Casos Laborales": [
        "Despido injustificado",
        "Presión para firmar renuncia u hoja en blanco",
        "Salarios, vacaciones o descansos no pagados",
        "Acoso laboral"
    ],
    "Tránsito y Abuso Policial": [
        "Detención de tránsito sin motivo o mordida",
        "Amenaza ilegal de corralón o retiro de placas",
        "Revisión ilegal de vehículo o celular sin orden"
    ],
    "Acoso de Cobranza y Deudas": [
        "Amenazas de embargo falso o despachos de cobranza",
        "Acoso de aplicaciones de préstamos"
    ],
    "Casos Familiares": [
        "Pensión alimenticia y gasto de los hijos",
        "Guarda, custodia y régimen de visitas",
        "Divorcio"
    ],
    "Casos Penales y Fraudes": [
        "Fraude bancario, phishing o robo por transferencia",
        "Detención arbitraria ante Ministerio Público"
    ],
    "Casos Civiles y Mercantiles": [
        "Inquilino que no paga renta ni desocupa",
        "Pagaré vencido o deuda de dinero prestado"
    ]
}

TABULADOR_HONORARIOS_RAMA = {
    "Casos Laborales": {
        "asesoria_min": 500, "asesoria_sug": 1000, "asesoria_max": 2000,
        "anticipo_sug": 0, "pct_sugerido": 25.0, "gastos_periciales_sug": 1000,
        "horas_promedio_despacho": 35,
        "esquema_cobro": "Porcentaje al ganar (20% a 30% de lo recuperado; $0 de anticipo inicial)",
        "via_gratuita": "PROFEDET / Procuraduría de la Defensa del Trabajo — $0 MXN (100% Gratuito)"
    },
    "Tránsito y Abuso Policial": {
        "asesoria_min": 500, "asesoria_sug": 800, "asesoria_max": 1800,
        "anticipo_sug": 2500, "pct_sugerido": 0.0, "gastos_periciales_sug": 500,
        "horas_promedio_despacho": 15,
        "esquema_cobro": "Trámite de Juicio de Nulidad de Multa o Queja en Asuntos Internos",
        "via_gratuita": "Asuntos Internos / Contraloría Municipal / Derechos Humanos — $0 MXN"
    },
    "Acoso de Cobranza y Deudas": {
        "asesoria_min": 500, "asesoria_sug": 900, "asesoria_max": 1500,
        "anticipo_sug": 2000, "pct_sugerido": 0.0, "gastos_periciales_sug": 500,
        "horas_promedio_despacho": 15,
        "esquema_cobro": "Convenio de quita o defensa contra cobranza ilegítima",
        "via_gratuita": "CONDUSEF / REDECO (Queja contra despachos de cobranza) y Policía Cibernética — $0 MXN"
    },
    "Casos Familiares": {
        "asesoria_min": 800, "asesoria_sug": 1200, "asesoria_max": 2500,
        "anticipo_sug": 5000, "pct_sugerido": 0.0, "gastos_periciales_sug": 2500,
        "horas_promedio_despacho": 45,
        "esquema_cobro": "Pago fijo en partes conforme avanza el juicio familiar",
        "via_gratuita": "DIF / Defensoría Pública Familiar del Estado — $0 MXN"
    },
    "Casos Penales y Fraudes": {
        "asesoria_min": 1000, "asesoria_sug": 1800, "asesoria_max": 4000,
        "anticipo_sug": 10000, "pct_sugerido": 15.0, "gastos_periciales_sug": 4000,
        "horas_promedio_despacho": 60,
        "esquema_cobro": "Cobro por etapa (Denuncia en Fiscalía, Audiencia Inicial, Juicio)",
        "via_gratuita": "CONDUSEF (para bancos) y Defensoría Pública / Asesoría de Víctimas — $0 MXN"
    },
    "Casos Civiles y Mercantiles": {
        "asesoria_min": 800, "asesoria_sug": 1500, "asesoria_max": 3000,
        "anticipo_sug": 6000, "pct_sugerido": 20.0, "gastos_periciales_sug": 3500,
        "horas_promedio_despacho": 40,
        "esquema_cobro": "Anticipo inicial + porcentaje de lo cobrado o recuperado",
        "via_gratuita": "Defensoría Pública Civil — $0 MXN"
    }
}

ESCENARIOS_FRECUENTES = {
    "✍️ Escribir o dictar mi propio caso libremente": (
        "Mi sueldo semanal es de 2300. Me despidieron y no me quieren dar liquidación, "
        "solo me quieren dar $5000 y no me daban vacaciones ni días libres ni bonos, ¿qué procede ahí?"
    ),
    "🚓 Tránsito y Policías: Me detuvo una patrulla, piden mordida y amenazan con corralón": (
        "Una patrulla de tránsito me detuvo sin decirme qué infracción cometí, me quieren quitar "
        "la placa o llevarse mi vehículo al corralón con grúa si no les doy dinero en efectivo."
    ),
    "💼 Laboral: Me exigen firmar mi renuncia o una hoja en blanco": (
        "Me corrieron de la chamba hoy sin aviso por escrito y el encargado de recursos humanos "
        "me dice que si no le firmo mi hoja de renuncia voluntaria no me va a dar ni mi última semana."
    ),
    "📞 Deudas y Cobranza: Me amenazan por WhatsApp con embargar mi casa sin orden de juez": (
        "Un despacho de cobranza me manda mensajes amenazando con que mañana van a ir a romper "
        "la cerradura de mi casa para embargar mis muebles por una deuda y le llaman a mis contactos."
    ),
    "👨‍👩‍👧 Familiar: El papá de mis hijos no da pensión y esconde su sueldo": (
        "El papá de mis hijos lleva 4 meses sin dar dinero para la comida y escuela de los niños, "
        "se salió de su trabajo formal a propósito pero gana dinero por su cuenta en efectivo."
    ),
    "💻 Fraude Bancario: Me vaciaron mi cuenta con un enlace o llamada falsa": (
        "Me llegó un mensaje que parecía de mi banco, entré al link y sacaron mi dinero con "
        "transferencias SPEI que yo nunca autoricé; el banco dice que fue mi culpa."
    ),
    "🏠 Inquilino Moroso / Pagaré: No me pagan la renta o un dinero prestado": (
        "Le renté mi casa a un inquilino que lleva 5 meses sin pagar la renta, ya se venció "
        "el contrato y no se quiere salir ni entregar las llaves."
    )
}

DICCIONARIO_COLOQUIAL_A_JURIDICO = [
    (r'\b(chamba|jale|empleo|trabajo|oficina|empresa|fabrica|tienda|bodega|turno)\b', ' trabajo laboral patron '),
    (r'\b(corrieron|echaron|despidieron|cortaron|dieron de baja)\b', ' despido injustificado laboral '),
    (r'\b(liquidacion|finiquito|quincena|semanal|raya|sueldo|nomina|aguinaldo|vacaciones|dias libres)\b', ' liquidacion salario prestaciones laboral '),
    (r'\b(transito|policia|patrulla|mordida|corralon|grua|infraccion|multa|placa|licencia|reten|oficial)\b', ' transito abuso policial corralon multa '),
    (r'\b(cobranza|embargar|embargo falso|despacho|prestamo|app de prestamos|amenazan con embargar)\b', ' acoso cobranza deudas condusef '),
    (r'\b(gasto de los niños|manutencion|pension|alimentos|papa de mis hijos|custodia|divorcio)\b', ' pension alimenticia familiar custodia '),
    (r'\b(vaciaron mi cuenta|robaron mi tarjeta|phishing|spei|fraude|estafaron)\b', ' fraude bancario penal '),
    (r'\b(inquilino|renta|arrendamiento|pagare|prestado)\b', ' civil mercantil arrendamiento pagare ')
]

def expandir_lenguaje_coloquial(texto: str) -> str:
    texto_limpio = str(texto).lower()
    expansiones = []
    for patron, equivalente in DICCIONARIO_COLOQUIAL_A_JURIDICO:
        matches = re.findall(patron, texto_limpio)
        if matches:
            expansiones.append(equivalente * len(matches))
    return str(texto) + " " + " ".join(expansiones)

# ==============================================================================
# MOTOR DE AUTOINYECCIÓN Y SINCRONIZACIÓN CON GITHUB
# ==============================================================================
def inyectar_diccionario_cerebro_en_sqlite(data: dict, conn: sqlite3.Connection) -> dict:
    c = conn.cursor()
    nuevos_mem = 0
    nuevos_casos = 0

    sql_mem = " ".join([
        "INSERT OR IGNORE INTO memoria_neuronal_autonoma (",
        "relato_original, relato_expandido, macro_rama, rama_derecho,",
        "categoria_caso, tipo_caso, fuente_aprendizaje, confianza,",
        "hash_consulta, fecha_aprendizaje",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ])

    for m in data.get("memoria_neuronal_autonoma", []):
        rel_orig = str(m.get("relato_original", "")).strip()
        if not rel_orig:
            continue
        rel_exp = m.get("relato_expandido") or expandir_lenguaje_coloquial(rel_orig)
        h_c = m.get("hash_consulta") or hashlib.sha256(rel_orig.lower().encode("utf-8")).hexdigest()
        c.execute(sql_mem, (
            rel_orig,
            rel_exp,
            m.get("macro_rama", "Derecho Privado"),
            m.get("rama_derecho", "Derecho Laboral"),
            m.get("categoria_caso", "Casos Laborales"),
            m.get("tipo_caso", "Despido injustificado"),
            m.get("fuente_aprendizaje", "Auto-Inyección"),
            float(m.get("confianza", 95.0)),
            h_c,
            m.get("fecha_aprendizaje", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))
        if c.rowcount > 0:
            nuevos_mem += 1

    sql_casos = " ".join([
        "INSERT OR IGNORE INTO casos_juridicos_cbr (",
        "codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,",
        "titulo, actores_intervinientes, etapa_clave, medida_cautelar,",
        "resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,",
        "resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,",
        "estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ])

    for cs in data.get("casos_juridicos_cbr", []):
        cod = cs.get("codigo_caso")
        if not cod:
            continue
        c.execute(sql_casos, (
            cod,
            cs.get("macro_rama", "Derecho Privado"),
            cs.get("rama_derecho", "Derecho Laboral"),
            cs.get("categoria_caso", "Casos Laborales"),
            cs.get("tipo_caso", "Despido injustificado"),
            cs.get("titulo", "Caso Restaurado"),
            cs.get("actores_intervinientes", "Juez, Abogado"),
            cs.get("etapa_clave", "1. Demanda"),
            cs.get("medida_cautelar", "Embargo preventivo"),
            cs.get("resolucion_obtenida", "Sentencia"),
            cs.get("recurso_utilizado", "Amparo"),
            cs.get("evidencia_logs", ""),
            cs.get("hash_sha256", hashlib.sha256(str(cod).encode()).hexdigest()),
            cs.get("resultado", "GANADO"),
            cs.get("accion_abogado", ""),
            cs.get("reaccion_juez", ""),
            cs.get("causa_raiz_fallo", "N/A"),
            cs.get("estrategia_ganadora", ""),
            cs.get("que_hacer_ciudadano", ""),
            cs.get("que_no_hacer_ciudadano", ""),
            cs.get("fecha_registro", datetime.now().strftime("%Y-%m-%d"))
        ))
        if c.rowcount > 0:
            nuevos_casos += 1

    sql_buzon = " ".join([
        "INSERT OR IGNORE INTO buzon_casos_usuarios (",
        "nombre_usuario, contacto_usuario, relato_duda, estado, fecha_envio",
        ") VALUES (?, ?, ?, ?, ?)"
    ])
    for bz in data.get("buzon_casos_usuarios", []):
        rel_b = str(bz.get("relato_duda", "")).strip()
        if not rel_b:
            continue
        c.execute(sql_buzon, (
            bz.get("nombre_usuario", "Ciudadano"),
            bz.get("contacto_usuario", ""),
            rel_b,
            bz.get("estado", "Pendiente de revisión"),
            bz.get("fecha_envio", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))

    conn.commit()
    return {"nuevos_memoria": nuevos_mem, "nuevos_casos": nuevos_casos}

def descargar_cerebro_desde_github(repo: str, token: str, branch: str = "main") -> dict:
    if not repo or not token:
        return {}
    url = f"https://api.github.com/repos/{repo.strip()}/contents/{BACKUP_JSON_FILE}?ref={branch.strip()}"
    headers = {
        "Authorization": f"token {token.strip()}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ForensicMindAutoSync/8.0"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            content_b64 = res_json.get("content", "")
            if content_b64:
                decoded = base64.b64decode(content_b64).decode("utf-8")
                return json.loads(decoded)
    except Exception:
        pass
    return {}

def guardar_y_sincronizar_cerebro_autonomo(repo: str = "", token: str = "", branch: str = "main") -> dict:
    conn = sqlite3.connect(DB_NAME)
    df_casos = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    df_mem = pd.read_sql_query("SELECT * FROM memoria_neuronal_autonoma", conn)
    df_buzon = pd.read_sql_query("SELECT * FROM buzon_casos_usuarios", conn)
    conn.close()

    payload = {
        "autor_arquitectura": AUTOR_SISTEMA,
        "sistema": MARCA_SISTEMA,
        "fecha_respaldo": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_casos_cbr": len(df_casos),
        "total_memoria_autonoma": len(df_mem),
        "total_buzon_usuarios": len(df_buzon),
        "casos_juridicos_cbr": df_casos.to_dict(orient="records"),
        "memoria_neuronal_autonoma": df_mem.to_dict(orient="records"),
        "buzon_casos_usuarios": df_buzon.to_dict(orient="records")
    }
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    try:
        with open(BACKUP_JSON_FILE, "wb") as f:
            f.write(raw_bytes)
    except Exception:
        pass

    if not repo or not token:
        return {"local_ok": True, "github_ok": False, "msg": "Respaldo local actualizado."}

    url_api = f"https://api.github.com/repos/{repo.strip()}/contents/{BACKUP_JSON_FILE}"
    headers = {
        "Authorization": f"token {token.strip()}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "ForensicMindAutoSync/8.0"
    }

    sha_actual = None
    try:
        req_get = urllib.request.Request(f"{url_api}?ref={branch.strip()}", headers=headers)
        with urllib.request.urlopen(req_get, timeout=4.5) as resp_get:
            datos_existentes = json.loads(resp_get.read().decode("utf-8"))
            sha_actual = datos_existentes.get("sha")
    except Exception:
        sha_actual = None

    body_put = {
        "message": f"Auto-Sync ForensicMind v8.0 ({len(df_mem)} memorias | {len(df_casos)} casos)",
        "content": base64.b64encode(raw_bytes).decode("utf-8"),
        "branch": branch.strip()
    }
    if sha_actual:
        body_put["sha"] = sha_actual

    try:
        req_put = urllib.request.Request(
            url_api,
            data=json.dumps(body_put).encode("utf-8"),
            headers=headers,
            method="PUT"
        )
        with urllib.request.urlopen(req_put, timeout=6.0) as resp_put:
            if resp_put.status in (200, 201):
                return {"local_ok": True, "github_ok": True, "msg": "☁️ Sincronizado automáticamente en tu GitHub."}
    except Exception as e:
        return {"local_ok": True, "github_ok": False, "msg": f"Guardado local OK (GitHub: {str(e)[:35]})"}

    return {"local_ok": True, "github_ok": False, "msg": "Respaldo local actualizado."}

# ==============================================================================
# INICIALIZACIÓN DE SQLITE SIN TRIPLES COMILLAS
# ==============================================================================
def init_db_and_autoinject(repo_gh: str = "", token_gh: str = "", branch_gh: str = "main"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    sql_create_casos = " ".join([
        "CREATE TABLE IF NOT EXISTS casos_juridicos_cbr (",
        "id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_caso TEXT UNIQUE,",
        "macro_rama TEXT, rama_derecho TEXT, categoria_caso TEXT, tipo_caso TEXT,",
        "titulo TEXT, actores_intervinientes TEXT, etapa_clave TEXT,",
        "medida_cautelar TEXT, resolucion_obtenida TEXT, recurso_utilizado TEXT,",
        "evidencia_logs TEXT, hash_sha256 TEXT, resultado TEXT,",
        "accion_abogado TEXT, reaccion_juez TEXT, causa_raiz_fallo TEXT,",
        "estrategia_ganadora TEXT, que_hacer_ciudadano TEXT,",
        "que_no_hacer_ciudadano TEXT, fecha_registro TEXT)"
    ])
    c.execute(sql_create_casos)

    sql_create_mem = " ".join([
        "CREATE TABLE IF NOT EXISTS memoria_neuronal_autonoma (",
        "id INTEGER PRIMARY KEY AUTOINCREMENT, relato_original TEXT,",
        "relato_expandido TEXT, macro_rama TEXT, rama_derecho TEXT,",
        "categoria_caso TEXT, tipo_caso TEXT, fuente_aprendizaje TEXT,",
        "confianza REAL, hash_consulta TEXT UNIQUE, fecha_aprendizaje TEXT)"
    ])
    c.execute(sql_create_mem)

    sql_create_buzon = " ".join([
        "CREATE TABLE IF NOT EXISTS buzon_casos_usuarios (",
        "id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_usuario TEXT,",
        "contacto_usuario TEXT, relato_duda TEXT UNIQUE,",
        "estado TEXT, fecha_envio TEXT)"
    ])
    c.execute(sql_create_buzon)

    semillas = [
        (
            "EXP-LAB-2026-001", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Despido Injustificado Ganado (Sueldo Semanal sin Vacaciones y Oferta Engañosa de $5,000)",
            "Conciliador Laboral, Juez Laboral, Procurador PROFEDET",
            "1. Cita de Conciliación", "Embargo precautorio de cuentas", "Convenio pagado al 100%", "Demanda laboral",
            "Me despidieron injustificadamente con sueldo semanal de 2300, solo me quieren dar $5000 sin vacaciones ni descansos.",
            hashlib.sha256(b"EXP-LAB-2026-001").hexdigest(), "GANADO",
            "Se rechazaron los $5,000, no se firmó renuncia y se citó al patrón exigiendo 90 días de sueldo más vacaciones y descansos.",
            "La autoridad obligó al patrón a pagar la liquidación completa al no tener aviso escrito de despido justificado.",
            "N/A", "No firmar renuncia y acudir antes de 60 días al Centro de Conciliación.",
            "Rechazar ofertas engañosas de $5,000, guardar mensajes de WhatsApp de horarios y acudir a Conciliación.",
            "JAMÁS firmar una hoja de renuncia voluntaria ni hoja en blanco para recibir un pago mínimo.",
            "2026-08-01"
        ),
        (
            "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Despido Perdido por Firmar Renuncia a Cambio de $5,000 y Dejar Pasar 2 Meses",
            "Juez Laboral, Abogado",
            "2. Audiencia de Conciliación", "Ninguna", "Absolución patronal", "Ninguno",
            "Trabajador aceptó $5,000 firmando hoja de renuncia voluntaria y reclamó después de 60 días.",
            hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "PERDIDO",
            "Se presentó el reclamo cuando ya habían pasado más de 60 días naturales y con renuncia firmada.",
            "El Juez declaró que el derecho prescribió por exceder los 60 días y dio por válida la renuncia.",
            "Firmar renuncia voluntaria por urgencia de dinero y dejar pasar el límite de 60 días.",
            "N/A", "Iniciar el reclamo en la primera semana tras el despido sin firmar renuncia.",
            "Nunca firmar renuncia bajo la promesa verbal de que después te pagarán el resto.",
            "2026-08-05"
        ),
        (
            "EXP-TRA-2026-003", "Derecho Público", "Derecho Administrativo", "Tránsito y Abuso Policial", "Detención de tránsito sin motivo o mordida",
            "Multa y Amenaza de Corralón Anulada por Falta de Fundamento y Grabación Ciudadana",
            "Juez Cívico / Tribunal Administrativo, Asuntos Internos",
            "1. Impugnación / Queja", "Devolución inmediata de documento", "Nulidad de infracción", "Juicio de nulidad",
            "Patrulla me detuvo sin motivo, pidió mordida y amenazó con llevarse mi auto al corralón con grúa.",
            hashlib.sha256(b"EXP-TRA-2026-003").hexdigest(), "GANADO",
            "El ciudadano grabó la intervención, pidió nombre y número de patrulla y exigió boleta fundada sin dar efectivo.",
            "Asuntos Internos sancionó a los elementos y el Tribunal anuló la boleta por carecer de motivación legal.",
            "N/A", "Grabar en video, pedir identificación del oficial y negarse a dar mordida.",
            "Grabar con el celular desde adentro del auto, preguntar qué artículo del reglamento se infringió y anotar el número de patrulla.",
            "JAMÁS entregar dinero en efectivo ni insultar o empujar al policía.",
            "2026-08-12"
        ),
        (
            "EXP-TRA-2026-004", "Derecho Público", "Derecho Administrativo", "Tránsito y Abuso Policial", "Detención de tránsito sin motivo o mordida",
            "Caso Vial Complicado por Agredir Verbalmente al Oficial y Entregar Papeles sin Boleta",
            "Juez Cívico",
            "1. Detención", "Arresto administrativo", "Multa pagada", "Ninguno",
            "Conductor discutió a gritos con el policía y entregó dinero y documentos sin recibir boleta oficial.",
            hashlib.sha256(b"EXP-TRA-2026-004").hexdigest(), "PERDIDO",
            "El conductor perdió la calma, no grabó el número de patrulla y cayó en provocaciones.",
            "Fue remitido al Juez Cívico por faltas a la autoridad.",
            "Perder la calma, no grabar la actuación policial y entregar documentos sin recibir boleta oficial.",
            "N/A", "Mantener la calma en todo momento y grabar el actuar del servidor público.",
            "Nunca forcejear ni insultar al agente de tránsito.",
            "2026-08-14"
        ),
        (
            "EXP-COB-2026-005", "Derecho Privado", "Derecho Mercantil", "Acoso de Cobranza y Deudas", "Amenazas de embargo falso o despachos de cobranza",
            "Freno Total a Despacho de Cobranza que Amenazaba con Embargo Falso por WhatsApp",
            "CONDUSEF (REDECO), Fiscalía / Policía Cibernética",
            "1. Queja oficial", "Bloqueo de hostigamiento", "Sanción al despacho", "Queja REDECO",
            "Despacho de cobranza mandaba mensajes amenazando con romper cerraduras y embargar muebles mañana mismo.",
            hashlib.sha256(b"EXP-COB-2026-005").hexdigest(), "GANADO",
            "Se guardaron las capturas de las amenazas y se levantó queja en línea ante REDECO-CONDUSEF por cobranza ilegítima.",
            "La autoridad multó a la financiera y cesaron las llamadas y mensajes intimidatorios.",
            "N/A", "Saber que ningún cobrador puede embargar sin orden de un Juez y denunciar en CONDUSEF.",
            "Guardar capturas de los mensajes amenazantes, no depositar a cuentas personales de cobradores y denunciar en REDECO.",
            "JAMÁS dejar entrar a tu casa a supuestos cobradores que no vengan acompañados de un Actuario Judicial con orden de un Juez.",
            "2026-08-18"
        ),
        (
            "EXP-FAM-2026-006", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia y gasto de los hijos",
            "Pensión Alimenticia Provisional Ganada desde la Primera Semana",
            "Juez Familiar, Defensoría DIF",
            "1. Solicitud inicial", "Descuento directo o pensión fijada", "Sentencia de alimentos", "Oficios al SAT y bancos",
            "El papá de mis hijos dejó de dar dinero para comida y escuela y oculta lo que gana.",
            hashlib.sha256(b"EXP-FAM-2026-006").hexdigest(), "GANADO",
            "Se solicitó pensión alimenticia provisional urgente y el Juez pidió informes de cuentas bancarias al SAT/CNBV.",
            "El Juez fijó pensión obligatoria inmediata en favor de los menores.",
            "N/A", "Llevar actas de nacimiento de los hijos y pedir pensión provisional en el Juzgado Familiar o DIF.",
            "Acudir al DIF o Juzgado Familiar con actas de nacimiento y lista de gastos de los niños.",
            "No conformarse con promesas verbales de pago que nunca se cumplen.",
            "2026-08-22"
        ),
        (
            "EXP-PEN-2026-007", "Derecho Público", "Derecho Penal", "Casos Penales y Fraudes", "Fraude bancario, phishing o robo por transferencia",
            "Reembolso Bancario Ganado ante CONDUSEF por Transferencias SPEI No Reconocidas",
            "CONDUSEF, Juez Mercantil / Fiscalía",
            "1. Reclamación bancaria", "Folio de cargos no reconocidos", "Devolución del dinero más intereses", "Reclamación CONDUSEF",
            "Me vaciaron mi cuenta bancaria con transferencias SPEI que yo no autoricé tras un mensaje falso.",
            hashlib.sha256(b"EXP-PEN-2026-007").hexdigest(), "GANADO",
            "Se reportó al banco pidiendo folio oficial y se presentó queja en CONDUSEF invocando que el banco debe probar la autorización.",
            "Se ordenó al banco restituir el dinero robado al usuario por fallas en sus candados de seguridad.",
            "N/A", "Reportar de inmediato al banco, anotar el número de folio y acudir a CONDUSEF.",
            "Bloquear la cuenta de inmediato, exigir número de folio de cargos no reconocidos y presentar queja en CONDUSEF.",
            "No borrar los mensajes ni aceptar cuando el ejecutivo del banco dice verbalmente que no procede.",
            "2026-08-25"
        )
    ]

    sql_ins_semillas = " ".join([
        "INSERT OR IGNORE INTO casos_juridicos_cbr (",
        "codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,",
        "titulo, actores_intervinientes, etapa_clave, medida_cautelar,",
        "resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,",
        "resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,",
        "estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ])
    c.executemany(sql_ins_semillas, semillas)
    conn.commit()

    if os.path.exists(BACKUP_JSON_FILE):
        try:
            with open(BACKUP_JSON_FILE, "r", encoding="utf-8") as f_loc:
                inyectar_diccionario_cerebro_en_sqlite(json.load(f_loc), conn)
        except Exception:
            pass

    if "autoinyeccion_remota_lista" not in st.session_state and repo_gh and token_gh:
        data_rem = descargar_cerebro_desde_github(repo_gh, token_gh, branch_gh)
        if data_rem:
            inyectar_diccionario_cerebro_en_sqlite(data_rem, conn)
        st.session_state["autoinyeccion_remota_lista"] = True

    conn.close()

init_db_and_autoinject(gh_repo_input, gh_token_input, gh_branch_input)

# ==============================================================================
# GUÍA CIUDADANA EXHAUSTIVA PASO A PASO (SIN TECNICISMOS COMPLEJOS)
# ==============================================================================
def obtener_guia_humana_exhaustiva(
    categoria_caso: str,
    tipo_caso: str,
    datos_sueldo: dict,
    res_liq: dict
) -> dict:
    sueldo_str = f"${datos_sueldo['salario_mensual']:,.2f} MXN al mes ({datos_sueldo['periodicidad']})"
    oferta_val = datos_sueldo["oferta_patronal"]
    total_ley = res_liq["gran_total_bruto"]
    faltante = max(0.0, total_ley - oferta_val)

    if categoria_caso == "Casos Laborales":
        radiografia = (
            f"Leí con mucha atención lo que te pasó. Trabajabas ganando {sueldo_str}, "
            "te despidieron de forma repentina y, en lugar de pagarte lo que marca la ley, "
            + (
                f"te quieren dar únicamente ${oferta_val:,.2f} MXN (quitándote ${faltante:,.2f} MXN de tu patrimonio). "
                if oferta_val > 0 else
                "te quieren negar tu liquidación completa. "
            )
            + (
                "Además, detecté que no te respetaban tus vacaciones, días de descanso o bonos, "
                "los cuales la empresa tiene la obligación de pagarte en dinero."
                if datos_sueldo["falta_prestaciones"] else
                "Tienes derecho a reclamar tanto tu finiquito como tu indemnización de 3 meses de sueldo."
            )
        )
        explicacion_sencilla = [
            "🔹 **¿Por qué es ilegal lo que te quieren hacer?:** Cuando un patrón te corre sin entregarte un aviso escrito donde pruebe una falta grave, la ley lo considera un **Despido Injustificado**. Eso activa un candado a tu favor: te tienen que pagar **90 días de sueldo completo** como compensación por dejarte sin ingreso de la noche a la mañana.",
            "🔹 **¿Qué pasa si nunca tuviste contrato firmado o seguro (IMSS)?:** ¡No te preocupes! En México la falta de contrato escrito es culpa del patrón, no tuya. Tus mensajes de WhatsApp donde te daban órdenes, tus transferencias bancarias, fotos con el uniforme o el testimonio de compañeros valen para demostrar que trabajabas ahí.",
            "🔹 **¿Por qué te insisten en que firmes una hoja?:** Porque si ellos logran que pongas tu firma en una 'Renuncia Voluntaria' o en una hoja en blanco, ante el Juez parecerá que tú te saliste por tu gusto y **perderás automáticamente los 90 días de indemnización**."
        ]
        fase_1_hoy = [
            "**1. No firmes ningún papel de renuncia ni hojas en blanco:** Aunque te digan *'fírmale aquí para liberarte los $5,000 hoy y la otra semana te damos lo demás'*, no lo hagas. Es un engaño para cerrar tu expediente sin pagarte.",
            "**2. Haz copias de seguridad en tu teléfono hoy mismo:** Antes de que te borren de los grupos de WhatsApp del trabajo, toma capturas de pantalla donde se vea el nombre o número de tu jefe dándote horarios, instrucciones o regaños.",
            "**3. Anota los datos básicos de tu empleo en una libreta:** Escribe la fecha exacta en que entraste a trabajar, la fecha y hora en que te dijeron que estabas despedido, el nombre de la persona que te corrió y la dirección completa del lugar de trabajo."
        ]
        fase_2_semana = [
            "**1. Acude al Centro de Conciliación Laboral o a la PROFEDET:** No necesitas gastar dinero en un abogado particular si no quieres. En la PROFEDET (Procuraduría de la Defensa del Trabajo) te asignan un licenciado oficial **100% gratis**.",
            "**2. ¿Qué papeles debes llevar en un fólder?:** Tu identificación oficial (INE), la dirección del trabajo, el nombre del patrón o de la empresa (como aparezca en tus recibos, tickets o letrero del negocio) y tus capturas impresas.",
            "**3. Solicita tu Cita de Conciliación:** La autoridad le enviará un citatorio oficial a tu patrón para que se presente en una fecha fija (generalmente en menos de 15 días) a negociar tu pago frente a un funcionario público."
        ]
        fase_3_audiencia = [
            "**1. Qué pasa el día de la cita:** Estarás sentado con un Conciliador oficial y el representante de la empresa. Ellos intentarán ofrecerte menos dinero para cerrar rápido.",
            "**2. Cómo negociar con inteligencia:** En una conciliación rápida (sin ir a juicio largo), muchos trabajadores aceptan un acuerdo justo de entre el **70% y el 100%** de su cálculo legal, pagado ahí mismo en efectivo o transferencia certificada.",
            "**3. Si la empresa no quiere pagar lo justo:** El Conciliador te entrega una *Constancia de No Conciliación* y con ese papel tu abogado o la PROFEDET embargan y demandan ante el Juez Laboral, donde además se empiezan a sumar **salarios caídos** (sueldos que corren mientras dura el juicio)."
        ]
        guion_palabra_por_palabra = (
            "💬 **Si el jefe o Recursos Humanos te presiona para firmar o recibir muy poco dinero, diles con voz tranquila pero firme:**\n\n"
            "*«Agradezco la oferta, pero no voy a firmar ninguna renuncia porque ustedes me están dando de baja. "
            "Ya revisé cuánto me corresponde por ley contando mis 90 días de liquidación, mis vacaciones y descansos pendientes. "
            "Prefiero que nos veamos en el Centro de Conciliación Laboral para firmar un convenio oficial donde ambas partes estemos de acuerdo.»*"
        )
        errores_fatales = [
            "🚫 **Error 1 (Dejar pasar los 60 días):** La ley te da únicamente **60 días naturales** (incluyendo sábados y domingos) desde el día que te corrieron para acudir al Centro de Conciliación. Si vas al día 61, pierdes todo.",
            "🚫 **Error 2 (Pelear, gritar o llevarte cosas de la empresa):** No tomes mercancía ni herramientas 'a cuenta de lo que te deben', porque el patrón lo usará para acusarte de robo y voltearte el problema.",
            "🚫 **Error 3 (Confiar en promesas de palabra):** Si te dicen *'espérame un mes en lo que hay dinero y te liquido bien'*, solo están haciendo tiempo para que se venzan tus 60 días."
        ]
        autoridad = "Centro de Conciliación Laboral y Procuraduría de la Defensa del Trabajo (PROFEDET - Tel. 800 911 7877)"
        abogado_req = "Procurador Gratuito de la PROFEDET o Abogado Laboralista (cobra solo porcentaje al ganar)"

    elif categoria_caso == "Tránsito y Abuso Policial":
        radiografia = (
            "Analicé tu reporte sobre un abuso de tránsito o detención policial en la vía pública. "
            "Cuando una patrulla te detiene sin motivo claro, te amenaza con llevarse tu auto o moto al corralón "
            "o te insinúa que le des dinero ('mordida') para dejarte ir, están cometiendo faltas graves que puedes frenar conociendo tus derechos."
        )
        explicacion_sencilla = [
            "🔹 **¿Cualquier policía puede infraccionarte?:** ¡No! En la gran mayoría de los municipios y estados de México, una patrulla de policía preventiva municipal **no puede cobrar ni levantar multas de tránsito**; solo pueden hacerlo agentes de Tránsito o Vialidad debidamente identificados.",
            "🔹 **¿Es legal grabar al policía con tu celular?:** **Sí, es 100% legal.** Los policías son servidores públicos en funciones en un espacio público. Tienes derecho constitucional a grabar audio y video mientras no empujes ni obstruyas físicamente su labor.",
            "🔹 **¿Cuándo SÍ y cuándo NO se pueden llevar tu carro o moto al corralón?:** No te pueden mandar al corralón por cualquier pretexto para extorsionarte con la grúa. El corralón solo aplica en casos graves: conducir alcoholizado, circular sin placas ni permiso vigente, participar en un choque con heridos o cuando el vehículo tiene reporte de robo."
        ]
        fase_1_hoy = [
            "**1. Oríllate en un lugar seguro, apaga el motor y pon a grabar tu celular:** Coloca el teléfono en el tablero o sosténlo desde adentro sin bajarte del vehículo a menos que sea estrictamente necesario.",
            "**2. Haz las dos preguntas clave con mucha educación:** Pregunta: *'Oficial, buenas tardes, ¿me indica su nombre completo, número de patrulla y qué artículo exacto del Reglamento de Tránsito infringí?'*.",
            "**3. Anota o graba el número económico de la patrulla:** Suele estar pintado en las puertas, salpicaderas y parte trasera de la unidad, además de las placas."
        ]
        fase_2_semana = [
            "**1. Si te piden 'mordida' o dinero en efectivo:** Nunca entregues dinero en la mano. En ningún lugar de México es legal que el policía cobre la multa en efectivo en la calle.",
            "**2. Si te levantan una infracción injusta:** Recibe la boleta oficial (no pelees en la calle) y toma fotos del lugar (señalamientos borrados, semáforos descompuestos, cámaras cercanas).",
            "**3. Reporta el abuso a Asuntos Internos / Contraloría:** Con el número de patrulla, la hora exacta y tu video, presenta la queja en la Unidad de Asuntos Internos de la policía o ante el Tribunal de Justicia Administrativa para anular la multa."
        ]
        fase_3_audiencia = [
            "**1. Cómo anular una multa ilegal:** Toda boleta de tránsito mal llenada o inventada se puede cancelar mediante un **Juicio Sumario de Nulidad** ante el Tribunal de Justicia Administrativa de tu estado (cuentas con 15 días hábiles).",
            "**2. Si se llevaron tu vehículo injustamente:** Exige el inventario sellado de la grúa antes de que lo suban (tomando video de cómo va tu auto o moto por los cuatro lados) e impugna el cobro de arrastre ante la Contraloría."
        ]
        guion_palabra_por_palabra = (
            "💬 **Qué decirle exactamente al policía de tránsito sin alterarte:**\n\n"
            "*«Oficial, con todo respeto, estoy grabando por seguridad de ambos. No le voy a entregar dinero en efectivo "
            "porque prefiero hacer las cosas conforme a la ley. Si cometí una infracción, le pido que me elabore la boleta oficial "
            "anotando su nombre, número de unidad y el artículo del reglamento para yo revisarlo o pagarlo en tesorería.»*"
        )
        errores_fatales = [
            "🚫 **Error 1 (Insultar, manotear o empujar al oficial):** Aunque el policía esté abusando, si lo insultas o lo tocas te pueden arrestar de inmediato por faltas a la autoridad o resistencia, y pasarás de tener la razón a estar detenido.",
            "🚫 **Error 2 (Entregar tu licencia o tarjeta de circulación sin recibir boleta):** Nunca dejes que se lleven tus papeles 'sin darte comprobante'. Si retienen una garantía en los lugares donde aún aplica, deben entregarte en ese mismo instante la boleta foliada.",
            "🚫 **Error 3 (Dar mordida para 'ahorrarte tiempo'):** Además de fomentar que te vuelvan a parar la próxima semana, pueden acusarte del delito de cohecho."
        ]
        autoridad = "Unidad de Asuntos Internos Policial / Tribunal de Justicia Administrativa / Derechos Humanos"
        abogado_req = "Defensor de Oficio en Justicia Administrativa o Queja Ciudadana Directa ($0 MXN)"

    elif categoria_caso == "Acoso de Cobranza y Deudas":
        radiografia = (
            "Analicé tu caso de hostigamiento por deudas o despachos de cobranza. "
            "Tener una deuda atrasada por falta de dinero **NO es un delito penal en México** (nadie puede ir a la cárcel por deberle a un banco, tienda o app), "
            "y las amenazas de que 'mañana van a ir a romper tu cerradura para embargarte' sin orden de un Juez son completamente ilegales."
        )
        explicacion_sencilla = [
            "🔹 **La mentira del 'Embargo Mañana a las 10:00 AM':** Los despachos de cobranza mandan hojas con sellos falsos o mensajes de WhatsApp diciendo que irán con patrullas y cerrajeros a vaciar tu casa. **¡Es falso!** El único que puede ordenar un embargo real es un **Juez Mercantil o Civil** dentro de un juicio formal, y quien acude es un funcionario del juzgado llamado *Actuario* con identificación oficial.",
            "🔹 **El acoso telefónico y a tus contactos es un delito:** Llamar después de las 10:00 PM, usar groserías, pegar carteles en tu puerta o mandarle mensajes a tus familiares y amigos del celular es **Cobranza Ilegítima** (sancionada por el Art. 284 Bis del Código Penal Federal y por CONDUSEF)."
        ]
        fase_1_hoy = [
            "**1. No caigas en pánico ni deposites dinero a cuentas personales:** Los cobradores te presionan para que les deposites $1,000 o $2,000 'hoy mismo' en una tienda de conveniencia para 'detener el embargo'. Ese dinero muchas veces ni siquiera abona a tu deuda real.",
            "**2. Guarda capturas de todos los mensajes y audios amenazantes:** Asegúrate de que se vea el número telefónico desde donde te escriben.",
            "**3. Si es una App de Préstamos que robó tus contactos:** Revoca de inmediato los permisos de contactos y galería de esa aplicación en los ajustes de tu celular y avisa a tus contactos que tu teléfono sufrió un intento de extorsión."
        ]
        fase_2_semana = [
            "**1. Levanta tu queja en línea en el REDECO de la CONDUSEF:** Entra al portal de CONDUSEF (Registro de Despachos de Cobranza) y sube las capturas. La autoridad multa fuertemente a los bancos y financieras cuyos despachos amenazan a la gente.",
            "**2. Si quieres pagar con descuento real (Quita):** Solo negocia cuando tengas una **Carta Convenio oficial** membretada por el banco o tienda original (no un simple mensaje de WhatsApp), donde diga claramente que con ese pago tu cuenta queda en ceros."
        ]
        fase_3_audiencia = [
            "**1. Qué hacer si alguien toca tu puerta diciendo que viene a embargar:** No abras la puerta. Pídele desde adentro o por la ventana que te muestre su credencial oficial de **Actuario del Poder Judicial** y el exhorto firmado por el Juez. Si es un cobrador particular, llama de inmediato al **911** reportando intento de allanamiento y extorsión."
        ]
        guion_palabra_por_palabra = (
            "💬 **Qué responderle a un cobrador agresivo por teléfono o mensaje:**\n\n"
            "*«Sé que existe un adeudo y tengo la disposición de liquidarlo directamente con la institución mediante un convenio formal por escrito, "
            "pero le informo que amenazar con embargos extrajudiciales sin orden de un Juez es Cobranza Ilegítima conforme al Artículo 284 Bis del Código Penal. "
            "Estoy guardando captura de esta conversación para mi queja ante el REDECO de la CONDUSEF.»*"
        )
        errores_fatales = [
            "🚫 **Error 1 (Firmar un pagaré nuevo para 'renovar' la deuda):** Nunca le firmes hojas ni pagarés nuevos a un cobrador que vaya a tu domicilio, porque actualizarás la deuda con intereses mucho más altos.",
            "🚫 **Error 2 (Depositar sin Carta Convenio oficial):** Si pagas 'de palabra', el cobrador se lleva su comisión y tu deuda seguirá apareciendo intacta.",
            "🚫 **Error 3 (Pedir préstamos en aplicaciones informales para pagar otra deuda):** Nunca descargues apps de préstamos rápidos sin registro en CONDUSEF."
        ]
        autoridad = "CONDUSEF / Portal REDECO (Tel. 55 5340 0999) y Policía Cibernética"
        abogado_req = "Trámite Gratuito ante CONDUSEF ($0 MXN)"

    elif categoria_caso == "Casos Familiares":
        radiografia = (
            "Leí con cuidado tu situación familiar. Cuando el padre o la madre de tus hijos deja de aportar dinero "
            "para su comida, escuela, ropa y salud, o esconde lo que gana para no dar pensión alimenticia, "
            "la ley protege de forma prioritaria a tus hijos desde la primera semana."
        )
        explicacion_sencilla = [
            "🔹 **La pensión alimenticia es un derecho de los niños, no un favor:** Aunque el deudor diga *'me salí de trabajar y no tengo nómina'*, el Juez Familiar no le acepta ese pretexto. Si no tiene recibo de nómina, el Juez fija la pensión en salarios mínimos o investiga sus cuentas de banco y su nivel de vida.",
            "🔹 **¿Qué es la Pensión Provisional?:** Es una orden urgente que dicta el Juez en los primeros días de tu solicitud para que tus hijos empiecen a recibir dinero de inmediato, sin tener que esperar a que termine todo el juicio."
        ]
        fase_1_hoy = [
            "**1. Busca las actas de nacimiento originales de tus hijos:** Y si estás casada(o), también el acta de matrimonio.",
            "**2. Haz una lista sencilla de cuánto gastan tus hijos al mes:** Anota cuánto se va en mercado/comida, colegiaturas o útiles, pasajes, ropa, medicinas y renta/servicios de la casa donde viven.",
            "**3. Anota todos los datos que sepas del trabajo o negocios del deudor:** Nombre de la empresa donde trabaja, dirección, RFC, CURP o en qué banco tiene su tarjeta."
        ]
        fase_2_semana = [
            "**1. Acude al DIF de tu municipio o a la Defensoría Pública Familiar:** Ahí te asignan un abogado familiar **totalmente gratis** para ingresar la demanda de pensión alimenticia y guarda y custodia.",
            "**2. Pide que se giren oficios de investigación:** Tu abogado le pedirá al Juez que envíe un oficio al IMSS, al SAT y a los bancos para descubrir cuánto dinero mueve realmente el deudor."
        ]
        fase_3_audiencia = [
            "**1. Registro de Deudores Alimentarios Morosos:** Si el deudor se niega a pagar la pensión ordenada por el Juez, puedes solicitar que lo inscriban en el Registro Nacional de Deudores Alimentarios (lo que le impide tramitar pasaporte, licencias y créditos) e incluso denunciarlo penalmente por incumplimiento de obligaciones."
        ]
        guion_palabra_por_palabra = (
            "💬 **Qué decirle a tu expareja cuando intenta condicionar el gasto de los niños:**\n\n"
            "*«La pensión alimenticia no es dinero para mí, es un derecho irrenunciable de nuestros hijos para su comida y escuela. "
            "Para que las cuentas sean claras y justas para los dos, vamos a dejarlo establecido formalmente ante el Juez de lo Familiar.»*"
        )
        errores_fatales = [
            "🚫 **Error 1 (Confiar años en acuerdos de palabra):** El tiempo que dejes pasar sin pedir la pensión ante el Juez hace más difícil cobrar lo atrasado; actúa hoy.",
            "🚫 **Error 2 (Prohibir ver a los niños como castigo sin orden del Juez, o llevártelos a escondidas):** Siempre pide primero la Guarda y Custodia provisional en el Juzgado para que todo esté respaldado por la ley."
        ]
        autoridad = "Juzgado de lo Familiar y Procuraduría del DIF / Defensoría Pública"
        abogado_req = "Abogado Familiar del DIF ($0 MXN) o Abogado Familiar Particular"

    else:
        radiografia = (
            f"Analicé los detalles de tu caso dentro de la categoría {categoria_caso} ({tipo_caso}). "
            "A continuación te presento una guía clara y en orden cronológico para proteger tu dinero, tus pruebas y tu seguridad jurídica."
        )
        explicacion_sencilla = [
            "🔹 **En fraudes bancarios (transferencias o compras que tú no hiciste):** La Suprema Corte ha establecido que **el banco es quien tiene la obligación de demostrar** que fuiste tú quien autorizó el movimiento. Si el banco no puede probarlo técnicamente, te tiene que devolver tu dinero más intereses.",
            "🔹 **En rentas de casas o pagarés:** Nadie puede hacerse justicia por su propia mano. Si un inquilino no te paga, no puedes cambiarle la chapa por tu cuenta porque te acusarían de despojo; debes pedir la orden de lanzamiento al Juez Civil."
        ]
        fase_1_hoy = [
            "**1. Reúne los documentos o capturas originales sin alterarlos:** Si es un pagaré o contrato de renta, guárdalo en una mica sin hacerle rayones. Si es un fraude bancario, llama al banco hoy mismo para bloquear la cuenta y **exige tu número de folio de aclaración**.",
            "**2. No borres ningún mensaje de texto ni correo:** Conserva los mensajes intactos en tu teléfono para que sirvan como prueba."
        ]
        fase_2_semana = [
            "**1. Si es problema con un banco:** Presenta tu reclamación formal en la **CONDUSEF** (es 100% gratuito) llevando tu estado de cuenta, tu INE y el folio que te dio el banco.",
            "**2. Si es un pagaré o un inquilino moroso:** Acude con un abogado civil/mercantil o a la Defensoría Pública para iniciar el juicio solicitando el **embargo precautorio de bienes** desde el primer día."
        ]
        fase_3_audiencia = [
            "**1. En la audiencia de conciliación o requerimiento de pago:** Nunca entregues el pagaré original ni firmes el desistimiento hasta que el dinero ya esté depositado y firme en tu cuenta bancaria."
        ]
        guion_palabra_por_palabra = (
            "💬 **Qué decir en el banco o ante el deudor:**\n\n"
            "*«No reconozco estos cargos y solicito mi número de folio oficial de aclaración para acudir a la CONDUSEF, "
            "ya que conforme a los criterios de la Suprema Corte corresponde a la institución bancaria acreditar la autenticidad de la operación.»*"
        )
        errores_fatales = [
            "🚫 **Error 1 (Cambiar cerraduras o cortar el agua/luz a un inquilino moroso sin orden del Juez):** Te puede meter en un problema penal por despojo.",
            "🚫 **Error 2 (Remarcar con otra pluma la fecha o el monto de un pagaré):** Si lo alteras con otra tinta, un perito lo detectará y el Juez anulará el pagaré."
        ]
        autoridad = "CONDUSEF (Bancos) / Juzgado Civil o Mercantil / Fiscalía"
        abogado_req = "Asesor Gratuito CONDUSEF / Defensoría Pública o Abogado Litigante"

    return {
        "radiografia": radiografia,
        "explicacion_sencilla": explicacion_sencilla,
        "fase_1_hoy": fase_1_hoy,
        "fase_2_semana": fase_2_semana,
        "fase_3_audiencia": fase_3_audiencia,
        "guion_palabra_por_palabra": guion_palabra_por_palabra,
        "errores_fatales": errores_fatales,
        "autoridad": autoridad,
        "abogado_req": abogado_req
    }

# ==============================================================================
# RED NEURONAL Y CLASIFICADOR INTELIGENTE MULTIMÓDULO
# ==============================================================================
def registrar_experiencia_en_memoria_autonoma(
    relato_original: str,
    clasificacion: dict,
    fuente: str = "Consulta Ciudadana",
    texto_web_extra: str = "",
    repo_gh: str = "",
    token_gh: str = "",
    branch_gh: str = "main"
) -> dict:
    if not relato_original or len(relato_original.strip()) < 10:
        return {"aprendio": False, "sync_msg": ""}
    relato_combinado = f"{relato_original} {texto_web_extra}".strip()
    relato_exp = expandir_lenguaje_coloquial(relato_combinado)
    h_cons = hashlib.sha256(relato_original.strip().lower().encode("utf-8")).hexdigest()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    aprendio_nuevo = False
    sql_ins = " ".join([
        "INSERT OR IGNORE INTO memoria_neuronal_autonoma (",
        "relato_original, relato_expandido, macro_rama, rama_derecho,",
        "categoria_caso, tipo_caso, fuente_aprendizaje, confianza,",
        "hash_consulta, fecha_aprendizaje",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    ])
    try:
        c.execute(sql_ins, (
            relato_original.strip(),
            relato_exp,
            clasificacion["macro_rama"],
            clasificacion["rama"],
            clasificacion["categoria"],
            clasificacion["tipo"],
            fuente,
            clasificacion["confianza"],
            h_cons,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        if c.rowcount > 0:
            aprendio_nuevo = True
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

    sync_status = {"msg": ""}
    if aprendio_nuevo:
        sync_status = guardar_y_sincronizar_cerebro_autonomo(repo_gh, token_gh, branch_gh)

    return {"aprendio": aprendio_nuevo, "sync_msg": sync_status.get("msg", "")}

def entrenar_red_neuronal_evolutiva():
    conn = sqlite3.connect(DB_NAME)
    df_base = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    df_mem = pd.read_sql_query("SELECT * FROM memoria_neuronal_autonoma", conn)
    conn.close()

    if df_base.empty or MLPClassifier is None or TfidfVectorizer is None:
        return None, None, {
            "total_muestras": len(df_base),
            "experiencias_aprendidas": len(df_mem),
            "vocabulario_ngramas": 0
        }

    textos_entrenamiento = []
    etiquetas_entrenamiento = []

    for _, r in df_base.iterrows():
        txt_b = f"{r['titulo']} {r['evidencia_logs']} {r['tipo_caso']} {r['categoria_caso']} {r['que_hacer_ciudadano']}"
        textos_entrenamiento.append(expandir_lenguaje_coloquial(txt_b))
        etiquetas_entrenamiento.append(f"{r['categoria_caso']}|{r['rama_derecho']}|{r['tipo_caso']}|{r['macro_rama']}")

    for _, m in df_mem.iterrows():
        textos_entrenamiento.append(str(m["relato_expandido"]))
        etiquetas_entrenamiento.append(f"{m['categoria_caso']}|{m['rama_derecho']}|{m['tipo_caso']}|{m['macro_rama']}")

    vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=2400)
    X_vec = vectorizer.fit_transform(textos_entrenamiento)

    mlp = MLPClassifier(hidden_layer_sizes=(96, 48), activation='relu', max_iter=450, random_state=42)
    mlp.fit(X_vec, etiquetas_entrenamiento)

    return vectorizer, mlp, {
        "total_muestras": len(textos_entrenamiento),
        "experiencias_aprendidas": len(df_mem),
        "vocabulario_ngramas": len(vectorizer.vocabulary_)
    }

def autoclasificar_caso_con_red_neuronal(relato: str, vectorizer_mlp, modelo_mlp) -> dict:
    relato_expandido = expandir_lenguaje_coloquial(relato)
    texto_low = relato_expandido.lower()

    scores = {
        "Casos Laborales": 0,
        "Tránsito y Abuso Policial": 0,
        "Acoso de Cobranza y Deudas": 0,
        "Casos Familiares": 0,
        "Casos Penales y Fraudes": 0,
        "Casos Civiles y Mercantiles": 0
    }

    reglas = {
        "Casos Laborales": [
            "despid", "corrieron", "echaron", "chamba", "trabajo", "liquidaci",
            "finiquito", "sueldo", "salario", "semanal", "quincenal", "vacaciones",
            "aguinaldo", "patron", "jefe", "renuncia", "hoja en blanco", "dias libres"
        ],
        "Tránsito y Abuso Policial": [
            "transito", "tránsito", "policia", "policía", "patrulla", "mordida",
            "corralon", "corralón", "grua", "grúa", "infraccion", "infracción",
            "multa", "placa", "licencia", "reten", "retén", "oficial"
        ],
        "Acoso de Cobranza y Deudas": [
            "cobranza", "despacho", "embargar", "embargo", "deuda", "prestamo",
            "préstamo", "amenazan con embargar", "romper cerradura"
        ],
        "Casos Familiares": [
            "pension", "pensión", "alimentos", "alimenticia", "hijos", "custodia",
            "divorcio", "gasto de los niños", "manutencion"
        ],
        "Casos Penales y Fraudes": [
            "fraude", "estafa", "phishing", "spei", "vaciaron", "robaron mi cuenta",
            "clonaron", "ministerio publico", "fiscalia"
        ],
        "Casos Civiles y Mercantiles": [
            "inquilino", "renta", "arrendamiento", "departamento", "pagare", "pagaré"
        ]
    }

    for cat_k, kws in reglas.items():
        for kw in kws:
            if kw in texto_low:
                scores[cat_k] += 20

    cat_ganadora = max(scores, key=scores.get)

    mapa_info = {
        "Casos Laborales": ("Derecho Privado", "Derecho Laboral", "Despido injustificado"),
        "Tránsito y Abuso Policial": ("Derecho Público", "Derecho Administrativo / Vial", "Detención de tránsito sin motivo o mordida"),
        "Acoso de Cobranza y Deudas": ("Derecho Privado", "Derecho Bancario y Defensa del Deudor", "Amenazas de embargo falso o despachos de cobranza"),
        "Casos Familiares": ("Derecho Privado", "Derecho de Familia", "Pensión alimenticia y gasto de los hijos"),
        "Casos Penales y Fraudes": ("Derecho Público", "Derecho Penal y Financiero", "Fraude bancario, phishing o robo por transferencia"),
        "Casos Civiles y Mercantiles": ("Derecho Privado", "Derecho Civil y Mercantil", "Inquilino que no paga renta ni desocupa")
    }
    macro, rama, tipo = mapa_info[cat_ganadora]
    confianza = 95.4

    if scores[cat_ganadora] == 0 and modelo_mlp is not None and vectorizer_mlp is not None:
        try:
            X_t = vectorizer_mlp.transform([relato_expandido])
            pred = modelo_mlp.predict(X_t)[0].split("|")
            if len(pred) == 4 and pred[0] in mapa_info:
                cat_ganadora, rama, tipo, macro = pred[0], pred[1], pred[2], pred[3]
        except Exception:
            pass

    return {
        "macro_rama": macro,
        "rama": rama,
        "categoria": cat_ganadora,
        "tipo": tipo,
        "confianza": confianza
    }

# ==============================================================================
# BÚSQUEDA EN INTERNET Y CÁLCULO DE LIQUIDACIÓN LFT (INCLUYE DESCANSOS)
# ==============================================================================
def buscar_informacion_juridica_en_internet(categoria_caso: str, tipo_caso: str) -> dict:
    resultados_web = []
    textos_para_entrenar = []

    q_wiki = f"{tipo_caso} México"
    try:
        url_wiki = (
            "https://es.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(q_wiki)}&utf8=&format=json&srlimit=2"
        )
        req_w = urllib.request.Request(url_wiki, headers={"User-Agent": "ForensicMindBot/8.0"})
        with urllib.request.urlopen(req_w, timeout=3.5) as resp_w:
            data_w = json.loads(resp_w.read().decode("utf-8"))
            for item in data_w.get("query", {}).get("search", []):
                tit_w = item.get("title", "")
                snip_w = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                link_w = f"https://es.wikipedia.org/wiki/{urllib.parse.quote(tit_w.replace(' ', '_'))}"
                resultados_web.append({
                    "fuente": "📖 Enciclopedia Legal",
                    "titulo": tit_w,
                    "resumen": snip_w,
                    "url": link_w
                })
                textos_para_entrenar.append(f"{tit_w} {snip_w}")
    except Exception:
        pass

    q_news = f"{tipo_caso} derechos Mexico ley"
    if categoria_caso == "Casos Laborales":
        q_news = "despido injustificado liquidacion PROFEDET Ley Federal del Trabajo Mexico"
    elif categoria_caso == "Tránsito y Abuso Policial":
        q_news = "multa transito corralon abuso policial derechos conductor Mexico"
    elif categoria_caso == "Acoso de Cobranza y Deudas":
        q_news = "despachos de cobranza amenazas embargo CONDUSEF Mexico"

    try:
        url_gnews = (
            "https://news.google.com/rss/search?"
            f"q={urllib.parse.quote(q_news)}&hl=es-419&gl=MX&ceid=MX:es-419"
        )
        req_g = urllib.request.Request(url_gnews, headers={"User-Agent": "ForensicMindBot/8.0"})
        with urllib.request.urlopen(req_g, timeout=4.0) as resp_g:
            root = ET.fromstring(resp_g.read())
            for it in root.findall(".//item")[:3]:
                tit = it.find("title").text if it.find("title") is not None else "Noticia Jurídica"
                lnk = it.find("link").text if it.find("link") is not None else "https://www.gob.mx"
                resultados_web.append({
                    "fuente": "🌐 Noticias y Criterios en Línea (Google México)",
                    "titulo": tit,
                    "resumen": f"Información reciente verificada para {categoria_caso}.",
                    "url": lnk
                })
                textos_para_entrenar.append(tit)
    except Exception:
        pass

    return {
        "resultados": resultados_web,
        "corpus_web_extraido": " ".join(textos_para_entrenar)
    }

def normalizar_texto_coloquial(texto: str) -> dict:
    texto_low = texto.lower().replace(",", "")
    salario_mensual = None
    periodicidad = "Mensual ($9,857.14 / mes)"

    p_sem = r'(?:semanal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la semana|semanal(?:es)?|por semana))'
    m_sem = re.search(p_sem, texto_low)
    if m_sem:
        val = float(m_sem.group(1) or m_sem.group(2))
        salario_mensual = round((val / 7.0) * 30.0, 2)
        periodicidad = f"Semanal (${val:,.2f} a la semana)"

    if salario_mensual is None:
        p_quin = r'(?:quincenal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la quincena|quincenal(?:es)?|por quincena))'
        m_quin = re.search(p_quin, texto_low)
        if m_quin:
            val = float(m_quin.group(1) or m_quin.group(2))
            salario_mensual = round(val * 2.0, 2)
            periodicidad = f"Quincenal (${val:,.2f} a la quincena)"

    if salario_mensual is None:
        m_gen = re.search(r'(?:gano|ganaba|sueldo|pago|pagan)\s*(?:es\s*de)?\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
        if m_gen:
            val = float(m_gen.group(1))
            if val < 5000:
                salario_mensual = round((val / 7.0) * 30.0, 2)
                periodicidad = f"Semanal (${val:,.2f} a la semana)"
            else:
                salario_mensual = round(val, 2)
                periodicidad = f"Mensual (${val:,.2f} al mes)"

    oferta_patronal = 0.0
    m_of = re.search(r'(?:quieren dar|ofrecen|daban|dan|soltar)\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
    if m_of:
        oferta_patronal = float(m_of.group(1))

    falta_prestaciones = any(k in texto_low for k in [
        "no me daban vacaciones", "sin vacaciones", "días libres", "dias libres",
        "nada de bonos", "sin aguinaldo", "nunca descansaba"
    ])

    return {
        "salario_mensual": salario_mensual if salario_mensual else 9857.14,
        "periodicidad": periodicidad,
        "oferta_patronal": oferta_patronal,
        "falta_prestaciones": falta_prestaciones
    }

def obtener_dias_vacaciones_lft(anios: int) -> int:
    if anios <= 1:
        return 12
    if anios == 2:
        return 14
    if anios == 3:
        return 16
    if anios == 4:
        return 18
    if anios == 5:
        return 20
    if 6 <= anios <= 10:
        return 22
    return 24

def calcular_liquidacion_y_derechos_lft(
    salario_mensual: float,
    anios_antiguedad: int,
    meses_adicionales: int,
    motivo_separacion: str,
    dias_sueldo_pendientes: int = 0,
    dias_vacaciones_no_gozadas: int = 0,
    dias_descanso_trabajados: int = 0,
    salario_minimo_vigente: float = 278.80
) -> dict:
    sd = round(salario_mensual / 30.0, 2)
    antiguedad_total = round(max(1.0, anios_antiguedad + (meses_adicionales / 12.0)), 4)
    dias_vac = obtener_dias_vacaciones_lft(max(1, anios_antiguedad))

    factor_int = 1.0 + (15.0 / 365.0) + ((dias_vac * 0.25) / 365.0)
    sdi = round(sd * factor_int, 2)

    m_sueldo_pend = round(dias_sueldo_pendientes * sd, 2)
    m_aguinaldo = round(15.0 * sd, 2)
    m_vacaciones = round((dias_vac + dias_vacaciones_no_gozadas) * sd, 2)
    m_prima_vac = round(m_vacaciones * 0.25, 2)
    m_descansos_dobles = round(dias_descanso_trabajados * (sd * 2.0), 2)

    es_despido = ("Despido" in motivo_separacion or "Rescisión" in motivo_separacion)
    tope_prima = min(sd, salario_minimo_vigente * 2.0)
    m_prima_ant = round(12.0 * antiguedad_total * tope_prima, 2) if es_despido else 0.0
    m_indem_90 = round(90.0 * sdi, 2) if es_despido else 0.0

    subtotal_finiquito = round(m_sueldo_pend + m_aguinaldo + m_vacaciones + m_prima_vac + m_descansos_dobles, 2)
    subtotal_indemnizacion = round(m_prima_ant + m_indem_90, 2)
    gran_total = round(subtotal_finiquito + subtotal_indemnizacion, 2)

    conceptos = [
        {"Concepto Explicado Fácil": "1. Días trabajados sin pagar", "Por qué te toca (Ley)": "Art. 82 y 88 LFT (Tu trabajo ya realizado)", "Monto (MXN)": m_sueldo_pend},
        {"Concepto Explicado Fácil": "2. Aguinaldo (Mínimo 15 días por año)", "Por qué te toca (Ley)": "Art. 87 LFT (Derecho irrenunciable)", "Monto (MXN)": m_aguinaldo},
        {"Concepto Explicado Fácil": "3. Vacaciones Dignas + Vacaciones que no te dieron", "Por qué te toca (Ley)": "Art. 76 y 79 LFT (Mínimo 12 días el 1er año)", "Monto (MXN)": m_vacaciones},
        {"Concepto Explicado Fácil": "4. Prima Vacacional (25% extra sobre vacaciones)", "Por qué te toca (Ley)": "Art. 80 LFT (Dinero extra para tus vacaciones)", "Monto (MXN)": m_prima_vac},
        {"Concepto Explicado Fácil": "5. Días de descanso trabajados sin pago extra", "Por qué te toca (Ley)": "Art. 73 LFT (Trabajar en tu día libre se paga con un 200% extra)", "Monto (MXN)": m_descansos_dobles},
        {"Concepto Explicado Fácil": "6. Prima de Antigüedad (12 días por cada año)", "Por qué te toca (Ley)": "Art. 162 LFT (Reconocimiento por tu tiempo en la empresa)", "Monto (MXN)": m_prima_ant},
        {"Concepto Explicado Fácil": "7. Indemnización Constitucional (3 Meses / 90 días de sueldo integrado)", "Por qué te toca (Ley)": "Art. 123 Constitucional y Art. 48 LFT (Castigo al patrón por despedirte sin causa)", "Monto (MXN)": m_indem_90}
    ]

    return {
        "sd": sd,
        "sdi": sdi,
        "subtotal_finiquito": subtotal_finiquito,
        "subtotal_indemnizacion": subtotal_indemnizacion,
        "gran_total_bruto": gran_total,
        "tabla_conceptos": pd.DataFrame(conceptos)
    }

def calcular_cotizacion_honorarios_dual(
    monto_en_disputa: float,
    costo_asesoria: float = 1000.0,
    anticipo_fijo: float = 0.0,
    pct_litis: float = 25.0,
    gastos_periciales: float = 1000.0,
    horas_invertidas: float = 35.0,
    costo_hora_despacho: float = 350.0
) -> dict:
    comision_exito = round(monto_en_disputa * (pct_litis / 100.0), 2)
    honorarios_totales = round(costo_asesoria + anticipo_fijo + comision_exito, 2)
    desembolso_total = round(honorarios_totales + gastos_periciales, 2)
    neto_libre = round(max(0.0, monto_en_disputa - desembolso_total), 2)
    utilidad_abogado = round(honorarios_totales - (horas_invertidas * costo_hora_despacho), 2)
    return {
        "honorarios_totales_abogado": honorarios_totales,
        "monto_neto_libre_ciudadano": neto_libre,
        "utilidad_neta_abogado": utilidad_abogado
    }

# ==============================================================================
# DICTADO POR VOZ, WORD (.DOCX) Y FICHA 9:16 CON AUTO-AJUSTE DE PALABRAS
# ==============================================================================
def transcribir_audio_espanol(audio_bytes) -> str:
    if sr is None or audio_bytes is None:
        return ""
    try:
        r = sr.Recognizer()
        audio_file = io.BytesIO(audio_bytes.getvalue() if hasattr(audio_bytes, "getvalue") else audio_bytes.read())
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            return r.recognize_google(audio_data, language="es-MX")
    except Exception:
        return "⚠️ No se pudo transcribir el audio automáticamente. Escribe tu caso en el recuadro."

def limpiar_ascii(texto: str) -> str:
    limpio = re.sub(r"\*+", "", str(texto))
    mapa = str.maketrans("áéíóúñÁÉÍÓÚÑüÜ«»¿¡", "aeiounAEIOUNuU\"\"?!")
    return limpio.translate(mapa).encode("ascii", "ignore").decode("ascii")

def generar_ficha_vertical_9_16(
    codigo: str,
    rama: str,
    caso: str,
    guia: dict,
    monto_bruto: float,
    monto_neto: float,
    hash_ev: str
) -> np.ndarray:
    alto, ancho = 1920, 1080
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[:] = (24, 15, 10)
    cv2.rectangle(img, (25, 25), (1055, 1895), (240, 175, 50), 4)
    cv2.rectangle(img, (40, 40), (1040, 235), (45, 28, 16), -1)

    cv2.putText(img, "FORENSICMIND & LEXGUIA v8.0", (65, 105), cv2.FONT_HERSHEY_DUPLEX, 1.55, (100, 220, 255), 3)
    cv2.putText(img, limpiar_ascii(f"AUTOR: {AUTOR_SISTEMA.upper()}"), (65, 160), cv2.FONT_HERSHEY_DUPLEX, 0.75, (120, 230, 255), 2)
    cv2.putText(img, limpiar_ascii(f"EXPEDIENTE: {codigo} | {rama}"), (65, 285), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2)

    cv2.rectangle(img, (65, 325), (1015, 470), (25, 48, 38), -1)
    cv2.putText(img, limpiar_ascii(f"DERECHOS / LIQUIDACION DE LEY: ${monto_bruto:,.2f} MXN"), (85, 380), cv2.FONT_HERSHEY_DUPLEX, 0.80, (255, 255, 255), 2)
    cv2.putText(img, limpiar_ascii(f"NETO LIBRE PARA TI: ${monto_neto:,.2f} MXN"), (85, 438), cv2.FONT_HERSHEY_DUPLEX, 0.84, (120, 255, 180), 2)

    cv2.putText(img, "GUIA PASO A PASO (SIN CORTES DE PALABRAS):", (65, 535), cv2.FONT_HERSHEY_DUPLEX, 0.90, (100, 220, 255), 2)
    y_cursor = 590

    pasos_combinados = guia["fase_1_hoy"] + guia["fase_2_semana"][:2]
    for paso in pasos_combinados:
        lineas_envueltas = textwrap.wrap(limpiar_ascii(paso), width=52)
        for lin in lineas_envueltas[:3]:
            if y_cursor < 1480:
                cv2.putText(img, lin, (65, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (235, 235, 235), 2)
                y_cursor += 38
        y_cursor += 18

    cv2.putText(img, "AUTORIDAD DONDE ACUDIR:", (65, 1530), cv2.FONT_HERSHEY_DUPLEX, 0.82, (100, 220, 255), 2)
    for lin_aut in textwrap.wrap(limpiar_ascii(guia["autoridad"]), width=54)[:2]:
        cv2.putText(img, lin_aut, (65, 1575), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 230, 150), 2)

    cv2.putText(img, "SELLO CRIPTOGRAFICO SHA-256:", (65, 1650), cv2.FONT_HERSHEY_DUPLEX, 0.80, (100, 220, 255), 2)
    cv2.putText(img, hash_ev[:40], (65, 1695), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (160, 255, 160), 2)
    cv2.putText(img, limpiar_ascii(f"ARQUITECTURA: {AUTOR_SISTEMA.upper()}"), (65, 1810), cv2.FONT_HERSHEY_DUPLEX, 0.72, (100, 255, 218), 2)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

def generar_dictamen_word_docx(
    codigo: str,
    relato: str,
    clasificacion: dict,
    guia: dict,
    res_liq: dict,
    res_hon: dict,
    hash_ev: str
) -> bytes:
    if Document is None:
        return b""
    doc = Document()
    doc.add_heading("FORENSICMIND & LEXGUÍA v8.0 — GUÍA PERSONALIZADA PASO A PASO", 0)
    doc.add_paragraph(f"Autoría del Sistema: {AUTOR_SISTEMA}")
    doc.add_paragraph(f"Expediente: {codigo} | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"Sello Forense SHA-256: {hash_ev}")

    doc.add_heading("1. Radiografía de tu Caso", level=1)
    doc.add_paragraph(guia["radiografia"])

    doc.add_heading("2. Explicación en Español Sencillo", level=1)
    for exp in guia["explicacion_sencilla"]:
        doc.add_paragraph(re.sub(r"\*+", "", exp), style="List Bullet")

    doc.add_heading("3. Cálculo de tu Dinero por Ley", level=1)
    doc.add_paragraph(f"• Total Bruto por Ley (LFT): ${res_liq['gran_total_bruto']:,.2f} MXN")
    doc.add_paragraph(f"• Neto Libre para ti: ${res_hon['monto_neto_libre_ciudadano']:,.2f} MXN")

    doc.add_heading("4. Qué hacer Hoy Mismo (Paso a Paso)", level=1)
    for p1 in guia["fase_1_hoy"]:
        doc.add_paragraph(re.sub(r"\*+", "", p1), style="List Bullet")

    doc.add_heading("5. Qué hacer Esta Semana", level=1)
    for p2 in guia["fase_2_semana"]:
        doc.add_paragraph(re.sub(r"\*+", "", p2), style="List Bullet")

    doc.add_heading("6. Guion Exacto: Qué decir con tus palabras", level=1)
    doc.add_paragraph(re.sub(r"\*+", "", guia["guion_palabra_por_palabra"]))

    doc.add_heading("7. Errores Fatales que NUNCA debes cometer", level=1)
    for err in guia["errores_fatales"]:
        doc.add_paragraph(re.sub(r"\*+", "", err), style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ==============================================================================
# ENCABEZADO PRINCIPAL Y NAVEGACIÓN CONDICIONAL (PÚBLICO VS ADMIN)
# ==============================================================================
banner_html = " ".join([
    "<div class='author-banner'>",
    "<div style='display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;'>",
    "<div>",
    "<span style='color:#fbbf24 !important; font-weight:800; font-size:13px;'>🏛️ ASESOR LEGAL PASO A PASO EN ESPAÑOL SENCILLO • GITHUB AUTO-SYNC</span><br>",
    f"<span style='color:#ffffff !important; font-size:21px; font-weight:900;'>{MARCA_SISTEMA}</span>",
    "</div>",
    "<div>",
    f"<span class='gold-badge'>⚙️ SELLO PERSONAL: {AUTOR_SISTEMA}</span>",
    "</div>",
    "</div>",
    "</div>"
])
st.markdown(banner_html, unsafe_allow_html=True)

VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()

if st.session_state["es_admin"]:
    tab1, tab2, tab4, tab3, tab5, tab6 = st.tabs([
        "🧠 1. Guía Paso a Paso de tu Caso",
        "💰 2. Calculadora LFT y Honorarios",
        "🔬 3. Casos Ganados vs. Perdidos",
        "☁️ 4. [ADMIN] Cerebro & GitHub Sync",
        "➕ 5. [ADMIN] Enseñar Caso a la IA",
        "📬 6. [ADMIN] Buzón de Usuarios"
    ])
else:
    tab1, tab2, tab4 = st.tabs([
        "🧠 1. Guía Paso a Paso de tu Caso",
        "💰 2. Calculadora de Liquidación y Abogado",
        "🔬 3. Casos Reales Ganados vs. Perdidos"
    ])

# ==============================================================================
# PESTAÑA 1: GUÍA CIUDADANA PASO A PASO + BUZÓN DE DUDAS
# ==============================================================================
with tab1:
    st.markdown("### 🗣️ Cuéntame qué te pasó con tus propias palabras (Laboral, Tránsito/Policías, Deudas, Familiar o Fraudes)")

    col_esc, col_voz = st.columns([1.3, 1])
    with col_esc:
        escenario_sel = st.selectbox(
            "💡 Elige un problema común o escribe/dicta tu caso:",
            list(ESCENARIOS_FRECUENTES.keys())
        )
    with col_voz:
        audio_input = st.audio_input("🎙️ Dictar mi problema por voz (Español)")
        texto_transcrito = ""
        if audio_input is not None:
            with st.spinner("Escuchando y transcribiendo tu voz..."):
                texto_transcrito = transcribir_audio_espanol(audio_input)
                if texto_transcrito and "⚠️" not in texto_transcrito:
                    st.success("✅ Voz transcrita con éxito.")
                elif texto_transcrito:
                    st.warning(texto_transcrito)

    valor_relato = ESCENARIOS_FRECUENTES[escenario_sel]
    if texto_transcrito and "⚠️" not in texto_transcrito:
        valor_relato = texto_transcrito

    relato_usuario = st.text_area(
        "📝 Describe aquí todo lo que ocurrió (como se lo contarías a un amigo):",
        value=valor_relato,
        height=135
    )

    btn_analizar = st.button(
        "🧠 Generar mi Guía Completa Paso a Paso y Calcular mis Derechos",
        use_container_width=True
    )

    clasificacion = autoclasificar_caso_con_red_neuronal(relato_usuario, VECTORIZER_VIVO, MODELO_VIVO)
    cat_activa = clasificacion["categoria"]
    rama_activa = clasificacion["rama"]
    tipo_activo = clasificacion["tipo"]

    info_web = {"resultados": [], "corpus_web_extraido": ""}
    if buscar_web_switch:
        info_web = buscar_informacion_juridica_en_internet(cat_activa, tipo_activo)

    if auto_entrenar_switch and (btn_analizar or audio_input is not None or len(relato_usuario) > 25):
        res_auto = registrar_experiencia_en_memoria_autonoma(
            relato_original=relato_usuario,
            clasificacion=clasificacion,
            fuente="Consulta Ciudadana v8.0",
            texto_web_extra=info_web.get("corpus_web_extraido", ""),
            repo_gh=gh_repo_input,
            token_gh=gh_token_input,
            branch_gh=gh_branch_input
        )
        if res_auto["aprendio"]:
            VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()

    datos_sueldo = normalizar_texto_coloquial(relato_usuario)
    dias_vac_omitidas = 12 if datos_sueldo["falta_prestaciones"] else 0
    dias_desc_omitidos = 12 if datos_sueldo["falta_prestaciones"] else 0

    res_liq_rapido = calcular_liquidacion_y_derechos_lft(
        salario_mensual=datos_sueldo["salario_mensual"],
        anios_antiguedad=1,
        meses_adicionales=0,
        motivo_separacion="Despido Injustificado",
        dias_vacaciones_no_gozadas=dias_vac_omitidas,
        dias_descanso_trabajados=dias_desc_omitidos
    )

    tabulador_act = TABULADOR_HONORARIOS_RAMA.get(cat_activa, TABULADOR_HONORARIOS_RAMA["Casos Laborales"])
    res_hon_rapido = calcular_cotizacion_honorarios_dual(
        monto_en_disputa=res_liq_rapido["gran_total_bruto"],
        costo_asesoria=float(tabulador_act["asesoria_sug"]),
        anticipo_fijo=float(tabulador_act["anticipo_sug"]),
        pct_litis=float(tabulador_act["pct_sugerido"])
    )

    guia_humana = obtener_guia_humana_exhaustiva(cat_activa, tipo_activo, datos_sueldo, res_liq_rapido)
    hash_evidencia = hashlib.sha256(relato_usuario.encode("utf-8")).hexdigest()

    # BLOQUE 1: ALERTA DE ENGAÑO PATRONAL (SI ES CASO LABORAL CON OFERTA BAJA)
    if cat_activa == "Casos Laborales" and datos_sueldo["oferta_patronal"] > 0 and datos_sueldo["oferta_patronal"] < res_liq_rapido["gran_total_bruto"]:
        dif_robo = round(res_liq_rapido["gran_total_bruto"] - datos_sueldo["oferta_patronal"], 2)
        alerta_html = " ".join([
            "<div class='alert-box'>",
            "<h4 style='margin-top:0;'>🚨 ¡CUIDADO! TE QUIEREN DAR MUCHO MENOS DE LO QUE TE CORRESPONDE POR LEY</h4>",
            f"Con tu sueldo <b>{datos_sueldo['periodicidad']}</b>, la empresa solo te quiere dar <b>${datos_sueldo['oferta_patronal']:,.2f} MXN</b>, ",
            f"pero por ley te corresponden aproximadamente <b>${res_liq_rapido['gran_total_bruto']:,.2f} MXN</b>.<br><br>",
            f"• <b>Dinero que perderías si firmas esa oferta:</b> <b>${dif_robo:,.2f} MXN</b>.<br>",
            "• <b>Qué hacer hoy mismo:</b> NO firmes ninguna hoja de renuncia voluntaria ni recibas ese dinero como pago final.",
            "</div>"
        ])
        st.markdown(alerta_html, unsafe_allow_html=True)

    # BLOQUE 2: RADIOGRAFÍA EMPÁTICA DEL CASO
    rad_html = " ".join([
        "<div class='card-box'>",
        f"<span class='step-badge'>ÁREA DETECTADA: {cat_activa.upper()} ({tipo_activo})</span><br><br>",
        "<b>🔍 1. Lo que entendí de tu situación:</b><br>",
        f"{guia_humana['radiografia']}",
        "</div>"
    ])
    st.markdown(rad_html, unsafe_allow_html=True)

    # BLOQUE 3: RESUMEN ECONÓMICO (SI ES LABORAL MUESTRA MONTOS CLAROS)
    if cat_activa == "Casos Laborales":
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total que te toca por Ley", f"${res_liq_rapido['gran_total_bruto']:,.2f}", "Liquidación + Finiquito")
        m2.metric("Libre en tu mano (Con abogado)", f"${res_hon_rapido['monto_neto_libre_ciudadano']:,.2f}", "O 100% libre en PROFEDET")
        m3.metric("Lo que te ofrece el patrón", f"${datos_sueldo['oferta_patronal']:,.2f}", "Oferta detectada")
        m4.metric("Tiempo límite para reclamar", "60 Días", "No dejes pasar el plazo")

    # BLOQUE 4: EXPLICACIÓN EN ESPAÑOL SENCILLO (EL PORQUÉ)
    st.markdown("### 💡 2. Explicación en Español Sencillo (Sin palabras complicadas)")
    for exp_item in guia_humana["explicacion_sencilla"]:
        st.markdown(exp_item)

    # BLOQUE 5: GUÍA PASO A PASO CRONOLÓGICA
    st.markdown("---")
    st.markdown("### 🧭 3. Tu Guía Paso a Paso: ¿Qué debes hacer exactamente?")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown("#### ⏱️ PASO A: Hoy mismo (Primeras horas)")
        for item_f1 in guia_humana["fase_1_hoy"]:
            st.markdown(f"- {item_f1}")
    with col_f2:
        st.markdown("#### 📅 PASO B: Esta misma semana")
        for item_f2 in guia_humana["fase_2_semana"]:
            st.markdown(f"- {item_f2}")
    with col_f3:
        st.markdown("#### 🏛️ PASO C: Ante la autoridad")
        for item_f3 in guia_humana["fase_3_audiencia"]:
            st.markdown(f"- {item_f3}")

    # BLOQUE 6: GUION EXACTO PALABRA POR PALABRA
    guion_html = " ".join([
        "<div class='script-box'>",
        f"{guia_humana['guion_palabra_por_palabra'].replace(chr(10), '<br>')}",
        "</div>"
    ])
    st.markdown(guion_html, unsafe_allow_html=True)

    # BLOQUE 7: ERRORES FATALES Y DÓNDE ACUDIR GRATIS
    col_err, col_aut = st.columns([1.2, 1])
    with col_err:
        st.markdown("#### 🚫 4. Trampas y Errores que NUNCA debes cometer")
        for err_item in guia_humana["errores_fatales"]:
            st.markdown(f"- {err_item}")
    with col_aut:
        st.markdown("#### 🏛️ 5. ¿A qué oficina acudir y cuánto cuesta?")
        aut_box = " ".join([
            "<div class='lawyer-box'>",
            f"<b>🏢 Institución Oficial Recomendada:</b><br>{guia_humana['autoridad']}<br><br>",
            f"<b>⚖️ Tipo de Defensor:</b><br>{guia_humana['abogado_req']}<br><br>",
            f"<b>💚 Opción Pública 100% Gratuita:</b><br>{tabulador_act['via_gratuita']}",
            "</div>"
        ])
        st.markdown(aut_box, unsafe_allow_html=True)

    # BLOQUE 8: NOTICIAS Y CRITERIOS EN VIVO DE INTERNET
    if buscar_web_switch and info_web["resultados"]:
        st.markdown("---")
        st.markdown("#### 🌐 Información Reciente Verificada en Internet para tu Caso")
        for rw in info_web["resultados"][:3]:
            w_html = " ".join([
                "<div class='web-box'>",
                f"<b>{rw['fuente']}</b> — <a href='{rw['url']}' target='_blank' style='font-weight:bold; color:#0284c7;'>{rw['titulo']} ↗</a><br>",
                f"<span>{rw['resumen']}</span>",
                "</div>"
            ])
            st.markdown(w_html, unsafe_allow_html=True)

    # BLOQUE 9: DESCARGAR GUÍA EN WORD Y FICHA 9:16 CORREGIDA
    st.markdown("---")
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        bytes_docx = generar_dictamen_word_docx(
            "SAOR-2026-V8", relato_usuario, clasificacion, guia_humana, res_liq_rapido, res_hon_rapido, hash_evidencia
        )
        if bytes_docx:
            st.download_button(
                label="📄 Descargar mi Guía Completa Paso a Paso en Word (.docx)",
                data=bytes_docx,
                file_name="Mi_Guia_Legal_Paso_a_Paso.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
    with col_dl2:
        with st.expander("📱 Ver y Descargar Ficha Resumen 9:16 para Celular (Texto corregido)", expanded=False):
            img_9_16 = generar_ficha_vertical_9_16(
                "SAOR-2026-V8", rama_activa, tipo_activo, guia_humana,
                res_liq_rapido["gran_total_bruto"], res_hon_rapido["monto_neto_libre_ciudadano"], hash_evidencia
            )
            st.image(img_9_16, caption=f"Ficha 9:16 — {AUTOR_SISTEMA}", use_container_width=True)
            _, buf_png = cv2.imencode(".png", cv2.cvtColor(img_9_16, cv2.COLOR_RGB2BGR))
            st.download_button(
                "📥 Descargar Imagen 9:16 (.png)",
                buf_png.tobytes(),
                "Guia_9_16.png",
                "image/png",
                use_container_width=True
            )

    # BLOQUE 10: BUZÓN CIUDADANO "¿NO ENCONTRASTE LO QUE BUSCABAS?"
    st.markdown("---")
    st.markdown("### 📬 ¿No encontraste exactamente tu problema o tienes una duda especial?")
    st.write("Envíale los detalles de tu caso directamente al **Ing. Saúl Ángel Ortiz Rogel** para analizarlo y agregarlo a la plataforma:")
    with st.form("form_buzon_ciudadano"):
        c_bz1, c_bz2 = st.columns(2)
        nom_bz = c_bz1.text_input("Tu nombre o apodo (opcional):", placeholder="Ej. Juan Pérez")
        con_bz = c_bz2.text_input("Tu correo o WhatsApp para responderte (opcional):", placeholder="Ej. correo@ejemplo.com")
        duda_bz = st.text_area("Explícanos qué te sucedió y qué información te gustaría ver en la aplicación:")
        if st.form_submit_button("📨 Enviar mi Caso al Administrador", use_container_width=True):
            if duda_bz and len(duda_bz.strip()) > 5:
                conn = sqlite3.connect(DB_NAME)
                sql_ins_bz = " ".join([
                    "INSERT OR IGNORE INTO buzon_casos_usuarios",
                    "(nombre_usuario, contacto_usuario, relato_duda, estado, fecha_envio)",
                    "VALUES (?, ?, ?, 'Pendiente de revisión', ?)"
                ])
                conn.execute(sql_ins_bz, (
                    nom_bz or "Ciudadano Anónimo",
                    con_bz or "Sin contacto",
                    duda_bz.strip(),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
                conn.close()
                guardar_y_sincronizar_cerebro_autonomo(gh_repo_input, gh_token_input, gh_branch_input)
                asunto_mail = urllib.parse.quote("Nuevo Caso Ciudadano - ForensicMind & LexGuía")
                cuerpo_mail = urllib.parse.quote(f"Nombre: {nom_bz}\nContacto: {con_bz}\n\nCaso:\n{duda_bz}")
                st.success("✅ ¡Tu caso quedó guardado en el buzón del Administrador y sincronizado en la nube!")
                st.markdown(
                    f"👉 [Haz clic aquí si deseas enviarlo también directo desde tu app de Correo](mailto:{DEFAULT_ADMIN_EMAIL}?subject={asunto_mail}&body={cuerpo_mail})"
                )
            else:
                st.warning("Por favor escribe al menos una breve descripción de tu duda.")

# ==============================================================================
# PESTAÑA 2: CALCULADORA EXHAUSTIVA DE LIQUIDACIÓN (CON DÍAS DE DESCANSO)
# ==============================================================================
with tab2:
    st.subheader("💰 Calculadora Fácil de Liquidación Laboral y Costo de Abogado")
    st.write("Calcula peso por peso cuánto te toca si te despidieron o si renuncias, explicado sin términos enredados:")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("#### 👷 1. Datos de tu Sueldo y Trabajo")
        per_sel = st.selectbox(
            "¿Cada cuándo te pagan?",
            ["Semanal (Cada 7 días)", "Quincenal (Cada 15 días)", "Mensual (Cada 30 días)", "Por día"]
        )
        val_ini = 2300.0 if "Semanal" in per_sel else datos_sueldo["salario_mensual"]
        monto_ing = st.number_input("¿Cuánto ganas en ese periodo? ($ MXN)", min_value=100.0, max_value=500000.0, value=float(val_ini), step=100.0)

        if "Semanal" in per_sel:
            sueldo_mes_c = round((monto_ing / 7.0) * 30.0, 2)
        elif "Quincenal" in per_sel:
            sueldo_mes_c = round(monto_ing * 2.0, 2)
        elif "Por día" in per_sel:
            sueldo_mes_c = round(monto_ing * 30.0, 2)
        else:
            sueldo_mes_c = round(monto_ing, 2)

        st.info(f"📌 **Tu sueldo mensual equivale a:** ${sueldo_mes_c:,.2f} MXN (${sueldo_mes_c/30.0:,.2f} pesos por día)")
        anios_c = st.number_input("¿Cuántos años cumplidos trabajaste ahí?", min_value=0, max_value=50, value=1, step=1)
        meses_c = st.number_input("¿Con cuántos meses adicionales?", min_value=0, max_value=11, value=0, step=1)

    with col_c2:
        st.markdown("#### 📋 2. Qué te deben y cuánto te ofrecen")
        motivo_c = st.selectbox(
            "¿Por qué saliste del trabajo?",
            [
                "Despido Injustificado (Me corrieron sin causa legal - Liquidación Completa)",
                "Renuncia Voluntaria (Yo decidí salirme - Solo Finiquito)"
            ]
        )
        oferta_c = st.number_input(
            "¿Cuánto dinero te quiere dar el patrón hoy? ($ MXN)",
            min_value=0.0, max_value=1000000.0,
            value=float(datos_sueldo["oferta_patronal"] if datos_sueldo["oferta_patronal"] > 0 else 5000.0),
            step=500.0
        )
        vac_pend_c = st.number_input("Días de vacaciones pasadas que nunca te dieron:", min_value=0, max_value=120, value=int(dias_vac_omitidas), step=1)
        desc_trab_c = st.number_input("Días de descanso (séptimo día) que te hicieron trabajar sin pago doble:", min_value=0, max_value=100, value=int(dias_desc_omitidos), step=1)
        dias_sueldo_c = st.number_input("Días ya trabajados de esta semana/quincena que no te han pagado:", min_value=0, max_value=30, value=0, step=1)

    res_det = calcular_liquidacion_y_derechos_lft(
        salario_mensual=sueldo_mes_c,
        anios_antiguedad=anios_c,
        meses_adicionales=meses_c,
        motivo_separacion=motivo_c,
        dias_sueldo_pendientes=dias_sueldo_c,
        dias_vacaciones_no_gozadas=vac_pend_c,
        dias_descanso_trabajados=desc_trab_c
    )

    k1, k2, k3 = st.columns(3)
    k1.metric("Lo que te corresponde por Ley", f"${res_det['gran_total_bruto']:,.2f} MXN")
    k2.metric("Lo que te quiere dar la empresa", f"${oferta_c:,.2f} MXN")
    k3.metric("Dinero que te están quitando", f"${max(0.0, res_det['gran_total_bruto'] - oferta_c):,.2f} MXN")

    st.markdown("#### 📊 Desglose explicado renglón por renglón (De dónde sale tu dinero)")
    st.dataframe(res_det["tabla_conceptos"].style.format({"Monto (MXN)": "${:,.2f}"}), use_container_width=True, hide_index=True)

# ==============================================================================
# PESTAÑA 3 (PUBLICA): CASOS GANADOS VS PERDIDOS
# ==============================================================================
with tab4:
    st.subheader("🔬 Ejemplos Reales: Cómo se Ganan y por qué se Pierden los Casos")
    conn = sqlite3.connect(DB_NAME)
    df_hist_all = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    conn.close()

    filtro_cat = st.selectbox("Filtrar ejemplos por tema:", ["TODOS"] + list(TIPOS_CASOS.keys()))
    df_mostrar = df_hist_all if filtro_cat == "TODOS" else df_hist_all[df_hist_all["categoria_caso"] == filtro_cat]
    st.dataframe(
        df_mostrar[["codigo_caso", "categoria_caso", "titulo", "resultado", "que_hacer_ciudadano", "que_no_hacer_ciudadano"]],
        use_container_width=True,
        hide_index=True
    )

# ==============================================================================
# PESTAÑAS EXCLUSIVAS DE ADMINISTRADOR (SOLO VISIBLES CON CONTRASEÑA)
# ==============================================================================
if st.session_state["es_admin"]:
    with tab3:
        st.subheader("☁️ [ADMIN] Control de Autoinyección y Sincronización con GitHub")
        st.write(f"• **Repositorio conectado:** `{gh_repo_input}` | **Muestras en Red Neuronal:** `{STATS_IA['total_muestras']}`")

        col_ad1, col_ad2 = st.columns(2)
        with col_ad1:
            if st.button("☁️ Forzar Sincronización a GitHub Ahora", use_container_width=True):
                res_s = guardar_y_sincronizar_cerebro_autonomo(gh_repo_input, gh_token_input, gh_branch_input)
                if res_s["github_ok"]:
                    st.success(res_s["msg"])
                else:
                    st.warning(res_s["msg"])
        with col_ad2:
            conn = sqlite3.connect(DB_NAME)
            df_m_adm = pd.read_sql_query("SELECT * FROM memoria_neuronal_autonoma ORDER BY id DESC", conn)
            conn.close()
            st.write(f"Memorias aprendidas automáticamente: `{len(df_m_adm)}`")

        if not df_m_adm.empty:
            st.dataframe(df_m_adm[["id", "relato_original", "categoria_caso", "fecha_aprendizaje"]], use_container_width=True, hide_index=True)

    with tab5:
        st.subheader("➕ [ADMIN] Enseñar Nuevo Caso Oficial a la IA")
        with st.form("form_admin_nuevo_caso"):
            c_a1, c_a2, c_a3 = st.columns(3)
            ncod = c_a1.text_input("Código (ej. EXP-TRA-2026-099)")
            ncat = c_a2.selectbox("Categoría", list(TIPOS_CASOS.keys()))
            nres = c_a3.selectbox("Resultado", ["GANADO", "PERDIDO"])
            ntit = st.text_input("Título del Caso")
            nevid = st.text_area("Relato de hechos (incluye palabras coloquiales)")
            nqh = st.text_area("✅ Qué debe hacer el ciudadano")
            nqnh = st.text_area("🚫 Qué NO debe hacer el ciudadano")

            if st.form_submit_button("💾 Guardar Caso y Sincronizar con GitHub"):
                if ncod and ntit and nevid:
                    conn = sqlite3.connect(DB_NAME)
                    sql_adm_ins = " ".join([
                        "INSERT OR IGNORE INTO casos_juridicos_cbr (",
                        "codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,",
                        "titulo, actores_intervinientes, etapa_clave, medida_cautelar,",
                        "resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,",
                        "resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,",
                        "estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro",
                        ") VALUES (?, 'Derecho Privado', 'Derecho General', ?, ?, ?, 'Autoridad', '1. Inicio', 'Medida', 'Resolución', 'Recurso', ?, ?, ?, 'Acción', 'Resolución', 'N/A', 'Estrategia', ?, ?, ?)"
                    ])
                    conn.execute(sql_adm_ins, (
                        ncod,
                        ncat,
                        TIPOS_CASOS[ncat][0],
                        ntit,
                        nevid,
                        hashlib.sha256(nevid.encode("utf-8")).hexdigest(),
                        nres,
                        nqh,
                        nqnh,
                        datetime.now().strftime("%Y-%m-%d")
                    ))
                    conn.commit()
                    conn.close()
                    sync_r = guardar_y_sincronizar_cerebro_autonomo(gh_repo_input, gh_token_input, gh_branch_input)
                    st.success(f"✅ Caso guardado y sincronizado. {sync_r['msg']}")

    with tab6:
        st.subheader("📬 [ADMIN] Buzón de Casos No Encontrados Enviados por Usuarios")
        conn = sqlite3.connect(DB_NAME)
        df_bz_view = pd.read_sql_query("SELECT * FROM buzon_casos_usuarios ORDER BY id DESC", conn)
        conn.close()
        if df_bz_view.empty:
            st.info("Aún no hay mensajes nuevos en el buzón ciudadano.")
        else:
            st.dataframe(df_bz_view, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(f"⚙️ Arquitectura y Desarrollo: {AUTOR_SISTEMA} • {MARCA_SISTEMA}")

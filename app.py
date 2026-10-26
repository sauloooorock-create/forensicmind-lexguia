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
# CONFIGURACIÓN GLOBAL Y SELLO DE AUTORÍA v8.0
# ==============================================================================
AUTOR_SISTEMA = "Ing. Industrial y de Sistemas Saúl Ángel Ortiz Rogel"
MARCA_SISTEMA = "ForensicMind & LexGuía CBR v8.0 — Asesoría Exhaustiva & Auto-Sync"

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
    DEFAULT_GH_REPO = st.secrets.get("GITHUB_REPO", "sauloooorock-create/forensicmind-lexguia")
    DEFAULT_GH_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
    DEFAULT_ADMIN_PASS = st.secrets.get("ADMIN_PASSWORD", "admin2026")
    DEFAULT_ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "contacto@forensicmind.mx")
except Exception:
    pass

if "es_admin" not in st.session_state:
    st.session_state["es_admin"] = False

# ==============================================================================
# BARRA LATERAL: LOGIN DE ADMINISTRADOR Y APARIENCIA
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎨 Apariencia de Lectura")
    modo_visual = st.radio(
        "Modo de pantalla:",
        ["☀️ Ejecutivo Claro (Fácil lectura en celular)", "🌙 Oscuro Forense Blindado"],
        index=0
    )
    buscar_web_switch = st.checkbox("🌐 Consultar noticias y leyes en vivo (Google/Wikipedia)", value=True)
    auto_entrenar_switch = st.checkbox("🧠 Auto-Aprendizaje Activo", value=True)

    st.markdown("---")
    st.markdown("### 🔐 Acceso Exclusivo Administrador")
    if not st.session_state["es_admin"]:
        clave_input = st.text_input("Contraseña de Administrador:", type="password", placeholder="Exclusivo Ing. Saúl")
        if st.button("🔓 Desbloquear Panel Admin", use_container_width=True):
            if clave_input == DEFAULT_ADMIN_PASS:
                st.session_state["es_admin"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        gh_repo_input = DEFAULT_GH_REPO
        gh_token_input = DEFAULT_GH_TOKEN
        gh_branch_input = DEFAULT_GH_BRANCH
    else:
        st.success("✅ Modo Administrador Activo")
        gh_repo_input = st.text_input("Repositorio GitHub:", value=DEFAULT_GH_REPO)
        gh_token_input = st.text_input("GitHub Token (ghp_...):", value=DEFAULT_GH_TOKEN, type="password")
        gh_branch_input = st.text_input("Rama (Branch):", value=DEFAULT_GH_BRANCH)
        if st.button("🔒 Cerrar Sesión Admin", use_container_width=True):
            st.session_state["es_admin"] = False
            st.rerun()

if "Claro" in modo_visual:
    st.markdown("""
    <style>
        .stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }
        .block-container { padding-top: 3.2rem !important; padding-bottom: 2.5rem !important; }
        h1, h2, h3, h4, h5, h6, p, li, span, div { color: #0f172a; }
        label, [data-testid="stWidgetLabel"] p { color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; font-weight: 700 !important; font-size: 1.02rem !important; }
        textarea, input[type="text"], input[type="number"], input[type="password"] {
            background-color: #ffffff !important; color: #0f172a !important; -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #2563eb !important; border-radius: 10px !important; font-size: 1.04rem !important; font-weight: 600 !important; padding: 12px !important;
        }
        .author-banner { background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%); border-left: 6px solid #f59e0b; border-radius: 14px; padding: 16px 20px; margin-bottom: 18px; }
        .author-banner * { color: #ffffff !important; }
        div[data-testid="metric-container"] { background: #ffffff !important; border: 1px solid #cbd5e1 !important; border-left: 5px solid #2563eb !important; padding: 14px !important; border-radius: 12px !important; }
        .win-badge { background-color: #059669; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .loss-badge { background-color: #dc2626; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .step-badge { background-color: #1d4ed8; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 5px 12px; border-radius: 6px; font-weight: 800; display: inline-block; }
        .card-box { background-color: #ffffff; border: 1px solid #cbd5e1; border-left: 6px solid #2563eb; border-radius: 12px; padding: 18px; margin: 10px 0; color: #0f172a !important; line-height: 1.6; }
        .money-box { background-color: #ecfdf5; border: 1px solid #6ee7b7; border-left: 6px solid #059669; border-radius: 12px; padding: 18px; margin: 10px 0; color: #064e3b !important; line-height: 1.6; }
        .lawyer-box { background-color: #eef2ff; border: 1px solid #a5b4fc; border-left: 6px solid #4f46e5; border-radius: 12px; padding: 18px; margin: 10px 0; color: #1e1b4b !important; line-height: 1.6; }
        .alert-box { background-color: #fef2f2; border: 1px solid #fca5a5; border-left: 6px solid #dc2626; border-radius: 12px; padding: 18px; margin: 10px 0; color: #7f1d1d !important; line-height: 1.6; }
        .script-box { background-color: #fffbeb; border: 1px solid #fcd34d; border-left: 6px solid #d97706; border-radius: 12px; padding: 18px; margin: 10px 0; color: #78350f !important; line-height: 1.6; }
        .web-box { background-color: #f0f9ff; border: 1px solid #7dd3fc; border-left: 6px solid #0284c7; border-radius: 12px; padding: 15px; margin: 10px 0; color: #0c4a6e !important; }
        div.stButton > button:first-child { background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important; color: #ffffff !important; font-weight: 800 !important; border-radius: 10px !important; padding: 12px 20px !important; }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .stApp { background-color: #0b0f19 !important; color: #f8fafc !important; }
        .block-container { padding-top: 3.2rem !important; padding-bottom: 2.5rem !important; }
        h1, h2, h3, h4, h5, h6, p, li, label, [data-testid="stWidgetLabel"] p { color: #f8fafc !important; font-weight: 600 !important; }
        textarea, input[type="text"], input[type="number"], input[type="password"] {
            background-color: #ffffff !important; color: #0f172a !important; -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #38bdf8 !important; border-radius: 10px !important; font-weight: 700 !important; padding: 12px !important;
        }
        .author-banner { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border: 1px solid #38bdf8; border-left: 6px solid #f59e0b; border-radius: 12px; padding: 16px 20px; margin-bottom: 18px; }
        .win-badge { background-color: #065f46; color: #34d399 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .loss-badge { background-color: #7f1d1d; color: #f87171 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .step-badge { background-color: #1e3a8a; color: #93c5fd !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .card-box { background-color: #131c2e; border: 1px solid #2dd4bf; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.6; }
        .money-box { background-color: #0f2922; border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.6; }
        .lawyer-box { background-color: #1e1b4b; border: 1px solid #818cf8; border-left: 5px solid #a78bfa; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.6; }
        .alert-box { background-color: #1f1215; border: 1px solid #f87171; border-left: 5px solid #ef4444; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.6; }
        .script-box { background-color: #271c09; border: 1px solid #f59e0b; border-left: 5px solid #fbbf24; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.6; }
        .web-box { background-color: #0c192c; border: 1px solid #38bdf8; border-left: 5px solid #0284c7; border-radius: 10px; padding: 15px; margin: 10px 0; }
        div.stButton > button:first-child { background-color: #2563eb !important; color: #ffffff !important; font-weight: bold !important; border-radius: 10px !important; padding: 12px 20px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. CATÁLOGO DE CASOS (INCLUYE TRÁNSITO/POLICÍAS Y COBRANZA)
# ==============================================================================
TIPOS_CASOS = {
    "Casos Laborales": [
        "Despido injustificado", "Coacción para firmar renuncia u hoja en blanco",
        "Falta de pago de vacaciones, días de descanso o aguinaldo", "Acoso laboral"
    ],
    "Tránsito y Abuso Policial": [
        "Policía de tránsito pide mordida o detiene sin motivo",
        "Amenaza ilegal de llevarse el auto o moto al corralón",
        "Retención indebida de licencia, tarjeta de circulación o placas",
        "Patrulla quiere revisar mi celular o pertenencias sin orden judicial"
    ],
    "Casos Familiares": [
        "Pensión alimenticia (Deudor que no paga u oculta ingresos)",
        "Divorcio y Guarda y custodia", "Régimen de visitas y convivencia"
    ],
    "Casos Penales": [
        "Fraude bancario / Phishing / Robo por transferencia SPEI",
        "Extorsión o amenazas", "Acoso de despachos de cobranza o apps de préstamos"
    ],
    "Casos Civiles": [
        "Arrendamiento (Inquilino que no paga renta o no entrega el inmueble)",
        "Incumplimiento de contrato civil", "Recuperación de propiedad"
    ],
    "Casos Mercantiles": [
        "Cobro de pagaré vencido o dinero prestado", "Incumplimiento comercial"
    ]
}

TABULADOR_HONORARIOS_RAMA = {
    "Casos Laborales": {
        "asesoria_min": 500, "asesoria_sug": 800, "asesoria_max": 1800, "anticipo_sug": 0,
        "esquema_cobro": "Porcentaje al ganar (20% a 30% solo de lo que recuperes; $0 de anticipo inicial)",
        "pct_sugerido": 25.0, "gastos_periciales_sug": 1000, "horas_promedio_despacho": 35,
        "via_gratuita": "PROFEDET / Procuraduría de la Defensa del Trabajo — $0 MXN (100% Gratuito para trabajadores)"
    },
    "Tránsito y Abuso Policial": {
        "asesoria_min": 0, "asesoria_sug": 600, "asesoria_max": 1500, "anticipo_sug": 1500,
        "esquema_cobro": "Juicio de Nulidad de Multa ante Tribunal de Justicia Administrativa o Queja en Asuntos Internos",
        "pct_sugerido": 0.0, "gastos_periciales_sug": 500, "horas_promedio_despacho": 15,
        "via_gratuita": "Asuntos Internos de Seguridad Pública / Defensoría de Justicia Administrativa — $0 MXN"
    },
    "Casos Familiares": {
        "asesoria_min": 700, "asesoria_sug": 1200, "asesoria_max": 2500, "anticipo_sug": 5000,
        "esquema_cobro": "Pago fijo dividido en etapas del juicio familiar",
        "pct_sugerido": 0.0, "gastos_periciales_sug": 2500, "horas_promedio_despacho": 45,
        "via_gratuita": "Procuraduría del DIF / Defensoría Pública Familiar del Estado — $0 MXN"
    },
    "Casos Penales": {
        "asesoria_min": 1000, "asesoria_sug": 1800, "asesoria_max": 4000, "anticipo_sug": 12000,
        "esquema_cobro": "Cobro por etapa (Denuncia en Fiscalía / Audiencia Inicial / Juicio)",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 6000, "horas_promedio_despacho": 65,
        "via_gratuita": "Instituto de la Defensoría Pública / CONDUSEF (en fraudes bancarios) — $0 MXN"
    },
    "Casos Civiles": {
        "asesoria_min": 800, "asesoria_sug": 1400, "asesoria_max": 2800, "anticipo_sug": 6500,
        "esquema_cobro": "Anticipo inicial + porcentaje sobre rentas o bienes recuperados",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 3500, "horas_promedio_despacho": 45,
        "via_gratuita": "Defensoría Pública Civil de tu Estado — $0 MXN"
    },
    "Casos Mercantiles": {
        "asesoria_min": 900, "asesoria_sug": 1500, "asesoria_max": 3000, "anticipo_sug": 5000,
        "esquema_cobro": "Porcentaje sobre lo cobrado del pagaré (15% a 25%)",
        "pct_sugerido": 20.0, "gastos_periciales_sug": 3500, "horas_promedio_despacho": 40,
        "via_gratuita": "PROFECO / CONDUSEF — $0 MXN"
    }
}

ESCENARIOS_FRECUENTES = {
    "✍️ Escribir o dictar mi propio caso con mis palabras": "Mi sueldo semanal es de 2300. Me despidieron y no me quieren dar liquidación, solo me quieren dar $5000 y no me daban vacaciones ni días libres ni bonos, ¿qué procede ahí?",
    "🚓 Tránsito y Policías: Me detuvo una patrulla, me amenaza con corralón y pide mordida": "Iba manejando mi vehículo y una patrulla me detuvo diciendo que era revisión de rutina, me quieren quitar mi licencia o placas y me amenazan con mandar mi vehículo al corralón con grúa si no les doy dinero en efectivo.",
    "💼 Laboral: Me quieren obligar a firmar mi renuncia o una hoja en blanco": "Me acaban de correr de mi trabajo sin darme aviso por escrito, el encargado de recursos humanos me tiene en la oficina y dice que si no le firmo mi hoja de renuncia voluntaria no me va a entregar ni los días que trabajé esta semana.",
    "👨‍👩‍👧 Familiar: El papá/mamá de mis hijos no da pensión y esconde su sueldo": "El padre de mis hijos lleva más de 3 meses sin dar dinero para la comida ni escuela de los niños, dice que no tiene trabajo para no dar pensión pero sí recibe dinero en efectivo y transferencias.",
    "📱 Cobranza / Fraude: Me amenazan de una app de préstamos o vaciaron mi cuenta": "Me están mandando mensajes de WhatsApp con amenazas e insultos de un despacho de cobranza diciendo que van a embargar mi casa hoy mismo y le están llamando a mis contactos.",
    "🏠 Civil: Mi inquilino no me paga la renta y no se quiere salir": "Le renté mi casa a un inquilino que lleva 5 meses sin pagarme la renta, ya se venció el contrato y se niega a salirse.",
    "📑 Mercantil: Presté dinero con un pagaré firmado y no me quieren pagar": "Le presté dinero a una persona que me firmó un pagaré, ya pasó la fecha de pago y se esconde para no pagarme."
}

DICCIONARIO_COLOQUIAL_A_JURIDICO = [
    (r'\b(chamba|jale|empleo|trabajo|oficina|empresa|fabrica|tienda|bodega|turno)\b', ' trabajo laboral patron '),
    (r'\b(corrieron|echaron|despidieron|cortaron|dieron de baja)\b', ' despido injustificado laboral '),
    (r'\b(liquidacion|finiquito|quincena|semanal|raya|sueldo|nomina|aguinaldo|vacaciones|dias libres|bonos)\b', ' liquidacion salario prestaciones laboral '),
    (r'\b(patrulla|transito|policia|mordida|corralon|grua|infraccion|multa|placas|licencia|tarjeta de circulacion|reten)\b', ' transito abuso policial corralon multa '),
    (r'\b(gasto de los niños|manutencion|pension|alimentos|hijos|divorcio|custodia)\b', ' pension alimenticia familiar custodia '),
    (r'\b(vaciaron|phishing|estafaron|spei|cobranza|embargar mi casa|prestamo)\b', ' fraude penal cobranza '),
    (r'\b(inquilino|renta|arrendamiento|depa|desalojar|chapa)\b', ' arrendamiento civil inquilino '),
    (r'\b(pagare|cheque|mercancia fiada)\b', ' pagare ejecutivo mercantil ')
]

def expandir_lenguaje_coloquial(texto: str) -> str:
    texto_limpio = str(texto).lower()
    expansiones = []
    for patron, eq in DICCIONARIO_COLOQUIAL_A_JURIDICO:
        matches = re.findall(patron, texto_limpio)
        if matches:
            expansiones.append(eq * len(matches))
    return str(texto) + " " + " ".join(expansiones)

# ==============================================================================
# 2. BASE DE DATOS SQLITE + AUTOINYECCIÓN + GITHUB AUTO-SYNC
# ==============================================================================
def inyectar_diccionario_cerebro_en_sqlite(data: dict, conn: sqlite3.Connection) -> dict:
    c = conn.cursor()
    nuevos_mem, nuevos_casos, nuevos_buzon = 0, 0, 0

    for m in data.get("memoria_neuronal_autonoma", []):
        rel_orig = str(m.get("relato_original", "")).strip()
        if not rel_orig:
            continue
        rel_exp = m.get("relato_expandido") or expandir_lenguaje_coloquial(rel_orig)
        h_c = m.get("hash_consulta") or hashlib.sha256(rel_orig.lower().encode("utf-8")).hexdigest()
        c.execute("""
            INSERT OR IGNORE INTO memoria_neuronal_autonoma (
                relato_original, relato_expandido, macro_rama, rama_derecho,
                categoria_caso, tipo_caso, fuente_aprendizaje, confianza,
                hash_consulta, fecha_aprendizaje
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rel_orig, rel_exp, m.get("macro_rama", "Derecho Privado"),
            m.get("rama_derecho", "Derecho Laboral"), m.get("categoria_caso", "Casos Laborales"),
            m.get("tipo_caso", "Despido injustificado"), m.get("fuente_aprendizaje", "Auto-Inyección"),
            float(m.get("confianza", 95.0)), h_c, m.get("fecha_aprendizaje", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))
        if c.rowcount > 0:
            nuevos_mem += 1

    for cs in data.get("casos_juridicos_cbr", []):
        cod = cs.get("codigo_caso")
        if not cod:
            continue
        c.execute("""
            INSERT OR IGNORE INTO casos_juridicos_cbr (
                codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,
                titulo, actores_intervinientes, etapa_clave, medida_cautelar,
                resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,
                resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,
                estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cod, cs.get("macro_rama", "Derecho Privado"), cs.get("rama_derecho", "Derecho Laboral"),
            cs.get("categoria_caso", "Casos Laborales"), cs.get("tipo_caso", "Despido injustificado"),
            cs.get("titulo", "Caso Restaurado"), cs.get("actores_intervinientes", "Juez, Abogado"),
            cs.get("etapa_clave", "1. Etapa Inicial"), cs.get("medida_cautelar", "Medida"),
            cs.get("resolucion_obtenida", "Sentencia"), cs.get("recurso_utilizado", "Recurso"),
            cs.get("evidencia_logs", ""), cs.get("hash_sha256", hashlib.sha256(str(cod).encode()).hexdigest()),
            cs.get("resultado", "GANADO"), cs.get("accion_abogado", ""), cs.get("reaccion_juez", ""),
            cs.get("causa_raiz_fallo", "N/A"), cs.get("estrategia_ganadora", ""),
            cs.get("que_hacer_ciudadano", ""), cs.get("que_no_hacer_ciudadano", ""),
            cs.get("fecha_registro", datetime.now().strftime("%Y-%m-%d"))
        ))
        if c.rowcount > 0:
            nuevos_casos += 1

    for bz in data.get("buzon_casos_usuarios", []):
        h_b = bz.get("hash_solicitud")
        if not h_b:
            continue
        c.execute("""
            INSERT OR IGNORE INTO buzon_casos_usuarios (
                nombre_usuario, medio_contacto, categoria_sugerida, duda_o_caso,
                estado_revision, respuesta_admin, hash_solicitud, fecha_envio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bz.get("nombre_usuario", "Ciudadano"), bz.get("medio_contacto", ""),
            bz.get("categoria_sugerida", "Otro"), bz.get("duda_o_caso", ""),
            bz.get("estado_revision", "PENDIENTE"), bz.get("respuesta_admin", ""),
            h_b, bz.get("fecha_envio", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ))
        if c.rowcount > 0:
            nuevos_buzon += 1

    conn.commit()
    return {"nuevos_memoria": nuevos_mem, "nuevos_casos": nuevos_casos, "nuevos_buzon": nuevos_buzon}

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
                return json.loads(base64.b64decode(content_b64).decode("utf-8"))
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
            sha_actual = json.loads(resp_get.read().decode("utf-8")).get("sha")
    except Exception:
        sha_actual = None

    body_put = {
        "message": f"Auto-Inyección IA v8.0 ({len(df_mem)} memorias | {len(df_buzon)} buzón)",
        "content": base64.b64encode(raw_bytes).decode("utf-8"),
        "branch": branch.strip()
    }
    if sha_actual:
        body_put["sha"] = sha_actual

    try:
        req_put = urllib.request.Request(url_api, data=json.dumps(body_put).encode("utf-8"), headers=headers, method="PUT")
        with urllib.request.urlopen(req_put, timeout=6.0) as resp_put:
            if resp_put.status in (200, 201):
                return {"local_ok": True, "github_ok": True, "msg": "☁️ Sincronizado automáticamente en tu GitHub."}
    except Exception as e:
        return {"local_ok": True, "github_ok": False, "msg": f"Guardado local OK (GitHub: {str(e)[:35]})"}

    return {"local_ok": True, "github_ok": False, "msg": "Respaldo local actualizado."}

def init_db_and_autoinject(repo_gh: str, token_gh: str, branch_gh: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS casos_juridicos_cbr (
            id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_caso TEXT UNIQUE, macro_rama TEXT,
            rama_derecho TEXT, categoria_caso TEXT, tipo_caso TEXT, titulo TEXT,
            actores_intervinientes TEXT, etapa_clave TEXT, medida_cautelar TEXT,
            resolucion_obtenida TEXT, recurso_utilizado TEXT, evidencia_logs TEXT,
            hash_sha256 TEXT, resultado TEXT, accion_abogado TEXT, reaccion_juez TEXT,
            causa_raiz_fallo TEXT, estrategia_ganadora TEXT, que_hacer_ciudadano TEXT,
            que_no_hacer_ciudadano TEXT, fecha_registro TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS memoria_neuronal_autonoma (
            id INTEGER PRIMARY KEY AUTOINCREMENT, relato_original TEXT, relato_expandido TEXT,
            macro_rama TEXT, rama_derecho TEXT, categoria_caso TEXT, tipo_caso TEXT,
            fuente_aprendizaje TEXT, confianza REAL, hash_consulta TEXT UNIQUE, fecha_aprendizaje TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS buzon_casos_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre_usuario TEXT, medio_contacto TEXT,
            categoria_sugerida TEXT, duda_o_caso TEXT, estado_revision TEXT,
            respuesta_admin TEXT, hash_solicitud TEXT UNIQUE, fecha_envio TEXT
        )
    """)

    semillas = [
        (
            "EXP-LAB-2026-001", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Despido Ganado: Trabajador con sueldo semanal al que solo le querían dar $5,000 sin vacaciones",
            "Centro de Conciliación, Juez Laboral, Procurador PROFEDET",
            "1. Audiencia de Conciliación", "Embargo precautorio", "Convenio pagado al 100%", "Demanda laboral",
            "Mi sueldo semanal es de 2300, me despidieron y solo me quieren dar $5000 sin vacaciones ni días libres.",
            hashlib.sha256(b"EXP-LAB-2026-001").hexdigest(), "GANADO",
            "El abogado rechazó los $5,000, negó la firma de renuncia y citó al patrón exigiendo 90 días de sueldo más vacaciones y descansos trabajados.",
            "La autoridad obligó a la empresa a pagar la liquidación completa para evitar juicio y embargo.",
            "N/A", "No firmar renuncia y acudir al Centro de Conciliación en la primera semana.",
            "Guardar mensajes de WhatsApp de horarios y rechazar firmar hojas de renuncia.",
            "JAMÁS firmar una hoja en blanco o carta de renuncia a cambio de un pago mínimo.",
            "2026-08-01"
        ),
        (
            "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Caso Perdido: Trabajador firmó hoja de renuncia por recibir $5,000 rápidos y dejó pasar 2 meses",
            "Juez Laboral", "2. Contestación de demanda", "Ninguna", "Sentencia absolutoria", "N/A",
            "Trabajador aceptó $5,000 firmando que renunciaba voluntariamente y reclamó después de 60 días.",
            hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "PERDIDO",
            "Presentó la demanda fuera de los 60 días naturales que da la ley.",
            "El Juez dio por válida la renuncia firmada y declaró vencido el plazo de 60 días.",
            "Firmar renuncia voluntaria bajo engaño o dejar pasar más de 60 días naturales.",
            "N/A", "Reclamar dentro de los primeros días sin haber firmado renuncia.",
            "NUNCA creer la promesa de 'firma tu renuncia para liberarte este cheque y luego vemos lo demás'.",
            "2026-08-05"
        ),
        (
            "EXP-TRA-2026-003", "Derecho Público", "Derecho Administrativo", "Tránsito y Abuso Policial", "Amenaza ilegal de llevarse el auto o moto al corralón",
            "Caso Ganado contra Patrulla que Amenazaba con Corralón Ilegal y Mordida",
            "Asuntos Internos, Tribunal de Justicia Administrativa", "1. Impugnación de Boleta", "Suspensión", "Nulidad total de multa", "Juicio de Nulidad",
            "Patrulla detuvo vehículo en revisión de rutina, amenazó con grúa y corralón para pedir mordida en efectivo.",
            hashlib.sha256(b"EXP-TRA-2026-003").hexdigest(), "GANADO",
            "El ciudadano grabó el número de patrulla, pidió que le indicaran el artículo del reglamento que ameritaba corralón y exigió boleta oficial.",
            "El oficial desistió de llamar a la grúa al ver que la falta no ameritaba corralón y la multa fue anulada.",
            "N/A", "Grabar legalmente la intervención, pedir fundamento legal y negarse a dar efectivo.",
            "Anotar número de patrulla y nombre del agente, exigir boleta oficial y no entregar dinero en efectivo.",
            "JAMÁS dar mordida ni agredir física o verbalmente al policía.",
            "2026-09-01"
        ),
        (
            "EXP-TRA-2026-004", "Derecho Público", "Derecho Administrativo", "Tránsito y Abuso Policial", "Policía de tránsito pide mordida o detiene sin motivo",
            "Caso Perdido: Conductor insultó y empujó al oficial en lugar de grabar la irregularidad",
            "Juez Cívico / Ministerio Público", "1. Puesta a disposición", "Arresto administrativo", "Sanción", "N/A",
            "Conductor perdió la calma ante detención arbitraria, empujó al policía y no grabó evidencia.",
            hashlib.sha256(b"EXP-TRA-2026-004").hexdigest(), "PERDIDO",
            "El conductor cayó en la provocación del mal elemento policial.",
            "El Juez Cívico sancionó al conductor por falta administrativa al existir agresión física.",
            "Perder la calma, insultar o forcejear con el oficial en lugar de documentar el abuso en video.",
            "N/A", "Mantener las manos visibles al volante y grabar con calma.",
            "NUNCA tocar físicamente al oficial ni entregar papeles originales sin saber quién te detiene.",
            "2026-09-04"
        ),
        (
            "EXP-FAM-2026-005", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia (Deudor que no paga u oculta ingresos)",
            "Pensión Alimenticia Ganada con Rastreo de Cuentas Bancarias (SAT/CNBV)",
            "Juez Familiar", "1. Pensión Provisional", "Retención de cuentas", "Sentencia condenatoria", "Oficios al SAT",
            "El papá de los niños dejó de dar gasto diciendo que no tiene trabajo formal pero recibe dinero en sus cuentas.",
            hashlib.sha256(b"EXP-FAM-2026-005").hexdigest(), "GANADO",
            "Se solicitó pensión provisional desde el primer día y se rastrearon sus movimientos bancarios reales.",
            "El Juez fijó pensión obligatoria y aseguró el pago mensual a favor de los menores.",
            "N/A", "Pedir pensión provisional inmediata y rastreo bancario.",
            "Juntar actas de nacimiento y tickets de gastos escolares, médicos y de comida.",
            "No conformarse con promesas de pago de palabra que nunca se cumplen.",
            "2026-09-10"
        )
    ]

    c.executemany("""
        INSERT OR IGNORE INTO casos_juridicos_cbr (
            codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,
            titulo, actores_intervinientes, etapa_clave, medida_cautelar,
            resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,
            resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,
            estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, semillas)
    conn.commit()

    if os.path.exists(BACKUP_JSON_FILE):
        try:
            with open(BACKUP_JSON_FILE, "r", encoding="utf-8") as f_local:
                inyectar_diccionario_cerebro_en_sqlite(json.load(f_local), conn)
        except Exception:
            pass

    if "autoinyeccion_remota_v8" not in st.session_state and repo_gh and token_gh:
        data_remota = descargar_cerebro_desde_github(repo_gh, token_gh, branch_gh)
        if data_remota:
            inyectar_diccionario_cerebro_en_sqlite(data_remota, conn)
        st.session_state["autoinyeccion_remota_v8"] = True

    conn.close()

init_db_and_autoinject(gh_repo_input, gh_token_input, gh_branch_input)

# ==============================================================================
# 3. CALCULADORA EXHAUSTIVA LFT (INCLUYE DÍAS DE DESCANSO Y VACACIONES OMITIDAS)
# ==============================================================================
def normalizar_texto_coloquial(texto: str) -> dict:
    texto_low = texto.lower().replace(",", "")
    salario_mensual = None
    periodicidad = "Mensual ($9,857.14 / mes)"
    sueldo_base_periodo = 2300.0

    m_sem = re.search(r'(?:semanal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la semana|semanal(?:es)?|por semana))', texto_low)
    if m_sem:
        val = float(m_sem.group(1) or m_sem.group(2))
        sueldo_base_periodo = val
        salario_mensual = round((val / 7.0) * 30.0, 2)
        periodicidad = f"Semanal (${val:,.2f} a la semana)"

    if salario_mensual is None:
        m_quin = re.search(r'(?:quincenal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la quincena|quincenal(?:es)?|por quincena))', texto_low)
        if m_quin:
            val = float(m_quin.group(1) or m_quin.group(2))
            sueldo_base_periodo = val
            salario_mensual = round(val * 2.0, 2)
            periodicidad = f"Quincenal (${val:,.2f} a la quincena)"

    if salario_mensual is None:
        m_men = re.search(r'(?:mensual(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:al mes|mensual(?:es)?|por mes))', texto_low)
        if m_men:
            val = float(m_men.group(1) or m_men.group(2))
            sueldo_base_periodo = val
            salario_mensual = round(val, 2)
            periodicidad = f"Mensual (${val:,.2f} al mes)"

    oferta_patronal = 0.0
    m_oferta = re.search(r'(?:quieren dar|ofrecen|daban|dan|ofreciendo|soltar)\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
    if m_oferta:
        oferta_patronal = float(m_oferta.group(1))

    sin_vacaciones = any(k in texto_low for k in ["no me daban vacaciones", "sin vacaciones", "nunca tuve vacaciones"])
    sin_dias_libres = any(k in texto_low for k in ["días libres", "dias libres", "sin descanso", "no descansaba", "sin dia de descanso"])

    return {
        "salario_mensual": salario_mensual if salario_mensual else 9857.14,
        "sueldo_periodo": sueldo_base_periodo,
        "periodicidad": periodicidad,
        "oferta_patronal": oferta_patronal,
        "sin_vacaciones": sin_vacaciones,
        "sin_dias_libres": sin_dias_libres
    }

def obtener_dias_vacaciones_lft(anios_cumplidos: int) -> int:
    if anios_cumplidos <= 1: return 12
    elif anios_cumplidos == 2: return 14
    elif anios_cumplidos == 3: return 16
    elif anios_cumplidos == 4: return 18
    elif anios_cumplidos == 5: return 20
    elif 6 <= anios_cumplidos <= 10: return 22
    else: return 24

def calcular_liquidacion_y_derechos_lft(
    salario_mensual: float,
    anios_antiguedad: int = 1,
    meses_adicionales: int = 0,
    motivo_separacion: str = "Despido Injustificado",
    dias_aguinaldo_anual: int = 15,
    prima_vacacional_pct: float = 25.0,
    dias_sueldo_pendientes: int = 0,
    dias_vacaciones_no_gozadas: int = 0,
    descansos_trabajados_no_pagados: int = 0,
    salario_minimo_vigente: float = 278.80
) -> dict:
    sd = round(salario_mensual / 30.0, 2)
    antiguedad_total_anios = round(max(1.0, anios_antiguedad + (meses_adicionales / 12.0)), 4)
    dias_trabajados_ultimo_anio = round((meses_adicionales / 12.0) * 365.0, 1) or 365.0

    dias_vac_correspondientes = obtener_dias_vacaciones_lft(max(1, anios_antiguedad))
    prop_diaria_aguinaldo = dias_aguinaldo_anual / 365.0
    prop_diaria_prima_vac = (dias_vac_correspondientes * (prima_vacacional_pct / 100.0)) / 365.0
    sdi = round(sd * (1.0 + prop_diaria_aguinaldo + prop_diaria_prima_vac), 2)

    monto_sueldo_pendiente = round(dias_sueldo_pendientes * sd, 2)
    monto_aguinaldo_prop = round((dias_aguinaldo_anual / 365.0) * dias_trabajados_ultimo_anio * sd, 2)
    monto_vacaciones_prop = round((dias_vac_correspondientes / 365.0) * dias_trabajados_ultimo_anio * sd, 2)
    monto_vacaciones_atrasadas = round(dias_vacaciones_no_gozadas * sd, 2)
    monto_prima_vac = round((monto_vacaciones_prop + monto_vacaciones_atrasadas) * (prima_vacacional_pct / 100.0), 2)
    # Según Art. 73 LFT, trabajar el día de descanso obligatorio se paga con un salario doble adicional al normal
    monto_descansos_trabajados = round(descansos_trabajados_no_pagados * (sd * 2.0), 2)

    salario_base_prima_ant = min(sd, salario_minimo_vigente * 2.0)
    es_despido = ("Despido" in motivo_separacion or "Rescisión" in motivo_separacion)
    monto_prima_antiguedad = round(12.0 * antiguedad_total_anios * salario_base_prima_ant, 2) if (es_despido or anios_antiguedad >= 15) else 0.0
    monto_indem_90_dias = round(90.0 * sdi, 2) if es_despido else 0.0

    subtotal_finiquito = round(
        monto_sueldo_pendiente + monto_aguinaldo_prop + monto_vacaciones_prop +
        monto_vacaciones_atrasadas + monto_prima_vac + monto_descansos_trabajados, 2
    )
    subtotal_indemnizacion = round(monto_prima_antiguedad + monto_indem_90_dias, 2)
    gran_total_bruto = round(subtotal_finiquito + subtotal_indemnizacion, 2)

    conceptos_tabla = [
        {"Concepto Explicado Fácil": "1. Días trabajados pendientes de pago", "Por qué te toca": "Son días que ya sudaste y nadie te los puede quitar (Art. 82 LFT)", "Monto (MXN)": monto_sueldo_pendiente},
        {"Concepto Explicado Fácil": "2. Aguinaldo proporcional", "Por qué te toca": "Tu parte de aguinaldo por los meses trabajados en el año (Art. 87 LFT)", "Monto (MXN)": monto_aguinaldo_prop},
        {"Concepto Explicado Fácil": "3. Vacaciones dignas + Vacaciones que no te dieron", "Por qué te toca": "Mínimo 12 días desde el primer año pagados al 100% (Art. 76 y 79 LFT)", "Monto (MXN)": round(monto_vacaciones_prop + monto_vacaciones_atrasadas, 2)},
        {"Concepto Explicado Fácil": "4. Prima vacacional (25% extra)", "Por qué te toca": "Dinero extra obligatorio sobre tus vacaciones (Art. 80 LFT)", "Monto (MXN)": monto_prima_vac},
        {"Concepto Explicado Fácil": "5. Días de descanso trabajados sin pagar", "Por qué te toca": "Si no te daban día libre semanal, se paga al doble adicional (Art. 73 LFT)", "Monto (MXN)": monto_descansos_trabajados},
        {"Concepto Explicado Fácil": "6. Prima de antigüedad (12 días por año)", "Por qué te toca": "Premio por el tiempo que trabajaste ahí al ser despedido (Art. 162 LFT)", "Monto (MXN)": monto_prima_antiguedad},
        {"Concepto Explicado Fácil": "7. Indemnización de 3 meses de sueldo (90 días)", "Por qué te toca": "Castigo obligatorio al patrón por correrte sin causa justa (Art. 48 LFT)", "Monto (MXN)": monto_indem_90_dias}
    ]

    return {
        "sd": sd, "sdi": sdi, "subtotal_finiquito": subtotal_finiquito,
        "subtotal_indemnizacion": subtotal_indemnizacion, "gran_total_bruto": gran_total_bruto,
        "monto_indem_90_dias": monto_indem_90_dias, "monto_prima_antiguedad": monto_prima_antiguedad,
        "monto_descansos_trabajados": monto_descansos_trabajados,
        "tabla_conceptos": pd.DataFrame(conceptos_tabla)
    }

def calcular_cotizacion_honorarios_dual(
    monto_en_disputa: float, costo_asesoria: float = 800.0, anticipo_fijo: float = 0.0,
    pct_litis: float = 25.0, gastos_periciales: float = 1000.0, horas_invertidas: float = 35.0, costo_hora_despacho: float = 350.0
) -> dict:
    comision_exito = round(monto_en_disputa * (pct_litis / 100.0), 2)
    honorarios_totales_abogado = round(costo_asesoria + anticipo_fijo + comision_exito, 2)
    desembolso_total_ciudadano = round(honorarios_totales_abogado + gastos_periciales, 2)
    neto_libre = round(max(0.0, monto_en_disputa - desembolso_total_ciudadano), 2)
    costo_operativo = round(horas_invertidas * costo_hora_despacho, 2)
    utilidad_abogado = round(honorarios_totales_abogado - costo_operativo, 2)
    return {
        "comision_exito": comision_exito,
        "honorarios_totales_abogado": honorarios_totales_abogado,
        "desembolso_total_ciudadano": desembolso_total_ciudadano,
        "monto_neto_libre_ciudadano": neto_libre,
        "utilidad_neta_abogado": utilidad_abogado
    }

# ==============================================================================
# 4. GENERADOR DE ASESORÍA HUMANA EXHAUSTIVA PASO A PASO (SIN TECNICISMOS)
# ==============================================================================
def generar_asesoria_humana_exhaustiva(
    categoria_caso: str, tipo_caso: str, relato_usuario: str, datos_norm: dict, res_liq: dict, res_hon: dict
) -> dict:
    oferta = datos_norm["oferta_patronal"]
    total_ley = res_liq["gran_total_bruto"]
    faltante = round(max(0.0, total_ley - oferta), 2)

    if categoria_caso == "Casos Laborales":
        radiografia = (
            f"Leí con mucha atención todo tu relato. Me explicas que ganabas un sueldo **{datos_norm['periodicidad']}** "
            f"(que equivale a **${datos_norm['salario_mensual']:,.2f} pesos al mes** o **${res_liq['sd']:,.2f} pesos por día**), "
            f"que te acaban de despedir y que la empresa pretende darte únicamente **${oferta:,.2f} pesos** en lugar de tu liquidación completa"
            + (", además de que no te respetaban tus vacaciones ni tus días libres de descanso." if (datos_norm["sin_vacaciones"] or datos_norm["sin_dias_libres"]) else ".")
        )
        explicacion_dinero = (
            f"**¿Por qué lo que te quieren hacer es ilegal?** Cuando un patrón te despide sin entregarte un aviso por escrito donde pruebe una falta grave, "
            f"la ley mexicana lo considera un **Despido Injustificado**. Por ley te corresponden **${total_ley:,.2f} MXN** (divididos en **${res_liq['subtotal_finiquito']:,.2f} MXN** "
            f"de tu aguinaldo, vacaciones y descansos trabajados, más **${res_liq['subtotal_indemnizacion']:,.2f} MXN** de indemnización de 3 meses de sueldo y antigüedad). "
            f"Si aceptas los **${oferta:,.2f} MXN** que te ofrecen hoy, **estarías perdiendo ${faltante:,.2f} MXN que son tuyos por derecho**."
        )
        fases_paso_a_paso = [
            "🕐 **FASE 1: ¿Qué hacer HOY MISMO (Primeras 24 horas)?** No firmes ninguna hoja que diga 'Renuncia Voluntaria', ni recibos donde diga que 'no se te debe nada', ni mucho menos hojas en blanco. Si te dicen que si no firmas no te dan los $5,000, prefiere dejar esos $5,000 en la mesa hoy para cobrar tus casi $50,000 completos por la vía legal.",
            "📲 **FASE 2: ¿Cómo juntar tus pruebas en casa aunque no tengas contrato?** No importa si te pagaban en efectivo o no tenías seguro (IMSS). Toma capturas de pantalla de tus grupos de WhatsApp del trabajo donde tu jefe te daba órdenes o te pasaba horarios, guarda estados de cuenta si te depositaban, toma foto a tu uniforme o gafete y anota el nombre y dirección exacta del negocio.",
            "🏛️ **FASE 3: ¿A dónde acudir ESTA MISMA SEMANA?** Ve al **Centro de Conciliación Laboral** de tu estado o a la **PROFEDET** (donde te asignan un procurador gratuito). Lleva tu INE y la dirección del trabajo. Ellos le enviarán un citatorio oficial a tu patrón para que se siente a pagarte en una oficina de gobierno.",
            "🤝 **FASE 4: ¿Qué hacer el día de la cita de Conciliación?** El abogado de la empresa intentará asustarte diciendo que el juicio dura años para que aceptes la mitad. En conciliación, un arreglo justo y rápido nunca debe bajar del 75% al 100% de tu liquidación real, y si no quieren pagar, se les embargan bienes o cuentas."
        ]
        guion_palabra_por_palabra = (
            "💬 **Frase exacta para decirle a tu jefe o a Recursos Humanos:**\n"
            "\"Yo no estoy renunciando, ustedes me están despidiendo. No voy a firmar una carta de renuncia voluntaria porque no es verdad, "
            "y los $5,000 pesos que me ofrecen están muy por debajo de los 90 días de liquidación, vacaciones y días de descanso que marca la ley. "
            "Para que todo sea transparente para los dos, prefiero que hagamos el cálculo y el pago oficial en el Centro de Conciliación Laboral.\""
        )
        errores_fatales = [
            "🚫 **Error Fatal 1 (Caer en la trampa del 'Firma y luego te damos el resto'):** En cuanto pones tu firma o huella en una hoja de renuncia, ante el Juez significa que tú quisiste irte por tu gusto y pierdes automáticamente los 3 meses de sueldo ($" + f"{res_liq['monto_indem_90_dias']:,.2f} MXN).",
            "🚫 **Error Fatal 2 (Dejar pasar más de 60 días naturales):** Desde el día en que te corrieron tienes un reloj de 60 días seguidos (contando sábados y domingos). Si dejas pasar los 2 meses sin ir a Conciliación, tu derecho caduca y el patrón ya no te debe nada.",
            "🚫 **Error Fatal 3 (Salirte del grupo de WhatsApp del trabajo o borrar chats):** Antes de que el jefe te elimine del grupo de WhatsApp, toma capturas de pantalla donde se vea el número de teléfono de tu jefe y los mensajes donde te daba indicaciones."
        ]
        autoridad = "Centro de Conciliación Laboral / Procuraduría de la Defensa del Trabajo (PROFEDET)"

    elif categoria_caso == "Tránsito y Abuso Policial":
        radiografia = (
            "Leí detenidamente lo que te ocurrió con la patrulla/oficial de tránsito. Me indicas que te detuvieron bajo un pretexto o revisión, "
            "y que están intentando intimidarte con llevarse tu vehículo al corralón, quitarte documentos o presionarte para dar dinero ('mordida')."
        )
        explicacion_dinero = (
            "**¿Qué dice el Reglamento de Tránsito en realidad?** En México, **ningún policía puede cobrarte una multa en efectivo en la calle**, "
            "ni detenerte bajo el argumento de 'revisión de rutina' si no cometiste una infracción visible. Además, **la grúa y el corralón NO aplican para faltas menores**: "
            "solo pueden llevarse tu auto o moto si conduces bajo efectos del alcohol, si el vehículo no tiene placas o tiene reporte de robo, o si participaste en un choque con lesionados."
        )
        fases_paso_a_paso = [
            "🛑 **FASE 1: En el momento en que te detiene la patrulla:** Oríllate en un lugar seguro e iluminado, apaga el motor, baja tu ventanilla solo a la mitad, pon las manos sobre el volante y empieza a grabar con tu celular (en México es 100% legal grabar a un servidor público en funciones en la calle).",
            "🪪 **FASE 2: Verifica quién te está deteniendo:** No cualquier policía municipal o estatal puede levantar multas de tránsito; solo los agentes de tránsito facultados (que portan uniforme distintivo y terminal electrónica autorizada). Pide ver su gafete y anota el número económico de la patrulla.",
            "📄 **FASE 3: Si te amenazan con quitarte placas, licencia o llevarse el carro al corralón:** Pregunta con voz tranquila qué artículo exacto del Reglamento de Tránsito dice que esa falta amerita corralón. Exige que si cometiste una falta, te entreguen la boleta de infracción escrita para pagarla en la Tesorería con descuento (o impugnarla).",
            "🏛️ **FASE 4: Cómo anular la multa o denunciar la extorsión después:** Con el número de patrulla, la hora y tu video, acude a **Asuntos Internos de Seguridad Pública** para denunciar el intento de extorsión, o al **Tribunal de Justicia Administrativa** donde un defensor público gratuito anula las multas mal fundamentadas."
        ]
        guion_palabra_por_palabra = (
            "💬 **Frase exacta para decirle al policía de tránsito (con calma y grabando):**\n"
            "\"Oficial, con todo respeto, estoy grabando por seguridad de ambos. ¿Me puede indicar su nombre completo, número de patrulla y qué artículo exacto del Reglamento de Tránsito infringí? "
            "No cuento con efectivo y sé que no está permitido pagar aquí; si cometí una infracción, por favor elabóreme mi boleta oficial para acudir a Tesorería o al Tribunal Administrativo.\""
        )
        errores_fatales = [
            "🚫 **Error Fatal 1 (Dar 'mordida' en efectivo):** Además de alimentar el abuso, muchos malos elementos te graban dándoles billetes para luego extorsionarte más fuerte acusándote del delito de cohecho.",
            "🚫 **Error Fatal 2 (Bajarte del vehículo alterado, insultar o empujar al policía):** Aunque la detención sea injusta, si tocas o insultas al oficial les das el pretexto legal perfecto para arrestarte por faltas a la autoridad.",
            "🚫 **Error Fatal 3 (Entregar la llave de tu vehículo o desbloquear tu celular):** Ningún policía puede revisar tu teléfono celular ni tus mensajes sin una orden escrita de un Juez de Control (Art. 16 Constitucional)."
        ]
        autoridad = "Asuntos Internos de Seguridad Pública / Tribunal de Justicia Administrativa / Derechos Humanos"

    elif categoria_caso == "Casos Familiares":
        radiografia = (
            "Analicé tu situación familiar. El deudor alimentario ha dejado de cumplir con el pago de alimentos para tus hijos "
            "y busca ocultar sus ingresos reales o salirse de su empleo formal para evadir su responsabilidad."
        )
        explicacion_dinero = (
            "**¿Por qué la ley protege primero a tus hijos?** En México, la pensión alimenticia es un derecho humano prioritario de los niños y **no depende de que el papá o mamá diga que 'no tiene trabajo'**. "
            "El Juez Familiar fija una pensión provisional inmediata (generalmente del 15% al 30% por hijo o basada en el nivel de vida de los menores) y ordena investigar todas sus cuentas bancarias y registros ante el SAT."
        )
        fases_paso_a_paso = [
            "📂 **FASE 1: Reúne tu carpeta básica hoy mismo:** Junta las actas de nacimiento originales de tus hijos, comprobantes de domicilio y haz una lista con tickets de todo lo que gastan al mes (supermercado, escuela, uniformes, medicinas, renta, luz).",
            "🏛️ **FASE 2: Pide la Pensión Provisional en el Juzgado Familiar o DIF:** Acude con un abogado familiar o de forma 100% gratuita a la Procuraduría del DIF / Defensoría Pública. En la primera hoja de la demanda se pide una **Pensión Alimenticia Provisional** que el Juez decreta en pocos días sin esperar a que termine el juicio.",
            "🔍 **FASE 3: Destapa sus ingresos ocultos:** Pide que el Juez envíe un oficio a la Comisión Nacional Bancaria (CNBV) y al SAT para que entreguen todos los depósitos en efectivo y transferencias que recibe el deudor, además de inscribirlo en el **Registro Nacional de Obligaciones Alimentarias (RNOA)** (donde no podrá sacar pasaporte, licencia ni trámites hasta que pague)."
        ]
        guion_palabra_por_palabra = (
            "💬 **Frase exacta para mantener firmeza sin caer en pleitos por WhatsApp:**\n"
            "\"La pensión no es un favor para mí, es un derecho irrenunciable de nuestros hijos para comer, vestir y estudiar. "
            "Como los acuerdos de palabra no se han cumplido, a partir de ahora todo depósito y acuerdo de convivencia quedará fijado directamente ante el Juez de lo Familiar.\""
        )
        errores_fatales = [
            "🚫 **Error Fatal 1 (Prohibirle ver a los niños por cuenta propia como castigo):** No mezcles los alimentos con ocultar a los menores sin orden de un Juez; mejor pide al Juez la guarda y custodia legal para no darle armas en tu contra.",
            "🚫 **Error Fatal 2 (Confiar meses y meses en promesas verbales):** Los meses que pasan sin demandar son meses en los que tus hijos se quedan sin respaldo judicial."
        ]
        autoridad = "Juzgado de lo Familiar / Procuraduría de Protección de Niñas, Niños y Adolescentes (DIF)"

    elif categoria_caso == "Casos Penales":
        radiografia = (
            "Analicé tu relato sobre fraude bancario, extorsión o acoso de despachos de cobranza / aplicaciones de préstamos."
        )
        explicacion_dinero = (
            "**¿Qué debes saber para recuperar tu tranquilidad y tu dinero?** "
            "1) **Si es acoso de cobranza o apps de préstamos:** Nadie puede ir a embargar tu casa sin que antes exista un juicio real y te notifique un Actuario del Juzgado con identificación oficial; las amenazas por WhatsApp son ilegales (Art. 284 Bis del Código Penal). "
            "2) **Si vaciaron tu cuenta bancaria (Phishing/SPEI):** La Suprema Corte ha determinado que el banco debe responder y devolverte tu dinero con intereses si no prueba que tú autorizaste esas transferencias."
        )
        fases_paso_a_paso = [
            "🔒 **FASE 1: Protege tu evidencia digital y tus cuentas hoy:** Si fue robo bancario, llama de inmediato a tu banco para bloquear la cuenta y exige tu **folio de aclaración por cargos no reconocidos**. Si son amenazas por WhatsApp, toma capturas de pantalla donde se vea el número telefónico completo (sin guardar el contacto con nombre para que salga el número en la foto).",
            "🏛️ **FASE 2: Denuncia ante la autoridad correcta:** Para fraudes bancarios o despachos de cobranza abusivos, levanta tu queja en línea o presencial en **CONDUSEF (REDECO)**. Si son apps ilegales de préstamos ('montadeudas') que amenazan a tus contactos, repórtalo a la **Policía Cibernética** y Fiscalía.",
            "🛡️ **FASE 3: Sella tus pruebas:** Descarga el Dictamen en Word de esta aplicación que incluye tu código Hash SHA-256 para dejar constancia de tus capturas y relato."
        ]
        guion_palabra_por_palabra = (
            "💬 **Frase exacta para responder a cobradores abusivos:**\n"
            "\"La cobranza con amenazas, insultos o llamando a mis contactos es un delito previsto en el artículo 284 Bis del Código Penal Federal. "
            "Cualquier requerimiento legal deberá notificarse por escrito a través de un juzgado competente; estoy grabando esta llamada para anexarla a mi reporte ante CONDUSEF y Policía Cibernética.\""
        )
        errores_fatales = [
            "🚫 **Error Fatal 1 (Depositar dinero a cuentas personales por miedo a un falso embargo):** Los despachos de cobranza envían hojas falsas con sellos inventados que dicen 'Embargo en 24 horas' para asustarte. Un embargo real solo lo ordena un Juez.",
            "🚫 **Error Fatal 2 (Borrar los mensajes o formatear tu celular):** Tu teléfono contiene las pruebas del fraude o la extorsión; consérvalas intactas."
        ]
        autoridad = "CONDUSEF / Policía Cibernética / Fiscalía General de Justicia (Ministerio Público)"

    else:
        radiografia = (
            f"Leí a detalle tu caso relacionado con **{categoria_caso} ({tipo_caso})** sobre incumplimiento de pago de rentas, contrato o pagaré."
        )
        explicacion_dinero = (
            "**¿Cómo recuperar tu casa o tu dinero sin meterte en un problema legal?** "
            "La ley protege al dueño de un inmueble o acreedor de un pagaré permitiéndole pedir al Juez el **embargo de bienes o cuentas desde el inicio del juicio** y la orden legal de desocupación."
        )
        fases_paso_a_paso = [
            "📑 **FASE 1: Asegura tus documentos originales:** Guarda en un lugar seguro el contrato de arrendamiento original, los pagarés firmados y los estados de cuenta donde se vea desde qué mes dejó de pagar.",
            "⚖️ **FASE 2: Presenta la demanda civil o ejecutiva mercantil:** Con un pagaré original, el Juez ordena acudir al domicilio del deudor desde el primer día para requerir el pago o embargar bienes en ese mismo acto.",
            "🔑 **FASE 3: Recuperación legal con apoyo del Actuario:** Si es un inquilino moroso, el Juez le da un plazo breve para demostrar que ya pagó o desocupar; si no lo hace, se autoriza el lanzamiento legal."
        ]
        guion_palabra_por_palabra = (
            "💬 **Frase exacta para requerir el pago al inquilino o deudor:**\n"
            "\"Ya venció el plazo acordado y tengo los documentos originales firmados. Te doy de plazo hasta este viernes para liquidar el adeudo o firmar el convenio de entrega; "
            "de lo contrario, el lunes ingresaré la demanda ante el Juez solicitando el embargo de bienes más el cobro de intereses y gastos del juicio.\""
        )
        errores_fatales = [
            "🚫 **Error Fatal 1 (Cambiar la chapa, cortar el agua/luz o sacar las cosas del inquilino a la calle por tu cuenta):** Aunque la casa sea tuya y te deba meses de renta, si te metes sin orden del Juez el inquilino te puede denunciar penalmente por el delito de **Despojo**.",
            "🚫 **Error Fatal 2 (Alterar o remarcar con otra pluma la fecha o cantidad de un pagaré):** Si rellenas espacios con otra tinta después de firmado, un perito puede anular todo tu pagaré."
        ]
        autoridad = "Juzgado Civil / Juzgado Mercantil / Centro de Mediación"

    return {
        "radiografia": radiografia,
        "explicacion_dinero": explicacion_dinero,
        "fases_paso_a_paso": fases_paso_a_paso,
        "guion_palabra_por_palabra": guion_palabra_por_palabra,
        "errores_fatales": errores_fatales,
        "autoridad": autoridad,
        "hash_evidencia": hashlib.sha256(relato_usuario.encode("utf-8")).hexdigest()
    }

# ==============================================================================
# 5. AGENTE DE BÚSQUEDA EN VIVO EN INTERNET + RED NEURONAL AUTO-EVOLUTIVA
# ==============================================================================
def buscar_informacion_juridica_en_internet(categoria_caso: str, tipo_caso: str) -> dict:
    resultados_web = []
    textos_para_entrenar = []

    termino_wiki = "Reglamento de tránsito México" if "Tránsito" in categoria_caso else f"{tipo_caso} derecho México"
    try:
        url_wiki = (
            "https://es.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(termino_wiki)}&utf8=&format=json&srlimit=2"
        )
        req_w = urllib.request.Request(url_wiki, headers={"User-Agent": "ForensicMindLegalBot/8.0"})
        with urllib.request.urlopen(req_w, timeout=4.0) as resp_w:
            data_w = json.loads(resp_w.read().decode("utf-8"))
            for item in data_w.get("query", {}).get("search", []):
                titulo_w = item.get("title", "")
                snip_w = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                link_w = f"https://es.wikipedia.org/wiki/{urllib.parse.quote(titulo_w.replace(' ', '_'))}"
                resultados_web.append({
                    "fuente": "📖 Enciclopedia Legal / Wikipedia",
                    "titulo": titulo_w,
                    "resumen": snip_w,
                    "url": link_w
                })
                textos_para_entrenar.append(f"{titulo_w} {snip_w}")
    except Exception:
        pass

    mapa_queries_news = {
        "Casos Laborales": "despido injustificado liquidacion Ley Federal del Trabajo PROFEDET Mexico",
        "Tránsito y Abuso Policial": "multa transito corralon abuso policial reglamento derechos conductor Mexico",
        "Casos Familiares": "pension alimenticia deudor alimentario Juez Familiar SCJN Mexico",
        "Casos Penales": "fraude bancario CONDUSEF cobranza ilegal SCJN Mexico",
        "Casos Civiles": "arrendamiento desalojo inquilino contrato civil Mexico",
        "Casos Mercantiles": "pagare embargo juicio ejecutivo mercantil Mexico"
    }
    q_news = mapa_queries_news.get(categoria_caso, "derechos ciudadanos ley Mexico")

    try:
        url_gnews = (
            "https://news.google.com/rss/search?"
            f"q={urllib.parse.quote(q_news)}&hl=es-419&gl=MX&ceid=MX:es-419"
        )
        req_g = urllib.request.Request(url_gnews, headers={"User-Agent": "ForensicMindLegalBot/8.0"})
        with urllib.request.urlopen(req_g, timeout=4.0) as resp_g:
            root = ET.fromstring(resp_g.read())
            for it in root.findall(".//item")[:3]:
                tit = it.find("title").text if it.find("title") is not None else "Criterio Jurídico Reciente"
                lnk = it.find("link").text if it.find("link") is not None else "https://www.scjn.gob.mx"
                pub = it.find("pubDate").text[:16] if it.find("pubDate") is not None else "Reciente"
                resultados_web.append({
                    "fuente": f"🌐 Google Noticias Jurídicas ({pub})",
                    "titulo": tit,
                    "resumen": f"Noticia y criterio actualizado en internet sobre {categoria_caso}.",
                    "url": lnk
                })
                textos_para_entrenar.append(tit)
    except Exception:
        pass

    return {"resultados": resultados_web, "corpus_web_extraido": " ".join(textos_para_entrenar)}

def entrenar_red_neuronal_evolutiva():
    conn = sqlite3.connect(DB_NAME)
    df_base = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    df_mem = pd.read_sql_query("SELECT * FROM memoria_neuronal_autonoma", conn)
    conn.close()

    if df_base.empty or MLPClassifier is None or TfidfVectorizer is None:
        return None, None, {"total_muestras": len(df_base), "experiencias_aprendidas": len(df_mem), "vocabulario_ngramas": 0}

    textos, etiquetas = [], []
    for _, r in df_base.iterrows():
        textos.append(expandir_lenguaje_coloquial(f"{r['titulo']} {r['evidencia_logs']} {r['tipo_caso']} {r['categoria_caso']} {r['que_hacer_ciudadano']}"))
        etiquetas.append(f"{r['categoria_caso']}|{r['rama_derecho']}|{r['tipo_caso']}|{r['macro_rama']}")
    for _, m in df_mem.iterrows():
        textos.append(str(m["relato_expandido"]))
        etiquetas.append(f"{m['categoria_caso']}|{m['rama_derecho']}|{m['tipo_caso']}|{m['macro_rama']}")

    vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=2400)
    X_vec = vectorizer.fit_transform(textos)
    mlp = MLPClassifier(hidden_layer_sizes=(96, 48), activation="relu", max_iter=450, random_state=42)
    mlp.fit(X_vec, etiquetas)

    return vectorizer, mlp, {
        "total_muestras": len(textos),
        "experiencias_aprendidas": len(df_mem),
        "vocabulario_ngramas": len(vectorizer.vocabulary_)
    }

def autoclasificar_caso_con_red_neuronal(relato: str, vectorizer_mlp, modelo_mlp) -> dict:
    relato_expandido = expandir_lenguaje_coloquial(relato)
    texto_low = relato_expandido.lower()

    scores = {
        "Casos Laborales": 0,
        "Tránsito y Abuso Policial": 0,
        "Casos Familiares": 0,
        "Casos Penales": 0,
        "Casos Civiles": 0,
        "Casos Mercantiles": 0
    }

    reglas = {
        "

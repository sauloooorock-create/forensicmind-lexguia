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
# SELLO DE AUTORÍA Y CONFIGURACIÓN GLOBAL v8.0 (NIVEL 1000%)
# ==============================================================================
AUTOR_SISTEMA = "Ing. Industrial y de Sistemas Saúl Ángel Ortiz Rogel"
MARCA_SISTEMA = "ForensicMind & LexGuía CBR v8.0 — Asesoría Ciudadana Paso a Paso & Auto-Sync"

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
DEFAULT_ADMIN_EMAIL = ""

try:
    DEFAULT_GH_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
    DEFAULT_GH_REPO = st.secrets.get("GITHUB_REPO", "sauloooorock-create/forensicmind-lexguia")
    DEFAULT_GH_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
    DEFAULT_ADMIN_PASS = st.secrets.get("ADMIN_PASSWORD", "admin2026")
    DEFAULT_ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "")
except Exception:
    pass

if "es_admin" not in st.session_state:
    st.session_state["es_admin"] = False

# ==============================================================================
# BARRA LATERAL: LOGIN DE ADMINISTRADOR Y AJUSTES VISUALES
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎨 Apariencia de la Pantalla")
    modo_visual = st.radio(
        "Elige cómo prefieres leer:",
        ["☀️ Modo Claro (Fácil lectura en celular)", "🌙 Modo Oscuro Forense"],
        index=0
    )
    buscar_web_switch = st.checkbox(
        "🌐 Consultar noticias y criterios en Internet en vivo",
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
                st.success("✅ Bienvenido, Ing. Saúl.")
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta.")
        gh_repo_input = DEFAULT_GH_REPO
        gh_token_input = DEFAULT_GH_TOKEN
        gh_branch_input = DEFAULT_GH_BRANCH
        admin_email_input = DEFAULT_ADMIN_EMAIL
        auto_entrenar_switch = True
    else:
        st.success("✅ Modo Administrador Activo")
        auto_entrenar_switch = st.checkbox("🧠 Auto-Aprendizaje e Inyección Activa", value=True)
        gh_repo_input = st.text_input("Repositorio GitHub:", value=DEFAULT_GH_REPO)
        gh_token_input = st.text_input("GitHub Token (ghp_...):", value=DEFAULT_GH_TOKEN, type="password")
        gh_branch_input = st.text_input("Rama (Branch):", value=DEFAULT_GH_BRANCH)
        admin_email_input = st.text_input(
            "Tu correo para recibir dudas:",
            value=DEFAULT_ADMIN_EMAIL,
            placeholder="tucorreo@gmail.com"
        )
        if st.button("🔒 Cerrar Sesión Admin", use_container_width=True):
            st.session_state["es_admin"] = False
            st.rerun()

if "Claro" in modo_visual:
    st.markdown("""
    <style>
        .stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }
        .block-container { padding-top: 3.2rem !important; padding-bottom: 2.5rem !important; }
        h1, h2, h3, h4, h5, h6, p, li, span, div { color: #0f172a; }
        label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 1.02rem !important;
        }
        textarea, input[type="text"], input[type="number"], input[type="password"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #2563eb !important;
            border-radius: 10px !important;
            font-size: 1.04rem !important;
            font-weight: 600 !important;
            padding: 12px !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }
        .author-banner {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
            border-left: 6px solid #f59e0b;
            border-radius: 14px;
            padding: 16px 20px;
            margin-bottom: 18px;
        }
        .author-banner * { color: #ffffff !important; }
        div[data-testid="metric-container"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-left: 5px solid #2563eb !important;
            padding: 14px !important;
            border-radius: 12px !important;
        }
        div[data-testid="metric-container"] label { color: #475569 !important; -webkit-text-fill-color: #475569 !important; }
        div[data-testid="stMetricValue"] { color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; font-weight: 800 !important; }
        .win-badge { background-color: #059669; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .loss-badge { background-color: #dc2626; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .step-badge { background-color: #1d4ed8; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 5px 12px; border-radius: 6px; font-weight: 800; display: inline-block; }
        .card-box { background-color: #ffffff; border: 1px solid #cbd5e1; border-left: 6px solid #2563eb; border-radius: 12px; padding: 18px; margin: 12px 0; color: #0f172a !important; line-height: 1.65; }
        .money-box { background-color: #ecfdf5; border: 1px solid #6ee7b7; border-left: 6px solid #059669; border-radius: 12px; padding: 18px; margin: 12px 0; color: #064e3b !important; line-height: 1.65; }
        .lawyer-box { background-color: #eef2ff; border: 1px solid #a5b4fc; border-left: 6px solid #4f46e5; border-radius: 12px; padding: 18px; margin: 12px 0; color: #1e1b4b !important; line-height: 1.65; }
        .alert-box { background-color: #fef2f2; border: 1px solid #fca5a5; border-left: 6px solid #dc2626; border-radius: 12px; padding: 18px; margin: 12px 0; color: #7f1d1d !important; line-height: 1.65; }
        .script-box { background-color: #fffbeb; border: 1px solid #fcd34d; border-left: 6px solid #d97706; border-radius: 12px; padding: 18px; margin: 12px 0; color: #78350f !important; line-height: 1.65; }
        .web-box { background-color: #f0f9ff; border: 1px solid #7dd3fc; border-left: 6px solid #0284c7; border-radius: 12px; padding: 16px; margin: 10px 0; color: #0c4a6e !important; }
        div.stButton > button:first-child {
            background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            font-weight: 800 !important;
            font-size: 1.04rem !important;
            border-radius: 10px !important;
            border: none !important;
            padding: 13px 20px !important;
        }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .stApp { background-color: #0b0f19 !important; color: #f8fafc !important; }
        .block-container { padding-top: 3.2rem !important; padding-bottom: 2.5rem !important; }
        h1, h2, h3, h4, h5, h6, p, li, label, [data-testid="stWidgetLabel"] p { color: #f8fafc !important; -webkit-text-fill-color: #f8fafc !important; font-weight: 600 !important; }
        textarea, input[type="text"], input[type="number"], input[type="password"] {
            background-color: #ffffff !important; color: #0f172a !important; -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #38bdf8 !important; border-radius: 10px !important; font-size: 1.04rem !important; font-weight: 700 !important; padding: 12px !important;
        }
        div[data-baseweb="select"] > div { background-color: #1e293b !important; color: #f8fafc !important; -webkit-text-fill-color: #f8fafc !important; border: 1px solid #38bdf8 !important; }
        .author-banner { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border: 1px solid #38bdf8; border-left: 6px solid #f59e0b; border-radius: 12px; padding: 16px 20px; margin-bottom: 18px; }
        div[data-testid="metric-container"] { background: #111827 !important; border: 1px solid #374151 !important; border-left: 4px solid #38bdf8 !important; padding: 14px !important; border-radius: 10px !important; }
        .win-badge { background-color: #065f46; color: #34d399 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .loss-badge { background-color: #7f1d1d; color: #f87171 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .step-badge { background-color: #1e3a8a; color: #93c5fd !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .card-box { background-color: #131c2e; border: 1px solid #2dd4bf; border-radius: 10px; padding: 18px; margin: 12px 0; line-height: 1.65; }
        .money-box { background-color: #0f2922; border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 10px; padding: 18px; margin: 12px 0; line-height: 1.65; }
        .lawyer-box { background-color: #1e1b4b; border: 1px solid #818cf8; border-left: 5px solid #a78bfa; border-radius: 10px; padding: 18px; margin: 12px 0; line-height: 1.65; }
        .alert-box { background-color: #1f1215; border: 1px solid #f87171; border-left: 5px solid #ef4444; border-radius: 10px; padding: 18px; margin: 12px 0; line-height: 1.65; }
        .script-box { background-color: #271c09; border: 1px solid #f59e0b; border-left: 5px solid #fbbf24; border-radius: 10px; padding: 18px; margin: 12px 0; line-height: 1.65; }
        .web-box { background-color: #0c192c; border: 1px solid #38bdf8; border-left: 5px solid #0284c7; border-radius: 10px; padding: 16px; margin: 10px 0; }
        div.stButton > button:first-child { background-color: #2563eb !important; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; font-weight: bold !important; border-radius: 10px !important; padding: 12px 20px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. CATÁLOGO DE PROBLEMAS CIUDADANOS (INCLUYE TRÁNSITO Y POLICÍAS)
# ==============================================================================
TIPOS_CASOS = {
    "Casos Laborales": [
        "Despido injustificado",
        "Coacción para firmar renuncia u hoja en blanco",
        "Salarios, vacaciones o días de descanso no pagados",
        "Acoso laboral o maltrato del jefe",
        "Accidente de trabajo sin seguro (IMSS)"
    ],
    "Casos de Tránsito y Policía": [
        "Abuso en retén o revisión de rutina sin motivo",
        "Intento de mordida o amenaza de llevar al corralón",
        "Retención ilegal de placas, licencia o tarjeta de circulación",
        "Policía quiere revisar mi celular o mochila sin orden",
        "Choque vial y abuso de grúa o ajustador"
    ],
    "Casos Familiares": [
        "Pensión alimenticia (Papá o mamá que no da gasto)",
        "Divorcio y separación de bienes",
        "Guarda, custodia y visitas de los hijos"
    ],
    "Casos Penales y Fraudes": [
        "Fraude bancario, vaciado de cuenta o transferencia SPEI",
        "Acoso de cobranza o préstamos por aplicación",
        "Detención arbitraria por patrulla",
        "Robo o estafa comercial"
    ],
    "Casos Civiles": [
        "Inquilino que no paga la renta ni se quiere salir",
        "Abuso del casero (quiere sacarme sin orden de juez)",
        "Incumplimiento de contrato o daños"
    ],
    "Casos Mercantiles": [
        "Cobro de pagaré firmado o dinero prestado",
        "Mercancía entregada que no quieren pagar"
    ]
}

TABULADOR_HONORARIOS_RAMA = {
    "Casos Laborales": {
        "asesoria_min": 0, "asesoria_sug": 800, "asesoria_max": 1500, "anticipo_sug": 0,
        "esquema_cobro": "Porcentaje al ganar (el abogado cobra del 20% al 30% solo cuando tú cobras tu dinero; $0 de anticipo inicial)",
        "pct_sugerido": 25.0, "gastos_periciales_sug": 500, "horas_promedio_despacho": 35,
        "via_gratuita": "PROFEDET y Centro de Conciliación Laboral — $0 pesos (100% Gratis para el trabajador)"
    },
    "Casos de Tránsito y Policía": {
        "asesoria_min": 0, "asesoria_sug": 800, "asesoria_max": 2000, "anticipo_sug": 2500,
        "esquema_cobro": "Trámite de impugnación de multa ante Tribunal Administrativo o queja en Asuntos Internos",
        "pct_sugerido": 0.0, "gastos_periciales_sug": 500, "horas_promedio_despacho": 15,
        "via_gratuita": "Asuntos Internos de Seguridad Pública / Defensoría de Justicia Administrativa — $0 pesos (100% Gratis)"
    },
    "Casos Familiares": {
        "asesoria_min": 500, "asesoria_sug": 1000, "asesoria_max": 2000, "anticipo_sug": 5000,
        "esquema_cobro": "Pago fijo dividido en etapas conforme avanza el juez familiar",
        "pct_sugerido": 0.0, "gastos_periciales_sug": 2000, "horas_promedio_despacho": 45,
        "via_gratuita": "Procuraduría del DIF y Defensoría Pública Familiar de tu Estado — $0 pesos"
    },
    "Casos Penales y Fraudes": {
        "asesoria_min": 800, "asesoria_sug": 1500, "asesoria_max": 3500, "anticipo_sug": 10000,
        "esquema_cobro": "Cobro por etapa (Denuncia en Ministerio Público / Audiencia Inicial / Juicio)",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 4000, "horas_promedio_despacho": 60,
        "via_gratuita": "CONDUSEF (para bancos), Policía Cibernética y Defensoría Pública Penal — $0 pesos"
    },
    "Casos Civiles": {
        "asesoria_min": 700, "asesoria_sug": 1200, "asesoria_max": 2500, "anticipo_sug": 6000,
        "esquema_cobro": "Anticipo inicial + porcentaje de las rentas o propiedad recuperada",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 3000, "horas_promedio_despacho": 45,
        "via_gratuita": "Defensoría Pública Civil del Poder Judicial de tu Estado — $0 pesos"
    },
    "Casos Mercantiles": {
        "asesoria_min": 800, "asesoria_sug": 1500, "asesoria_max": 3000, "anticipo_sug": 5000,
        "esquema_cobro": "Anticipo para embargo + 15% a 25% de lo que se le cobre al deudor",
        "pct_sugerido": 20.0, "gastos_periciales_sug": 3000, "horas_promedio_despacho": 35,
        "via_gratuita": "PROFECO o Defensoría de Oficio — $0 pesos"
    }
}

ESCENARIOS_FRECUENTES = {
    "✍️ Escribir o dictar mi propio problema con mis palabras": "Mi sueldo semanal es de 2300. Me despidieron y no me quieren dar liquidación, solo me quieren dar $5000 y no me daban vacaciones ni días libres ni bonos, ¿qué procede ahí?",
    "🚓 Tránsito y Policía: Patrulla me paró sin motivo, pide mordida y amenaza con corralón": "Iba manejando mi moto o carro tranquilo, una patrulla de tránsito me paró diciendo que es revisión de rutina, me quieren quitar la placa o llevarse mi vehículo al corralón con grúa si no les doy para el refresco.",
    "💼 Laboral: Me corrieron hoy y me quieren obligar a firmar mi renuncia u hoja en blanco": "Me corrieron del trabajo hoy sin darme aviso escrito, el encargado de recursos humanos me tiene en la oficina y dice que si no le firmo mi hoja de renuncia voluntaria no me va a pagar ni mi semana trabajada.",
    "👨‍👩‍👧 Familiar: El papá o mamá de mis hijos no da gasto y esconde su dinero": "El papá de mis hijos lleva meses sin dar dinero para la comida ni escuela de los niños, dice que no tiene trabajo para no dar pensión pero sí cobra dinero por fuera.",
    "📱 Fraude Bancario / Cobranza: Me vaciaron la cuenta o me amenazan de una app de préstamos": "Me robaron dinero de mi cuenta del banco con movimientos que yo no hice y además me están mandando mensajes de amenazas a mí y a mis contactos.",
    "🏠 Renta / Inquilinos: Mi inquilino no paga la renta o el dueño me quiere sacar a la fuerza": "Le renté a una persona que lleva 4 meses sin pagar renta, ya venció el contrato y no se quiere salir de la casa.",
    "📑 Deudas y Pagarés: Presté dinero con un pagaré firmado y se esconden para no pagar": "Una persona me firmó un pagaré hace meses por dinero que le presté, ya pasó la fecha de pago y no me quiere pagar."
}

# ==============================================================================
# 2. TRADUCTOR DE PALABRAS COLOQUIALES -> COMPRENSIÓN DE LA RED NEURONAL
# ==============================================================================
DICCIONARIO_COLOQUIAL_A_JURIDICO = [
    (r'\b(chamba|jale|empleo|trabajo|oficina|empresa|fabrica|tienda|bodega|turno)\b', ' trabajo laboral patron '),
    (r'\b(corrieron|echaron|despidieron|cortaron|dieron de baja|ya no me dejaron entrar)\b', ' despido injustificado laboral '),
    (r'\b(patron|jefe|gerente|rh|recursos humanos|supervisor|encargado)\b', ' patron laboral empleador '),
    (r'\b(liquidacion|finiquito|quincena|semanal|raya|sueldo|nomina|aguinaldo|vacaciones|dias libres|descanso|horas extras|bonos)\b', ' liquidacion salario prestaciones laboral '),
    (r'\b(hoja en blanco|firmar mi renuncia|renuncia voluntaria|quieren dar solo|solo me dan)\b', ' coaccion laboral despido injustificado '),
    (r'\b(transito|policia|patrulla|mordida|infraccion|multa|corralon|grua|placas|licencia|tarjeta de circulacion|reten|moto|carro|auto|vehiculo|oficial)\b', ' transito policia vialidad corralon multa abuso '),
    (r'\b(gasto de los niños|manutencion|pension|alimentos|papa de mis hijos|mama de mis hijos|divorcio|custodia)\b', ' pension alimenticia familiar custodia hijos '),
    (r'\b(vaciaron mi cuenta|robaron mi tarjeta|phishing|hackearon|estafaron|clonaron|spei|cobranza|prestamo)\b', ' fraude bancario penal ciberdelito '),
    (r'\b(inquilino|renta|arrendamiento|depa|departamento|casa rentada|desalojar|cambiar la chapa)\b', ' arrendamiento civil inquilino desocupacion '),
    (r'\b(pagare|cheque sin fondos|mercancia fiada|deudor comercial)\b', ' pagare ejecutivo mercantil cobranza ')
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
# 3. AUTOINYECCIÓN PERPETUA Y SINCRONIZACIÓN CON GITHUB API
# ==============================================================================
def inyectar_diccionario_cerebro_en_sqlite(data: dict, conn: sqlite3.Connection) -> dict:
    c = conn.cursor()
    nuevos_mem = 0
    nuevos_casos = 0
    nuevos_buzon = 0

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
            rel_orig, rel_exp,
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
            cod,
            cs.get("macro_rama", "Derecho Privado"),
            cs.get("rama_derecho", "Derecho Laboral"),
            cs.get("categoria_caso", "Casos Laborales"),
            cs.get("tipo_caso", "Despido injustificado"),
            cs.get("titulo", "Caso Restaurado"),
            cs.get("actores_intervinientes", "Autoridad, Abogado"),
            cs.get("etapa_clave", "1. Inicio"),
            cs.get("medida_cautelar", "Protección"),
            cs.get("resolucion_obtenida", "Resolución"),
            cs.get("recurso_utilizado", "Defensa"),
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

    for bz in data.get("buzon_casos_usuarios", []):
        h_bz = bz.get("hash_mensaje")
        if not h_bz:
            continue
        c.execute("""
            INSERT OR IGNORE INTO buzon_casos_usuarios (
                nombre_usuario, contacto_usuario, categoria_sugerida,
                descripcion_duda, estado_revision, hash_mensaje, fecha_envio
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            bz.get("nombre_usuario", "Ciudadano"),
            bz.get("contacto_usuario", ""),
            bz.get("categoria_sugerida", "Casos Laborales"),
            bz.get("descripcion_duda", ""),
            bz.get("estado_revision", "PENDIENTE"),
            h_bz,
            bz.get("fecha_envio", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
        "message": f"Auto-Sync ForensicMind v8.0 ({len(df_mem)} memorias | {len(df_buzon)} buzon)",
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
# 4. INICIALIZACIÓN DE SQLITE Y CASOS SEMILLA (INCLUYE TRÁNSITO Y LABORAL)
# ==============================================================================
def init_db_and_autoinject(repo_gh: str = "", token_gh: str = "", branch_gh: str = "main"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS casos_juridicos_cbr (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_caso TEXT UNIQUE,
            macro_rama TEXT,
            rama_derecho TEXT,
            categoria_caso TEXT,
            tipo_caso TEXT,
            titulo TEXT,
            actores_intervinientes TEXT,
            etapa_clave TEXT,
            medida_cautelar TEXT,
            resolucion_obtenida TEXT,
            recurso_utilizado TEXT,
            evidencia_logs TEXT,
            hash_sha256 TEXT,
            resultado TEXT,
            accion_abogado TEXT,
            reaccion_juez TEXT,
            causa_raiz_fallo TEXT,
            estrategia_ganadora TEXT,
            que_hacer_ciudadano TEXT,
            que_no_hacer_ciudadano TEXT,
            fecha_registro TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS memoria_neuronal_autonoma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relato_original TEXT,
            relato_expandido TEXT,
            macro_rama TEXT,
            rama_derecho TEXT,
            categoria_caso TEXT,
            tipo_caso TEXT,
            fuente_aprendizaje TEXT,
            confianza REAL,
            hash_consulta TEXT UNIQUE,
            fecha_aprendizaje TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS buzon_casos_usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_usuario TEXT,
            contacto_usuario TEXT,
            categoria_sugerida TEXT,
            descripcion_duda TEXT,
            estado_revision TEXT,
            hash_mensaje TEXT UNIQUE,
            fecha_envio TEXT
        )
    """)

    semillas = [
        (
            "EXP-LAB-2026-001", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Trabajador con Sueldo Semanal Despedido sin Vacaciones Rechaza $5,000 y Cobra Liquidación Completa",
            "Procurador PROFEDET / Conciliador Laboral",
            "Cita de Conciliación", "Citación obligatoria al patrón", "Pago completo en convenio oficial", "Solicitud de Conciliación",
            "Mi sueldo semanal es de 2300, me despidieron y solo me quieren dar $5000 sin vacaciones ni días libres ni bonos.",
            hashlib.sha256(b"EXP-LAB-2026-001").hexdigest(), "GANADO",
            "El trabajador no firmó la renuncia, rechazó los $5,000 engañosos y acudió al Centro de Conciliación exigiendo sus 90 días de sueldo más vacaciones y descansos trabajados.",
            "La autoridad laboral obligó a la empresa a pagar la liquidación real completa para evitar juicio y embargo.",
            "N/A", "No firmar renuncia y acudir en la primera semana al Centro de Conciliación.",
            "Guardar mensajes de WhatsApp del jefe, no firmar renuncia y acudir gratis a PROFEDET o Conciliación.",
            "JAMÁS firmar una hoja en blanco o carta de renuncia a cambio de $5,000.",
            "2026-08-01"
        ),
        (
            "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Trabajador Pierde su Liquidación por Firmar Hoja de Renuncia a Cambio de $5,000 Rápidos",
            "Juez Laboral",
            "Audiencia Inicial", "Ninguna", "Absolución del patrón", "Demanda tardía",
            "Trabajador aceptó $5,000 en efectivo y firmó una hoja que decía renuncia voluntaria creyendo que luego podía reclamar más.",
            hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "PERDIDO",
            "El patrón exhibió en el juzgado la hoja firmada por el trabajador donde decía que él solito renunció y que no se le debía nada.",
            "El Juez dio por válida la renuncia firmada y el trabajador perdió más de $40,000 pesos.",
            "Firmar papeles de renuncia por presión o dejar pasar más de 60 días.",
            "N/A", "Leer todo antes de firmar y salir de la oficina sin firmar si el monto es injusto.",
            "NUNCA firmar renuncia voluntaria cuando en realidad te están corriendo.",
            "2026-08-05"
        ),
        (
            "EXP-VIAL-2026-003", "Derecho Público", "Derecho Administrativo", "Casos de Tránsito y Policía", "Intento de mordida o amenaza de llevar al corralón",
            "Conductor Frena Extorsión de Patrulla y Evita Corralón Ilegal Grabando el Procedimiento",
            "Agente de Tránsito, Asuntos Internos",
            "Detención en vía pública", "Grabación ciudadana y solicitud de boleta oficial", "Cancelación de acto arbitrario", "Queja en Asuntos Internos",
            "Una patrulla me paró por supuesta revisión de rutina en mi moto o carro, me amenazaron con llevarse el vehículo al corralón con grúa si no les daba dinero de mordida.",
            hashlib.sha256(b"EXP-VIAL-2026-003").hexdigest(), "GANADO",
            "El conductor mantuvo la calma, encendió la cámara de su celular, pidió el nombre y número de patrulla del oficial y exigió que le señalaran el artículo exacto del Reglamento de Tránsito.",
            "Al ver que el ciudadano conocía que una revisión de rutina no amerita corralón y estaba grabando legalmente, los policías devolvieron los documentos y se retiraron.",
            "N/A", "Conocer las únicas causas reales de corralón, grabar con respeto y nunca dar mordida.",
            "Grabar desde tu asiento sin obstruir, pedir número de patrulla y exigir boleta oficial si hubo infracción real.",
            "JAMÁS insultar ni empujar al policía, ni entregar dinero en efectivo en la calle.",
            "2026-09-02"
        ),
        (
            "EXP-VIAL-2026-004", "Derecho Público", "Derecho Administrativo", "Casos de Tránsito y Policía", "Intento de mordida o amenaza de llevar al corralón",
            "Conductor Termina Detenido en el Juez Cívico por Insultar y Forcejear con el Policía de Tránsito",
            "Juez Cívico / Policía Municipal",
            "Detención en calle", "Ninguna", "Arresto administrativo y corralón", "Ninguno",
            "Conductor se bajó furioso del auto, gritó groserías y trató de arrebatarle su licencia de las manos al policía.",
            hashlib.sha256(b"EXP-VIAL-2026-004").hexdigest(), "PERDIDO",
            "Aunque la parada inicial de la patrulla era injusta, el conductor perdió la calma y agredió verbal y físicamente al oficial.",
            "Los policías pidieron refuerzos, lo subieron a la patrulla por faltas a la autoridad y se llevaron el vehículo al corralón.",
            "Perder los estribos, gritar insultos o tocar físicamente al policía.",
            "N/A", "Mantener las manos visibles en el volante y reclamar todo por la vía legal con video.",
            "NUNCA forcejear, insultar ni bajarte agresivo frente a una patrulla.",
            "2026-09-06"
        ),
        (
            "EXP-FAM-2026-005", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia (Papá o mamá que no da gasto)",
            "Madre Logra Pensión Alimenticia Provisional Aunque el Padre Ocultaba su Sueldo",
            "Juez Familiar, Procuraduría DIF",
            "Demanda inicial de alimentos", "Descuento directo y rastreo SAT/Bancos", "Pensión asegurada para los hijos", "Oficios a bancos y SAT",
            "El papá de mis hijos lleva meses sin dar gasto, se salió de su trabajo para decir que no tiene dinero pero cobra por fuera.",
            hashlib.sha256(b"EXP-FAM-2026-005").hexdigest(), "GANADO",
            "Se acudió al Juez Familiar pidiendo pensión provisional urgente y que se revisaran las cuentas bancarias y nivel de vida del deudor.",
            "El Juez fijó pensión obligatoria desde la primera semana a favor de los niños.",
            "N/A", "Pedir pensión provisional con las actas de nacimiento de los niños.",
            "Juntar actas de nacimiento y recibos de gastos de los hijos y acudir al DIF o Juez Familiar.",
            "No quedarte esperando promesas de palabra que nunca cumple.",
            "2026-09-12"
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

    if "autoinyeccion_remota_lista" not in st.session_state and repo_gh and token_gh:
        data_remota = descargar_cerebro_desde_github(repo_gh, token_gh, branch_gh)
        if data_remota:
            inyectar_diccionario_cerebro_en_sqlite(data_remota, conn)
        st.session_state["autoinyeccion_remota_lista"] = True

    conn.close()

init_db_and_autoinject(gh_repo_input, gh_token_input, gh_branch_input)

# ==============================================================================
# 5. EXTRACTOR DE DATOS DEL RELATO Y CALCULADORA LABORAL COMPLETA (CON DESCANSOS)
# ==============================================================================
def normalizar_texto_coloquial(texto: str) -> dict:
    texto_low = texto.lower().replace(",", "")
    salario_mensual = None
    periodicidad = "Mensual ($9,857.14 / mes)"
    sueldo_base_periodo = 2300.0

    m_sem = re.search(
        r'(?:semanal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la semana|semanal(?:es)?|por semana))',
        texto_low
    )
    if m_sem:
        val = float(m_sem.group(1) or m_sem.group(2))
        sueldo_base_periodo = val
        salario_mensual = round((val / 7.0) * 30.0, 2)
        periodicidad = f"Semanal (${val:,.2f} a la semana)"

    if salario_mensual is None:
        m_quin = re.search(
            r'(?:quincenal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la quincena|quincenal(?:es)?|por quincena))',
            texto_low
        )
        if m_quin:
            val = float(m_quin.group(1) or m_quin.group(2))
            sueldo_base_periodo = val
            salario_mensual = round(val * 2.0, 2)
            periodicidad = f"Quincenal (${val:,.2f} a la quincena)"

    if salario_mensual is None:
        m_men = re.search(
            r'(?:mensual(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:al mes|mensual(?:es)?|por mes))',
            texto_low
        )
        if m_men:
            val = float(m_men.group(1) or m_men.group(2))
            sueldo_base_periodo = val
            salario_mensual = round(val, 2)
            periodicidad = f"Mensual (${val:,.2f} al mes)"

    if salario_mensual is None:
        m_gen = re.search(r'(?:gano|ganaba|sueldo|pago|pagan)\s*(?:es\s*de)?\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
        if m_gen:
            val = float(m_gen.group(1))
            sueldo_base_periodo = val
            if val < 5000:
                salario_mensual = round((val / 7.0) * 30.0, 2)
                periodicidad = f"Semanal (${val:,.2f} a la semana)"
            else:
                salario_mensual = round(val, 2)
                periodicidad = f"Mensual (${val:,.2f} al mes)"

    oferta_patronal = 0.0
    m_oferta = re.search(r'(?:quieren dar|ofrecen|daban|dan|ofreciendo|soltar)\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
    if m_oferta:
        oferta_patronal = float(m_oferta.group(1))

    sin_vacaciones = any(k in texto_low for k in ["no me daban vacaciones", "sin vacaciones", "nunca tuve vacaciones"])
    sin_dias_libres = any(k in texto_low for k in ["días libres", "dias libres", "sin descanso", "no descansaba", "sin dia de descanso"])
    sin_bonos = any(k in texto_low for k in ["bonos", "comisiones", "horas extras"])

    return {
        "salario_mensual": salario_mensual if salario_mensual else 9857.14,
        "sueldo_periodo": sueldo_base_periodo,
        "periodicidad": periodicidad,
        "oferta_patronal": oferta_patronal,
        "sin_vacaciones": sin_vacaciones,
        "sin_dias_libres": sin_dias_libres,
        "sin_bonos": sin_bonos
    }

def obtener_dias_vacaciones_lft(anios_cumplidos: int) -> int:
    if anios_cumplidos <= 1: return 12
    elif anios_cumplidos == 2: return 14
    elif anios_cumplidos == 3: return 16
    elif anios_cumplidos == 4: return 18
    elif anios_cumplidos == 5: return 20
    elif 6 <= anios_cumplidos <= 10: return 22
    elif 11 <= anios_cumplidos <= 15: return 24
    else: return 30

def calcular_liquidacion_y_derechos_lft(
    salario_mensual: float,
    anios_antiguedad: int,
    meses_adicionales: int,
    motivo_separacion: str,
    dias_aguinaldo_anual: int = 15,
    prima_vacacional_pct: float = 25.0,
    dias_sueldo_pendientes: int = 0,
    dias_vacaciones_no_gozadas: int = 0,
    dias_descanso_trabajados: int = 0,
    salario_minimo_vigente: float = 278.80
) -> dict:
    sd = round(salario_mensual / 30.0, 2)
    antiguedad_total_anios = round(anios_antiguedad + (meses_adicionales / 12.0), 4)
    if antiguedad_total_anios <= 0:
        antiguedad_total_anios = 1.0
    dias_trabajados_ultimo_anio = round((meses_adicionales / 12.0) * 365.0, 1)
    if dias_trabajados_ultimo_anio == 0:
        dias_trabajados_ultimo_anio = 365.0

    dias_vac_correspondientes = obtener_dias_vacaciones_lft(max(1, anios_antiguedad))
    prop_diaria_aguinaldo = dias_aguinaldo_anual / 365.0
    prop_diaria_prima_vac = (dias_vac_correspondientes * (prima_vacacional_pct / 100.0)) / 365.0
    factor_integracion = 1.0 + prop_diaria_aguinaldo + prop_diaria_prima_vac
    sdi = round(sd * factor_integracion, 2)

    monto_sueldo_pendiente = round(dias_sueldo_pendientes * sd, 2)
    monto_aguinaldo_prop = round((dias_aguinaldo_anual / 365.0) * dias_trabajados_ultimo_anio * sd, 2)
    monto_vacaciones_prop = round((dias_vac_correspondientes / 365.0) * dias_trabajados_ultimo_anio * sd, 2)
    monto_vacaciones_atrasadas = round(dias_vacaciones_no_gozadas * sd, 2)
    monto_prima_vac_prop = round((monto_vacaciones_prop + monto_vacaciones_atrasadas) * (prima_vacacional_pct / 100.0), 2)
    # Art. 73 LFT: El día de descanso trabajado se paga con un salario doble adicional al salario normal
    monto_descansos_trabajados = round(dias_descanso_trabajados * (sd * 2.0), 2)

    salario_base_prima_ant = min(sd, salario_minimo_vigente * 2.0)
    es_despido = ("Despido" in motivo_separacion or "Rescisión" in motivo_separacion)
    monto_prima_antiguedad = round(12.0 * antiguedad_total_anios * salario_base_prima_ant, 2) if (es_despido or anios_antiguedad >= 15) else 0.0
    subtotal_finiquito = round(
        monto_sueldo_pendiente + monto_aguinaldo_prop + monto_vacaciones_prop +
        monto_vacaciones_atrasadas + monto_prima_vac_prop + monto_descansos_trabajados, 2
    )

    monto_indem_90_dias = round(90.0 * sdi, 2) if es_despido else 0.0
    subtotal_indemnizacion = round(monto_prima_antiguedad + monto_indem_90_dias, 2)
    gran_total_bruto = round(subtotal_finiquito + subtotal_indemnizacion, 2)

    conceptos_tabla = [
        {"Qué te deben pagar": "1. Días trabajados que aún no te pagan", "Explicación sencilla": "Los días de esta semana o quincena que ya trabajaste", "Monto (MXN)": monto_sueldo_pendiente},
        {"Qué te deben pagar": "2. Aguinaldo proporcional", "Explicación sencilla": "La parte de tu aguinaldo acumulada en el año (mínimo 15 días por año)", "Monto (MXN)": monto_aguinaldo_prop},
        {"Qué te deben pagar": "3. Vacaciones acumuladas y atrasadas", "Explicación sencilla": "Los días de vacaciones que la empresa no te dio pagados en dinero", "Monto (MXN)": round(monto_vacaciones_prop + monto_vacaciones_atrasadas, 2)},
        {"Qué te deben pagar": "4. Prima vacacional (25% extra)", "Explicación sencilla": "Un 25% adicional sobre el valor de tus vacaciones por ley", "Monto (MXN)": monto_prima_vac_prop},
        {"Qué te deben pagar": "5. Días libres / descansos trabajados", "Explicación sencilla": "Si trabajaste en tu día de descanso semanal, la ley obliga a pagarlo al doble extra", "Monto (MXN)": monto_descansos_trabajados},
        {"Qué te deben pagar": "6. Prima de antigüedad (12 días por año)", "Explicación sencilla": "Recompensa obligatoria de 12 días de sueldo por cada año trabajado", "Monto (MXN)": monto_prima_antiguedad},
        {"Qué te deben pagar": "7. Indemnización de 3 meses (90 días)", "Explicación sencilla": "El castigo principal a la empresa por correrte sin causa justificada", "Monto (MXN)": monto_indem_90_dias}
    ]

    return {
        "sd": sd,
        "sdi": sdi,
        "subtotal_finiquito": subtotal_finiquito,
        "subtotal_indemnizacion": subtotal_indemnizacion,
        "monto_descansos_trabajados": monto_descansos_trabajados,
        "gran_total_bruto": gran_total_bruto,
        "tabla_conceptos": pd.DataFrame(conceptos_tabla)
    }

def calcular_cotizacion_honorarios_dual(
    monto_en_disputa: float,
    costo_asesoria: float = 0.0,
    anticipo_fijo: float = 0.0,
    pct_litis: float = 25.0,
    gastos_periciales: float = 500.0,
    horas_invertidas: float = 35.0,
    costo_hora_despacho: float = 350.0
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
# 6. GENERADOR DE ASESORÍA EXHAUSTIVA PASO A PASO (LENGUAJE HUMANO Y CLARO)
# ==============================================================================
def construir_asesoria_exhaustiva_ciudadana(
    categoria: str,
    tipo: str,
    relato: str,
    datos_sueldo: dict,
    res_liq: dict,
    res_hon: dict
) -> dict:
    if categoria == "Casos Laborales":
        oferta = datos_sueldo["oferta_patronal"]
        total_ley = res_liq["gran_total_bruto"]
        faltante = max(0.0, round(total_ley - oferta, 2))
        detalles_detectados = [
            f"Te pagaban un sueldo **{datos_sueldo['periodicidad']}** (lo que equivale a **${datos_sueldo['salario_mensual']:,.2f} pesos al mes** o **${res_liq['sd']:,.2f} pesos por día**)."
        ]
        if oferta > 0:
            detalles_detectados.append(
                f"La empresa te quiere dar únicamente **${oferta:,.2f} pesos** para deshacerte de ti, cuando por ley te corresponden aproximadamente **${total_ley:,.2f} pesos** (te están queriendo quitar **${faltante:,.2f} pesos** de tu trabajo)."
            )
        if datos_sueldo["sin_vacaciones"]:
            detalles_detectados.append(
                "Mencionaste que **no te daban vacaciones**: la ley prohíbe que trabajes sin vacaciones, por lo tanto la empresa está obligada a pagarte todos esos días en efectivo más un 25% extra."
            )
        if datos_sueldo["sin_dias_libres"]:
            detalles_detectados.append(
                "Mencionaste que **no te daban días libres de descanso**: por ley, por cada 6 días de trabajo debes descansar 1 día pagado. Si te hicieron trabajar en tus días de descanso, ese día se tiene que pagar **al doble adicional**."
            )

        return {
            "titulo_guia": "Guía Completa Paso a Paso para Defender tu Trabajo y tu Liquidación",
            "radiografia_caso": detalles_detectados,
            "explicacion_sencilla": (
                "Cuando te corren del trabajo sin que hayas cometido una falta grave comprobada, la ley mexicana dice que es un **Despido Injustificado**. "
                "Muchos patrones usan la maña de ofrecerte poquito dinero en efectivo (como $5,000 pesos) pidiéndote que a cambio firmes una hoja que dice 'Renuncia Voluntaria'. "
                "¡Esa es una trampa! Si tú firmas que renunciaste, legalmente estás diciendo: 'Yo me quise ir solito y la empresa no me debe nada'. "
                "En cambio, si NO firmas nada, la empresa está obligada a pagarte dos bolsas de dinero: **1) Tu Finiquito** (aguinaldo, vacaciones y días trabajados) y **2) Tu Liquidación de 3 meses de sueldo completo** por haberte dejado sin empleo."
            ),
            "fases_paso_a_paso": [
                {
                    "fase": "FASE 1: ¿Qué hacer HOY MISMO (Primeras 24 horas)?",
                    "pasos": [
                        "No firmes absolutamente ningún papel que diga 'Renuncia Voluntaria', 'Finiquito total' ni mucho menos una hoja en blanco. Nadie te puede obligar ni encerrar en la oficina.",
                        "Si te ofrecen los $5,000 pesos a cambio de tu firma, diles con calma que primero vas a revisar tu cuenta en el Centro de Conciliación y retírate tranquilo.",
                        "Haz respaldo hoy mismo en tu celular de todas las pruebas de que trabajabas ahí: toma capturas de pantalla de los grupos de WhatsApp del trabajo, mensajes donde tu jefe te daba órdenes o te ponía horarios, fotos de tu uniforme, credencial o transferencias de pago."
                    ]
                },
                {
                    "fase": "FASE 2: ¿Qué hacer ESTA MISMA SEMANA (Días 2 al 5)?",
                    "pasos": [
                        "Acude personalmente al **Centro de Conciliación Laboral** de tu ciudad o a la **PROFEDET** (Procuraduría de la Defensa del Trabajo). El trámite es 100% gratuito y no necesitas llevar abogado pagado.",
                        "Lleva en un fólder: tu INE original y copia, el nombre de la empresa o del dueño/jefe, y la dirección aproximada del lugar donde trabajabas (si tienes fotos de la fachada en Google Maps, mejor).",
                        "En la ventanilla di: 'Vengo a levantar una solicitud de conciliación porque me despidieron y me quieren dar menos de mi liquidación de ley'. Ahí te darán un citatorio oficial para obligar al patrón a presentarse."
                    ]
                },
                {
                    "fase": "FASE 3: ¿Qué hacer el DÍA DE LA CITA frente al patrón?",
                    "pasos": [
                        "En la sala de conciliación habrá un funcionario público neutral (el Conciliador). El abogado de la empresa intentará asustarte diciendo que el juicio dura años para que aceptes poquito dinero.",
                        "Mantente firme: en conciliación es común negociar un pago inmediato en efectivo o transferencia (por ejemplo, entre el 75% y el 100% de tu liquidación total), pero jamás aceptes migajas como $5,000 pesos.",
                        "Si el patrón no se presenta a la cita, le ponen una multa y a ti te entregan tu constancia para que un abogado público gratuito o privado le embargue bienes o cuentas a la empresa."
                    ]
                }
            ],
            "guiones_palabra_por_palabra": [
                "🗣️ **Qué decirle a tu jefe o a Recursos Humanos si te presionan para firmar:**\n\"Le agradezco, pero no voy a firmar ninguna hoja de renuncia porque ustedes me están despidiendo. Voy a acudir al Centro de Conciliación para que ahí hagamos la cuenta justa conforme a la ley y allá les firmo cuando esté mi pago completo.\"",
                "🗣️ **Qué decir al llegar a la ventanilla del Centro de Conciliación o PROFEDET:**\n\"Buenos días, me acaban de despedir de mi trabajo, ganaba por semana, no me daban vacaciones ni días libres y solo me quieren dar $5,000 pesos si firmo renuncia. Quiero citar al patrón para reclamar mi liquidación completa.\""
            ],
            "errores_fatales": [
                "🚫 **ERROR 1 — Creer la mentira de 'Firma hoy para darte los $5,000 y la otra semana te damos lo demás':** En el segundo en que pones tu firma en una hoja de renuncia, pierdes legalmente el resto de tu dinero.",
                "🚫 **ERROR 2 — Dejar pasar más de 60 días (2 meses):** La ley te da exactamente 60 días en el calendario desde que te corrieron para ir a Conciliación. Si vas en el día 61, tu derecho caduca y el patrón ya no te debe nada.",
                "🚫 **ERROR 3 — Pelear, gritar o llevarte cosas de la empresa para 'cobrarte a lo chino':** No tomes mercancía ni herramientas porque el patrón lo usará para voltearte las cosas y acusarte de robo."
            ],
            "oficina_ayuda": "Centro de Conciliación Laboral de tu Estado / PROFEDET (Tel. gratuito nacional: 800 911 7877)"
        }

    elif categoria == "Casos de Tránsito y Policía":
        return {
            "titulo_guia": "Guía Ciudadana Paso a Paso contra Abusos de Tránsito, Retenes y Patrullas",
            "radiografia_caso": [
                "Reportaste una situación con policías o agentes de tránsito en la calle (parada sin motivo claro, intento de mordida, amenaza de grúa/corralón o revisión indebida).",
                "En México, ninguna autoridad puede inventar infracciones ni cobrarte dinero en efectivo en la banqueta."
            ],
            "explicacion_sencilla": (
                "Los malos elementos de tránsito o policía suelen usar el miedo para sacarte dinero ('mordida'). Su amenaza favorita es decirte: "
                "*'Nos vamos a llevar tu carro o tu moto al corralón con la grúa y te va a salir en $5,000 pesos sacarlo, mejor cómo nos arreglamos'*. "
                "Debes saber la regla de oro: **El corralón NO aplica por cualquier falta menor**. Solo se pueden llevar tu vehículo al corralón en casos graves muy específicos: "
                "1) Si vienes manejando en estado de ebriedad, 2) Si tu vehículo no trae placas o el permiso está vencido y alterado, 3) Si chocaste y hay heridos o daños a la vía pública, o 4) Si el vehículo tiene reporte de robo. "
                "Por pasarte un alto, dar vuelta prohibida o una revisión común, **solo procede levantar la boleta de infracción, nunca quitarte tu vehículo con grúa para extorsionarte**."
            ),
            "fases_paso_a_paso": [
                {
                    "fase": "FASE 1: En el momento exacto en que te detiene la patrulla",
                    "pasos": [
                        "Oríllate en un lugar seguro e iluminado, apaga el motor, baja tu ventanilla solo a la mitad, enciende la luz interior si es de noche y pon tus manos visibles sobre el volante o manubrio.",
                        "Saca tu celular y empieza a grabar video o audio. **En México es 100% legal grabar a cualquier policía en la vía pública** porque es un servidor público en funciones, siempre y cuando no lo empujes ni obstruyas físicamente.",
                        "No entregues tu licencia ni tarjeta de circulación en su mano hasta que el oficial se identifique con nombre completo, te diga el motivo exacto de la detención y te confirme que es agente de Tránsito facultado para infraccionar (una patrulla municipal preventiva normal no suele tener facultad de levantar multas de tránsito)."
                    ]
                },
                {
                    "fase": "FASE 2: Si te piden 'mordida' o te amenazan con el corralón",
                    "pasos": [
                        "Anota o graba el **número económico de la patrulla** (viene pintado en las puertas o salpicaderas) y la hora exacta.",
                        "Si te amenazan con llamar a la grúa por una falta menor, diles con voz tranquila que estás grabando y que conoces el Reglamento de Tránsito: pide que te levanten la boleta oficial para pagarla en la Tesorería.",
                        "Si quieren revisar tu mochila, cajuela o desbloquear tu celular: recuerda que **ningún policía puede revisar tus pertenencias privadas ni tu teléfono sin una orden de un Juez**, salvo que te hayan sorprendido cometiendo un delito en ese instante."
                    ]
                },
                {
                    "fase": "FASE 3: Después del incidente (Cómo anular la multa o denunciar al policía)",
                    "pasos": [
                        "Si el policía actuó con abuso o te pidió dinero, llama inmediatamente a **Asuntos Internos / Contraloría de Seguridad Pública** o al **911 / 089** dando el número de patrulla y la calle exacta.",
                        "Si te levantaron una multa injusta, no tienes que pagarla a ciegas: tienes 15 días hábiles para acudir al **Tribunal de Justicia Administrativa** de tu estado, donde un defensor público gratuito impugna la multa y en la mayoría de los casos la anula al 100%."
                    ]
                }
            ],
            "guiones_palabra_por_palabra": [
                "🗣️ **Qué decir cuando el policía se acerca a tu ventanilla:**\n\"Buenas tardes oficial. Estoy grabando por seguridad de ambos. ¿Me puede indicar su nombre completo, su número de patrulla y qué artículo exacto del Reglamento de Tránsito infringí para que me detuviera?\"",
                "🗣️ **Qué decir si te amenaza con llevarse tu carro/moto al corralón para pedirte mordida:**\n\"Oficial, usted y yo sabemos que el Reglamento de Tránsito no marca remisión al corralón por este motivo, ya que traigo mis placas y documentos en regla. No le voy a dar dinero en efectivo; si cometí una infracción, elabóreme mi boleta oficial con su terminal para pagarla en Tesorería.\"",
                "🗣️ **Qué decir si quieren revisar tu celular o tu mochila sin motivo:**\n\"Oficial, con todo respeto no autorizo ninguna revisión a mi teléfono ni a mis pertenencias personales porque el Artículo 16 de la Constitución exige orden judicial.\""
            ],
            "errores_fatales": [
                "🚫 **ERROR 1 — Insultar, gritar o empujar al policía:** Aunque tú tengas toda la razón, si le gritas groserías o le manoteas, les das el pretexto perfecto para arrestarte por 'faltas a la autoridad' y ahí sí se llevan tu vehículo.",
                "🚫 **ERROR 2 — Darles dinero ('para el refresco'):** Además de fomentar que te vuelvan a parar, algunos malos elementos te graban dándoles billetes para luego extorsionarte más caro acusándote de cohecho.",
                "🚫 **ERROR 3 — Entregar tus llaves del carro o moto:** Jamás entregues las llaves de tu vehículo en la mano de un oficial."
            ],
            "oficina_ayuda": "Unidad de Asuntos Internos de la Policía / Defensoría del Tribunal de Justicia Administrativa (100% Gratis)"
        }

    elif categoria == "Casos Familiares":
        return {
            "titulo_guia": "Guía Paso a Paso para Exigir Pensión Alimenticia y Proteger a tus Hijos",
            "radiografia_caso": [
                "Detectamos un problema de falta de pago de pensión alimenticia (gasto de los hijos), custodia o separación familiar.",
                "La alimentación, escuela, ropa y salud de los niños es prioridad absoluta para cualquier Juez en México."
            ],
            "explicacion_sencilla": (
                "Muchos deudores creen que saliéndose de trabajar o cobrando en efectivo por fuera ya se libraron de dar gasto para sus hijos. "
                "¡Eso es falso! El Juez Familiar tiene poder para fijar una **Pensión Alimenticia Provisional desde la primera semana** y pedirle al SAT y a los bancos todos los movimientos de dinero del papá o mamá que no quiere pagar."
            ),
            "fases_paso_a_paso": [
                {
                    "fase": "FASE 1: ¿Qué reunir HOY MISMO en tu casa?",
                    "pasos": [
                        "Busca las actas de nacimiento originales de tus hijos y, si estuvieron casados, el acta de matrimonio.",
                        "Guarda todos los tickets y notas de lo que gastas en los niños: supermercado, colegiaturas, útiles, medicinas, ropa, renta y luz.",
                        "Anota el nombre y dirección del trabajo del papá/mamá de tus hijos, o si tiene negocio propio, fotos del negocio, placas de su auto o capturas de sus redes sociales donde presume gastos."
                    ]
                },
                {
                    "fase": "FASE 2: ¿A dónde acudir ESTA SEMANA sin gastar dinero?",
                    "pasos": [
                        "Acude a la **Procuraduría del DIF** de tu municipio o a la **Defensoría Pública Familiar** en los Juzgados Familiares. Ahí te asignan un abogado familiar totalmente gratis.",
                        "Pide que ingresen la demanda de pensión alimenticia solicitando **Pensión Provisional Urgente** para que el Juez ordene el descuento inmediato de su nómina o fije una cantidad mensual obligatoria."
                    ]
                }
            ],
            "guiones_palabra_por_palabra": [
                "🗣️ **Qué decir en la Defensoría Familiar o el DIF:**\n\"Vengo a solicitar un abogado gratuito para tramitar la pensión alimenticia provisional y guarda y custodia de mis hijos, ya que su progenitor dejó de aportar para sus gastos básicos.\""
            ],
            "errores_fatales": [
                "🚫 **ERROR 1 — Confiar en acuerdos de palabra:** Si no está firmado ante un Juez Familiar o Mediador oficial, el día de mañana vuelve a dejar de pagar sin consecuencias.",
                "🚫 **ERROR 2 — Prohibirle ver a los niños como venganza sin avisar al Juez:** Todo debe hacerse mediante el Juez para que la otra parte no se haga la víctima en el juzgado."
            ],
            "oficina_ayuda": "Procuraduría de Protección de Niñas, Niños y Adolescentes (DIF) / Juzgados de lo Familiar"
        }

    else:
        return {
            "titulo_guia": f"Guía Ciudadana Paso a Paso para Resolver tu Caso ({categoria})",
            "radiografia_caso": [
                f"Analizamos tu problema clasificado dentro de **{categoria} ({tipo})**.",
                "Tu caso requiere proteger tus pruebas documentales y acudir ante la instancia correcta sin cometer actos por cuenta propia."
            ],
            "explicacion_sencilla": (
                "En problemas de fraudes bancarios, rentas o deudas de dinero (pagarés), gana quien conserva intactos sus documentos o evidencias digitales y actúa primero ante la autoridad correspondiente."
            ),
            "fases_paso_a_paso": [
                {
                    "fase": "FASE 1: Primeras 24 horas (Protección de tus pruebas)",
                    "pasos": [
                        "No borres conversaciones de WhatsApp, correos ni estados de cuenta; guárdalos íntegros sin recortar las capturas.",
                        "Si tienes un contrato de renta o un pagaré firmado, guárdalo en una mica protectora sin rayarlo ni remarcarlo con otra pluma."
                    ]
                },
                {
                    "fase": "FASE 2: Esta semana (Acción oficial)",
                    "pasos": [
                        "Si fue un cargo o transferencia bancaria que no reconoces: llama hoy a tu banco para pedir el folio de aclaración y levanta tu queja gratuita en la **CONDUSEF**.",
                        "Si es un inquilino que no paga o un deudor de pagaré: acude con un abogado civil/mercantil o a la Defensoría Pública para iniciar el juicio de embargo o desocupación legal."
                    ]
                }
            ],
            "guiones_palabra_por_palabra": [
                "🗣️ **Qué decir al presentar tu reclamación:**\n\"Solicito que se registre formalmente mi queja con número de folio y se conserven íntegros los registros electrónicos y documentales de mi caso.\""
            ],
            "errores_fatales": [
                "🚫 **ERROR 1 — Hacer justicia por tu propia mano:** Si eres dueño de una casa rentada, jamás cambies la chapa ni saques las cosas del inquilino a la banqueta sin orden del Juez, porque te pueden denunciar por despojo.",
                "🚫 **ERROR 2 — Entregar documentos originales sin recibir tu pago:** Nunca entregues el pagaré original hasta que el dinero esté firme en tu cuenta."
            ],
            "oficina_ayuda": "CONDUSEF (800 999 8080) / Fiscalía / Defensoría Pública Civil y Mercantil"
        }

# ==============================================================================
# 7. AGENTE DE BÚSQUEDA EN VIVO EN INTERNET Y RED NEURONAL AUTO-EVOLUTIVA
# ==============================================================================
def buscar_informacion_juridica_en_internet(categoria_caso: str, tipo_caso: str) -> dict:
    resultados_web = []
    textos_para_entrenar = []

    termino_wiki = f"{tipo_caso} Mexico"
    if categoria_caso == "Casos de Tránsito y Policía":
        termino_wiki = "Reglamento de transito infraccion Mexico"
    elif categoria_caso == "Casos Laborales":
        termino_wiki = "Despido laboral Ley Federal del Trabajo Mexico"

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

    palabras_clave_busqueda = f"{tipo_caso} derechos Mexico"
    if categoria_caso == "Casos Laborales":
        palabras_clave_busqueda = "despido injustificado liquidacion PROFEDET Ley Federal del Trabajo Mexico"
    elif categoria_caso == "Casos de Tránsito y Policía":
        palabras_clave_busqueda = "multas transito corralon policia derechos conductor Mexico"

    try:
        url_gnews = (
            "https://news.google.com/rss/search?"
            f"q={urllib.parse.quote(palabras_clave_busqueda)}&hl=es-419&gl=MX&ceid=MX:es-419"
        )
        req_g = urllib.request.Request(url_gnews, headers={"User-Agent": "ForensicMindLegalBot/8.0"})
        with urllib.request.urlopen(req_g, timeout=4.5) as resp_g:
            root = ET.fromstring(resp_g.read())
            for it in root.findall(".//item")[:3]:
                tit = it.find("title").text if it.find("title") is not None else "Noticia Jurídica"
                lnk = it.find("link").text if it.find("link") is not None else "https://www.scjn.gob.mx"
                pub = it.find("pubDate").text[:16] if it.find("pubDate") is not None else "Reciente"
                resultados_web.append({
                    "fuente": f"🌐 Google Noticias México ({pub})",
                    "titulo": tit,
                    "resumen": f"Información reciente localizada en internet sobre {categoria_caso}.",
                    "url": lnk
                })
                textos_para_entrenar.append(tit)
    except Exception:
        pass

    return {
        "resultados": resultados_web,
        "corpus_web_extraido": " ".join(textos_para_entrenar)
    }

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
    try:
        c.execute("""
            INSERT OR IGNORE INTO memoria_neuronal_autonoma (
                relato_original, relato_expandido, macro_rama, rama_derecho,
                categoria_caso, tipo_caso, fuente_aprendizaje, confianza,
                hash_consulta, fecha_aprendizaje
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
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
        return None, None, {"total_muestras": len(df_base), "experiencias_aprendidas": len(df_mem), "vocabulario_ngramas": 0}

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

    mlp = MLPClassifier(hidden_layer_sizes=(96, 48), activation='relu', max_iter=500, random_state=42)
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
        "Casos de Tránsito y Policía": 0,
        "Casos Familiares": 0,
        "Casos Penales y Fraudes": 0,
        "Casos Civiles": 0,
        "Casos Mercantiles": 0
    }

    reglas = {
        "Casos Laborales": [
            "despid", "corrieron", "echaron", "chamba", "trabajo", "liquidaci", "finiquito",
            "sueldo", "salario", "semanal", "quincenal", "vacaciones", "aguinaldo", "patron",
            "jefe", "renuncia", "hoja en blanco", "dias libres", "bonos", "nomina"
        ],
        "Casos de Tránsito y Policía": [
            "transito", "policia", "patrulla", "mordida", "corralon", "grua", "infraccion",
            "multa", "placas", "licencia", "tarjeta de circulacion", "reten", "rutina", "moto", "oficial"
        ],
        "Casos Familiares": [
            "pension", "alimentos", "alimenticia", "hijos", "custodia", "divorcio", "gasto de los niños", "manutencion"
        ],
        "Casos Penales y Fraudes": [
            "fraude", "estafa", "phishing", "spei", "vaciaron", "robaron", "cobranza", "prestamo", "amenaza"
        ],
        "Casos Civiles": [
            "inquilino", "renta", "arrendamiento", "departamento", "desalojar", "chapa", "casero"
        ],
        "Casos Mercantiles": [
            "pagare", "cheque", "mercancia", "deudor comercial"
        ]
    }

    for cat_k, kws in reglas.items():
        for kw in kws:
            if kw in texto_low:
                scores[cat_k] += 20

    cat_ganadora = max(scores, key=scores.get)

    mapa_defaults = {
        "Casos Laborales": ("Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado"),
        "Casos de Tránsito y Policía": ("Derecho Público", "Derecho Administrativo y Vial", "Casos de Tránsito y Policía", "Intento de mordida o amenaza de llevar al corralón"),
        "Casos Familiares": ("Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia (Papá o mamá que no da gasto)"),
        "Casos Penales y Fraudes": ("Derecho Público", "Derecho Penal", "Casos Penales y Fraudes", "Fraude bancario, vaciado de cuenta o transferencia SPEI"),
        "Casos Civiles": ("Derecho Privado", "Derecho Civil", "Casos Civiles", "Inquilino que no paga la renta ni se quiere salir"),
        "Casos Mercantiles": ("Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Cobro de pagaré firmado o dinero prestado")
    }
    macro, rama, cat, tipo = mapa_defaults[cat_ganadora]

    confianza = 94.5
    if modelo_mlp is not None and vectorizer_mlp is not None and scores[cat_ganadora] == 0:
        try:
            X_t = vectorizer_mlp.transform([relato_expandido])
            pred = modelo_mlp.predict(X_t)[0].split("|")
            if len(pred) == 4:
                cat, rama, tipo, macro = pred[0], pred[1], pred[2], pred[3]
        except Exception:
            pass

    return {
        "macro_rama": macro,
        "rama": rama,
        "categoria": cat,
        "tipo": tipo,
        "confianza": confianza,
        "hash_evidencia": hashlib.sha256(relato.encode("utf-8")).hexdigest()
    }

def tokenizar(texto: str) -> Counter:
    palabras = re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ0-9_./-]+', texto.lower())
    stopwords = {'de', 'la', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como', 'que', 'es', 'sin'}
    return Counter(w for w in palabras if w not in stopwords and len(w) > 2)

def calcular_similitud_coseno(texto1: str, texto2: str) -> float:
    vec1 = tokenizar(texto1)
    vec2 = tokenizar(texto2)
    inter = set(vec1.keys()) & set(vec2.keys())
    num = sum([vec1[x] * vec2[x] for x in inter])
    den = math.sqrt(sum([v ** 2 for v in vec1.values()])) * math.sqrt(sum([v ** 2 for v in vec2.values()]))
    if not den:
        return 0.0
    return round((float(num) / den) * 100, 1)

# ==============================================================================
# 8. VOZ, WORD (.DOCX) EXHAUSTIVO Y FICHA 9:16 CON AUTO-AJUSTE SIN CORTAR PALABRAS
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
        return "⚠️ No se pudo transcribir el audio automáticamente. Escribe tu caso en el cuadro de texto."

def generar_dictamen_word_docx(codigo: str, relato: str, clasificacion: dict, asesoria: dict, res_liq: dict, res_hon: dict) -> bytes:
    if Document is None:
        return b""
    doc = Document()
    doc.add_heading("GUÍA PERSONALIZADA DE DEFENSA CIUDADANA — FORENSICMIND v8.0", 0)
    doc.add_paragraph(f"Autor del Sistema: {AUTOR_SISTEMA}")
    doc.add_paragraph(f"Expediente: {codigo} | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    doc.add_paragraph(f"Sello SHA-256: {clasificacion['hash_evidencia']}")

    doc.add_heading("1. Tu Caso Explicado de Forma Sencilla", level=1)
    doc.add_paragraph(relato)
    for item_r in asesoria["radiografia_caso"]:
        doc.add_paragraph(re.sub(r"\*", "", item_r), style="List Bullet")
    doc.add_paragraph(re.sub(r"\*", "", asesoria["explicacion_sencilla"]))

    if clasificacion["categoria"] == "Casos Laborales":
        doc.add_heading("2. Resumen de tu Dinero por Ley (LFT)", level=1)
        doc.add_paragraph(f"• Liquidación Total por Ley: ${res_liq['gran_total_bruto']:,.2f} MXN")
        doc.add_paragraph(f"• Dinero Libre para Ti (descontando abogado): ${res_hon['monto_neto_libre_ciudadano']:,.2f} MXN")

    doc.add_heading("3. Plan de Acción Paso a Paso", level=1)
    for bloque_f in asesoria["fases_paso_a_paso"]:
        doc.add_heading(bloque_f["fase"], level=2)
        for p_f in bloque_f["pasos"]:
            doc.add_paragraph(re.sub(r"\*", "", p_f), style="List Bullet")

    doc.add_heading("4. Qué Decir Exactamente (Guiones Palabra por Palabra)", level=1)
    for g_txt in asesoria["guiones_palabra_por_palabra"]:
        doc.add_paragraph(re.sub(r"\*", "", g_txt))

    doc.add_heading("5. Errores Fatales que NUNCA Debes Cometer", level=1)
    for err_txt in asesoria["errores_fatales"]:
        doc.add_paragraph(re.sub(r"\*", "", err_txt), style="List Bullet")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def limpiar_ascii(texto: str) -> str:
    limpio = re.sub(r"\*", "", str(texto))
    reemplazos = str.maketrans("áéíóúñÁÉÍÓÚÑüÜ", "aeiounAEIOUNuU")
    limpio = limpio.translate(reemplazos)
    return limpio.encode("ascii", "ignore").decode("ascii")

def generar_ficha_vertical_9_16(codigo: str, clasificacion: dict, asesoria: dict, monto_bruto: float, monto_neto: float) -> np.ndarray:
    """Genera una imagen vertical 1080x1920 usando textwrap.wrap para JAMÁS cortar palabras a la mitad."""
    alto, ancho = 1920, 1080
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[:] = (24, 15, 10)

    cv2.rectangle(img, (25, 25), (1055, 1895), (240, 175, 50), 4)
    cv2.rectangle(img, (40, 40), (1040, 225), (45, 28, 16), -1)
    cv2.putText(img, "FORENSICMIND & LEXGUIA v8.0", (65, 105), cv2.FONT_HERSHEY_DUPLEX, 1.55, (100, 220, 255), 3)
    cv2.putText(img, limpiar_ascii(f"AUTOR: {AUTOR_SISTEMA.upper()}"), (65, 165), cv2.FONT_HERSHEY_DUPLEX, 0.75, (140, 235, 255), 2)

    cat_txt = limpiar_ascii(f"EXPEDIENTE: {codigo} | {clasificacion['categoria']}")
    cv2.putText(img, cat_txt[:54], (65, 280), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2)

    cv2.rectangle(img, (65, 315), (1015, 455), (25, 48, 38), -1)
    if clasificacion["categoria"] == "Casos Laborales":
        cv2.putText(img, limpiar_ascii(f"LIQUIDACION TOTAL POR LEY: ${monto_bruto:,.2f} MXN"), (85, 370), cv2.FONT_HERSHEY_DUPLEX, 0.82, (255, 255, 255), 2)
        cv2.putText(img, limpiar_ascii(f"DINERO LIBRE PARA TI: ${monto_neto:,.2f} MXN"), (85, 425), cv2.FONT_HERSHEY_DUPLEX, 0.85, (120, 255, 180), 2)
    else:
        cv2.putText(img, limpiar_ascii(f"MODULO: {clasificacion['tipo'][:44]}"), (85, 370), cv2.FONT_HERSHEY_DUPLEX, 0.80, (255, 255, 255), 2)
        cv2.putText(img, "ASESORIA CIUDADANA PASO A PASO (VIA GRATUITA DISPONIBLE)", (85, 425), cv2.FONT_HERSHEY_DUPLEX, 0.68, (120, 255, 180), 2)

    cv2.putText(img, "GUIA PASO A PASO (SIN PALABRAS CORTADAS):", (65, 520), cv2.FONT_HERSHEY_DUPLEX, 0.90, (100, 220, 255), 2)

    y_cursor = 575
    contador_paso = 1
    for fase_obj in asesoria["fases_paso_a_paso"][:2]:
        for paso_str in fase_obj["pasos"][:2]:
            texto_paso = limpiar_ascii(f"{contador_paso}. {paso_str}")
            lineas_envueltas = textwrap.wrap(texto_paso, width=54)
            for lin in lineas_envueltas[:3]:
                cv2.putText(img, lin, (65, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (235, 235, 235), 2)
                y_cursor += 38
            y_cursor += 18
            contador_paso += 1

    cv2.putText(img, "QUE NO DEBES HACER JAMAS:", (65, y_cursor + 20), cv2.FONT_HERSHEY_DUPLEX, 0.88, (120, 140, 255), 2)
    y_cursor += 65
    for err_str in asesoria["errores_fatales"][:2]:
        lineas_err = textwrap.wrap(limpiar_ascii(err_str), width=54)
        for lin_e in lineas_err[:3]:
            cv2.putText(img, lin_e, (65, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (210, 210, 255), 2)
            y_cursor += 36
        y_cursor += 16

    cv2.putText(img, "DONDE ACUDIR GRATIS:", (65, 1520), cv2.FONT_HERSHEY_DUPLEX, 0.82, (100, 220, 255), 2)
    for lin_of in textwrap.wrap(limpiar_ascii(asesoria["oficina_ayuda"]), width=54)[:2]:
        cv2.putText(img, lin_of, (65, 1565), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (180, 255, 200), 2)

    cv2.putText(img, "SELLO CRIPTOGRAFICO SHA-256:", (65, 1660), cv2.FONT_HERSHEY_DUPLEX, 0.80, (100, 220, 255), 2)
    cv2.putText(img, clasificacion["hash_evidencia"][:38], (65, 1705), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (160, 255, 160), 2)
    cv2.putText(img, limpiar_ascii(f"ARQUITECTURA: {AUTOR_SISTEMA.upper()}"), (65, 1825), cv2.FONT_HERSHEY_DUPLEX, 0.72, (100, 255, 218), 2)

    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# ==============================================================================
# 9. ENCABEZADO Y NAVEGACIÓN (PÚBLICO VS ADMINISTRADOR)
# ==============================================================================
st.markdown(f"""
<div class="author-banner">
    <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
        <div>
            <span style="color:#fbbf24 !important; font-weight:800; font-size:13px;">🏛️ ASESORÍA CIUDADANA PASO A PASO • LABORAL, TRÁNSITO Y FAMILIAR v8.0</span><br>
            <span style="color:#ffffff !important; font-size:21px; font-weight:900;">{MARCA_SISTEMA}</span>
        </div>
        <div>
            <span class="gold-badge">⚙️ AUTOR: {AUTOR_SISTEMA}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()

if st.session_state["es_admin"]:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🧠 1. Asesoría Paso a Paso (Público)",
        "💰 2. Calculadora de Liquidación LFT",
        "🔬 3. Casos Ganados vs. Perdidos",
        "📬 4. [ADMIN] Buzón de Usuarios",
        "☁️ 5. [ADMIN] Cerebro & GitHub Sync"
    ])
else:
    tab1, tab2, tab3 = st.tabs([
        "🧠 1. Mi Asesoría Paso a Paso",
        "💰 2. Calcular mi Liquidación y Abogado",
        "🔬 3. Casos Reales (Qué Hacer y Qué No Hacer)"
    ])

# ------------------------------------------------------------------------------
# PESTAÑA 1: ASESORÍA EXHAUSTIVA PASO A PASO + TRÁNSITO + BUZÓN CIUDADANO
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### 🗣️ Cuéntame qué te pasó con tus propias palabras (Te guiaré paso a paso y sin palabras complicadas)")

    col_esc, col_voz = st.columns([1.35, 1])
    with col_esc:
        escenario_sel = st.selectbox(
            "💡 Elige una situación parecida a la tuya o escribe tu caso abajo:",
            list(ESCENARIOS_FRECUENTES.keys())
        )
    with col_voz:
        audio_input = st.audio_input("🎙️ Si prefieres, graba tu problema con tu voz:")
        texto_transcrito = ""
        if audio_input is not None:
            with st.spinner("Escuchando tu audio y preparando tu guía paso a paso..."):
                texto_transcrito = transcribir_audio_espanol(audio_input)
                if texto_transcrito and "⚠️" not in texto_transcrito:
                    st.success("✅ Audio escuchado correctamente.")
                elif texto_transcrito:
                    st.warning(texto_transcrito)

    valor_inicial_relato = ESCENARIOS_FRECUENTES[escenario_sel]
    if texto_transcrito and "⚠️" not in texto_transcrito:
        valor_inicial_relato = texto_transcrito

    relato_usuario = st.text_area(
        "📝 Describe todo lo que te sucedió (tu sueldo, cuánto te quieren dar, si no te daban vacaciones/descansos, o qué te dijo la patrulla):",
        value=valor_inicial_relato,
        height=135
    )

    btn_analizar = st.button("🧠 Generar mi Guía Completa Paso a Paso", use_container_width=True)

    clasificacion = autoclasificar_caso_con_red_neuronal(relato_usuario, VECTORIZER_VIVO, MODELO_VIVO)
    cat_activa = clasificacion["categoria"]
    tipo_activo = clasificacion["tipo"]

    info_web_vivo = {"resultados": [], "corpus_web_extraido": ""}
    if buscar_web_switch:
        info_web_vivo = buscar_informacion_juridica_en_internet(cat_activa, tipo_activo)

    if auto_entrenar_switch and (btn_analizar or audio_input is not None or len(relato_usuario) > 25):
        res_auto = registrar_experiencia_en_memoria_autonoma(
            relato_original=relato_usuario,
            clasificacion=clasificacion,
            fuente="Consulta Ciudadana v8.0",
            texto_web_extra=info_web_vivo.get("corpus_web_extraido", ""),
            repo_gh=gh_repo_input,
            token_gh=gh_token_input,
            branch_gh=gh_branch_input
        )
        if res_auto["aprendio"]:
            VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()

    datos_sueldo = normalizar_texto_coloquial(relato_usuario)
    dias_vac_auto = 12 if datos_sueldo["sin_vacaciones"] else 0
    dias_desc_auto = 24 if datos_sueldo["sin_dias_libres"] else 0

    res_liq_rapido = calcular_liquidacion_y_derechos_lft(
        salario_mensual=datos_sueldo["salario_mensual"],
        anios_antiguedad=1,
        meses_adicionales=0,
        motivo_separacion="Despido Injustificado",
        dias_vacaciones_no_gozadas=dias_vac_auto,
        dias_descanso_trabajados=dias_desc_auto
    )
    tabulador_activo = TABULADOR_HONORARIOS_RAMA.get(cat_activa, TABULADOR_HONORARIOS_RAMA["Casos Laborales"])
    res_hon_rapido = calcular_cotizacion_honorarios_dual(
        monto_en_disputa=res_liq_rapido["gran_total_bruto"],
        costo_asesoria=0.0,
        anticipo_fijo=float(tabulador_activo["anticipo_sug"]),
        pct_litis=float(tabulador_activo["pct_sugerido"]),
        gastos_periciales=float(tabulador_activo["gastos_periciales_sug"])
    )

    asesoria = construir_asesoria_exhaustiva_ciudadana(
        categoria=cat_activa,
        tipo=tipo_activo,
        relato=relato_usuario,
        datos_sueldo=datos_sueldo,
        res_liq=res_liq_rapido,
        res_hon=res_hon_rapido
    )

    # BLOQUE 1: ALERTA SI ES ENGAÑO PATRONAL O ABUSO VIAL
    if cat_activa == "Casos Laborales" and datos_sueldo["oferta_patronal"] > 0 and datos_sueldo["oferta_patronal"] < res_liq_rapido["gran_total_bruto"]:
        faltante_dinero = round(res_liq_rapido["gran_total_bruto"] - datos_sueldo["oferta_patronal"], 2)
        st.markdown(f"""
        <div class="alert-box">
            <h3 style="margin-top:0;">🚨 ¡CUIDADO! TE QUIEREN DAR MUCHO MENOS DE LO QUE TE CORRESPONDE POR LEY</h3>
            • <b>Lo que la empresa te ofrece hoy:</b> ${datos_sueldo['oferta_patronal']:,.2f} pesos.<br>
            • <b>Lo que realmente te pertenece por Ley (incluyendo tus 3 meses de liquidación, aguinaldo, vacaciones y descansos):</b> <b>${res_liq_rapido['gran_total_bruto']:,.2f} pesos</b>.<br>
            • <b>Dinero que perderías si firmas su hoja:</b> <b>${faltante_dinero:,.2f} pesos de menos</b>.<br>
            👉 <b>Regla de oro:</b> NO firmes ninguna hoja de renuncia ni aceptes esos ${datos_sueldo['oferta_patronal']:,.0f} pesos como pago final. Sigue los pasos de abajo.
        </div>
        """, unsafe_allow_html=True)

    # BLOQUE 2: RADIOGRAFÍA DE LO QUE ENTENDIÓ LA IA Y EXPLICACIÓN HUMANA
    st.markdown(f"## 📋 {asesoria['titulo_guia']}")
    lista_radiografia_html = "".join([f"<li>{item}</li>" for item in asesoria["radiografia_caso"]])
    st.markdown(f"""
    <div class="card-box">
        <h4 style="margin-top:0;">🔎 1. Lo que analicé de tu problema ({cat_activa}):</h4>
        <ul>{lista_radiografia_html}</ul>
        <h4>💡 2. Explicación en español simple (Sin palabras complicadas):</h4>
        <p style="margin-bottom:0;">{asesoria['explicacion_sencilla']}</p>
    </div>
    """, unsafe_allow_html=True)

    # BLOQUE 3: DESGLOSE DE DINERO SI ES CASO LABORAL, O SEMÁFORO DE CORRALÓN SI ES TRÁNSITO
    if cat_activa == "Casos Laborales":
        c_din1, c_din2 = st.columns(2)
        with c_din1:
            st.markdown(f"""
            <div class="money-box">
                <h4 style="margin-top:0;">💵 ¿De dónde sale el dinero que te deben?</h4>
                • <b>Tu sueldo calculado:</b> {datos_sueldo['periodicidad']} (${res_liq_rapido['sd']:,.2f} pesos al día).<br>
                • <b>Finiquito (Aguinaldo + Vacaciones + Descansos no dados):</b> ${res_liq_rapido['subtotal_finiquito']:,.2f} MXN<br>
                • <b>Indemnización por correrte (90 días + Antigüedad):</b> ${res_liq_rapido['subtotal_indemnizacion']:,.2f} MXN<br>
                • <b>TOTAL QUE MARCA LA LEY:</b> <span style="font-size:1.25rem; font-weight:900;">${res_liq_rapido['gran_total_bruto']:,.2f} MXN</span>
            </div>
            """, unsafe_allow_html=True)
        with c_din2:
            st.markdown(f"""
            <div class="lawyer-box">
                <h4 style="margin-top:0;">⚖️ ¿Cuánto te queda libre y dónde te defienden GRATIS?</h4>
                • <b>Opción 1 (100% GRATIS — $0 pesos):</b> Acude a la <b>PROFEDET o Centro de Conciliación</b>. Ahí no te cobran ni un peso y recibes tus <b>${res_liq_rapido['gran_total_bruto']:,.2f} MXN</b> íntegros.<br>
                • <b>Opción 2 (Con Abogado Particular):</b> No pagas por adelantado; el abogado cobra alrededor del 25% al ganar y a ti te quedan libres <b>${res_hon_rapido['monto_neto_libre_ciudadano']:,.2f} MXN</b> en tu bolsa.
            </div>
            """, unsafe_allow_html=True)
    elif cat_activa == "Casos de Tránsito y Policía":
        c_v1, c_v2 = st.columns(2)
        with c_v1:
            st.markdown("""
            <div class="money-box">
                <h4 style="margin-top:0;">🟢 ¿Cuándo NO se pueden llevar tu carro o moto al corralón?</h4>
                • Por una supuesta <b>"revisión de rutina"</b>.<br>
                • Por pasarte un semáforo, vuelta prohibida o exceso de velocidad (eso solo amerita boleta de multa, <b>no grúa</b>).<br>
                • Si traes tu tarjeta de circulación, licencia vigente y placas bien puestas.<br>
                • Tampoco pueden quitarte tu celular ni obligarte a desbloquearlo sin orden de un Juez.
            </div>
            """, unsafe_allow_html=True)
        with c_v2:
            st.markdown("""
            <div class="alert-box">
                <h4 style="margin-top:0;">🔴 ¿Cuándo SÍ marca el reglamento llevar al corralón?</h4>
                • Si conduces en estado de ebriedad (alcoholímetro).<br>
                • Si el vehículo circula <b>sin placas</b> ni permiso vigente.<br>
                • Si participaste en un choque con personas lesionadas.<br>
                • Si el vehículo tiene reporte de robo.
            </div>
            """, unsafe_allow_html=True)

    # BLOQUE 4: PLAN CRONOLÓGICO PASO A PASO
    st.markdown("### 🧭 3. Tu Plan de Acción Paso a Paso (Qué hacer en orden)")
    for bloque_f in asesoria["fases_paso_a_paso"]:
        pasos_html = "".join([f"<li style='margin-bottom:8px;'>{p}</li>" for p in bloque_f["pasos"]])
        st.markdown(f"""
        <div class="card-box">
            <span class="step-badge">{bloque_f['fase']}</span>
            <ul style="margin-top:12px; margin-bottom:0;">{pasos_html}</ul>
        </div>
        """, unsafe_allow_html=True)

    # BLOQUE 5: GUIONES PALABRA POR PALABRA Y ERRORES FATALES
    col_script, col_err = st.columns(2)
    with col_script:
        st.markdown("### 🗣️ 4. Qué decir exactamente (Guiones listos para leer)")
        for g_item in asesoria["guiones_palabra_por_palabra"]:
            st.markdown(f"""
            <div class="script-box">
                {g_item.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)

    with col_err:
        st.markdown("### 🚫 5. Trampas y Errores que NUNCA debes cometer")
        for err_item in asesoria["errores_fatales"]:
            st.markdown(f"""
            <div class="alert-box">
                {err_item}
            </div>
            """, unsafe_allow_html=True)

    st.info(f"🏛️ **Oficina Pública Gratuita donde debes acudir:** {asesoria['oficina_ayuda']}")

    # BLOQUE 6: NOTICIAS Y CRITERIOS EN VIVO DE INTERNET
    if buscar_web_switch and info_web_vivo["resultados"]:
        st.markdown("#### 🌐 Información Relacionada Consultada en Tiempo Real en Internet")
        for item_w in info_web_vivo["resultados"][:3]:
            st.markdown(f"""
            <div class="web-box">
                <b>{item_w['fuente']}</b> — <a href="{item_w['url']}" target="_blank" style="font-weight:bold; color:#0284c7;">{item_w['titulo']} (Ver fuente ↗)</a><br>
                <span>{item_w['resumen']}</span>
            </div>
            """, unsafe_allow_html=True)

    # BLOQUE 7: DESCARGA DE GUÍA EN WORD Y FICHA VERTICAL 9:16 CORREGIDA
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        bytes_docx = generar_dictamen_word_docx("SAOR-2026-V8", relato_usuario, clasificacion, asesoria, res_liq_rapido, res_hon_rapido)
        if bytes_docx:
            st.download_button(
                label="📄 Descargar mi Guía Completa en Word (.docx)",
                data=bytes_docx,
                file_name="Mi_Guia_Legal_Paso_a_Paso.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
    with col_dl2:
        with st.expander("📱 Ver y Descargar Ficha para Celular (Imagen 9:16 sin letras cortadas)", expanded=False):
            img_9_16 = generar_ficha_vertical_9_16(
                "SAOR-2026-V8", clasificacion, asesoria,
                res_liq_rapido["gran_total_bruto"], res_hon_rapido["monto_neto_libre_ciudadano"]
            )
            st.image(img_9_16, caption=f"Ficha 9:16 — {AUTOR_SISTEMA}", use_container_width=True)
            _, buffer_png = cv2.imencode(".png", cv2.cvtColor(img_9_16, cv2.COLOR_RGB2BGR))
            st.download_button(
                "📥 Guardar Imagen en mi Teléfono (.png)",
                buffer_png.tobytes(),
                "Guia_Celular_9_16.png",
                "image/png",
                use_container_width=True
            )

    # BLOQUE 8: BUZÓN CIUDADANO "¿NO ENCONTRASTE TU CASO?" DIRECTO AL ING. SAÚL
    st.markdown("---")
    st.markdown("### 📬 ¿Tu problema es diferente o no encontraste exactamente lo que buscabas?")
    st.write("Cuéntanos qué te pasó aquí abajo. Tu mensaje le llegará directamente al administrador (**Ing. Saúl Ángel Ortiz Rogel**) para agregar esa guía a la aplicación:")

    with st.form("form_buzon_ciudadano"):
        cb1, cb2, cb3 = st.columns(3)
        nombre_bz = cb1.text_input("Tu nombre o apodo (opcional):", placeholder="Ej. Juan Pérez")
        contacto_bz = cb2.text_input("Tu correo o WhatsApp (opcional, por si quieres respuesta):", placeholder="Ej. 55 1234 5678")
        cat_bz = cb3.selectbox("¿De qué tema es tu duda?", list(TIPOS_CASOS.keys()) + ["Otro tema diferente"])
        duda_bz = st.text_area(
            "Explica qué información te hizo falta o qué problema tienes:",
            placeholder="Ej. No encontré qué hacer cuando una grúa ya se llevó mi moto sin infracción..."
        )
        enviar_bz = st.form_submit_button("📨 Enviar mi Caso al Administrador para que lo agregue", use_container_width=True)

        if enviar_bz:
            if duda_bz and len(duda_bz.strip()) > 5:
                h_msg = hashlib.sha256(duda_bz.strip().lower

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
# SELLO DE AUTORÍA Y CONFIGURACIÓN GLOBAL v8.0
# ==============================================================================
AUTOR_SISTEMA = "Ing. Industrial y de Sistemas Saúl Ángel Ortiz Rogel"
MARCA_SISTEMA = "ForensicMind & LexGuía CBR v8.0 — Asesor Ciudadano Paso a Paso & GitHub Sync"

st.set_page_config(
    page_title=f"{MARCA_SISTEMA} | {AUTOR_SISTEMA}",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_NAME = "boveda_juridica_cbr_v8.db"
BACKUP_JSON_FILE = "cerebro_autonomo_backup.json"

# Lectura segura desde Streamlit Secrets
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
# BARRA LATERAL: LOGIN DE ADMINISTRADOR Y AJUSTES OCULTOS AL PÚBLICO
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎨 Apariencia de Lectura")
    modo_visual = st.radio(
        "Estilo visual de la pantalla:",
        ["☀️ Ejecutivo Claro (Máxima Lectura en Celular)", "🌙 Oscuro Forense Blindado"],
        index=0
    )

    st.markdown("---")
    st.markdown("### 🔐 Acceso Exclusivo Administrador")
    if not st.session_state["es_admin"]:
        pass_input = st.text_input(
            "Clave de Administrador:",
            type="password",
            placeholder="Exclusivo Ing. Saúl Ortiz"
        )
        if st.button("🔓 Desbloquear Panel Maestro", use_container_width=True):
            if pass_input == DEFAULT_ADMIN_PASS:
                st.session_state["es_admin"] = True
                st.success("✅ Bienvenido, Ing. Saúl. Panel total desbloqueado.")
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta.")
        # Valores por defecto seguros cuando un ciudadano usa la app
        auto_entrenar_switch = True
        buscar_web_switch = True
        gh_repo_input = DEFAULT_GH_REPO
        gh_token_input = DEFAULT_GH_TOKEN
        gh_branch_input = DEFAULT_GH_BRANCH
    else:
        st.success("✅ Modo Administrador Activo")
        if st.button("🔒 Cerrar Sesión de Administrador", use_container_width=True):
            st.session_state["es_admin"] = False
            st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Controles Maestros de la IA")
        auto_entrenar_switch = st.checkbox("🧠 Auto-Aprendizaje e Inyección Activa", value=True)
        buscar_web_switch = st.checkbox("🌐 Búsqueda en Vivo en Internet (Google & Wikipedia)", value=True)
        st.markdown("### ☁️ Credenciales GitHub Auto-Sync")
        gh_repo_input = st.text_input("Repositorio (usuario/repo):", value=DEFAULT_GH_REPO)
        gh_token_input = st.text_input("GitHub Token (ghp_...):", value=DEFAULT_GH_TOKEN, type="password")
        gh_branch_input = st.text_input("Rama (Branch):", value=DEFAULT_GH_BRANCH)

# ==============================================================================
# ESTILOS VISUALES ADAPTATIVOS (CLARO Y OSCURO)
# ==============================================================================
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
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            line-height: 1.5 !important;
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
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.15);
        }
        .author-banner * { color: #ffffff !important; }
        div[data-testid="metric-container"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-left: 5px solid #2563eb !important;
            padding: 14px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
        }
        div[data-testid="metric-container"] label { color: #475569 !important; -webkit-text-fill-color: #475569 !important; }
        div[data-testid="stMetricValue"] { color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; font-weight: 800 !important; }
        .win-badge { background-color: #059669; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .loss-badge { background-color: #dc2626; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .step-badge { background-color: #1d4ed8; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 5px 12px; border-radius: 6px; font-weight: 800; display: inline-block; }
        .card-box { background-color: #ffffff; border: 1px solid #cbd5e1; border-left: 6px solid #2563eb; border-radius: 12px; padding: 18px; margin: 10px 0; color: #0f172a !important; line-height: 1.65; }
        .money-box { background-color: #ecfdf5; border: 1px solid #6ee7b7; border-left: 6px solid #059669; border-radius: 12px; padding: 18px; margin: 10px 0; color: #064e3b !important; line-height: 1.65; }
        .lawyer-box { background-color: #eef2ff; border: 1px solid #a5b4fc; border-left: 6px solid #4f46e5; border-radius: 12px; padding: 18px; margin: 10px 0; color: #1e1b4b !important; line-height: 1.65; }
        .alert-box { background-color: #fef2f2; border: 1px solid #fca5a5; border-left: 6px solid #dc2626; border-radius: 12px; padding: 18px; margin: 10px 0; color: #7f1d1d !important; line-height: 1.65; }
        .script-box { background-color: #fffbeb; border: 1px solid #fde68a; border-left: 6px solid #d97706; border-radius: 12px; padding: 18px; margin: 10px 0; color: #78350f !important; line-height: 1.65; }
        .web-box { background-color: #f0f9ff; border: 1px solid #7dd3fc; border-left: 6px solid #0284c7; border-radius: 12px; padding: 16px; margin: 10px 0; color: #0c4a6e !important; }
        div.stButton > button:first-child {
            background: linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            font-weight: 800 !important;
            font-size: 1.05rem !important;
            border-radius: 10px !important;
            border: none !important;
            padding: 14px 22px !important;
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
            border: 2px solid #38bdf8 !important; border-radius: 10px !important; font-size: 1.05rem !important; font-weight: 700 !important; padding: 12px !important;
        }
        div[data-baseweb="select"] > div { background-color: #1e293b !important; color: #f8fafc !important; -webkit-text-fill-color: #f8fafc !important; border: 1px solid #38bdf8 !important; }
        .author-banner { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border: 1px solid #38bdf8; border-left: 6px solid #f59e0b; border-radius: 12px; padding: 16px 20px; margin-bottom: 18px; }
        div[data-testid="metric-container"] { background: #111827 !important; border: 1px solid #374151 !important; border-left: 4px solid #38bdf8 !important; padding: 14px !important; border-radius: 10px !important; }
        .win-badge { background-color: #065f46; color: #34d399 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .loss-badge { background-color: #7f1d1d; color: #f87171 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .step-badge { background-color: #1e3a8a; color: #93c5fd !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .card-box { background-color: #131c2e; border: 1px solid #2dd4bf; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.65; }
        .money-box { background-color: #0f2922; border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.65; }
        .lawyer-box { background-color: #1e1b4b; border: 1px solid #818cf8; border-left: 5px solid #a78bfa; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.65; }
        .alert-box { background-color: #1f1215; border: 1px solid #f87171; border-left: 5px solid #ef4444; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.65; }
        .script-box { background-color: #271c09; border: 1px solid #f59e0b; border-left: 5px solid #fbbf24; border-radius: 10px; padding: 18px; margin: 10px 0; line-height: 1.65; }
        .web-box { background-color: #0c192c; border: 1px solid #38bdf8; border-left: 5px solid #0284c7; border-radius: 10px; padding: 16px; margin: 10px 0; }
        div.stButton > button:first-child { background-color: #2563eb !important; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; font-weight: bold !important; border-radius: 10px !important; padding: 12px 20px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. TAXONOMÍA COMPLETA (6 GRANDES FAMILIAS INCLUYENDO TRÁNSITO Y POLICÍAS)
# ==============================================================================
TIPOS_CASOS = {
    "Casos Laborales": [
        "Despido injustificado", "Coacción para firmar renuncia / hoja en blanco",
        "Falta de pago de vacaciones / días de descanso", "Salarios o quincenas retenidas",
        "Acoso laboral (Mobbing)", "Accidente de trabajo sin IMSS"
    ],
    "Tránsito, Multas y Abuso Policial": [
        "Policía pide mordida o amenaza con corralón", "Retención ilegal de placas, licencia o tarjeta",
        "Detención en retén o revisión arbitraria de vehículo", "Choque vial y abuso de grúas o ajustadores",
        "Multa fantasma o infracción improcedente"
    ],
    "Casos Familiares": [
        "Pensión alimenticia y ocultamiento de ingresos", "Divorcio e inventario de bienes",
        "Guarda y custodia de hijos", "Régimen de visitas impedido", "Reconocimiento de paternidad"
    ],
    "Casos Penales": [
        "Fraude bancario SPEI / Phishing digital", "Detención arbitraria y revisión ilegal de celular",
        "Robo o extorsión", "Violencia familiar", "Abuso de autoridad ministerial"
    ],
    "Casos Civiles": [
        "Arrendamiento (Inquilino que no paga renta)", "Acoso de despachos de cobranza o apps de préstamos",
        "Incumplimiento de contrato civil", "Disputa de propiedad o terrenos", "Herencias y sucesiones"
    ],
    "Casos Mercantiles": [
        "Cobro de pagaré vencido", "Mercancía entregada y no pagada",
        "Cheque sin fondos o factura comercial", "Fraude entre socios comerciales"
    ]
}

ETAPAS_PROCESO = {
    "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)": [
        "1. Solicitud de Conciliación / Demanda Inicial",
        "2. Audiencia de Conciliación / Contestación",
        "3. Ofrecimiento y Admisión de Pruebas",
        "4. Desahogo de Pruebas y Alegatos",
        "5. Laudo / Sentencia Definitiva",
        "6. Recursos / Amparo Directo",
        "7. Ejecución Forzosa y Embargo"
    ],
    "Proceso Administrativo / Tránsito y Vialidad (5 Etapas)": [
        "1. Intervención en Vía Pública y Verificación de Facultades",
        "2. Levantamiento de Boleta de Infracción / Acta Circunstanciada",
        "3. Queja ante Asuntos Internos / Contraloría Municipal o Estatal",
        "4. Juicio de Nulidad ante Tribunal de Justicia Administrativa",
        "5. Devolución de Garantías o Cancelación de Multa"
    ],
    "Proceso Penal (8 Etapas)": [
        "1. Denuncia o Querella ante Fiscalía/MP",
        "2. Investigación Inicial y Complementaria",
        "3. Audiencia Inicial y Control de Detención",
        "4. Etapa Intermedia (Admisión de Pruebas)",
        "5. Audiencia de Juicio Oral",
        "6. Emisión de Sentencia",
        "7. Recursos de Apelación / Amparo",
        "8. Ejecución de Sanciones y Reparación del Daño"
    ]
}

TABULADOR_HONORARIOS_RAMA = {
    "Casos Laborales": {
        "asesoria_min": 500, "asesoria_sug": 800, "asesoria_max": 1800, "anticipo_sug": 0,
        "esquema_cobro": "Porcentaje al ganar (Cuota Litis del 20% al 30% solo cuando cobres tu dinero; $0 de anticipo inicial)",
        "pct_sugerido": 25.0, "gastos_periciales_sug": 1000, "horas_promedio_despacho": 35,
        "via_gratuita": "PROFEDET / Procuraduría de la Defensa del Trabajo y Centro de Conciliación — $0 MXN (100% Gratuito)"
    },
    "Tránsito, Multas y Abuso Policial": {
        "asesoria_min": 400, "asesoria_sug": 700, "asesoria_max": 1500, "anticipo_sug": 1500,
        "esquema_cobro": "Honorario fijo por Juicio de Nulidad de Multa o Amparo contra Corralón/Retención",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 500, "horas_promedio_despacho": 15,
        "via_gratuita": "Unidad de Asuntos Internos Policial / Defensoría en Justicia Administrativa / Derechos Humanos — $0 MXN"
    },
    "Casos Familiares": {
        "asesoria_min": 700, "asesoria_sug": 1200, "asesoria_max": 2500, "anticipo_sug": 5000,
        "esquema_cobro": "Honorario dividido en pagos mensuales o por etapa procesal",
        "pct_sugerido": 0.0, "gastos_periciales_sug": 2500, "horas_promedio_despacho": 45,
        "via_gratuita": "DIF Municipal/Estatal y Defensoría Pública Familiar — $0 MXN (100% Gratuito)"
    },
    "Casos Penales": {
        "asesoria_min": 1000, "asesoria_sug": 2000, "asesoria_max": 4500, "anticipo_sug": 15000,
        "esquema_cobro": "Cobro por etapa (Ministerio Público / Audiencia Inicial / Juicio Oral)",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 8000, "horas_promedio_despacho": 75,
        "via_gratuita": "Instituto de la Defensoría Pública y Comisión de Atención a Víctimas — $0 MXN"
    },
    "Casos Civiles": {
        "asesoria_min": 800, "asesoria_sug": 1400, "asesoria_max": 2800, "anticipo_sug": 6000,
        "esquema_cobro": "Anticipo inicial + 15% sobre el monto recuperado o inmueble liberado",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 3500, "horas_promedio_despacho": 50,
        "via_gratuita": "Defensoría Pública Civil o CONDUSEF (contra cobranza bancaria abusiva) — $0 MXN"
    },
    "Casos Mercantiles": {
        "asesoria_min": 900, "asesoria_sug": 1600, "asesoria_max": 3200, "anticipo_sug": 5000,
        "esquema_cobro": "Anticipo para diligencia de embargo + 20% sobre lo cobrado efectivamente",
        "pct_sugerido": 20.0, "gastos_periciales_sug": 4000, "horas_promedio_despacho": 40,
        "via_gratuita": "PROFECO o CONDUSEF — $0 MXN"
    }
}

ESCENARIOS_FRECUENTES = {
    "✍️ Escribir o dictar mi propio caso con mis palabras": "Mi sueldo semanal es de 2300. Me despidieron y no me quieren dar liquidación, solo me quieren dar $5000 y no me daban vacaciones ni días libres ni bonos, ¿qué procede ahí?",
    "🚓 Tránsito / Policía: Me detuvo una patrulla, me amenazan con corralón y piden mordida": "Un policía me detuvo diciendo que cometí una infracción, me quitó mi licencia y tarjeta de circulación, me amenaza con llevarse mi vehículo al corralón con grúa si no le doy $2,500 en efectivo ahorita mismo.",
    "💼 Laboral: Me quieren obligar a firmar mi renuncia o una hoja en blanco": "Me corrieron de la chamba hoy sin darme aviso por escrito, el de recursos humanos me encerró en la oficina y dice que si no le firmo mi hoja de renuncia voluntaria no me deja salir ni me paga mi semana.",
    "📱 Cobranza Abusiva: Me amenazan por deudas o préstamos de aplicación": "Pedí un préstamo y ahora un despacho de cobranza me manda mensajes con insultos, amenazas de embargo falso mañana mismo y están mandando fotos mías a mis contactos de WhatsApp.",
    "👨‍👩‍👧 Familiar: El papá/mamá de mis hijos no da gasto y esconde su sueldo": "El papá de mis hijos lleva 4 meses sin dar pensión alimenticia, se salió de su trabajo con seguro para decirle al juez que no gana nada, pero tiene un negocio y recibe transferencias.",
    "💻 Penal / Banco: Me vaciaron mi cuenta bancaria con un enlace o llamada falsa": "Me llegó un mensaje según de mi banco por un cargo no reconocido, entré al link y me vaciaron $38,000 pesos por transferencia SPEI que yo jamás autoricé.",
    "🏠 Civil: Mi inquilino no me paga la renta y no se quiere salir de la casa": "Le renté mi casa a una persona que lleva 5 meses sin pagarme renta, ya se venció el contrato y me dice que le haga como quiera porque no se va a salir.",
    "📑 Mercantil: Me firmaron un pagaré por dinero prestado y se esconden": "Le presté $45,000 pesos a un conocido que me firmó un pagaré, ya pasó la fecha de pago y ahora me bloqueó de WhatsApp y no me quiere pagar."
}

# ==============================================================================
# 2. TRADUCTOR SEMÁNTICO DE LENGUAJE COLOQUIAL A CONCEPTOS LEGALES
# ==============================================================================
DICCIONARIO_COLOQUIAL_A_JURIDICO = [
    (r'\b(chamba|jale|empleo|trabajo|oficina|empresa|fabrica|tienda|bodega|turno|raya)\b', ' trabajo laboral patron '),
    (r'\b(corrieron|echaron|despidieron|cortaron|dieron de baja|ya no me dejaron entrar)\b', ' despido injustificado laboral '),
    (r'\b(patron|jefe|gerente|rh|recursos humanos|supervisor|dueño)\b', ' patron laboral empleador '),
    (r'\b(liquidacion|finiquito|quincena|semanal|sueldo|nomina|aguinaldo|vacaciones|dias libres|descanso|horas extras|bonos)\b', ' liquidacion salario prestaciones laboral '),
    (r'\b(hoja en blanco|firmar mi renuncia|renuncia voluntaria|quieren dar solo|solo me dan)\b', ' coaccion laboral despido injustificado '),
    (r'\b(transito|multa|infraccion|corralon|grua|mordida|placa|placas|licencia|tarjeta de circulacion|reten|alcoholimetro|verificacion|motocicleta|moto|carro|auto)\b', ' transito vialidad policia corralon multa administrativo '),
    (r'\b(para el refresco|ponernos de acuerdo|bajarle a la multa|quitaron la placa)\b', ' extorsion policial transito mordida corralon '),
    (r'\b(gasto de los niños|manutencion|pension|alimentos|papa de mis hijos|mama de mis hijos|divorcio|custodia)\b', ' pension alimenticia familiar custodia hijos '),
    (r'\b(vaciaron mi cuenta|robaron mi tarjeta|phishing|hackearon|estafaron|clonaron|spei)\b', ' fraude bancario penal ciberdelito '),
    (r'\b(patrulla|policias|mp|ministerio publico|detuvieron|arrestaron|separos|revisaron mi celular)\b', ' detencion arbitraria abuso de autoridad penal '),
    (r'\b(inquilino|renta|arrendamiento|depa|departamento|casa rentada|desalojar|cambiar la chapa|cobranza|despacho|prestamo|embargo falso)\b', ' arrendamiento civil inquilino desocupacion cobranza '),
    (r'\b(pagare|cheque sin fondos|mercancia fiada|letra de cambio|deudor comercial)\b', ' pagare ejecutivo mercantil cobranza ')
]

def expandir_lenguaje_coloquial(texto: str) -> str:
    texto_limpio = str(texto).lower()
    expansiones = []
    for patron, equivalente_juridico in DICCIONARIO_COLOQUIAL_A_JURIDICO:
        matches = re.findall(patron, texto_limpio)
        if matches:
            expansiones.append(equivalente_juridico * len(matches))
    return str(texto) + " " + " ".join(expansiones)

# ==============================================================================
# 3. MOTOR DE AUTOINYECCIÓN PERPETUA Y SINCRONIZACIÓN GITHUB API (INCLUYE BUZÓN)
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
            m.get("fuente_aprendizaje", "Auto-Inyección de Respaldo"),
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

    for bz in data.get("buzon_casos_usuarios", []):
        rel_bz = str(bz.get("relato_usuario", "")).strip()
        if not rel_bz:
            continue
        h_bz = bz.get("hash_caso") or hashlib.sha256(rel_bz.lower().encode("utf-8")).hexdigest()
        c.execute("""
            INSERT OR IGNORE INTO buzon_casos_usuarios (
                nombre_contacto, medio_contacto, categoria_sugerida,
                relato_usuario, duda_especifica, estado_revision,
                respuesta_admin, hash_caso, fecha_envio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bz.get("nombre_contacto", "Anónimo"),
            bz.get("medio_contacto", "Sin especificar"),
            bz.get("categoria_sugerida", "Casos Laborales"),
            rel_bz,
            bz.get("duda_especifica", ""),
            bz.get("estado_revision", "PENDIENTE"),
            bz.get("respuesta_admin", ""),
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
        return {"local_ok": True, "github_ok": False, "msg": "Respaldo local autoinyectable actualizado."}

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
        "message": f"Auto-Inyección IA v8.0 ({len(df_mem)} memorias | {len(df_casos)} casos | {len(df_buzon)} buzón)",
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
# 4. INICIALIZACIÓN DE SQLITE CON CASOS SEMILLA (INCLUYE TRÁNSITO Y LABORAL)
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
            nombre_contacto TEXT,
            medio_contacto TEXT,
            categoria_sugerida TEXT,
            relato_usuario TEXT,
            duda_especifica TEXT,
            estado_revision TEXT,
            respuesta_admin TEXT,
            hash_caso TEXT UNIQUE,
            fecha_envio TEXT
        )
    """)

    semillas = [
        (
            "EXP-LAB-2026-001", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Despido Injustificado Ganado (Sueldo Semanal sin Vacaciones ni Descansos y Oferta Trampa de $5,000)",
            "Conciliador Laboral, Juez Laboral, Abogado / Procurador PROFEDET",
            "1. Solicitud de Conciliación / Demanda Inicial", "Embargo precautorio de cuentas", "Convenio ratificado al 100% de Ley", "Demanda laboral",
            "Mi sueldo semanal es de 2300, me despidieron sin aviso y solo me quieren dar $5000 sin liquidación, no me daban vacaciones ni días libres ni bonos.",
            hashlib.sha256(b"EXP-LAB-2026-001").hexdigest(), "GANADO",
            "El abogado rechazó los $5,000 iniciales, citó al patrón en el Centro de Conciliación y exigió 90 días de Salario Diario Integrado, vacaciones atrasadas, aguinaldo y séptimos días trabajados.",
            "La autoridad laboral obligó al patrón a pagar más de $49,000 MXN al no existir aviso escrito de rescisión.",
            "N/A", "No firmar renuncia voluntaria, rechazar pagos engañosos y acudir a Conciliación en la primera semana.",
            "Rechazar los $5,000 si te piden firmar renuncia, respaldar mensajes de WhatsApp de horarios y citar al patrón en el Centro de Conciliación.",
            "JAMÁS firmar una hoja en blanco o carta de renuncia voluntaria para que te suelten un pago chiquito.",
            "2026-08-01"
        ),
        (
            "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Despido Perdido por Aceptar $5,000 Firmando Carta de Renuncia y Dejar Pasar 60 Días",
            "Juez Laboral, Abogado de empresa",
            "2. Audiencia de Conciliación / Contestación", "Ninguna", "Sentencia absolutoria para la empresa", "Amparo directo",
            "El trabajador aceptó $5,000 por urgencia económica firmando una hoja de renuncia voluntaria y reclamó hasta después de dos meses.",
            hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "PERDIDO",
            "Se presentó la demanda fuera del plazo de 60 días y sin pruebas de coacción en la firma.",
            "El Juez declaró prescrita la acción y dio por válida la renuncia firmada.",
            "Firmar renuncia voluntaria bajo promesa verbal y dejar vencer los 60 días naturales.",
            "N/A", "Acudir a PROFEDET o Conciliación inmediatamente sin firmar papelería de baja.",
            "NUNCA creer en la promesa de 'firma tu renuncia hoy para liberarte este cheque y luego vemos lo demás'.",
            "2026-08-05"
        ),
        (
            "EXP-TRA-2026-003", "Derecho Público", "Derecho Administrativo", "Tránsito, Multas y Abuso Policial", "Policía pide mordida o amenaza con corralón",
            "Amenaza de Corralón y Retención de Licencia Anulada por Grabación y Queja en Asuntos Internos",
            "Agente de Tránsito, Unidad de Asuntos Internos, Magistrado Administrativo",
            "1. Intervención en Vía Pública y Verificación de Facultades", "Suspensión de cobro y devolución de licencia", "Nulidad lisa y llana de infracción", "Juicio Contencioso Administrativo",
            "Un policía me detuvo sin motivo claro, me quitó mi licencia y me amenazó con llevarse mi carro o moto al corralón con grúa si no le daba $2,500 de mordida.",
            hashlib.sha256(b"EXP-TRA-2026-003").hexdigest(), "GANADO",
            "El ciudadano grabó el número de patrulla y gafete, exigió boleta oficial en lugar de dar efectivo e impugnó la falta de fundamentación ante el Tribunal Administrativo.",
            "Asuntos Internos inició investigación al oficial y el Tribunal anuló la multa ordenando devolver los documentos sin costo.",
            "N/A", "Grabar legalmente la intervención, pedir el artículo exacto del Reglamento de Tránsito y jamás entregar dinero en efectivo.",
            "Grabar con el celular, anotar número de patrulla, exigir que te digan qué artículo te permite corralón y reportar a Asuntos Internos.",
            "JAMÁS dar mordida ni ponerte a empujar o insultar al policía (para que no te acusen de resistencia de particulares).",
            "2026-08-12"
        ),
        (
            "EXP-TRA-2026-004", "Derecho Público", "Derecho Administrativo", "Tránsito, Multas y Abuso Policial", "Policía pide mordida o amenaza con corralón",
            "Caso Vial Complicado por Agredir Verbalmente al Oficial y Entregar Dinero sin Recibo",
            "Juez Cívico, Agente Policial",
            "2. Levantamiento de Boleta de Infracción / Acta Circunstanciada", "Remisión a Juzgado Cívico", "Arresto administrativo y arrastre de grúa", "Queja",
            "El conductor discutió a gritos y empujones con la patrulla, no grabó evidencia y entregó dinero en efectivo sin recibo.",
            hashlib.sha256(b"EXP-TRA-2026-004").hexdigest(), "PERDIDO",
            "No existían pruebas de la extorsión original y los oficiales reportaron faltas a la autoridad.",
            "El Juez Cívico impuso sanción administrativa.",
            "Perder la calma, caer en provocaciones físicas y no documentar en video el abuso.",
            "N/A", "Mantener voz tranquila, manos visibles en el volante y grabar todo desde el primer segundo.",
            "NUNCA insultar ni tocar físicamente a un oficial ni soltar dinero en efectivo sin boleta oficial.",
            "2026-08-14"
        ),
        (
            "EXP-FAM-2026-005", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia y ocultamiento de ingresos",
            "Pensión Alimenticia Ganada Rastreando Cuentas Bancarias del Deudor que Renunció a su Empleo",
            "Juez de lo Familiar, Abogado Familiar, Trabajador Social",
            "1. Solicitud de Conciliación / Demanda Inicial", "Pensión provisional urgente y oficio a bancos (CNBV)", "Sentencia de pensión definitiva y aseguramiento", "Incidente de alimentos",
            "El papá de mis hijos dejó de dar gasto, se salió de trabajar para decir que no tiene ingresos pero cobra en efectivo y transferencias.",
            hashlib.sha256(b"EXP-FAM-2026-005").hexdigest(), "GANADO",
            "El abogado solicitó pensión provisional desde el día 1 y pidió al Juez girar oficios al SAT y a la Comisión Nacional Bancaria para ver todos sus depósitos.",
            "El Juez fijó pensión con base en sus depósitos bancarios reales y ordenó inscripción en el Registro de Deudores Alimentarios Morosos.",
            "N/A", "Pedir pensión provisional inmediata e investigar estados de cuenta bancarios y nivel de vida.",
            "Juntar actas de nacimiento, tickets de gastos de comida/escuela y acudir al Juez Familiar o DIF.",
            "No conformarse con promesas de palabra ni ocultar a los menores sin orden judicial.",
            "2026-08-18"
        ),
        (
            "EXP-PEN-2026-006", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude bancario SPEI / Phishing digital",
            "Recuperación de Dinero por Fraude Bancario SPEI y Phishing con Sello Forense y CONDUSEF",
            "CONDUSEF, Fiscal MP, Juez Civil/Mercantil",
            "1. Denuncia o Querella ante Fiscalía/MP", "Bloqueo de folio SPEI y dictamen CONDUSEF", "Restitución de fondos bancarios más intereses", "Juicio Oral Mercantil contra el Banco",
            "Me vaciaron mi cuenta del banco tras picarle a un enlace falso de mensaje SMS y se hicieron transferencias SPEI no reconocidas.",
            hashlib.sha256(b"EXP-PEN-2026-006").hexdigest(), "GANADO",
            "Se reportó el cargo en las primeras 24 horas, se descargó el comprobante CEP de Banxico para identificar al titular destino y se demandó al banco conforme a jurisprudencia de la SCJN.",
            "El banco fue condenado a reembolsar el dinero porque no acreditó que el cliente autorizó la operación con sus factores de seguridad.",
            "N/A", "Reportar de inmediato al banco pidiendo folio, descargar el CEP en Banxico y acudir a CONDUSEF.",
            "Llamar a tu banco para bloquear la cuenta y pedir número de folio, sacar capturas sin recortar y acudir a CONDUSEF/Fiscalía.",
            "No borrar el mensaje SMS falso ni dejar pasar semanas sin levantar el folio de cargo no reconocido.",
            "2026-08-22"
        ),
        (
            "EXP-CIV-2026-007", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento (Inquilino que no paga renta)",
            "Recuperación Legal de Casa Rentada y Cobro de Rentas mediante Juicio de Arrendamiento",
            "Juez Civil, Actuario, Abogado Civil",
            "1. Solicitud de Conciliación / Demanda Inicial", "Embargo de bienes del fiador/inquilino", "Sentencia de desocupación y entrega del inmueble", "Juicio de Arrendamiento",
            "Mi inquilino lleva 5 meses sin pagarme la renta, ya se acabó el contrato y dice que no se va a salir.",
            hashlib.sha256(b"EXP-CIV-2026-007").hexdigest(), "GANADO",
            "Se promovió controversia de arrendamiento civil solicitando orden de lanzamiento legal y embargo de cuentas/bienes.",
            "El Juez ordenó la desocupación con apoyo de actuario y fuerza pública legal.",
            "N/A", "Usar la vía judicial civil sin caer en el delito de despojo por cuenta propia.",
            "Buscar el contrato de renta, mensajes de cobro y promover juicio civil de desocupación.",
            "JAMÁS cambiar la chapa tú mismo ni cortar el agua o la luz por la fuerza (porque el inquilino te denuncia por despojo).",
            "2026-08-26"
        ),
        (
            "EXP-MER-2026-008", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Cobro de pagaré vencido",
            "Cobro Exitoso de Pagaré con Embargo desde la Primera Visita al Deudor",
            "Juez Mercantil, Actuario Ejecutor, Abogado",
            "1. Solicitud de Conciliación / Demanda Inicial", "Auto de exequendo (Embargo inmediato)", "Sentencia de remate y pago total", "Juicio Ejecutivo Mercantil",
            "Me firmaron un pagaré por dinero prestado, ya venció la fecha y el deudor se esconde para no pagar.",
            hashlib.sha256(b"EXP-MER-2026-008").hexdigest(), "GANADO",
            "Se presentó demanda ejecutiva mercantil con el pagaré original y el Actuario embargó bienes en la primera diligencia.",
            "El Juez condenó al pago del capital más intereses moratorios.",
            "N/A", "Conservar el pagaré original sin tachaduras y embargar en el primer acto.",
            "Guardar el pagaré original en lugar seguro y demandar antes de cumplir 3 años de vencido.",
            "NUNCA remarcar con otra pluma la fecha o el monto del pagaré después de firmado.",
            "2026-08-29"
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
                data_local = json.load(f_local)
                inyectar_diccionario_cerebro_en_sqlite(data_local, conn)
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
# 5. EXTRACTOR COLOQUIAL DE SUELDO Y CALCULADORA LFT COMPLETA (CON DÍAS LIBRES)
# ==============================================================================
def normalizar_texto_coloquial(texto: str) -> dict:
    texto_low = texto.lower().replace(",", "")
    salario_mensual = None
    periodicidad = "Mensual ($9,857.14 / mes)"

    m_sem = re.search(r'(?:semanal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la semana|semanal(?:es)?|por semana))', texto_low)
    if m_sem:
        val = float(m_sem.group(1) or m_sem.group(2))
        salario_mensual = round((val / 7.0) * 30.0, 2)
        periodicidad = f"Semanal (${val:,.2f} a la semana)"

    if salario_mensual is None:
        m_quin = re.search(r'(?:quincenal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la quincena|quincenal(?:es)?|por quincena))', texto_low)
        if m_quin:
            val = float(m_quin.group(1) or m_quin.group(2))
            salario_mensual = round(val * 2.0, 2)
            periodicidad = f"Quincenal (${val:,.2f} a la quincena)"

    if salario_mensual is None:
        m_men = re.search(r'(?:mensual(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:al mes|mensual(?:es)?|por mes))', texto_low)
        if m_men:
            val = float(m_men.group(1) or m_men.group(2))
            salario_mensual = round(val, 2)
            periodicidad = f"Mensual (${val:,.2f} al mes)"

    if salario_mensual is None:
        m_gen = re.search(r'(?:gano|ganaba|sueldo|pago|pagan)\s*(?:es\s*de)?\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
        if m_gen:
            val = float(m_gen.group(1))
            if val < 5000:
                salario_mensual = round((val / 7.0) * 30.0, 2)
                periodicidad = f"Semanal detectado (${val:,.2f} a la semana)"
            else:
                salario_mensual = round(val, 2)
                periodicidad = f"Mensual detectado (${val:,.2f} al mes)"

    oferta_patronal = 0.0
    m_oferta = re.search(r'(?:quieren dar|ofrecen|daban|dan|ofreciendo|soltar|piden|mordida de)\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
    if m_oferta:
        oferta_patronal = float(m_oferta.group(1))

    sin_vacaciones = any(k in texto_low for k in ["no me daban vacaciones", "sin vacaciones", "nunca tuve vacaciones"])
    sin_dias_libres = any(k in texto_low for k in ["días libres", "dias libres", "sin descanso", "no descansaba", "sin dia de descanso"])

    return {
        "salario_mensual": salario_mensual if salario_mensual else 9857.14,
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
    bonos_o_comisiones_adeudadas: float = 0.0,
    incluir_20_dias_por_anio: bool = False,
    meses_duracion_juicio: int = 0,
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
        monto_vacaciones_atrasadas + monto_prima_vac_prop + monto_descansos_trabajados + bonos_o_comisiones_adeudadas, 2
    )

    monto_indem_90_dias = round(90.0 * sdi, 2) if es_despido else 0.0
    monto_20_dias_anio = round(20.0 * antiguedad_total_anios * sdi, 2) if (es_despido and incluir_20_dias_por_anio) else 0.0
    meses_topados_12 = min(12, max(0, meses_duracion_juicio))
    monto_salarios_caidos = round(meses_topados_12 * 30.0 * sdi, 2) if es_despido else 0.0

    subtotal_indemnizacion = round(monto_prima_antiguedad + monto_indem_90_dias + monto_20_dias_anio + monto_salarios_caidos, 2)
    gran_total_bruto = round(subtotal_finiquito + subtotal_indemnizacion, 2)

    conceptos_tabla = [
        {"Concepto en Español Simple": "1. Días trabajados que no te han pagado", "Qué dice la Ley": "Art. 82 y 88 LFT", "Tipo de Pago": "Tu Finiquito Seguro", "Monto (MXN)": monto_sueldo_pendiente},
        {"Concepto en Español Simple": "2. Tu parte de Aguinaldo del año", "Qué dice la Ley": "Art. 87 LFT (Mínimo 15 días/año)", "Tipo de Pago": "Tu Finiquito Seguro", "Monto (MXN)": monto_aguinaldo_prop},
        {"Concepto en Español Simple": "3. Vacaciones que no te dieron + Proporcionales", "Qué dice la Ley": "Art. 76 y 79 LFT (Vacaciones Dignas)", "Tipo de Pago": "Tu Finiquito Seguro", "Monto (MXN)": round(monto_vacaciones_prop + monto_vacaciones_atrasadas, 2)},
        {"Concepto en Español Simple": "4. Prima Vacacional (25% extra sobre vacaciones)", "Qué dice la Ley": "Art. 80 LFT", "Tipo de Pago": "Tu Finiquito Seguro", "Monto (MXN)": monto_prima_vac_prop},
        {"Concepto en Español Simple": "5. Días de descanso trabajados (se pagan al doble extra)", "Qué dice la Ley": "Art. 69 y 73 LFT (Séptimo día)", "Tipo de Pago": "Prestación Omitida", "Monto (MXN)": monto_descansos_trabajados},
        {"Concepto en Español Simple": "6. Bonos o comisiones pendientes", "Qué dice la Ley": "Art. 84 LFT (Parte del salario)", "Tipo de Pago": "Prestación Omitida", "Monto (MXN)": bonos_o_comisiones_adeudadas},
        {"Concepto en Español Simple": "7. Prima de Antigüedad (12 días por cada año trabajado)", "Qué dice la Ley": "Art. 162 LFT", "Tipo de Pago": "Indemnización por Despido", "Monto (MXN)": monto_prima_antiguedad},
        {"Concepto en Español Simple": "8. Indemnización Constitucional (3 meses / 90 días de sueldo integrado)", "Qué dice la Ley": "Art. 123 Constitucional y Art. 48 LFT", "Tipo de Pago": "Indemnización por Despido", "Monto (MXN)": monto_indem_90_dias},
        {"Concepto en Español Simple": "9. 20 Días por Año (si aplica negativa de reinstalación)", "Qué dice la Ley": "Art. 50 LFT", "Tipo de Pago": "Condena Especial", "Monto (MXN)": monto_20_dias_anio},
        {"Concepto en Español Simple": "10. Salarios Caídos durante el juicio", "Qué dice la Ley": "Art. 48 LFT", "Tipo de Pago": "Condena en Juicio", "Monto (MXN)": monto_salarios_caidos}
    ]

    return {
        "sd": sd, "sdi": sdi, "subtotal_finiquito": subtotal_finiquito,
        "subtotal_indemnizacion": subtotal_indemnizacion, "gran_total_bruto": gran_total_bruto,
        "monto_indem_90_dias": monto_indem_90_dias, "monto_prima_antiguedad": monto_prima_antiguedad,
        "monto_descansos_trabajados": monto_descansos_trabajados,
        "tabla_conceptos": pd.DataFrame(conceptos_tabla)
    }

def calcular_cotizacion_honorarios_dual(
    monto_en_disputa: float,
    costo_asesoria: float = 800.0,
    anticipo_fijo: float = 0.0,
    pct_litis: float = 25.0,
    gastos_periciales: float = 1000.0,
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
# 6. GENERADOR DE ASESORÍA HUMANA EXHAUSTIVA PASO A PASO (SIN TECNICISMOS)
# ==============================================================================
def generar_asesoria_humana_exhaustiva(
    categoria_caso: str,
    tipo_caso: str,
    relato_usuario: str,
    datos_sueldo: dict,
    res_liq: dict,
    res_hon: dict
) -> dict:
    sueldo_mes = datos_sueldo["salario_mensual"]
    periodicidad = datos_sueldo["periodicidad"]
    oferta = datos_sueldo["oferta_patronal"]
    total_ley = res_liq["gran_total_bruto"]
    neto_bolsillo = res_hon["monto_neto_libre_ciudadano"]

    if categoria_caso == "Casos Laborales":
        faltante = max(0.0, round(total_ley - oferta, 2))
        txt_oferta = (
            f"Además, detecté que la empresa te quiere dar únicamente **${oferta:,.2f} MXN** para deshacerse de ti, lo cual significa que **te están intentando quitar ${faltante:,.2f} MXN** que por ley son tuyos."
            if oferta > 0 else
            "Además, te despidieron sin pagarte la indemnización completa que marca la ley."
        )
        txt_vac = (
            "También tomé en cuenta que **no te daban vacaciones ni días libres de descanso**, por lo que esos días no se pierden: el patrón tiene obligación de pagártelos en dinero (y los días de descanso trabajados valen al doble extra)."
            if (datos_sueldo["sin_vacaciones"] or datos_sueldo["sin_dias_libres"]) else
            "También incluí el pago proporcional de tus vacaciones, prima vacacional y aguinaldo."
        )

        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Centro de Conciliación Laboral (Etapa 1 amigable) / Juez del Tribunal Laboral (si no pagan)",
            "abogado": "Procurador gratuito de la PROFEDET ($0 pesos) o Abogado Laboralista privado (que cobra solo porcentaje al ganar)",
            "profesionales": "Conciliador Oficial del Gobierno + Actuario notificador",
            "medida_sugerida": "Citar formalmente al patrón al Centro de Conciliación y, si no paga, embargar cuentas de la empresa",
            "recurso_clave": "Solicitud de Conciliación Prejudicial (Trámite gratuito e inmediato)",
            "radiografia_empatica": (
                f"Leí con mucha atención todo lo que escribiste. Tu caso es un **Despido Injustificado**: trabajabas ganando un sueldo **{periodicidad}** "
                f"(que equivale a **${sueldo_mes:,.2f} MXN al mes** o **${res_liq['sd']:,.2f} MXN por día**). {txt_oferta} {txt_vac}"
            ),
            "explicacion_sencilla_dinero": (
                f"**¿Por qué te tocan ${total_ley:,.2f} MXN y no los ${oferta:,.0f} que te quieren dar?**\n\n"
                f"En México, la Ley Federal del Trabajo dice que ningún jefe te puede correr nomás de palabra diciendo *'ya no vengas mañana'*. Cuando hacen eso, la ley los castiga obligándolos a pagarte dos bolsas de dinero:\n"
                f"1. **Tu Finiquito Seguro (${res_liq['subtotal_finiquito']:,.2f} MXN):** Es el dinero que ya te ganaste trabajando (tu aguinaldo proporcional, tus vacaciones que nunca te dieron más un 25% extra, y los días de descanso trabajados).\n"
                f"2. **Tu Indemnización por Despido (${res_liq['subtotal_indemnizacion']:,.2f} MXN):** Son **3 meses completos de sueldo integrado (90 días = ${res_liq['monto_indem_90_dias']:,.2f} MXN)** más tu **Prima de Antigüedad (${res_liq['monto_prima_antiguedad']:,.2f} MXN)** para que tengas con qué mantenerte mientras encuentras otro trabajo.\n\n"
                f"Si vas con un defensor gratuito del gobierno (**PROFEDET**), los **${total_ley:,.2f} MXN son íntegros para ti**. Si contratas un abogado particular que te cobre al ganar, te quedarán libres en tu bolsillo alrededor de **${neto_bolsillo:,.2f} MXN**."
            ),
            "fases_cronologicas": [
                {
                    "titulo_fase": "FASE 1: ¿Qué hacer HOY MISMO frente al jefe o Recursos Humanos? (Primeras 2 horas)",
                    "explicacion": (
                        "• **No firmes ningún papel de 'Renuncia Voluntaria' ni hojas en blanco:** Muchos patrones te dicen: *'Fírmame tu renuncia para que contabilidad me libere hoy mismo tus $5,000 pesos'*. ¡Es una trampa! Si firmas esa hoja, legalmente estás diciendo que tú te saliste por tu gusto y pierdes automáticamente los otros $44,000+ pesos.\n"
                        "• **Si te quieren encerrar o presionar en una oficina:** Nadie puede retenerte a la fuerza (eso es un delito llamado privación ilegal de la libertad). Saca tu celular, empieza a grabar audio o llama al 911 desde ahí mismo y verás cómo te abren la puerta de inmediato.\n"
                        "• **¿Qué pasa si no tenías contrato escrito ni seguro (IMSS)?:** ¡No te preocupes! La ley dice que la culpa de no hacer contrato es 100% del patrón, no tuya. Tienes exactamente los mismos derechos."
                    )
                },
                {
                    "titulo_fase": "FASE 2: ¿Qué pruebas caseras juntar al llegar a tu casa? (Primeras 24 horas)",
                    "explicacion": (
                        "Antes de que tu jefe te borre de los grupos de WhatsApp, haz capturas de pantalla de todo esto:\n"
                        "1. **Mensajes de WhatsApp:** Donde tu jefe o encargado te daba órdenes, te pedía llegar a cierta hora, te mandaba el rol de turnos o te avisaba que ya no te presentaras.\n"
                        "2. **Comprobantes de pago:** Estados de cuenta si te depositaban en tarjeta, o fotos de los sobres amarillos/recibos si te pagaban en efectivo.\n"
                        "3. **Fotos y ubicación:** Fotos tuyas con el uniforme, gafete o dentro del negocio, y el nombre completo y dirección exacta del lugar donde trabajabas."
                    )
                },
                {
                    "titulo_fase": "FASE 3: ¿A dónde ir ESTA MISMA SEMANA sin gastar un peso? (Días 2 al 5)",
                    "explicacion": (
                        "• **Acude al Centro de Conciliación Laboral de tu Estado o a la PROFEDET:** Lleva tu INE, el nombre de tu patrón o del negocio y la dirección del trabajo.\n"
                        "• **¿Qué hacen ahí?:** Un funcionario público gratuito levanta tu **Solicitud de Conciliación** en 20 minutos y te entrega un citatorio oficial (o lo lleva un notificador) para obligar a tu patrón a presentarse en una sala de conciliación en menos de 15 días."
                    )
                },
                {
                    "titulo_fase": "FASE 4: ¿Cómo actuar el día de la Cita de Conciliación? (Día de cobrar)",
                    "explicacion": (
                        "• En esa cita no hay jueces regañones; es una mesa donde un Conciliador oficial le explica al patrón que si no llega a un arreglo contigo ahí mismo, le vas a meter demanda ante el Juez y le saldrá mucho más caro.\n"
                        "• **La regla de oro en la negociación:** En conciliación rápida (para cobrar en 2 semanas sin esperar meses de juicio), la mayoría de las empresas ofrecen pagar entre el **70% y el 100%** de tu liquidación. Nunca aceptes migajas como $5,000 pesos; exige un convenio justo certificado por el Conciliador."
                    )
                }
            ],
            "guiones_dialogo": [
                {
                    "situacion": "🗣️ Qué decirle exactamente al jefe o Recursos Humanos cuando te ofrecen $5,000 y te piden firmar:",
                    "frase_exacta": "\"Entiendo que ya no quieran mis servicios, pero esos $5,000 pesos no cubren mis 90 días de liquidación por ley ni mis vacaciones y descansos trabajados. No voy a firmar ninguna hoja de renuncia voluntaria. Si me van a dar de baja, entréguenme el aviso por escrito o nos vemos esta semana en el Centro de Conciliación Laboral para hacer la cuenta conforme a la ley.\""
                },
                {
                    "situacion": "🗣️ Qué decir al llegar a la ventanilla de la PROFEDET o Centro de Conciliación:",
                    "frase_exacta": "\"Buenos días. Vengo a solicitar apoyo gratuito y abrir mi cita de conciliación porque me acaban de despedir injustificadamente de mi trabajo. Ganaba por semana, no me daban vacaciones ni días de descanso y me quieren dar solo una mínima parte a cambio de firmar mi renuncia.\""
                }
            ],
            "trampas_mortales": [
                "🚫 **TRAMPA 1 (La hoja de renuncia disfrazada):** Te dicen *'Firma aquí de recibido por los $5,000'*, pero el papel arriba o a la mitad dice *'Renuncia Voluntaria y recibo finiquito sin que me deban nada'*. Si firmas eso, regalaste tu caso.",
                "🚫 **TRAMPA 2 (Dejar pasar el tiempo creyendo promesas):** El patrón te dice *'Aguántame 2 meses y te liquido bien'*. ¡Cuidado! La ley te da **60 días naturales (2 meses en el calendario)** desde el día que te corrieron para ir a Conciliación. Si pasa el día 61, tu derecho caduca y pierdes todo.",
                "🚫 **TRAMPA 3 (Salirte gritando o llevarte cosas del trabajo):** Aunque tengas mucho coraje, no rompas nada ni te lleves herramientas o dinero de la caja para 'cobrarte a lo chino', porque entonces el patrón te voltea la tortilla y te denuncia penalmente por robo."
            ],
            "glosario_sencillo": {
                "Salario Diario Integrado (SDI)": "Es tu sueldo de un día normal sumándole unos pesitos extra que corresponden a tu aguinaldo y prima vacacional. Con este sueldo más alto se calculan tus 90 días.",
                "Finiquito vs. Liquidación": "El Finiquito es lo poquito que te dan cuando tú renuncias (solo días trabajados y vacaciones). La Liquidación es el pago grande (con 3 meses extra de sueldo) cuando ellos te corren.",
                "Prescripción de 60 días": "Es tu fecha de caducidad. Tienes 60 días seguidos desde el despido para iniciar tu reclamo oficial."
            },
            "pasos_inmediatos": [
                f"1. NO FIRMAR renuncia ni hojas en blanco, ni aceptar los ${oferta:,.0f} como pago final.",
                "2. Guardar hoy mismo capturas de WhatsApp de horarios, órdenes del jefe y recibos/transferencias.",
                "3. Acudir esta semana al Centro de Conciliación Laboral o PROFEDET (trámite 100% gratuito).",
                f"4. Exigir tu liquidación legal de ${total_ley:,.2f} MXN (90 días SDI + vacaciones + descansos + aguinaldo)."
            ],
            "alerta_fatal": "¡EL RELOJ CORRE! Tienes exactamente 60 días naturales desde el día en que te despidieron para acudir al Centro de Conciliación. Si dejas pasar los 60 días, pierdes el derecho a cobrar."
        }

    elif categoria_caso == "Tránsito, Multas y Abuso Policial":
        return {
            "proceso": "Proceso Administrativo / Tránsito y Vialidad (5 Etapas)",
            "juez": "Juez Cívico / Magistrado del Tribunal de Justicia Administrativa / Asuntos Internos",
            "abogado": "Defensor Público Administrativo ($0 pesos) o Abogado Especialista en Nulidad de Multas",
            "profesionales": "Inspector de Asuntos Internos Policial + Perito en Vialidad",
            "medida_sugerida": "Grabación en video de la patrulla, negativa a dar mordida y suspensión del acto administrativo",
            "recurso_clave": "Denuncia en Asuntos Internos Policial y Juicio de Nulidad de Infracción",
            "radiografia_empatica": (
                "Analicé tu situación vial. Estás enfrentando un **posible abuso de autoridad policial o de tránsito**: te detuvieron en la vía pública, "
                "te están reteniendo documentos (licencia, tarjeta de circulación o placa) o te están **amenazando con llevarse tu carro o moto al corralón con grúa** para presionarte a soltar dinero ('mordida')."
            ),
            "explicacion_sencilla_dinero": (
                "**¿Cuándo SÍ y cuándo NO se pueden llevar tu carro o moto al corralón?**\n\n"
                "Muchos policías usan la palabra *'Corralón'* como espantapájaros porque saben que el arrastre de grúa cuesta miles de pesos y así te asustan para que les des $1,000 o $2,500 en efectivo. **¡Que no te engañen!** En la mayoría de los Reglamentos de Tránsito de México:\n"
                "• **NO se pueden llevar tu vehículo al corralón** por una falta simple (como pasarte un alto, dar vuelta prohibida, traer un faro fundido o hablar por celular) si traes tus papeles vigentes.\n"
                "• **SÓLO procede corralón** en casos graves contados con los dedos: 1) Conducir en estado de ebriedad (alcoholímetro oficial), 2) Circular sin placas o con placas que no coinciden con el engomado/tarjeta, 3) Participar en un choque con heridos o daños a bienes públicos, o 4) Estacionarte bloqueando rampas de discapacitados o entradas de emergencia.\n"
                "• **¿Cualquiera puede multarte?:** ¡No! Un policía preventivo municipal o estatal en patrulla normal **no puede levantar multas de tránsito**; solo pueden hacerlo los agentes de Tránsito/Vialidad facultados (que suelen portar uniforme distintivo y terminal electrónica)."
            ),
            "fases_cronologicas": [
                {
                    "titulo_fase": "FASE 1: En los primeros 30 segundos cuando te marca el alto la patrulla",
                    "explicacion": (
                        "1. Oríllate en un lugar seguro e iluminado, apaga el motor, baja tu ventanilla solo a la mitad y pon tus manos visibles sobre el volante o manubrio.\n"
                        "2. **Pon tu celular a grabar video o audio de inmediato:** En México **es 100% legal grabar a cualquier policía en la calle** porque es un servidor público en funciones (protegido por el Artículo 6° y 7° de la Constitución). No le pongas el teléfono pegado a la cara para no provocarlo; graba desde tu asiento apuntando a tu ventanilla.\n"
                        "3. **No entregues tus documentos en su mano todavía:** Primero pídele que se identifique y te diga por qué te detuvo. Si le das tu licencia y tarjeta de circulación en los primeros 5 segundos, el mal policía las usa como 'rehén' y se las lleva a su patrulla para obligarte a bajar a negociar."
                    )
                },
                {
                    "titulo_fase": "FASE 2: Cómo desarmar la amenaza del corralón o la mordida (Minutos 2 al 10)",
                    "explicacion": (
                        "• Pídele con voz súper tranquila que te enseñe en su reglamento **qué artículo exacto cometiste y en qué artículo dice que esa falta amerita corralón**.\n"
                        "• Si te insinúa *'¿cómo nos arreglamos para no llamar a la grúa?'*, dile con firmeza que **no traes efectivo y que prefieres que te levante tu boleta de infracción oficial** para pagarla en la Tesorería con descuento (en casi todos los municipios te hacen 50% a 70% de descuento si pagas en los primeros días, o puedes anularla gratis en el Tribunal).\n"
                        "• Cuando el policía corrupto ve que estás grabando, que conoces la regla del corralón y que le estás pidiendo que escriba su nombre y firma en una boleta oficial, en el 90% de los casos te devuelve tus cosas y te dice *'ya váyase pues, que sea la última vez'*."
                    )
                },
                {
                    "titulo_fase": "FASE 3: ¿Qué hacer si ya te quitaron la placa/licencia o te levantaron la multa?",
                    "explicacion": (
                        "1. Anota o toma foto del **número económico de la patrulla** (viene pintado en las puertas y cajuela), la **hora exacta**, la **calle/esquina** y el **nombre del oficial**.\n"
                        "2. Si te levantaron una boleta de infracción injusta, **tienes 15 días hábiles para impugnarla gratis** ante el Tribunal de Justicia Administrativa de tu estado/municipio. Como el 80% de las boletas están mal llenadas por los policías, el Tribunal las declara nulas y te devuelven tu placa, licencia o dinero sin pagar un peso."
                    )
                },
                {
                    "titulo_fase": "FASE 4: Cómo denunciar al policía abusivo en Asuntos Internos",
                    "explicacion": (
                        "• Llama o acude a la **Unidad de Asuntos Internos / Contraloría de la Policía** o al **911 / 089** reportando el número de patrulla y la hora. Los policías le tienen pánico a una queja formal en Asuntos Internos porque les suspenden el sueldo y les abren expediente de destitución."
                    )
                }
            ],
            "guiones_dialogo": [
                {
                    "situacion": "🗣️ Qué decirle al policía en cuanto se acerca a tu ventanilla:",
                    "frase_exacta": "\"Buenas tardes, oficial. Antes de mostrarle mis documentos, ¿me puede indicar su nombre completo, número de patrulla y cuál es el artículo exacto del Reglamento de Tránsito por el que me detuvo? Estoy grabando por seguridad de ambos.\""
                },
                {
                    "situacion": "🗣️ Qué responderle si te amenaza con llamar a la grúa / corralón o te pide mordida:",
                    "frase_exacta": "\"Oficial, traigo mis documentos vigentes y no vengo en estado de ebriedad, por lo que el reglamento no autoriza remisión al corralón. No le voy a entregar dinero en efectivo; por favor levánteme la boleta de infracción oficial con su nombre y firma para revisarla en el Tribunal Administrativo o con Asuntos Internos.\""
                }
            ],
            "trampas_mortales": [
                "🚫 **TRAMPA 1 (Bajarte del carro a discutir o empujar al policía):** Jamás te bajes furioso ni toques físicamente al oficial. Si lo empujas o lo insultas, pasas de una simple falta de tránsito a que te esposen y te lleven al Ministerio Público por 'delitos contra servidores públicos'. Mantente sentado y tranquilo.",
                "🚫 **TRAMPA 2 (Darle tus papeles antes de que te diga el motivo):** Muéstralos primero a través del cristal para que vea que están vigentes, y solo entrégalos si es un agente de tránsito facultado que va a llenar la boleta oficial.",
                "🚫 **TRAMPA 3 (Permitir que revisen tu cajuela o mochila sin motivo):** Una revisión de rutina ('bájese para revisarle el carro y sus bolsas') sin orden judicial ni flagrancia de delito es inconstitucional (Art. 16 Constitucional). Di claramente en tu grabación: *'No doy mi consentimiento para que revisen mi vehículo'*."
            ],
            "glosario_sencillo": {
                "Boleta de Infracción Fundada y Motivada": "Significa que el policía está obligado a escribir exactamente qué artículo de la ley rompiste y cómo pasó. Si no lo escribe bien, la multa es nula.",
                "Garantía (Placa o Licencia)": "En algunos municipios retienen una placa o licencia para asegurar que pagues la multa, pero SOLO un agente de tránsito autorizado entregándote tu boleta oficial firmada puede hacerlo, nunca una patrulla común sin recibo.",
                "Juicio de Nulidad Administrativa": "Es un trámite sencillo y gratuito donde un juez administrativo cancela tu multa y obliga a Tránsito a devolverte tu placa o tu dinero."
            },
            "pasos_inmediatos": [
                "1. Grabar en video desde tu asiento el número de patrulla, rostro/gafete del oficial y la conversación.",
                "2. NO entregar dinero en efectivo ('mordida') ni dejarte intimidar con la amenaza falsa de corralón.",
                "3. Exigir que te indique el artículo exacto del Reglamento de Tránsito y, si procede, te entregue boleta oficial firmada.",
                "4. Reportar el número de patrulla a Asuntos Internos e impugnar la boleta en los primeros 15 días hábiles."
            ],
            "alerta_fatal": "¡NUNCA CAIGAS EN PROVOCACIONES FÍSICAS NI DES DINERO EN EFECTIVO! Graba todo con calma; tienes 15 días hábiles para anular cualquier multa ilegal en el Tribunal Administrativo."
        }

    elif categoria_caso == "Casos Familiares":
        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez de lo Familiar de Primera Instancia",
            "abogado": "Defensor Público Familiar / Procuraduría del DIF ($0 pesos) o Abogado Familiar",
            "profesionales": "Trabajador Social + Perito en Psicología adscrito al Juzgado",
            "medida_sugerida": "Fijación inmediata de Pensión Alimenticia Provisional y rastreo bancario ante el SAT/CNBV",
            "recurso_clave": "Demanda inicial de Alimentos y Guarda y Custodia",
            "radiografia_empatica": (
                "Analicé tu caso familiar. Estás enfrentando el **incumplimiento de pensión alimenticia (gasto de los hijos) y/o disputa de guarda y custodia**, "
                "incluyendo la maña común donde el deudor esconde su dinero o se sale de su trabajo formal para fingir que no tiene ingresos."
            ),
            "explicacion_sencilla_dinero": (
                "**¿Qué pasa si el papá o mamá de tus hijos dice que 'no tiene trabajo' para no dar gasto?**\n\n"
                "La ley mexicana protege primero a los niños por encima de cualquier pretexto:\n"
                "• Aunque se haya salido de su empleo formal para no aparecer en el IMSS, **el Juez Familiar tiene poder para pedirle a todos los bancos (vía Comisión Nacional Bancaria) y al SAT** la lista de todas sus tarjetas, transferencias y depósitos en efectivo.\n"
                "• Si no tiene cuenta de banco y cobra puro efectivo, el Juez le fija una pensión obligatoria basada en el **Salario Mínimo o en el nivel de vida** que han tenido los niños (usualmente del **15% al 20% por cada hijo**).\n"
                "• Además, dejar de pagar alimentos sin justificación es un **delito penal (abandono de obligaciones alimenticias)** y hace que lo metan al **Registro Nacional de Deudores Alimentarios**, donde le bloquean el trámite de pasaporte, licencia de conducir y créditos."
            ),
            "fases_cronologicas": [
                {
                    "titulo_fase": "FASE 1: ¿Qué papeles y pruebas juntar hoy en tu casa?",
                    "explicacion": (
                        "1. **Actas de nacimiento originales** de tus hijos y acta de matrimonio (si estuvieron casados).\n"
                        "2. **Lista y tickets de todo lo que gastan los niños al mes:** Supermercado, leche, ropa, colegiaturas, útiles, medicinas, renta, luz e internet.\n"
                        "3. **Datos del deudor:** Su nombre completo, CURP o RFC (si lo tienes), domicilio donde vive o trabaja, fotos de sus redes sociales donde presuma negocios, carros, viajes o fiestas, y el número de tarjeta o banco donde sabes que mueve dinero."
                    )
                },
                {
                    "titulo_fase": "FASE 2: Ir al Juzgado Familiar o DIF por tu 'Pensión Provisional' (Esta semana)",
                    "explicacion": (
                        "• No necesitas esperar un año de juicio para recibir dinero. En cuanto presentas tu solicitud con un defensor gratuito del **DIF / Defensoría de Oficio** o con tu abogado, el Juez dicta en los primeros días una **Pensión Alimenticia Provisional** obligatoria mientras dura el proceso."
                    )
                },
                {
                    "titulo_fase": "FASE 3: Investigación de ingresos ocultos y Guarda y Custodia",
                    "explicacion": (
                        "• El Juez manda oficios al IMSS, SAT y Bancos para congelar o descontar directamente el porcentaje de los niños, y te otorga la **Guarda y Custodia Provisional** para que nadie te pueda quitar a tus hijos por la fuerza."
                    )
                }
            ],
            "guiones_dialogo": [
                {
                    "situacion": "🗣️ Qué responder cuando tu expareja te amenaza con 'no te voy a dar un peso porque ya me salí de trabajar y te voy a quitar a los niños':",
                    "frase_exacta": "\"La pensión no es un favor para mí, es un derecho de nuestros hijos por ley. Aunque ocultes tu sueldo, el Juez Familiar va a revisar tus cuentas bancarias y tu nivel de vida, y la custodia solo la decide un Juez. Todo lo vamos a arreglar por escrito en el Juzgado Familiar.\""
                }
            ],
            "trampas_mortales": [
                "🚫 **TRAMPA 1 (Confiar en acuerdos de palabra):** Si te dice *'No me demandes, yo te doy $1,000 cuando pueda'*, te va a dar dos semanas y luego volverá a fallar. Todo acuerdo debe estar firmado ante el Juez Familiar.",
                "🚫 **TRAMPA 2 (Prohibirle ver a los niños como venganza sin orden del Juez):** No mezcles la pensión con las visitas por tu propia mano; pide primero al Juez la custodia provisional para que todo esté respaldado legalmente."
            ],
            "glosario_sencillo": {
                "Pensión Provisional": "Es el dinero urgente que el Juez ordena que te empiecen a pagar desde el inicio de la demanda, sin esperar a que termine el juicio.",
                "Guarda y Custodia": "Significa con quién viven y quién cuida todos los días a los hijos.",
                "Deudor Alimentario Moroso": "Persona que debe más de 90 días de pensión y queda boletinada a nivel nacional."
            },
            "pasos_inmediatos": [
                "1. Reunir actas de nacimiento de tus hijos y tickets/recibos de comida, escuela, médico y casa.",
                "2. Anotar el domicilio, trabajo, RFC/CURP y bancos donde el deudor recibe dinero.",
                "3. Acudir al DIF o Defensoría Familiar gratuita para pedir Pensión Alimenticia Provisional urgente.",
                "4. Solicitar al Juez que gire oficios al SAT y Comisión Bancaria para detectar ingresos ocultos."
            ],
            "alerta_fatal": "¡No te quedes esperando promesas verbales! Cada mes que no demandas es dinero para tus hijos que cuesta mucho más trabajo cobrar hacia atrás."
        }

    elif categoria_caso == "Casos Penales":
        return {
            "proceso": "Proceso Penal (8 Etapas)",
            "juez": "Juez de Control Penal / CONDUSEF (en caso de fraude bancario)",
            "abogado": "Asesor Jurídico de Víctimas / CONDUSEF ($0 pesos) o Abogado Penalista",
            "profesionales": "Fiscal del Ministerio Público + Perito en Informática Forense",
            "medida_sugerida": "Reporte inmediato de folio bancario, descarga de CEP Banxico y denuncia con sello SHA-256",
            "recurso_clave": "Reclamación en CONDUSEF y Querella Penal ante Fiscalía Ciberdelitos",
            "radiografia_empatica": (
                "Analicé tu emergencia penal/digital. Estás sufriendo un **Fraude Bancario (vaciado de cuenta por enlace falso/SPEI) o un delito que requiere preservar tus pruebas digitales intactas**."
            ),
            "explicacion_sencilla_dinero": (
                "**¿El banco está obligado a devolverte tu dinero si te vaciaron la cuenta?**\n\n"
                "¡Sí hay forma de recuperarlo! La Suprema Corte de Justicia de la Nación (SCJN) determinó que **los bancos tienen la obligación de cuidar los ahorros de sus clientes** y que, cuando ocurre una transferencia electrónica no reconocida, el banco no puede lavarse las manos diciendo *'fue tu culpa'* a menos que pruebe con peritajes técnicos que tú mismo autorizaste la operación de forma segura."
            ),
            "fases_cronologicas": [
                {
                    "titulo_fase": "FASE 1: Primeras 2 horas (Bloquear y rastrear a quién le cayó tu dinero)",
                    "explicacion": (
                        "1. Llama ya a tu banco, bloquea tu tarjeta/banca móvil y **exige que levanten un Folio de Aclaración por Transferencia o Cargo No Reconocido**. Anota el número de folio y el nombre de quien te atendió.\n"
                        "2. **El truco maestro para saber quién te robó (CEP de Banxico):** Entra a la página oficial de Banxico (`banxico.org.mx/cep`) con la fecha, monto y clave de rastreo de la transferencia que te robaron. Ahí podrás descargar el comprobante oficial que revela el **nombre completo y RFC real del delincuente** que recibió tu dinero."
                    )
                },
                {
                    "titulo_fase": "FASE 2: Preservar tu celular sin borrar nada (Primeras 24 horas)",
                    "explicacion": (
                        "• **No borres el mensaje de texto (SMS), WhatsApp ni el historial de llamadas** donde entró el enlace falso. Toma capturas de pantalla completas (sin recortar la hora de arriba) y guárdalas."
                    )
                },
                {
                    "titulo_fase": "FASE 3: Queja gratuita en CONDUSEF y Denuncia en Fiscalía",
                    "explicacion": (
                        "• Si el banco te responde que 'tu reclamo no procede', entra al portal de la **CONDUSEF** (es 100% gratis). Ahí citan al banco y te dan un dictamen técnico para obligarlos a devolverte tu dinero más intereses."
                    )
                }
            ],
            "guiones_dialogo": [
                {
                    "situacion": "🗣️ Qué decirle al ejecutivo del banco por teléfono:",
                    "frase_exacta": "\"Quiero reportar transferencias electrónicas que yo jamás autoricé ni reconozco. Solicito el bloqueo preventivo de mi cuenta y que me proporcione en este momento mi número de folio de aclaración por cargos no reconocidos para presentarlo ante la CONDUSEF.\""
                }
            ],
            "trampas_mortales": [
                "🚫 **TRAMPA 1 (Borrar el chat o formatear el celular por miedo):** Si borras el mensaje donde te engañaron, destruyes la prueba principal para el Ministerio Público.",
                "🚫 **TRAMPA 2 (Rendirse cuando el banco te dice que 'no procede'):** Los bancos rechazan por sistema el primer reclamo esperando que la gente se rinda; el verdadero cobro se logra al llevar ese rechazo a la CONDUSEF."
            ],
            "glosario_sencillo": {
                "CEP de Banxico": "Es el recibo oficial del Banco de México que te dice el nombre y RFC real de la persona a la que le llegó tu dinero robado.",
                "Sello Criptográfico SHA-256": "Es una huella digital única que genera esta aplicación para demostrar ante un juez que tu relato y tus pruebas no fueron alterados."
            },
            "pasos_inmediatos": [
                "1. Llamar al banco para bloquear la cuenta y exigir Folio de Aclaración por Cargo No Reconocido.",
                "2. Descargar el comprobante CEP en la página de Banxico para obtener nombre y RFC del receptor.",
                "3. NO borrar los mensajes SMS/WhatsApp falsos y tomar capturas de pantalla completas.",
                "4. Presentar queja gratuita en CONDUSEF y denuncia en Fiscalía con los datos del CEP."
            ],
            "alerta_fatal": "¡No borres los mensajes de tu teléfono ni aceptes un 'no procede' del banco sin ir a la CONDUSEF!"
        }

    elif categoria_caso == "Casos Civiles":
        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez Civil de Primera Instancia / CONDUSEF y Policía Cibernética (en cobranza abusiva)",
            "abogado": "Abogado Litigante Civil o Defensoría Pública Civil ($0 pesos)",
            "profesionales": "Actuario Judicial + Notario / Mediador Certificado",
            "medida_sugerida": "Demanda de Controversia de Arrendamiento y Embargo de Bienes / Denuncia por Cobranza Ilegítima",
            "recurso_clave": "Juicio de Desocupación y Cobro de Rentas / Denuncia Penal Art. 284 Bis (Cobranza Ilegítima)",
            "radiografia_empatica": (
                "Analicé tu problema civil/patrimonial. Se trata de un **conflicto de arrendamiento (inquilino que no paga y no se sale) o de amenazas ilegales por deudas y despachos de cobranza**."
            ),
            "explicacion_sencilla_dinero": (
                "**Dos verdades legales que todo ciudadano debe saber en materia civil:**\n\n"
                "1. **Si tienes un inquilino que no te paga la renta:** La única forma legal de sacarlo es con una orden del Juez Civil. Si tú vas con un cerrajero, le cambias la chapa o le sacas sus muebles a la banqueta, **el inquilino moroso te puede meter a la cárcel a ti por el delito de Despojo**.\n"
                "2. **Si te amenazan por una deuda o préstamo de aplicación:** En México (Artículo 17 de la Constitución), **nadie puede ir a la cárcel por deber dinero civil o bancario**, y ningún cobrador de WhatsApp puede llegar mañana a embargarte tu casa sin que antes exista un juicio donde te notifique un Actuario oficial del Juzgado con identificación."
            ),
            "fases_cronologicas": [
                {
                    "titulo_fase": "FASE 1: Qué hacer hoy mismo según tu caso",
                    "explicacion": (
                        "• **Si eres dueño de casa rentada:** Busca tu contrato de arrendamiento (y si no hiciste contrato escrito, junta los recibos de transferencia, mensajes de WhatsApp donde le cobras la renta y testigos).\n"
                        "• **Si te acosan cobradores o apps de préstamos:** Pon tus redes sociales en privado, avisa a tus contactos que tu teléfono sufrió robo de datos por una app fraudulenta y **bloquea/reporta** los números ante la Policía Cibernética y REDECO de CONDUSEF."
                    )
                },
                {
                    "titulo_fase": "FASE 2: Promover el trámite ante el Juez Civil o Centro de Mediación",
                    "explicacion": (
                        "• En arrendamiento, el Juez Civil admite tu demanda, ordena requerir el pago de todas las rentas atrasadas y le fija un plazo forzoso al inquilino para entregar las llaves o ser desalojado legalmente con fuerza pública."
                    )
                }
            ],
            "guiones_dialogo": [
                {
                    "situacion": "🗣️ Qué responderle a un cobrador agresivo que amenaza con 'ir mañana a embargar y romper cerraduras':",
                    "frase_exacta": "\"Sé perfectamente que en México ningún despacho privado puede embargar sin orden de un Juez y presencia de un Actuario judicial. Sus amenazas y papeles falsos constituyen el delito de Cobranza Ilegítima (Art. 284 Bis del Código Penal). Estoy guardando estas capturas para denunciarlos en Fiscalía y CONDUSEF.\""
                }
            ],
            "trampas_mortales": [
                "🚫 **TRAMPA 1 (Cortarle el agua, la luz o cambiarle la chapa a tu inquilino):** Aunque sea tu propia casa, no lo hagas por tu cuenta sin orden del Juez; le darías armas al inquilino para denunciarte por despojo.",
                "🚫 **TRAMPA 2 (Pedir otro préstamo en otra app ilegal para pagar la primera):** Las apps 'montadeudas' nunca dejan de extorsionar aunque les pagues; repórtalas al 089 y Policía Cibernética."
            ],
            "glosario_sencillo": {
                "Lanzamiento Judicial": "Es cuando el Juez manda al Actuario y a la policía para sacar legalmente al inquilino que no quiso salirse por las buenas.",
                "Cobranza Ilegítima": "Es el delito que cometen los cobradores cuando usan insultos, amenazas, sellos falsos de juzgados o molestan a tus familiares y amigos."
            },
            "pasos_inmediatos": [
                "1. Reunir contrato, transferencias y mensajes de WhatsApp que comprueben el adeudo o las amenazas.",
                "2. NO hacer justicia por propia mano (no cambiar chapas ni cortar servicios sin orden del Juez).",
                "3. Si es cobranza abusiva, recordar que nadie puede embargarte por WhatsApp y reportar a REDECO/Policía Cibernética.",
                "4. Acudir al Juzgado Civil o Centro de Mediación Pública para iniciar el juicio legal."
            ],
            "alerta_fatal": "¡Jamás te metas por la fuerza al inmueble rentado ni creas en 'embargos por WhatsApp' sin orden de un Juez!"
        }

    else:
        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez Mercantil",
            "abogado": "Abogado Litigante Mercantil",
            "profesionales": "Actuario Ejecutor + Perito en Grafoscopía",
            "medida_sugerida": "Juicio Ejecutivo Mercantil con embargo de bienes desde la primera visita",
            "recurso_clave": "Demanda Ejecutiva Mercantil (Auto de Exequendo)",
            "radiografia_empatica": (
                "Analicé tu caso mercantil. Tienes un **pagaré, cheque o deuda comercial vencida** y la persona que te debe se esconde o se niega a pagarte."
            ),
            "explicacion_sencilla_dinero": (
                "**¿Por qué un Pagaré firmado tiene tanta fuerza legal?**\n\n"
                "Un pagaré es un documento especial que en la ley se llama *'Título que trae aparejada ejecución'*. En español simple: **con un pagaré no tienes que esperar un año de juicio para ver si el juez te da permiso de embargar**. Desde el primer día que metes la demanda, el Juez ordena que el Actuario vaya al domicilio del deudor a cobrarle y, si no paga en ese instante, **le embargan su carro, mercancía, cuentas o bienes ahí mismo**."
            ),
            "fases_cronologicas": [
                {
                    "titulo_fase": "FASE 1: Cuidar el pagaré original como oro",
                    "explicacion": (
                        "• Guarda el pagaré original en una mica protectora. **Por ningún motivo le anotes nada encima con otra pluma**, ni le remarques la fecha ni los intereses después de que te lo firmaron, porque si usas dos tintas diferentes el deudor puede meter un perito y anular el pagaré por alteración."
                    )
                },
                {
                    "titulo_fase": "FASE 2: Diligencia de requerimiento de pago y embargo",
                    "explicacion": (
                        "• Ubica qué bienes tiene el deudor (placas de su vehículo, negocio o casa) y acude con un abogado mercantil para presentar la demanda antes de que pasen **3 años** desde que venció el pagaré."
                    )
                }
            ],
            "guiones_dialogo": [
                {
                    "situacion": "🗣️ Último aviso formal antes de meter el embargo con el Actuario:",
                    "frase_exacta": "\"Te informo que el pagaré que me firmaste ya se encuentra vencido. Te doy de plazo hasta el viernes para liquidar por las buenas; de lo contrario, la próxima semana acudiré directamente con el Actuario del Juzgado Mercantil a realizar el embargo de bienes en tu domicilio por la deuda más los intereses y gastos del juicio.\""
                }
            ],
            "trampas_mortales": [
                "🚫 **TRAMPA 1 (Rellenar espacios vacíos con otra tinta frente al deudor o después):** Si el pagaré tenía espacios en blanco, asesórate antes de tocarlo.",
                "🚫 **TRAMPA 2 (Entregar el pagaré original a cambio de una promesa):** Nunca sueltes el papel original hasta que el dinero ya esté firme en tus manos o en tu cuenta."
            ],
            "glosario_sencillo": {
                "Auto de Exequendo": "Es la orden del Juez que permite ir a embargarle cosas al deudor desde la primera visita a su casa o negocio.",
                "Interés Moratorio": "Es el dinero extra que se va sumando cada mes por haberse tardado en pagarte después de la fecha prometida."
            },
            "pasos_inmediatos": [
                "1. Resguardar el pagaré o documento original intacto, sin hacerle rayones ni anotaciones con otra pluma.",
                "2. Ubicar el domicilio exacto del deudor y qué bienes tiene a su nombre (vehículos, local, cuentas).",
                "3. Iniciar Juicio Ejecutivo Mercantil solicitando embargo desde la primera diligencia.",
                "4. No entregar jamás el pagaré original hasta haber recibido el pago completo."
            ],
            "alerta_fatal": "¡No alteres el pagaré con otra pluma ni dejes pasar 3 años desde su vencimiento!"
        }

# ==============================================================================
# 7. AGENTE DE BÚSQUEDA EN VIVO EN INTERNET Y RED NEURONAL EVOLUTIVA
# ==============================================================================
def buscar_informacion_juridica_en_internet(categoria_caso: str, tipo_caso: str, relato_usuario: str) -> dict:
    resultados_web = []
    textos_para_entrenar = []

    termino_wiki = f"{tipo_caso} derecho México"
    if categoria_caso == "Tránsito, Multas y Abuso Policial":
        termino_wiki = "Reglamento de tránsito infracción México derechos"

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
                    "fuente": "📖 Enciclopedia Jurídica / Wikipedia",
                    "titulo": titulo_w,
                    "resumen": snip_w,
                    "url": link_w
                })
                textos_para_entrenar.append(f"{titulo_w} {snip_w}")
    except Exception:
        pass

    palabras_clave_busqueda = f"{tipo_caso} ley derechos Mexico"
    if categoria_caso == "Casos Laborales":
        palabras_clave_busqueda = "despido injustificado liquidacion Ley Federal del Trabajo PROFEDET Mexico"
    elif categoria_caso == "Tránsito, Multas y Abuso Policial":
        palabras_clave_busqueda = "multas de transito corralon abuso policial reglamento Mexico derechos"
    elif categoria_caso == "Casos Familiares":
        palabras_clave_busqueda = "pension alimenticia guarda custodia Juez Familiar Mexico"

    try:
        url_gnews = (
            "https://news.google.com/rss/search?"
            f"q={urllib.parse.quote(palabras_clave_busqueda)}&hl=es-419&gl=MX&ceid=MX:es-419"
        )
        req_g = urllib.request.Request(url_gnews, headers={"User-Agent": "ForensicMindLegalBot/8.0"})
        with urllib.request.urlopen(req_g, timeout=4.5) as resp_g:
            xml_data = resp_g.read()
            root = ET.fromstring(xml_data)
            for it in root.findall(".//item")[:3]:
                tit = it.find("title").text if it.find("title") is not None else "Criterio Jurídico en Línea"
                lnk = it.find("link").text if it.find("link") is not None else "https://www.scjn.gob.mx"
                pub = it.find("pubDate").text[:16] if it.find("pubDate") is not None else "Reciente"
                resultados_web.append({
                    "fuente": f"🌐 Google Noticias Jurídicas México ({pub})",
                    "titulo": tit,
                    "resumen": f"Noticia o criterio reciente aplicable a {categoria_caso} ({tipo_caso}).",
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
    fuente: str = "Consulta Ciudadana / Voz",
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

    vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=2500)
    X_vec = vectorizer.fit_transform(textos_entrenamiento)

    mlp = MLPClassifier(hidden_layer_sizes=(96, 48), activation='relu', max_iter=500, random_state=42)
    mlp.fit(X_vec, etiquetas_entrenamiento)

    stats_modelo = {
        "total_muestras": len(textos_entrenamiento),
        "experiencias_aprendidas": len(df_mem),
        "vocabulario_ngramas": len(vectorizer.vocabulary_)
    }
    return vectorizer, mlp, stats_modelo

def autoclasificar_caso_con_red_neuronal(relato: str, vectorizer_mlp, modelo_mlp) -> dict:
    relato_expandido = expandir_lenguaje_coloquial(relato)
    texto_low = relato_expandido.lower()

    scores_ramas = {
        "Casos Laborales": 0,
        "Tránsito, Multas y Abuso Policial": 0,
        "Casos Familiares": 0,
        "Casos Penales": 0,
        "Casos Civiles": 0,
        "Casos Mercantiles": 0
    }

    reglas_puntaje = {
        "Casos

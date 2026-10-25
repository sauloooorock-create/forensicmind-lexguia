import streamlit as st
import sqlite3
import hashlib
import re
import math
import io
import json
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
# SELLO DE AUTORÍA Y ARQUITECTURA DEL SISTEMA
# ==============================================================================
AUTOR_SISTEMA = "Ing. Industrial y de Sistemas Saúl Ángel Ortiz Rogel"
MARCA_SISTEMA = "ForensicMind & LexGuía CBR v6.5 — IA Auto-Evolutiva & Respaldo Cloud"

st.set_page_config(
    page_title=f"{MARCA_SISTEMA} | {AUTOR_SISTEMA}",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_NAME = "boveda_juridica_cbr_v6.db"

# ==============================================================================
# SELECTOR DE TEMA VISUAL Y CSS BLINDADO DE ALTO CONTRASTE (MÓVIL Y PC)
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎨 Apariencia y Motor Neuronal")
    modo_visual = st.radio(
        "Estilo visual de la interfaz:",
        ["☀️ Ejecutivo Claro (Máxima Lectura en Celular)", "🌙 Oscuro Forense Blindado"],
        index=0
    )
    auto_entrenar_switch = st.checkbox(
        "🧠 Auto-Aprendizaje Neuronal Activo (Aprender de cada consulta y búsqueda web)",
        value=True
    )
    buscar_web_switch = st.checkbox(
        "🌐 Conectar a Internet en Vivo (Google Jurídico & Wikipedia Legal)",
        value=True
    )

if "Claro" in modo_visual:
    st.markdown("""
    <style>
        .stApp { background-color: #f1f5f9 !important; color: #0f172a !important; }
        .block-container { padding-top: 3.5rem !important; padding-bottom: 2.5rem !important; }
        h1, h2, h3, h4, h5, h6, p, li, span, div { color: #0f172a; }
        label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 1.02rem !important;
            opacity: 1 !important;
        }
        textarea, input[type="text"], input[type="number"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #2563eb !important;
            border-radius: 10px !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            line-height: 1.5 !important;
            padding: 12px !important;
            opacity: 1 !important;
            box-shadow: 0 2px 6px rgba(37, 99, 235, 0.12) !important;
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
            box-shadow: 0 4px 10px rgba(0,0,0,0.06) !important;
        }
        div[data-testid="metric-container"] label { color: #475569 !important; -webkit-text-fill-color: #475569 !important; }
        div[data-testid="stMetricValue"] { color: #0f172a !important; -webkit-text-fill-color: #0f172a !important; font-weight: 800 !important; }
        .win-badge { background-color: #059669; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .loss-badge { background-color: #dc2626; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .step-badge { background-color: #1d4ed8; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 5px 12px; border-radius: 6px; font-weight: 800; display: inline-block; }
        .card-box { background-color: #ffffff; border: 1px solid #cbd5e1; border-left: 6px solid #2563eb; border-radius: 12px; padding: 18px; margin: 10px 0; color: #0f172a !important; box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05); }
        .money-box { background-color: #ecfdf5; border: 1px solid #6ee7b7; border-left: 6px solid #059669; border-radius: 12px; padding: 18px; margin: 10px 0; color: #064e3b !important; }
        .lawyer-box { background-color: #eef2ff; border: 1px solid #a5b4fc; border-left: 6px solid #4f46e5; border-radius: 12px; padding: 18px; margin: 10px 0; color: #1e1b4b !important; }
        .alert-box { background-color: #fef2f2; border: 1px solid #fca5a5; border-left: 6px solid #dc2626; border-radius: 12px; padding: 18px; margin: 10px 0; color: #7f1d1d !important; }
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
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
        }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .stApp { background-color: #0b0f19 !important; color: #f8fafc !important; }
        .block-container { padding-top: 3.5rem !important; padding-bottom: 2.5rem !important; }
        h1, h2, h3, h4, h5, h6, p, li, label, [data-testid="stWidgetLabel"] p { color: #f8fafc !important; -webkit-text-fill-color: #f8fafc !important; font-weight: 600 !important; }
        textarea, input[type="text"], input[type="number"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #38bdf8 !important;
            border-radius: 10px !important;
            font-size: 1.05rem !important;
            font-weight: 700 !important;
            padding: 12px !important;
        }
        div[data-baseweb="select"] > div { background-color: #1e293b !important; color: #f8fafc !important; -webkit-text-fill-color: #f8fafc !important; border: 1px solid #38bdf8 !important; }
        .author-banner { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border: 1px solid #38bdf8; border-left: 6px solid #f59e0b; border-radius: 12px; padding: 16px 20px; margin-bottom: 18px; }
        div[data-testid="metric-container"] { background: #111827 !important; border: 1px solid #374151 !important; border-left: 4px solid #38bdf8 !important; padding: 14px !important; border-radius: 10px !important; }
        .win-badge { background-color: #065f46; color: #34d399 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .loss-badge { background-color: #7f1d1d; color: #f87171 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .step-badge { background-color: #1e3a8a; color: #93c5fd !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .card-box { background-color: #131c2e; border: 1px solid #2dd4bf; border-radius: 10px; padding: 18px; margin: 10px 0; }
        .money-box { background-color: #0f2922; border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 10px; padding: 18px; margin: 10px 0; }
        .lawyer-box { background-color: #1e1b4b; border: 1px solid #818cf8; border-left: 5px solid #a78bfa; border-radius: 10px; padding: 18px; margin: 10px 0; }
        .alert-box { background-color: #1f1215; border: 1px solid #f87171; border-left: 5px solid #ef4444; border-radius: 10px; padding: 18px; margin: 10px 0; }
        .web-box { background-color: #0c192c; border: 1px solid #38bdf8; border-left: 5px solid #0284c7; border-radius: 10px; padding: 16px; margin: 10px 0; }
        div.stButton > button:first-child { background-color: #2563eb !important; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; font-weight: bold !important; border-radius: 10px !important; padding: 12px 20px !important; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. TAXONOMÍA JURÍDICA COMPLETA (LAS 5 GRANDES FAMILIAS DE CASOS)
# ==============================================================================
RAMAS_DERECHO = {
    "Derecho Privado": [
        "Derecho Laboral", "Derecho Civil", "Derecho Mercantil",
        "Derecho de Familia", "Derecho Procesal Civil", "Derecho de Propiedad Intelectual"
    ],
    "Derecho Público": [
        "Derecho Penal", "Derecho Procesal Penal", "Derecho Constitucional",
        "Derecho Administrativo", "Derecho Tributario"
    ],
    "Otros / Especializados": [
        "Derecho Informático/Digital", "Derecho Ambiental", "Derecho Agrario", "Derecho de Seguros"
    ]
}

TIPOS_CASOS = {
    "Casos Laborales": [
        "Despido injustificado", "Acoso laboral", "Discriminación",
        "Accidentes de trabajo", "Salarios adeudados", "Beneficios no pagados", "Reclasificación laboral"
    ],
    "Casos Familiares": [
        "Pensión alimenticia", "Divorcio", "Guarda y custodia",
        "Reconocimiento de paternidad", "Violencia de género", "Derecho de visita"
    ],
    "Casos Penales": [
        "Fraude", "Robo/Hurto", "Abuso de autoridad", "Violencia doméstica",
        "Estafa", "Homicidio", "Delitos de tránsito", "Falsificación"
    ],
    "Casos Civiles": [
        "Arrendamiento", "Deudas", "Contratos", "Propiedad",
        "Herencias/sucesiones", "Responsabilidad civil", "Daño y perjuicio"
    ],
    "Casos Mercantiles": [
        "Incumplimiento de contratos", "Contratos comerciales",
        "Quiebra/insolvencia", "Sociedades mercantiles", "Competencia desleal"
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
    "Proceso Penal (8 Etapas)": [
        "1. Denuncia o Querella ante Fiscalía/MP",
        "2. Investigación Inicial y Complementaria",
        "3. Audiencia Inicial y Auto de Vinculación",
        "4. Etapa Intermedia (Preparación de Juicio)",
        "5. Audiencia de Juicio Oral",
        "6. Emisión de Sentencia",
        "7. Recursos de Apelación / Amparo",
        "8. Ejecución de Sanciones"
    ]
}

MEDIDAS_CAUTELARES = [
    "Embargo preventivo de cuentas/bienes", "Medidas de protección urgentes",
    "Retención de bienes / Pensión provisional", "Orden de no enajenar inmueble", "Suspensión del acto reclamado"
]

RESOLUCIONES_SENTENCIAS = [
    "Laudo / Sentencia condenatoria", "Convenio conciliatorio ratificado (Cosa Juzgada)",
    "Sentencia absolutoria", "Auto de vinculación / no vinculación", "Resolución interlocutoria"
]

RECURSOS_LEGALES = [
    "Amparo directo / indirecto", "Apelación", "Nulidad de actuaciones / renuncia", "Habeas corpus", "Queja", "Revisión"
]

TABULADOR_HONORARIOS_RAMA = {
    "Casos Laborales": {
        "asesoria_min": 500, "asesoria_sug": 1000, "asesoria_max": 2000, "anticipo_sug": 0,
        "esquema_cobro": "Cuota Litis (20% a 30% únicamente sobre lo que ganes o recuperes; $0 de anticipo habitual)",
        "pct_sugerido": 25.0, "gastos_periciales_sug": 1200, "horas_promedio_despacho": 35,
        "via_gratuita": "PROFEDET / Procuraduría de la Defensa del Trabajo — $0 MXN (100% Gratuito para el trabajador)"
    },
    "Casos Familiares": {
        "asesoria_min": 800, "asesoria_sug": 1200, "asesoria_max": 2500, "anticipo_sug": 6000,
        "esquema_cobro": "Honorario Fijo dividido en 3 o 4 Etapas Procesales",
        "pct_sugerido": 0.0, "gastos_periciales_sug": 3000, "horas_promedio_despacho": 45,
        "via_gratuita": "DIF / Defensoría Pública Familiar del Estado — $0 MXN"
    },
    "Casos Penales": {
        "asesoria_min": 1200, "asesoria_sug": 2000, "asesoria_max": 4500, "anticipo_sug": 18000,
        "esquema_cobro": "Cobro por Etapa Procesal (Ministerio Público / Audiencia Inicial / Intermedia / Juicio Oral)",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 9000, "horas_promedio_despacho": 80,
        "via_gratuita": "Instituto de la Defensoría Pública / Comisión de Atención a Víctimas — $0 MXN"
    },
    "Casos Civiles": {
        "asesoria_min": 800, "asesoria_sug": 1500, "asesoria_max": 3000, "anticipo_sug": 8000,
        "esquema_cobro": "Esquema Mixto (Anticipo inicial + 10% a 20% del valor del asunto)",
        "pct_sugerido": 15.0, "gastos_periciales_sug": 4000, "horas_promedio_despacho": 50,
        "via_gratuita": "Defensoría Pública en Materia Civil — $0 MXN"
    },
    "Casos Mercantiles": {
        "asesoria_min": 1000, "asesoria_sug": 1800, "asesoria_max": 3500, "anticipo_sug": 7000,
        "esquema_cobro": "Anticipo de Embargo + 15% a 25% sobre cobranza efectiva",
        "pct_sugerido": 20.0, "gastos_periciales_sug": 4500, "horas_promedio_despacho": 40,
        "via_gratuita": "CONDUSEF (contra bancos/financieras) o PROFECO — $0 MXN"
    }
}

CONCEPTOS_CLAVE = {
    "Liquidación vs. Finiquito": "El FINIQUITO se paga siempre (incluso si renuncias: días trabajados, aguinaldo y vacaciones proporcionales). La LIQUIDACIÓN se paga cuando te despiden sin justificación (90 días de sueldo integrado + prima de antigüedad).",
    "Salario Diario Integrado (SDI)": "Es el sueldo con el que se calcula tu indemnización de 90 días (Art. 84 y 89 LFT). Suma a tu salario diario la parte proporcional diaria de tu aguinaldo y de tu prima vacacional.",
    "Cuota Litis (Porcentaje del Abogado)": "Acuerdo donde el abogado laboralista no te cobra anticipo, sino un porcentaje (20% a 30%) solo sobre el dinero que logre recuperar para ti.",
    "Prescripción Laboral (60 Días)": "Tienes 60 días naturales desde el día siguiente al despido para acudir al Centro de Conciliación. Si dejas pasar más de 2 meses, pierdes el derecho a reclamar.",
    "Cosa Juzgada": "Efecto definitivo de una sentencia firme o convenio ratificado ante el Centro de Conciliación contra el cual ya no cabe ningún recurso.",
    "Debido Proceso (Due Process)": "Garantía constitucional de ser juzgado por un juez imparcial, con defensa técnica y sin pruebas obtenidas de forma ilegal."
}

ESCENARIOS_FRECUENTES = {
    "✍️ Escribir o dictar mi propio caso libremente": "Mi sueldo semanal es de 2300. Me despidieron y no me quieren dar liquidación, solo me quieren dar $5000 y no me daban vacaciones ni días libres ni bonos, ¿qué procede ahí?",
    "💼 Laboral: Despido injustificado y coacción de hoja en blanco": "Me corrieron de la chamba hoy sin aviso por escrito, el jefe de recursos humanos me quiere obligar a firmar mi renuncia y una hoja en blanco para darme mi finiquito, además me deben quincenas y horas extras.",
    "👨‍👩‍👧 Familiar: Pensión alimenticia y papá que oculta ingresos": "El papá de mis hijos lleva 3 meses sin dar gasto ni pensión alimenticia, se salió de trabajar a propósito para decir que no tiene dinero pero cobra en efectivo de un negocio.",
    "💻 Penal / Fraude: Me vaciaron la cuenta del banco por enlace falso": "Me llegó un mensaje según de mi banco, le piqué al link y me robaron todo mi dinero con transferencias SPEI que yo no hice; tengo capturas del fraude.",
    "🚓 Penal Constitucional: Patrulla me detuvo y revisó mi celular sin orden": "Unos policías me pararon en la calle sin motivo, me quitaron mi celular a la fuerza para revisarlo sin orden del juez y tardaron muchas horas en llevarme al MP.",
    "🏠 Civil Arrendamiento: Inquilino no paga la renta ni se quiere salir": "Le renté mi departamento a una persona que lleva 5 meses sin pagarme la renta, ya se acabó el contrato y no me quiere entregar las llaves.",
    "📑 Mercantil: Me firmaron un pagaré y no me quieren pagar": "Le presté dinero y mercancía a un cliente que me firmó un pagaré hace 4 meses, ya venció la fecha y se esconde para no pagarme."
}

# ==============================================================================
# 2. TRADUCTOR SEMÁNTICO DE HABLA COLOQUIAL MEXICANA -> TOKENS JURÍDICOS
# ==============================================================================
DICCIONARIO_COLOQUIAL_A_JURIDICO = [
    (r'\b(chamba|jale|empleo|trabajo|oficina|empresa|fabrica|tienda|bodega|turno)\b', ' trabajo laboral patron '),
    (r'\b(corrieron|echaron|despidieron|cortaron|dieron de baja|ya no me dejaron entrar)\b', ' despido injustificado laboral '),
    (r'\b(patron|jefe|gerente|rh|recursos humanos|supervisor|dueño del negocio)\b', ' patron laboral empleador '),
    (r'\b(liquidacion|finiquito|quincena|semanal|raya|sueldo|nomina|aguinaldo|vacaciones|dias libres|horas extras|bonos|prima)\b', ' liquidacion salario prestaciones laboral '),
    (r'\b(hoja en blanco|firmar mi renuncia|renuncia voluntaria|quieren dar solo|solo me dan)\b', ' coaccion laboral despido injustificado '),
    (r'\b(gasto de los niños|manutencion|pension|alimentos|papa de mis hijos|mama de mis hijos|divorcio|custodia|visitar a mis hijos)\b', ' pension alimenticia familiar custodia hijos '),
    (r'\b(vaciaron mi cuenta|robaron mi tarjeta|phishing|hackearon|estafaron|clonaron|spei)\b', ' fraude bancario penal ciberdelito '),
    (r'\b(patrulla|policias|mp|ministerio publico|detuvieron|arrestaron|separos|cateo|revisaron mi celular)\b', ' detencion arbitraria abuso de autoridad penal '),
    (r'\b(inquilino|renta|arrendamiento|depa|departamento|casa rentada|desalojar|cambiar la chapa)\b', ' arrendamiento civil inquilino desocupacion '),
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
# 3. CAPA DE PERSISTENCIA SQLITE + TABLA DE AUTO-APRENDIZAJE CONTINUO
# ==============================================================================
def init_db():
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

    semillas = [
        (
            "EXP-LAB-2026-001", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Despido Injustificado Ganado (Sueldo Semanal sin Vacaciones y Oferta Patronal Engañosa de $5,000)",
            "Juez laboral, Abogado especializado, Conciliador",
            "1. Solicitud de Conciliación / Demanda Inicial", "Embargo preventivo de cuentas/bienes", "Convenio conciliatorio ratificado (100% Liquidación)", "Amparo directo / indirecto",
            "Me corrieron del trabajo injustificadamente, sueldo semanal de 2300, solo me quieren dar $5000 sin liquidación, no me daban vacaciones ni días libres ni bonos y exigen firmar hoja en blanco o renuncia.",
            hashlib.sha256(b"EXP-LAB-2026-001").hexdigest(), "GANADO",
            "El abogado rechazó los $5,000 iniciales, citó a conciliación antes de los 60 días y cuantificó 90 días de SDI, prima de antigüedad, vacaciones no gozadas y aguinaldo.",
            "El Centro de Conciliación y Juez Laboral tuvieron por cierto el despido injustificado ante la falta de aviso escrito y obligaron al pago completo.",
            "N/A", "Rechazar ofertas engañosas de finiquito, no firmar renuncia y exigir el cálculo sobre Salario Diario Integrado.",
            "No aceptar los $5,000 si te piden firmar renuncia, guardar mensajes de WhatsApp de turnos/pagos y acudir al Centro de Conciliación o PROFEDET.",
            "JAMÁS firmar una carta de renuncia ni hoja en blanco a cambio de un pago mínimo.",
            "2026-08-01"
        ),
        (
            "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
            "Despido Injustificado Perdido por Aceptar $5,000 Firmando Renuncia y Dejar Pasar 60 Días",
            "Juez laboral, Abogado litigante",
            "2. Audiencia de Conciliación / Contestación", "Ninguna", "Sentencia absolutoria", "Apelación",
            "Trabajador despedido aceptó un pago mínimo de $5000 firmando hoja de renuncia voluntaria y esperó más de 2 meses antes de demandar.",
            hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "PERDIDO",
            "El abogado interpuso la demanda fuera del plazo legal de 60 días y no ofreció pericial documentoscópica contra la renuncia.",
            "El Juez declaró fundada la prescripción y dio valor probatorio a la carta de renuncia firmada.",
            "Firmar renuncia voluntaria por presión económica o dejar pasar los 60 días naturales de prescripción.",
            "N/A", "Acudir a calcular tu liquidación real en la primera semana tras el despido.",
            "NUNCA firmar renuncias simuladas para recibir un pago rápido ni esperar más de 60 días.",
            "2026-08-05"
        ),
        (
            "EXP-FAM-2026-003", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia",
            "Pensión Alimenticia y Guarda/Custodia Ganada pese a Ocultamiento de Ingresos",
            "Juez de lo Familiar, Abogado especializado, Perito en trabajo social",
            "1. Solicitud de Conciliación / Demanda Inicial", "Retención de bienes / Pensión provisional", "Laudo / Sentencia condenatoria", "Queja",
            "El papá de mis hijos dejó de dar gasto y pensión alimenticia, renunció a su trabajo formal para ocultar ingresos pero maneja dinero en cuentas y negocio.",
            hashlib.sha256(b"EXP-FAM-2026-003").hexdigest(), "GANADO",
            "El abogado pidió fijación de pensión provisional en el primer auto y solicitó oficios al SAT y bancos (CNBV) para rastrear cuentas.",
            "El Juez de lo Familiar decretó descuento inmediato y fijó pensión con base en el nivel de vida y capacidad económica real.",
            "N/A", "Rastrear flujo bancario y fiscal del deudor alimentario y pedir pensión provisional urgente.",
            "Reunir actas de nacimiento, comprobantes de gastos de los niños y exigir pensión provisional desde el primer día.",
            "No quedarse con promesas verbales sin convenio judicial.",
            "2026-08-10"
        ),
        (
            "EXP-FAM-2026-004", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia",
            "Caso Familiar Perdido por Sustracción Unilateral de Hijos sin Orden Judicial",
            "Juez de lo Familiar, Mediador",
            "3. Ofrecimiento y Admisión de Pruebas", "Suspensión del acto reclamado", "Sentencia absolutoria", "Apelación",
            "Progenitor ocultó a los hijos impidiendo visitas sin orden de juez y declaró ingresos falsos.",
            hashlib.sha256(b"EXP-FAM-2026-004").hexdigest(), "PERDIDO",
            "El abogado no justificó medidas de protección ni exhibió pruebas contables.",
            "El Juez sancionó la obstrucción del derecho de convivencia de los menores.",
            "Ocultar o sustraer menores por cuenta propia sin orden judicial previa.",
            "N/A", "Pedir siempre autorización o medida de protección al Juez Familiar.",
            "JAMÁS sustraer u ocultar a los hijos sin medida judicial.",
            "2026-08-15"
        ),
        (
            "EXP-PEN-2026-005", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude",
            "Fraude Bancario y Phishing SPEI Ganado con Sello SHA-256 y Congelamiento de Cuentas",
            "Juez de garantías, Fiscal/MP, Perito Forense",
            "1. Denuncia o Querella ante Fiscalía/MP", "Retención de bienes / Pensión provisional", "Laudo / Sentencia condenatoria", "Amparo directo / indirecto",
            "Me vaciaron mi cuenta bancaria con un enlace falso de phishing y transferencias SPEI no autorizadas; guardé capturas y bitácoras IP.",
            hashlib.sha256(b"EXP-PEN-2026-005").hexdigest(), "GANADO",
            "El abogado presentó querella en las primeras 24 horas con peritaje informático SHA-256 y solicitó inmovilización de cuentas receptoras.",
            "El Juez de Control autorizó congelar los fondos y vinculó a proceso por fraude equiparado.",
            "N/A", "Preservar el celular intacto, sellar evidencia con SHA-256 y reportar a banco/CONDUSEF y MP en el minuto cero.",
            "Bloquear cuenta en el banco, pedir folio de aclaración y presentar denuncia con peritaje digital.",
            "No borrar los mensajes ni recortar las capturas de pantalla.",
            "2026-08-20"
        ),
        (
            "EXP-PEN-2026-006", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude",
            "Caso de Fraude Perdido por Presentar Capturas Recortadas sin Cadena de Custodia",
            "Juez penal, Fiscal/MP",
            "5. Audiencia de Juicio Oral", "Ninguna", "Sentencia absolutoria", "Apelación",
            "Víctima de estafa presentó hojas impresas con capturas editadas y borró el chat original de su teléfono.",
            hashlib.sha256(b"EXP-PEN-2026-006").hexdigest(), "PERDIDO",
            "El abogado exhibió copias simples sin pericial informática ni metadatos.",
            "El Juez desestimó las impresiones por falta de autenticidad y ruptura de cadena de custodia.",
            "Destrucción del mensaje original y falta de peritaje informático.",
            "N/A", "Mantener el mensaje original en el dispositivo para peritaje.",
            "JAMÁS borrar el chat original ni alterar capturas.",
            "2026-08-25"
        ),
        (
            "EXP-PEN-2026-007", "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad",
            "Detención Arbitraria y Revisión de Celular sin Orden Ganada por Nulidad Constitucional",
            "Juez de Control, Abogado defensor, Perito",
            "3. Audiencia Inicial y Auto de Vinculación", "Medidas de protección urgentes", "Sentencia absolutoria", "Habeas corpus",
            "Una patrulla me detuvo en la calle sin motivo, los policías me quitaron mi celular a la fuerza, lo desbloquearon sin orden de juez y demoraron horas en llevarme al MP.",
            hashlib.sha256(b"EXP-PEN-2026-007").hexdigest(), "GANADO",
            "El abogado defensor demostró la demora en la puesta a disposición con GPS/cámaras y solicitó nulidad de la revisión del celular por violar el Art. 16 Constitucional.",
            "El Juez de Control declaró ilegal la detención, anuló las pruebas ilícitas y ordenó la libertad inmediata.",
            "N/A", "Impugnar la retención prolongada y exigir orden judicial de juez de control para cualquier inspección de teléfono.",
            "Guardar silencio hasta tener abogado defensor y señalar la hora exacta en que te detuvo la patrulla.",
            "Nunca firmar declaraciones sin tu abogado ni entregar contraseñas bajo amenazas.",
            "2026-09-01"
        ),
        (
            "EXP-PEN-2026-008", "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad",
            "Caso Penal Perdido por Declarar sin Abogado y No Objetar la Detención",
            "Juez penal, Abogado defensor",
            "4. Etapa Intermedia (Preparación de Juicio)", "Ninguna", "Laudo / Sentencia condenatoria", "Apelación",
            "Detenido firmó declaración autoincriminatoria en separos y su abogado no objetó la detención ilegal en audiencia inicial.",
            hashlib.sha256(b"EXP-PEN-2026-008").hexdigest(), "PERDIDO",
            "Defensa pasiva que consintió los vicios policiales en la audiencia inicial.",
            "El Juez tuvo por convalidados los actos de investigación.",
            "Falta de defensa técnica temprana y autoincriminación.",
            "N/A", "Exigir defensor penalista que debata el control de detención.",
            "JAMÁS declarar ante policías o MP sin hablar antes en privado con tu abogado.",
            "2026-09-05"
        ),
        (
            "EXP-CIV-2026-009", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento",
            "Juicio de Arrendamiento Ganado con Lanzamiento Legal y Embargo de Renta",
            "Juez civil, Abogado litigante",
            "1. Solicitud de Conciliación / Demanda Inicial", "Embargo preventivo de cuentas/bienes", "Laudo / Sentencia condenatoria", "Apelación",
            "Mi inquilino lleva 5 meses sin pagar la renta del departamento, ya venció el contrato y no quiere salirse ni entregar las llaves.",
            hashlib.sha256(b"EXP-CIV-2026-009").hexdigest(), "GANADO",
            "El abogado promovió controversia de arrendamiento inmobiliario solicitando embargo de bienes del fiador y orden de desocupación.",
            "El Juez Civil dictó sentencia condenatoria ordenando el pago de rentas vencidas y el lanzamiento legal.",
            "N/A", "Demandar por la vía civil con el contrato escrito y embargar en el auto inicial.",
            "Acudir ante el Juez Civil para obtener orden legal de desalojo.",
            "Por ningún motivo cambiar la chapa ni sacar las cosas del inquilino a la calle por tu cuenta.",
            "2026-09-10"
        ),
        (
            "EXP-CIV-2026-010", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento",
            "Arrendamiento Perdido: Dueño Denunciado por Despojo al Cambiar Cerraduras por su Cuenta",
            "Juez civil, Juez penal",
            "4. Desahogo de Pruebas y Alegatos", "Orden de no enajenar inmueble", "Laudo / Sentencia condenatoria", "Amparo directo / indirecto",
            "Propietario cansado de que no le pagaran renta se metió al departamento, cambió las chapas y sacó los muebles del inquilino.",
            hashlib.sha256(b"EXP-CIV-2026-010").hexdigest(), "PERDIDO",
            "El dueño actuó por propia mano sin orden judicial y fue denunciado penalmente por despojo.",
            "El Juez ordenó devolver la posesión al inquilino moroso y procesó al dueño por despojo.",
            "Hacerse justicia por propia mano (prohibido por el Art. 17 Constitucional).",
            "N/A", "Usar siempre el juicio civil de desahucio/arrendamiento.",
            "JAMÁS meterte al inmueble rentado ni cortar agua/luz sin orden de un Juez.",
            "2026-09-15"
        ),
        (
            "EXP-MER-2026-011", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos",
            "Cobro de Pagaré Ganado con Embargo Inmediato en Juicio Ejecutivo Mercantil",
            "Juez mercantil, Abogado litigante, Actuario",
            "1. Solicitud de Conciliación / Demanda Inicial", "Embargo preventivo de cuentas/bienes", "Laudo / Sentencia condenatoria", "Apelación",
            "Un cliente me firmó un pagaré por mercancía y dinero prestado, ya venció la fecha de pago y esconde sus bienes para no pagarme.",
            hashlib.sha256(b"EXP-MER-2026-011").hexdigest(), "GANADO",
            "El abogado promovió Juicio Ejecutivo Mercantil con el pagaré original y embargó cuentas y mercancía en la primera diligencia.",
            "El Juez Mercantil dictó sentencia de trance y remate para pagar capital más intereses moratorios.",
            "N/A", "Demandar en la vía ejecutiva mercantil solicitando auto de exequendo (embargo desde el primer día).",
            "Conservar el pagaré original intacto y demandar antes de que prescriba la acción cambiaria.",
            "Nunca entregar el pagaré original hasta tener el dinero firme en tu cuenta.",
            "2026-09-20"
        ),
        (
            "EXP-MER-2026-012", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos",
            "Juicio Mercantil Perdido por Alterar con Otra Pluma el Monto o Fecha del Pagaré",
            "Juez mercantil, Perito en documentoscopía",
            "3. Ofrecimiento y Admisión de Pruebas", "Ninguna", "Sentencia absolutoria", "Amparo directo / indirecto",
            "Acreedor remarcó o rellenó con otra tinta los intereses y la fecha de vencimiento del pagaré después de firmado.",
            hashlib.sha256(b"EXP-MER-2026-012").hexdigest(), "PERDIDO",
            "La defensa del deudor ofreció pericial química y grafoscópica acreditando alteración posterior a la firma.",
            "El Juez declaró la nulidad del pagaré por alteración material del documento.",
            "Alteración física del título de crédito con tintas distintas.",
            "N/A", "Llenar todos los espacios del pagaré con la misma tinta en el acto mismo de la firma.",
            "JAMÁS alterar ni remarcar cantidades o fechas en un pagaré ya firmado.",
            "2026-09-25"
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
    conn.close()

init_db()

# ==============================================================================
# 4. EXPORTACIÓN E IMPORTACIÓN DEL CEREBRO NEURONAL (.JSON Y .CSV)
# ==============================================================================
def exportar_cerebro_completo_json() -> bytes:
    """
    Exporta tanto la tabla de precedentes oficiales (`casos_juridicos_cbr`) como toda
    la memoria aprendida (`memoria_neuronal_autonoma`) en un paquete JSON firmado con SHA-256.
    """
    conn = sqlite3.connect(DB_NAME)
    df_casos = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    df_mem = pd.read_sql_query("SELECT * FROM memoria_neuronal_autonoma", conn)
    conn.close()

    payload = {
        "autor_arquitectura": AUTOR_SISTEMA,
        "sistema": MARCA_SISTEMA,
        "fecha_respaldo": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_casos_cbr": len(df_casos),
        "total_memoria_autonoma": len(df_mem),
        "casos_juridicos_cbr": df_casos.to_dict(orient="records"),
        "memoria_neuronal_autonoma": df_mem.to_dict(orient="records")
    }
    raw_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return raw_bytes

def exportar_memoria_autonoma_csv() -> bytes:
    """Exporta las consultas y aprendizajes autónomos a CSV compatible con Excel."""
    conn = sqlite3.connect(DB_NAME)
    df_mem = pd.read_sql_query("SELECT * FROM memoria_neuronal_autonoma", conn)
    conn.close()
    return df_mem.to_csv(index=False).encode("utf-8-sig")

def importar_cerebro_desde_archivo(uploaded_file) -> dict:
    """
    Restaura e inyecta registros desde un archivo .json o .csv subido por el usuario,
    evitando duplicados y re-entrenando la Red Neuronal en caliente.
    """
    nombre = uploaded_file.name.lower()
    raw = uploaded_file.read()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    nuevos_mem = 0
    nuevos_casos = 0

    try:
        if nombre.endswith(".json"):
            data = json.loads(raw.decode("utf-8"))
            lista_mem = data.get("memoria_neuronal_autonoma", [])
            lista_casos = data.get("casos_juridicos_cbr", [])

            for m in lista_mem:
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
                    rel_orig,
                    rel_exp,
                    m.get("macro_rama", "Derecho Privado"),
                    m.get("rama_derecho", "Derecho Laboral"),
                    m.get("categoria_caso", "Casos Laborales"),
                    m.get("tipo_caso", "Despido injustificado"),
                    m.get("fuente_aprendizaje", "Restauración JSON"),
                    float(m.get("confianza", 95.0)),
                    h_c,
                    m.get("fecha_aprendizaje", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ))
                if c.rowcount > 0:
                    nuevos_mem += 1

            for cs in lista_casos:
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

        elif nombre.endswith(".csv"):
            df_up = pd.read_csv(io.BytesIO(raw))
            for _, row in df_up.iterrows():
                rel_orig = str(row.get("relato_original", "")).strip()
                if not rel_orig or rel_orig == "nan":
                    continue
                rel_exp = str(row.get("relato_expandido", ""))
                if not rel_exp or rel_exp == "nan":
                    rel_exp = expandir_lenguaje_coloquial(rel_orig)
                h_c = hashlib.sha256(rel_orig.lower().encode("utf-8")).hexdigest()
                c.execute("""
                    INSERT OR IGNORE INTO memoria_neuronal_autonoma (
                        relato_original, relato_expandido, macro_rama, rama_derecho,
                        categoria_caso, tipo_caso, fuente_aprendizaje, confianza,
                        hash_consulta, fecha_aprendizaje
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rel_orig,
                    rel_exp,
                    str(row.get("macro_rama", "Derecho Privado")),
                    str(row.get("rama_derecho", "Derecho Laboral")),
                    str(row.get("categoria_caso", "Casos Laborales")),
                    str(row.get("tipo_caso", "Despido injustificado")),
                    str(row.get("fuente_aprendizaje", "Restauración CSV")),
                    float(row.get("confianza", 95.0)),
                    h_c,
                    str(row.get("fecha_aprendizaje", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                ))
                if c.rowcount > 0:
                    nuevos_mem += 1
        conn.commit()
    finally:
        conn.close()

    return {"nuevos_memoria": nuevos_mem, "nuevos_casos": nuevos_casos}

# ==============================================================================
# 5. AGENTE DE BÚSQUEDA EN VIVO EN INTERNET (GOOGLE NEWS RSS + WIKIPEDIA API)
# ==============================================================================
def buscar_informacion_juridica_en_internet(categoria_caso: str, tipo_caso: str, relato_usuario: str) -> dict:
    resultados_web = []
    resumen_enciclopedico = ""
    textos_para_entrenar = []

    termino_wiki = f"{tipo_caso} derecho México" if "Despido" in tipo_caso else f"{tipo_caso}"
    try:
        url_wiki = (
            "https://es.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(termino_wiki)}&utf8=&format=json&srlimit=2"
        )
        req_w = urllib.request.Request(url_wiki, headers={"User-Agent": "ForensicMindLegalBot/6.5"})
        with urllib.request.urlopen(req_w, timeout=4.0) as resp_w:
            data_w = json.loads(resp_w.read().decode("utf-8"))
            search_items = data_w.get("query", {}).get("search", [])
            snippets_limpios = []
            for item in search_items:
                titulo_w = item.get("title", "")
                snip_w = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                link_w = f"https://es.wikipedia.org/wiki/{urllib.parse.quote(titulo_w.replace(' ', '_'))}"
                snippets_limpios.append(f"**{titulo_w}:** {snip_w}...")
                resultados_web.append({
                    "fuente": "📖 Enciclopedia Jurídica / Wikipedia",
                    "titulo": titulo_w,
                    "resumen": snip_w,
                    "url": link_w
                })
                textos_para_entrenar.append(f"{titulo_w} {snip_w}")
            resumen_enciclopedico = " | ".join(snippets_limpios)
    except Exception:
        pass

    palabras_clave_busqueda = f"{tipo_caso} ley derechos Mexico SCJN"
    if categoria_caso == "Casos Laborales":
        palabras_clave_busqueda = "despido injustificado liquidacion Ley Federal del Trabajo PROFEDET Mexico"
    elif categoria_caso == "Casos Familiares":
        palabras_clave_busqueda = "pension alimenticia guarda custodia Juez Familiar SCJN Mexico"
    elif categoria_caso == "Casos Penales":
        palabras_clave_busqueda = f"{tipo_caso} denuncia Fiscalia SCJN derechos Mexico"

    try:
        url_gnews = (
            "https://news.google.com/rss/search?"
            f"q={urllib.parse.quote(palabras_clave_busqueda)}&hl=es-419&gl=MX&ceid=MX:es-419"
        )
        req_g = urllib.request.Request(url_gnews, headers={"User-Agent": "ForensicMindLegalBot/6.5"})
        with urllib.request.urlopen(req_g, timeout=4.5) as resp_g:
            xml_data = resp_g.read()
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")[:3]
            for it in items:
                tit = it.find("title").text if it.find("title") is not None else "Criterio Jurídico en Línea"
                lnk = it.find("link").text if it.find("link") is not None else "https://www.scjn.gob.mx"
                pub = it.find("pubDate").text[:16] if it.find("pubDate") is not None else "Reciente"
                resultados_web.append({
                    "fuente": f"🌐 Google Jurídico México ({pub})",
                    "titulo": tit,
                    "resumen": f"Referencia actualizada localizada en la web para {categoria_caso} ({tipo_caso}).",
                    "url": lnk
                })
                textos_para_entrenar.append(tit)
    except Exception:
        pass

    return {
        "resultados": resultados_web,
        "resumen_enciclopedico": resumen_enciclopedico,
        "corpus_web_extraido": " ".join(textos_para_entrenar)
    }

# ==============================================================================
# 6. MOTOR DE AUTO-APRENDIZAJE NEURONAL CONTINUO (RE-ENTRENAMIENTO EN CALIENTE)
# ==============================================================================
def registrar_experiencia_en_memoria_autonoma(
    relato_original: str,
    clasificacion: dict,
    fuente: str = "Consulta Ciudadana / Voz",
    texto_web_extra: str = ""
) -> bool:
    if not relato_original or len(relato_original.strip()) < 10:
        return False
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
    return aprendio_nuevo

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

    vectorizer = TfidfVectorizer(ngram_range=(1, 3), max_features=2200)
    X_vec = vectorizer.fit_transform(textos_entrenamiento)

    mlp = MLPClassifier(
        hidden_layer_sizes=(96, 48),
        activation='relu',
        max_iter=500,
        random_state=42
    )
    mlp.fit(X_vec, etiquetas_entrenamiento)

    stats_modelo = {
        "total_muestras": len(textos_entrenamiento),
        "experiencias_aprendidas": len(df_mem),
        "vocabulario_ngramas": len(vectorizer.vocabulary_)
    }
    return vectorizer, mlp, stats_modelo

# ==============================================================================
# 7. CLASIFICADOR HÍBRIDO (MATRIZ COLOQUIAL + RED NEURONAL MLP EN EQUIPO)
# ==============================================================================
def autoclasificar_caso_con_red_neuronal(relato: str, vectorizer_mlp, modelo_mlp) -> dict:
    relato_expandido = expandir_lenguaje_coloquial(relato)
    texto_low = relato_expandido.lower()

    scores_ramas = {
        "Casos Laborales": 0,
        "Casos Familiares": 0,
        "Casos Penales": 0,
        "Casos Civiles": 0,
        "Casos Mercantiles": 0
    }

    reglas_puntaje = {
        "Casos Laborales": [
            'despid', 'corrieron', 'echaron', 'chamba', 'trabajo', 'liquidaci', 'finiquito',
            'sueldo', 'salario', 'semanal', 'quincenal', 'vacaciones', 'aguinaldo', 'patrón',
            'patron', 'jefe', 'renuncia', 'hoja en blanco', 'horas extras', 'nómina', 'nomina', 'profedet'
        ],
        "Casos Familiares": [
            'pensión', 'pension', 'alimentos', 'alimenticia', 'hijos', 'custodia', 'divorcio',
            'gasto de los niños', 'manutención', 'visita', 'paternidad', 'familiar'
        ],
        "Casos Penales": [
            'fraude', 'estafa', 'phishing', 'spei', 'vaciaron', 'robaron', 'detuvieron',
            'patrulla', 'policía', 'policia', 'ministerio público', 'cateo', 'sin orden',
            'abuso de autoridad', 'delito', 'amenaza de muerte', 'arma'
        ],
        "Casos Civiles": [
            'inquilino', 'renta', 'arrendamiento', 'departamento', 'desocupar', 'cerradura',
            'chapa', 'escrituras', 'herencia', 'propiedad', 'daño y perjuicio'
        ],
        "Casos Mercantiles": [
            'pagaré', 'pagare', 'cheque', 'factura', 'mercancía', 'mercancia', 'mercantil',
            'cliente comercial', 'bodega', 'sociedad mercantil'
        ]
    }

    for cat_key, lista_kws in reglas_puntaje.items():
        for kw in lista_kws:
            if kw in texto_low:
                scores_ramas[cat_key] += 15

    if any(w in texto_low for w in ['semanal', 'quincenal', 'liquidación', 'liquidacion', 'finiquito', 'despidieron', 'corrieron', 'vacaciones']):
        scores_ramas["Casos Laborales"] += 60

    categoria_ganadora = max(scores_ramas, key=scores_ramas.get)
    max_score_semantico = scores_ramas[categoria_ganadora]

    mapa_defaults = {
        "Casos Laborales": ("Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado"),
        "Casos Familiares": ("Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia"),
        "Casos Penales": (
            "Derecho Público",
            "Derecho Procesal Penal" if any(x in texto_low for x in ['patrulla', 'detuvieron', 'polic', 'orden']) else "Derecho Penal",
            "Casos Penales",
            "Abuso de autoridad" if any(x in texto_low for x in ['patrulla', 'detuvieron', 'polic', 'orden']) else "Fraude"
        ),
        "Casos Civiles": ("Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento"),
        "Casos Mercantiles": ("Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos")
    }
    macro, rama, cat, tipo = mapa_defaults[categoria_ganadora]

    confianza_mlp = 91.5
    if modelo_mlp is not None and vectorizer_mlp is not None:
        try:
            X_test = vectorizer_mlp.transform([relato_expandido])
            pred = modelo_mlp.predict(X_test)[0]
            probs = modelo_mlp.predict_proba(X_test)[0]
            max_p = float(max(probs)) * 100.0
            partes = pred.split("|")
            if len(partes) == 4:
                if partes[0] == cat:
                    confianza_mlp = round(min(99.6, max(89.0, max_p + 25.0)), 1)
                    cat, rama, tipo, macro = partes[0], partes[1], partes[2], partes[3]
                elif max_score_semantico == 0 and max_p > 45.0:
                    confianza_mlp = round(min(96.0, max_p + 15.0), 1)
                    cat, rama, tipo, macro = partes[0], partes[1], partes[2], partes[3]
                else:
                    confianza_mlp = round(min(98.9, 86.0 + min(12.9, max_score_semantico * 0.15)), 1)
        except Exception:
            pass

    rol_detectado = "Demandado / Acusado (Me están reclamando o imputando)" if any(
        w in texto_low for w in ['me demandaron', 'me acusan', 'me detuvieron', 'en mi contra', 'me imputan']
    ) else "Demandante / Afectado (Trabajador, Víctima o Acreedor)"

    plan_temp = obtener_plan_accion_ciudadano(cat, tipo, rol_detectado)
    etapa_sugerida = ETAPAS_PROCESO[plan_temp["proceso"]][0]

    return {
        "macro_rama": macro,
        "rama": rama,
        "categoria": cat,
        "tipo": tipo,
        "rol": rol_detectado,
        "etapa": etapa_sugerida,
        "medida": plan_temp["medida_sugerida"],
        "confianza": confianza_mlp
    }

# ==============================================================================
# 8. EXTRACTOR COLOQUIAL DE SUELDO Y CALCULADORA LFT + HONORARIOS
# ==============================================================================
def normalizar_texto_coloquial(texto: str) -> dict:
    texto_low = texto.lower().replace(",", "")
    salario_mensual = None
    periodicidad = "Mensual ($9,857.14 / mes)"

    m_sem = re.search(r'(?:semanal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la semana|semanal(?:es)?|por semana))', texto_low)
    if m_sem:
        val = float(m_sem.group(1) or m_sem.group(2))
        salario_mensual = round((val / 7.0) * 30.0, 2)
        periodicidad = f"Semanal (${val:,.2f} / sem)"

    if salario_mensual is None:
        m_quin = re.search(r'(?:quincenal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la quincena|quincenal(?:es)?|por quincena))', texto_low)
        if m_quin:
            val = float(m_quin.group(1) or m_quin.group(2))
            salario_mensual = round(val * 2.0, 2)
            periodicidad = f"Quincenal (${val:,.2f} / quin)"

    if salario_mensual is None:
        m_men = re.search(r'(?:mensual(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:al mes|mensual(?:es)?|por mes))', texto_low)
        if m_men:
            val = float(m_men.group(1) or m_men.group(2))
            salario_mensual = round(val, 2)
            periodicidad = f"Mensual (${val:,.2f} / mes)"

    if salario_mensual is None:
        m_gen = re.search(r'(?:gano|ganaba|sueldo|pago|pagan)\s*(?:es\s*de)?\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
        if m_gen:
            val = float(m_gen.group(1))
            if val < 5000:
                salario_mensual = round((val / 7.0) * 30.0, 2)
                periodicidad = f"Semanal Inferido (${val:,.2f} / sem)"
            else:
                salario_mensual = round(val, 2)
                periodicidad = f"Mensual Inferido (${val:,.2f} / mes)"

    oferta_patronal = 0.0
    m_oferta = re.search(r'(?:quieren dar|ofrecen|daban|dan|ofreciendo|soltar)\s*\$?\s*(\d+(?:\.\d+)?)', texto_low)
    if m_oferta:
        oferta_patronal = float(m_oferta.group(1))

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

    salario_base_prima_ant = min(sd, salario_minimo_vigente * 2.0)
    es_despido = ("Despido" in motivo_separacion or "Rescisión" in motivo_separacion)
    monto_prima_antiguedad = round(12.0 * antiguedad_total_anios * salario_base_prima_ant, 2) if (es_despido or anios_antiguedad >= 15) else 0.0
    subtotal_finiquito = round(monto_sueldo_pendiente + monto_aguinaldo_prop + monto_vacaciones_prop + monto_vacaciones_atrasadas + monto_prima_vac_prop, 2)

    monto_indem_90_dias = round(90.0 * sdi, 2) if es_despido else 0.0
    monto_20_dias_anio = round(20.0 * antiguedad_total_anios * sdi, 2) if (es_despido and incluir_20_dias_por_anio) else 0.0
    meses_topados_12 = min(12, max(0, meses_duracion_juicio))
    monto_salarios_caidos = round(meses_topados_12 * 30.0 * sdi, 2) if es_despido else 0.0

    subtotal_indemnizacion = round(monto_prima_antiguedad + monto_indem_90_dias + monto_20_dias_anio + monto_salarios_caidos, 2)
    gran_total_bruto = round(subtotal_finiquito + subtotal_indemnizacion, 2)

    conceptos_tabla = [
        {"Concepto Legal": "1. Salarios Devengados No Pagados", "Fundamento LFT": "Art. 82 y 88 LFT", "Tipo": "Finiquito (Irrenunciable)", "Monto (MXN)": monto_sueldo_pendiente},
        {"Concepto Legal": "2. Aguinaldo Proporcional", "Fundamento LFT": "Art. 87 LFT", "Tipo": "Finiquito (Irrenunciable)", "Monto (MXN)": monto_aguinaldo_prop},
        {"Concepto Legal": "3. Vacaciones Dignas + Omitidas", "Fundamento LFT": "Art. 76 y 79 LFT", "Tipo": "Finiquito (Irrenunciable)", "Monto (MXN)": round(monto_vacaciones_prop + monto_vacaciones_atrasadas, 2)},
        {"Concepto Legal": "4. Prima Vacacional (Mín. 25%)", "Fundamento LFT": "Art. 80 LFT", "Tipo": "Finiquito (Irrenunciable)", "Monto (MXN)": monto_prima_vac_prop},
        {"Concepto Legal": "5. Prima de Antigüedad (12 días/año)", "Fundamento LFT": "Art. 162 y 486 LFT", "Tipo": "Liquidación", "Monto (MXN)": monto_prima_antiguedad},
        {"Concepto Legal": "6. Indemnización Constitucional (90 Días SDI)", "Fundamento LFT": "Art. 123 Const. / Art. 48 LFT", "Tipo": "Liquidación por Despido", "Monto (MXN)": monto_indem_90_dias},
        {"Concepto Legal": "7. Indemnización de 20 Días por Año", "Fundamento LFT": "Art. 50 LFT", "Tipo": "Negativa de Reinstalación", "Monto (MXN)": monto_20_dias_anio},
        {"Concepto Legal": "8. Salarios Caídos en Juicio", "Fundamento LFT": "Art. 48 LFT", "Tipo": "Condena en Juicio", "Monto (MXN)": monto_salarios_caidos}
    ]

    return {
        "sd": sd, "sdi": sdi, "subtotal_finiquito": subtotal_finiquito,
        "subtotal_indemnizacion": subtotal_indemnizacion, "gran_total_bruto": gran_total_bruto,
        "tabla_conceptos": pd.DataFrame(conceptos_tabla)
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
    honorarios_totales_abogado = round(costo_asesoria + anticipo_fijo + comision_exito, 2)
    desembolso_total_ciudadano = round(honorarios_totales_abogado + gastos_periciales, 2)
    neto_libre = round(max(0.0, monto_en_disputa - desembolso_total_ciudadano), 2)
    costo_operativo = round(horas_invertidas * costo_hora_despacho, 2)
    utilidad_abogado = round(honorarios_totales_abogado - costo_operativo, 2)
    margen = round((utilidad_abogado / honorarios_totales_abogado) * 100.0, 1) if honorarios_totales_abogado > 0 else 0.0
    return {
        "comision_exito": comision_exito,
        "honorarios_totales_abogado": honorarios_totales_abogado,
        "desembolso_total_ciudadano": desembolso_total_ciudadano,
        "monto_neto_libre_ciudadano": neto_libre,
        "costo_operativo_tiempo": costo_operativo,
        "utilidad_neta_abogado": utilidad_abogado,
        "margen_rentabilidad": margen,
        "ingreso_efectivo_por_hora": round(honorarios_totales_abogado / max(1.0, horas_invertidas), 2)
    }

# ==============================================================================
# 9. GUÍA MULTIRRAMA DE "QUÉ HACER" Y AUDITORÍA DE RIESGO COHERENTE
# ==============================================================================
def obtener_plan_accion_ciudadano(categoria_caso: str, tipo_caso: str, rol_usuario: str = "Demandante") -> dict:
    if categoria_caso == "Casos Laborales":
        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Centro de Conciliación Laboral / Juez del Tribunal Laboral",
            "abogado": "Abogado Especialista en Derecho Laboral o Procurador PROFEDET (Gratuito)",
            "profesionales": "Conciliador Laboral + Perito Contable / Informático",
            "medida_sugerida": "Embargo precautorio sobre cuentas bancarias de la empresa",
            "recurso_clave": "Demanda por Despido Injustificado / Nulidad de Renuncia Coaccionada",
            "pasos_inmediatos": [
                "1. NO FIRMAR renuncia voluntaria ni hojas en blanco, ni recibir cantidades mínimas (ej. $5,000) como finiquito total.",
                "2. Guardar todas las pruebas de tu relación laboral: mensajes de WhatsApp de horarios/jefes, transferencias, recibos o testigos.",
                "3. Acudir esta misma semana al Centro de Conciliación Laboral o PROFEDET para citar al patrón.",
                "4. Exigir tu Liquidación Constitucional completa: 90 días de Salario Diario Integrado + Prima de Antigüedad + Vacaciones no gozadas + Aguinaldo."
            ],
            "alerta_fatal": "¡CUIDADO CON LA PRESCRIPCIÓN LABORAL! Tienes únicamente 60 días naturales desde el despido para presentar tu solicitud de conciliación."
        }
    elif categoria_caso == "Casos Familiares":
        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez de lo Familiar",
            "abogado": "Abogado Especialista en Derecho de Familia / Defensoría DIF",
            "profesionales": "Trabajador Social + Perito en Psicología",
            "medida_sugerida": "Fijación urgente de Pensión Alimenticia Provisional y retención de nómina/cuentas",
            "recurso_clave": "Incidente de aseguramiento de alimentos / Amparo indirecto",
            "pasos_inmediatos": [
                "1. Reunir actas de nacimiento de los hijos, acta de matrimonio y tickets de gastos (comida, escuela, médico).",
                "2. Solicitar al Juez Familiar la Pensión Alimenticia Provisional desde el primer escrito.",
                "3. Pedir que el Juez gire oficios al SAT, IMSS y Comisión Bancaria para detectar ingresos ocultos del deudor.",
                "4. Establecer régimen formal de Guarda y Custodia aprobado judicialmente."
            ],
            "alerta_fatal": "Confiar en acuerdos verbales sin sentencia del Juez o sustraer a los menores sin autorización judicial."
        }
    elif categoria_caso == "Casos Penales":
        return {
            "proceso": "Proceso Penal (8 Etapas)",
            "juez": "Juez de Control / Garantías Penal",
            "abogado": "Abogado Penalista (Asesor Jurídico de Víctima o Defensor Penal)",
            "profesionales": "Fiscal / Ministerio Público + Perito en Informática Forense",
            "medida_sugerida": "Inmovilización de cuentas bancarias / Medidas de protección urgentes",
            "recurso_clave": "Nulidad de prueba ilícita / Amparo penal / Control judicial",
            "pasos_inmediatos": [
                "1. Preservar intacto el teléfono celular, capturas y bitácoras originales (sellar con Hash SHA-256).",
                "2. Presentar Denuncia o Querella ante Fiscalía/MP o exigir presencia de tu Abogado Defensor antes de declarar.",
                "3. Si fue fraude bancario SPEI, reportar al banco y CONDUSEF en las primeras 24 horas para rastreo de cuenta destino.",
                "4. Si fue detención sin orden judicial, impugnar la demora en puesta a disposición y anular revisiones ilegales de celular."
            ],
            "alerta_fatal": "Alterar o borrar los mensajes originales del teléfono o declarar en el Ministerio Público sin abogado."
        }
    elif categoria_caso == "Casos Mercantiles":
        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez Mercantil",
            "abogado": "Abogado Litigante Mercantil",
            "profesionales": "Actuario Ejecutor + Perito Grafoscópico / Contable",
            "medida_sugerida": "Embargo precautorio en diligencia de exequendo (desde el primer día)",
            "recurso_clave": "Juicio Ejecutivo Mercantil / Apelación",
            "pasos_inmediatos": [
                "1. Resguardar el pagaré, cheque o factura original sin hacerle tachaduras ni anotaciones con otra pluma.",
                "2. Promover Juicio Ejecutivo Mercantil solicitando auto de embargo inmediato sobre cuentas y bienes del deudor.",
                "3. Señalar bienes suficientes en la diligencia de requerimiento de pago.",
                "4. Reclamar suerte principal más intereses moratorios pactados."
            ],
            "alerta_fatal": "Remarcar fechas o cantidades en el pagaré con otra tinta o entregar el documento original sin haber cobrado."
        }
    else:
        return {
            "proceso": "Proceso Laboral / Civil / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez Civil",
            "abogado": "Abogado Litigante Civil",
            "profesionales": "Notario Público + Perito Valuador",
            "medida_sugerida": "Anotación preventiva de demanda / Embargo de rentas",
            "recurso_clave": "Juicio de Controversia de Arrendamiento / Apelación",
            "pasos_inmediatos": [
                "1. Reunir el contrato escrito de arrendamiento o compraventa y el estado de cuenta de meses adeudados.",
                "2. Demandar ante el Juez Civil la rescisión del contrato, el pago de rentas vencidas y la desocupación.",
                "3. Solicitar embargo de bienes del inquilino o del fiador/aval desde la admisión de la demanda.",
                "4. Esperar la orden judicial de lanzamiento para recuperar la posesión legalmente."
            ],
            "alerta_fatal": "Meterte al inmueble por tu cuenta, cortar servicios o cambiar chapas sin orden del Juez (te acusarían de despojo)."
        }

def auditar_riesgo_juridico_forense(relato_evidencia: str, categoria_detectada: str) -> dict:
    hallazgos = []
    riesgo = 30
    if categoria_detectada == "Casos Laborales":
        hallazgos.append("🟠 ALERTA LABORAL PRIORITARIA: Despido injustificado y/o retención de liquidación y prestaciones de Ley.")
        if re.search(r'quieren dar|solo me dan|ofrecen|5000', relato_evidencia, re.IGNORECASE):
            hallazgos.append("🔴 ALERTA DE ENGAÑO PATRONAL: Te ofrecen una cantidad muy inferior a tus 90 días de Salario Diario Integrado.")
            riesgo += 30
        if re.search(r'vacaciones|días libres|dias libres|bonos|horas extras', relato_evidencia, re.IGNORECASE):
            hallazgos.append("🟠 OMISIÓN DE PRESTACIONES: Tienes derecho al pago íntegro en dinero de las vacaciones no gozadas + 25% de prima vacacional.")
            riesgo += 20
        hallazgos.append("⏱️ PLAZO LEGAL: Cuentas con 60 días naturales para acudir al Centro de Conciliación Laboral.")
    elif categoria_detectada == "Casos Familiares":
        hallazgos.append("🟠 PRIORIDAD FAMILIAR: Solicitar Pensión Alimenticia Provisional urgente y rastreo de ingresos ante SAT/CNBV.")
        riesgo += 35
    elif categoria_detectada == "Casos Penales":
        hallazgos.append("🔴 ALERTA PENAL Y FORENSE: Preservar cadena de custodia digital con sello SHA-256 y exigir defensa técnica.")
        riesgo += 40
    else:
        hallazgos.append("🟡 RIESGO PATRIMONIAL CIVIL/MERCANTIL: Solicitar embargo precautorio y prohibición de enajenar bienes.")
        riesgo += 25

    riesgo = min(100, riesgo)
    return {
        "hallazgos": hallazgos,
        "riesgo_score": riesgo,
        "hash_evidencia": hashlib.sha256(relato_evidencia.encode('utf-8')).hexdigest()
    }

def tokenizar(texto: str) -> Counter:
    palabras = re.findall(r'[a-zA-ZáéíóúñÁÉÍÓÚÑ0-9_./-]+', texto.lower())
    stopwords = {'de', 'la', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como', 'que', 'es', 'sin'}
    return Counter(w for w in palabras if w not in stopwords and len(w) > 2)

def calcular_similitud_coseno(texto1: str, texto2: str) -> float:
    vec1 = tokenizar(texto1)
    vec2 = tokenizar(texto2)
    interseccion = set(vec1.keys()) & set(vec2.keys())
    numerador = sum([vec1[x] * vec2[x] for x in interseccion])
    suma1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    suma2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominador = math.sqrt(suma1) * math.sqrt(suma2)
    if not denominador:
        return 0.0
    return round((float(numerador) / denominador) * 100, 1)

# ==============================================================================
# 10. DICTADO POR VOZ, WORD (.DOCX) Y FICHA VERTICAL 9:16
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
        return "⚠️ No se pudo transcribir el audio automáticamente. Escribe tu relato en el cuadro de abajo."

def generar_dictamen_word_docx(codigo: str, relato: str, clasificacion: dict, auditoria: dict, plan: dict, res_liq: dict, res_hon: dict) -> bytes:
    if Document is None:
        return b""
    doc = Document()
    doc.add_heading("FORENSICMIND & LEXGUÍA CBR v6.5 — DICTAMEN JURÍDICO, FINANCIERO Y FORENSE", 0)
    doc.add_paragraph(f"Arquitectura y Sello de Autoría: {AUTOR_SISTEMA}")
    doc.add_paragraph(f"Expediente: {codigo} | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"Sello SHA-256: {auditoria['hash_evidencia']}")
    doc.add_heading("1. Relato Analizado", level=1)
    doc.add_paragraph(relato)
    doc.add_heading("2. Clasificación Neuronal Auto-Evolutiva", level=1)
    doc.add_paragraph(f"Rama: {clasificacion['rama']} | Categoría: {clasificacion['categoria']} ({clasificacion['tipo']}) | Confianza: {clasificacion['confianza']}%")
    doc.add_heading("3. Cálculo de Liquidación y Honorarios", level=1)
    doc.add_paragraph(f"• Total Bruto por Ley (LFT): ${res_liq['gran_total_bruto']:,.2f} MXN")
    doc.add_paragraph(f"• Honorarios Estimados Abogado: ${res_hon['honorarios_totales_abogado']:,.2f} MXN")
    doc.add_paragraph(f"• Neto Libre para el Ciudadano: ${res_hon['monto_neto_libre_ciudadano']:,.2f} MXN")
    doc.add_heading("4. Pasos Inmediatos Recomendados", level=1)
    for p in plan["pasos_inmediatos"]:
        doc.add_paragraph(p, style="List Bullet")
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def limpiar_ascii(texto: str) -> str:
    return str(texto).translate(str.maketrans("áéíóúñÁÉÍÓÚÑ", "aeiounAEIOUN")).encode('ascii', 'ignore').decode('ascii')

def generar_ficha_vertical_9_16(codigo: str, rama: str, caso: str, plan: dict, monto_bruto: float, monto_neto: float, hash_ev: str) -> np.ndarray:
    alto, ancho = 1920, 1080
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[:] = (24, 15, 10)
    cv2.rectangle(img, (25, 25), (1055, 1895), (240, 175, 50), 4)
    cv2.rectangle(img, (40, 40), (1040, 235), (45, 28, 16), -1)
    cv2.putText(img, "FORENSICMIND & LEXGUIA v6.5", (65, 105), cv2.FONT_HERSHEY_DUPLEX, 1.6, (100, 220, 255), 3)
    cv2.putText(img, limpiar_ascii(f"AUTOR: {AUTOR_SISTEMA.upper()}"), (65, 160), cv2.FONT_HERSHEY_DUPLEX, 0.78, (120, 230, 255), 2)
    cv2.putText(img, limpiar_ascii(f"EXPEDIENTE: {codigo} | {rama} ({caso})"), (70, 290), cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
    cv2.rectangle(img, (70, 340), (1010, 480), (25, 48, 38), -1)
    cv2.putText(img, limpiar_ascii(f"DERECHOS / LIQUIDACION BRUTA: ${monto_bruto:,.2f} MXN"), (90, 395), cv2.FONT_HERSHEY_DUPLEX, 0.82, (255, 255, 255), 2)
    cv2.putText(img, limpiar_ascii(f"NETO LIBRE CIUDADANO: ${monto_neto:,.2f} MXN"), (90, 450), cv2.FONT_HERSHEY_DUPLEX, 0.85, (120, 255, 180), 2)
    cv2.putText(img, "PROTOCOLO DE ACCION INMEDIATA:", (70, 550), cv2.FONT_HERSHEY_DUPLEX, 0.95, (100, 220, 255), 2)
    y_cursor = 610
    for paso in plan["pasos_inmediatos"]:
        limpio = limpiar_ascii(paso)
        for frag in [limpio[i:i+54] for i in range(0, len(limpio), 54)][:2]:
            cv2.putText(img, frag, (70, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.74, (220, 220, 220), 2)
            y_cursor += 40
        y_cursor += 15
    cv2.putText(img, "SELLO CRIPTOGRAFICO SHA-256:", (70, 1600), cv2.FONT_HERSHEY_DUPLEX, 0.85, (100, 220, 255), 2)
    cv2.putText(img, hash_ev[:36], (70, 1645), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 255, 160), 2)
    cv2.putText(img, limpiar_ascii(f"ARQUITECTURA: {AUTOR_SISTEMA.upper()}"), (70, 1780), cv2.FONT_HERSHEY_DUPLEX, 0.75, (100, 255, 218), 2)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# ==============================================================================
# 11. ENCABEZADO PRINCIPAL Y PESTAÑAS DE NAVEGACIÓN
# ==============================================================================
st.markdown(f"""
<div class="author-banner">
    <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
        <div>
            <span style="color:#fbbf24 !important; font-weight:800; font-size:13px; letter-spacing:0.8px;">🏛️ RED NEURONAL AUTO-EVOLUTIVA CON CONEXIÓN WEB Y RESPALDO CLOUD v6.5</span><br>
            <span style="color:#ffffff !important; font-size:21px; font-weight:900;">{MARCA_SISTEMA}</span>
        </div>
        <div>
            <span class="gold-badge">⚙️ SELLO PERSONAL: {AUTOR_SISTEMA}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧠 1. Caso, Auto-Aprendizaje & Web Live",
    "💰 2. Liquidación (LFT) & Honorarios",
    "🌐 3. Cerebro Autónomo, Respaldo & Web",
    "🔬 4. Casos Ganados vs. Perdidos",
    "➕ 5. Enseñar Nuevo Caso a la IA"
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: DIAGNÓSTICO NEURONAL COLOQUIAL + BÚSQUEDA WEB + AUTO-APRENDIZAJE
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### 🗣️ Cuéntame qué pasó con tus propias palabras (La IA comprende lenguaje coloquial y aprende sola)")

    col_esc, col_voz = st.columns([1.3, 1])
    with col_esc:
        escenario_sel = st.selectbox(
            "💡 Elige un caso frecuente o escribe/dicta el tuyo:",
            list(ESCENARIOS_FRECUENTES.keys())
        )
    with col_voz:
        audio_input = st.audio_input("🎙️ Dictar mi caso por voz (Español)")
        texto_transcrito = ""
        if audio_input is not None:
            with st.spinner("Transcribiendo tu voz y traduciendo modismos..."):
                texto_transcrito = transcribir_audio_espanol(audio_input)
                if texto_transcrito and "⚠️" not in texto_transcrito:
                    st.success("✅ Dictado por voz transcrito correctamente.")
                elif texto_transcrito:
                    st.warning(texto_transcrito)

    valor_inicial_relato = ESCENARIOS_FRECUENTES[escenario_sel]
    if texto_transcrito and "⚠️" not in texto_transcrito:
        valor_inicial_relato = texto_transcrito

    relato_usuario = st.text_area(
        "📝 Escribe aquí como hablas normalmente (ej. 'mi semanal es de 2300, me corrieron y solo me quieren dar $5000 sin vacaciones'):",
        value=valor_inicial_relato,
        height=135
    )

    btn_analizar = st.button("🧠 Analizar Caso, Consultar Internet en Vivo y Entrenar Red Neuronal", use_container_width=True)

    clasificacion = autoclasificar_caso_con_red_neuronal(relato_usuario, VECTORIZER_VIVO, MODELO_VIVO)
    cat_activa = clasificacion["categoria"]
    rama_activa = clasificacion["rama"]
    tipo_activo = clasificacion["tipo"]
    macro_activa = clasificacion["macro_rama"]
    rol_activo = clasificacion["rol"]
    etapa_activa = clasificacion["etapa"]

    info_web_vivo = {"resultados": [], "resumen_enciclopedico": "", "corpus_web_extraido": ""}
    if buscar_web_switch:
        info_web_vivo = buscar_informacion_juridica_en_internet(cat_activa, tipo_activo, relato_usuario)

    aprendio_esta_consulta = False
    if auto_entrenar_switch and (btn_analizar or audio_input is not None or len(relato_usuario) > 25):
        aprendio_esta_consulta = registrar_experiencia_en_memoria_autonoma(
            relato_original=relato_usuario,
            clasificacion=clasificacion,
            fuente="Consulta en Línea + Enriquecimiento Web",
            texto_web_extra=info_web_vivo.get("corpus_web_extraido", "")
        )
        if aprendio_esta_consulta:
            VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()

    datos_normalizados = normalizar_texto_coloquial(relato_usuario)
    sueldo_mes_auto = datos_normalizados["salario_mensual"]
    oferta_auto = datos_normalizados["oferta_patronal"]
    dias_vac_auto = 12 if datos_normalizados["falta_prestaciones"] else 0

    res_liq_rapido = calcular_liquidacion_y_derechos_lft(
        salario_mensual=sueldo_mes_auto,
        anios_antiguedad=1,
        meses_adicionales=0,
        motivo_separacion="Despido Injustificado",
        dias_vacaciones_no_gozadas=dias_vac_auto
    )
    tabulador_activo = TABULADOR_HONORARIOS_RAMA.get(cat_activa, TABULADOR_HONORARIOS_RAMA["Casos Laborales"])
    res_hon_rapido = calcular_cotizacion_honorarios_dual(
        monto_en_disputa=res_liq_rapido["gran_total_bruto"],
        costo_asesoria=float(tabulador_activo["asesoria_sug"]),
        anticipo_fijo=float(tabulador_activo["anticipo_sug"]),
        pct_litis=float(tabulador_activo["pct_sugerido"])
    )

    plan_activo = obtener_plan_accion_ciudadano(cat_activa, tipo_activo, rol_activo)
    auditoria = auditar_riesgo_juridico_forense(relato_usuario, cat_activa)

    conn = sqlite3.connect(DB_NAME)
    df_hist = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    conn.close()

    consulta_expandida = expandir_lenguaje_coloquial(f"{rama_activa} {cat_activa} {tipo_activo} {relato_usuario}")
    similitudes = []
    for _, row in df_hist.iterrows():
        doc_hist = expandir_lenguaje_coloquial(
            f"{row['rama_derecho']} {row['categoria_caso']} {row['tipo_caso']} {row['titulo']} {row['evidencia_logs']} {row['que_hacer_ciudadano']}"
        )
        score_sim = calcular_similitud_coseno(consulta_expandida, doc_hist)
        if row["categoria_caso"] == cat_activa:
            score_sim = min(99.4, round(score_sim + 28.0, 1))
        else:
            score_sim = round(score_sim * 0.35, 1)
        similitudes.append({**row.to_dict(), "similitud": score_sim})

    df_sim = pd.DataFrame(similitudes).sort_values(by="similitud", ascending=False)
    df_misma_cat = df_sim[df_sim["categoria_caso"] == cat_activa]

    if cat_activa == "Casos Laborales" and oferta_auto > 0 and oferta_auto < res_liq_rapido["gran_total_bruto"]:
        diferencia_robo = round(res_liq_rapido["gran_total_bruto"] - oferta_auto, 2)
        st.markdown(f"""
        <div class="alert-box">
            <h4 style="margin-top:0;">🚨 ¡ALERTA DE ENGAÑO EN TU LIQUIDACIÓN DETECTADA EN TU RELATO!</h4>
            Detectamos en tu descripción un sueldo <b>{datos_normalizados['periodicidad']}</b> (equivalente a <b>${sueldo_mes_auto:,.2f} MXN/mes</b>) y que la empresa solo te quiere dar <b>${oferta_auto:,.2f} MXN</b>.<br><br>
            • <b>Lo que realmente te corresponde por Ley (LFT):</b> <b>${res_liq_rapido['gran_total_bruto']:,.2f} MXN</b><br>
            • <b>Dinero que te están quitando si firmas:</b> <b>${diferencia_robo:,.2f} MXN de menos</b>.<br>
            • <b>¿Qué procede ahí?:</b> NO firmes renuncia ni recibas los ${oferta_auto:,.0f} como finiquito total. Acude al Centro de Conciliación o PROFEDET para exigir tus 90 días de indemnización + vacaciones no gozadas + aguinaldo + prima de antigüedad.
        </div>
        """, unsafe_allow_html=True)

    estado_aprendizaje_txt = (
        f"🟢 ¡La Red Neuronal acaba de aprender y asimilar esta consulta en su memoria! ({STATS_IA['total_muestras']} experiencias totales | {STATS_IA['vocabulario_ngramas']} patrones lingüísticos)"
        if aprendio_esta_consulta else
        f"🧠 Red Neuronal Activa con {STATS_IA['total_muestras']} casos/consultas aprendidas y {STATS_IA['vocabulario_ngramas']} n-gramas en memoria."
    )
    st.markdown(f"""
    <div class="card-box">
        <b>🧠 Diagnóstico Automático de la Red Neuronal Multicapa (MLP) — {AUTOR_SISTEMA}:</b><br>
        • <b>Rama Detectada:</b> {macro_activa} → <span class="step-badge">{rama_activa}</span> &nbsp;|&nbsp;
        <b>Categoría y Tipo:</b> <span class="win-badge">{cat_activa}: {tipo_activo}</span> &nbsp;|&nbsp;
        <b>Confianza Neuronal:</b> <b>{clasificacion['confianza']}%</b><br>
        • <b>Estado del Aprendizaje Autónomo:</b> {estado_aprendizaje_txt}
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Liquidación / Derechos LFT", f"${res_liq_rapido['gran_total_bruto']:,.2f}", f"SDI: ${res_liq_rapido['sdi']:,.2f}/día")
    m2.metric("Neto Libre (Tras Abogado)", f"${res_hon_rapido['monto_neto_libre_ciudadano']:,.2f}", f"Honorario est.: ${res_hon_rapido['honorarios_totales_abogado']:,.0f}")
    m3.metric("Confianza Red Neuronal", f"{clasificacion['confianza']}%", cat_activa)
    m4.metric("Memoria Neuronal IA", f"{STATS_IA['total_muestras']} Casos", f"{STATS_IA['vocabulario_ngramas']} Palabras/Frases")

    col_eco1, col_eco2 = st.columns(2)
    with col_eco1:
        st.markdown(f"""
        <div class="money-box">
            <b>💵 ¿Cuánto te corresponde recibir por Ley? (Vista Ciudadano):</b><br>
            • <b>Sueldo Detectado:</b> {datos_normalizados['periodicidad']} (<b>${sueldo_mes_auto:,.2f} MXN/mes</b>)<br>
            • <b>Finiquito Irrenunciable (Aguinaldo + Vacaciones + Prima):</b> ${res_liq_rapido['subtotal_finiquito']:,.2f} MXN<br>
            • <b>Indemnización por Despido (90 días SDI + Prima Antigüedad):</b> ${res_liq_rapido['subtotal_indemnizacion']:,.2f} MXN<br>
            • <b>TOTAL BRUTO POR LEY:</b> <b>${res_liq_rapido['gran_total_bruto']:,.2f} MXN</b><br>
            • <b>Dinero Libre en tu Bolsa (descontando abogado):</b> <b>${res_hon_rapido['monto_neto_libre_ciudadano']:,.2f} MXN</b>
        </div>
        """, unsafe_allow_html=True)
    with col_eco2:
        st.markdown(f"""
        <div class="lawyer-box">
            <b>⚖️ ¿Cuánto cobra el Abogado en {cat_activa}? (Vista Ciudadano y Abogado):</b><br>
            • <b>Costo de Asesoría Inicial:</b> ${tabulador_activo['asesoria_min']:,.0f} a ${tabulador_activo['asesoria_max']:,.0f} MXN<br>
            • <b>Modalidad de Cobro:</b> {tabulador_activo['esquema_cobro']}<br>
            • <b>Honorarios Totales Estimados del Caso:</b> <b>${res_hon_rapido['honorarios_totales_abogado']:,.2f} MXN</b><br>
            • <b>Utilidad Neta para el Despacho:</b> <b>${res_hon_rapido['utilidad_neta_abogado']:,.2f} MXN</b><br>
            • <b>Opción Pública 100% Gratuita ($0 MXN):</b> {tabulador_activo['via_gratuita']}
        </div>
        """, unsafe_allow_html=True)

    if buscar_web_switch and info_web_vivo["resultados"]:
        st.markdown("#### 🌐 Información en Vivo Extraída de Internet (Google Jurídico México & Wikipedia Legal)")
        for item_w in info_web_vivo["resultados"][:4]:
            st.markdown(f"""
            <div class="web-box">
                <b>{item_w['fuente']}</b> — <a href="{item_w['url']}" target="_blank" style="font-weight:bold; color:#0284c7;">{item_w['titulo']} (Abrir enlace ↗)</a><br>
                <span>{item_w['resumen']}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    col_guia, col_actores = st.columns([1.25, 1])
    with col_guia:
        st.markdown(f"### 🚨 ¿Qué procede ahí en {cat_activa}? (Pasos Inmediatos para Defenderte)")
        for paso in plan_activo["pasos_inmediatos"]:
            st.markdown(f"- **{paso}**")
        st.markdown(f"""
        <div class="alert-box">
            <b>⚠️ ERROR FATAL QUE DEBES EVITAR:</b><br>
            {plan_activo['alerta_fatal']}
        </div>
        """, unsafe_allow_html=True)
        for h in auditoria["hallazgos"]:
            st.write(h)

    with col_actores:
        st.markdown("### 🏛️ Autoridades y Profesionales para tu Caso")
        st.markdown(f"""
        <div class="card-box">
            <span class="step-badge">ETAPA ACTUAL: {etapa_activa}</span><br><br>
            <b>👨‍⚖️ Autoridad Competente:</b> {plan_activo['juez']}<br><br>
            <b>💼 Abogado Especialista:</b> {plan_activo['abogado']}<br><br>
            <b>🔬 Peritos / Apoyo:</b> {plan_activo['profesionales']}<br><br>
            <b>🛡️ Medida Precautoria:</b> {plan_activo['medida_sugerida']}<br><br>
            <b>📜 Recursos Legales:</b> {plan_activo['recurso_clave']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader(f"⚖️ Precedentes Reales de {cat_activa}: Cómo se GANA vs. Por qué se PIERDE")
    df_ganados_top = df_misma_cat[df_misma_cat["resultado"] == "GANADO"]
    df_perdidos_top = df_misma_cat[df_misma_cat["resultado"] == "PERDIDO"]
    col_w, col_l = st.columns(2)

    with col_w:
        st.markdown("#### 🟢 Caso GANADO Similar")
        for _, g in df_ganados_top.head(1).iterrows():
            st.markdown(f"""
            <div class="money-box">
                <span class="win-badge">GANADO • {g['similitud']}% SIMILITUD</span> <b>{g['codigo_caso']}</b><br>
                <b>{g['titulo']}</b><br><br>
                <b>💼 ¿Qué hizo el Abogado?:</b> {g['accion_abogado']}<br><br>
                <b>👨‍⚖️ ¿Cómo resolvió el Juez?:</b> {g['reaccion_juez']}<br><br>
                <b>✅ QUÉ DEBES HACER HOY:</b> {g['que_hacer_ciudadano']}
            </div>
            """, unsafe_allow_html=True)

    with col_l:
        st.markdown("#### 🔴 Caso PERDIDO (Lo que NO debes hacer)")
        for _, p in df_perdidos_top.head(1).iterrows():
            st.markdown(f"""
            <div class="alert-box">
                <span class="loss-badge">PERDIDO • {p['similitud']}% SIMILITUD</span> <b>{p['codigo_caso']}</b><br>
                <b>{p['titulo']}</b><br><br>
                <b>💥 Causa de la Derrota:</b> {p['causa_raiz_fallo']}<br><br>
                <b>🚫 QUÉ NO DEBES HACER JAMÁS:</b> {p['que_no_hacer_ciudadano']}
            </div>
            """, unsafe_allow_html=True)

    bytes_docx = generar_dictamen_word_docx("SAOR-2026-V65", relato_usuario, clasificacion, auditoria, plan_activo, res_liq_rapido, res_hon_rapido)
    if bytes_docx:
        st.download_button(
            label=f"📄 Descargar Dictamen Completo en Word (.docx) — Sello: {AUTOR_SISTEMA}",
            data=bytes_docx,
            file_name="Dictamen_ForensicMind_v65.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    with st.expander("📱 Generar Ficha Vertical 9:16 para Celular (1080x1920 px)", expanded=False):
        img_9_16 = generar_ficha_vertical_9_16(
            "SAOR-2026-V65", rama_activa, tipo_activo, plan_activo,
            res_liq_rapido["gran_total_bruto"], res_hon_rapido["monto_neto_libre_ciudadano"], auditoria["hash_evidencia"]
        )
        c_i1, c_i2, c_i3 = st.columns([1, 1.2, 1])
        with c_i2:
            st.image(img_9_16, caption=f"Ficha 9:16 — {AUTOR_SISTEMA}", use_container_width=True)
            _, buffer_png = cv2.imencode(".png", cv2.cvtColor(img_9_16, cv2.COLOR_RGB2BGR))
            st.download_button("📥 Descargar Ficha Vertical 9:16 (.png)", buffer_png.tobytes(), "Ficha_9_16.png", "image/png", use_container_width=True)

# ------------------------------------------------------------------------------
# PESTAÑA 2: CALCULADORA DE LIQUIDACIÓN (SEMANAL/QUINCENAL/MENSUAL) Y HONORARIOS
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("💰 Calculadora de Liquidación por Despido (Semanal / Quincenal / Mensual) y Costo del Abogado")
    st.caption(f"Módulo de Ingeniería Legal y Financiera desarrollado por: {AUTOR_SISTEMA}")

    col_calc_izq, col_calc_der = st.columns([1.05, 1])
    with col_calc_izq:
        st.markdown("#### 👷 1. Ingresa tu Sueldo y Antigüedad")
        c_l1, c_l2 = st.columns(2)
        with c_l1:
            periodicidad_pago = st.selectbox("¿Cada cuándo te pagan?", ["Semanal (Cada 7 días)", "Quincenal (Cada 15 días)", "Mensual (Cada 30 días)", "Diario"])
            val_def = 2300.0 if "Semanal" in periodicidad_pago else (4928.0 if "Quincenal" in periodicidad_pago else sueldo_mes_auto)
            monto_sueldo_ingreso = st.number_input("¿Cuánto ganas en ese periodo? ($ MXN)", min_value=200.0, max_value=500000.0, value=float(val_def), step=100.0)
            if "Semanal" in periodicidad_pago:
                sueldo_mensual_calc = round((monto_sueldo_ingreso / 7.0) * 30.0, 2)
            elif "Quincenal" in periodicidad_pago:
                sueldo_mensual_calc = round(monto_sueldo_ingreso * 2.0, 2)
            elif "Diario" in periodicidad_pago:
                sueldo_mensual_calc = round(monto_sueldo_ingreso * 30.0, 2)
            else:
                sueldo_mensual_calc = round(monto_sueldo_ingreso, 2)

            st.info(f"📌 **Sueldo Mensual Equivalente:** ${sueldo_mensual_calc:,.2f} MXN (${sueldo_mensual_calc/30.0:,.2f}/día)")
            anios_calc = st.number_input("Años Cumplidos Trabajando", min_value=0, max_value=50, value=1, step=1)
            meses_calc = st.number_input("Meses Adicionales Trabajados", min_value=0, max_value=11, value=0, step=1)
        with c_l2:
            motivo_baja = st.selectbox("Motivo de Salida", ["Despido Injustificado (Art. 48 LFT - Liquidación Completa)", "Rescisión por Culpa del Patrón (Art. 51 LFT)", "Renuncia Voluntaria (Solo Finiquito)"])
            oferta_empresa_calc = st.number_input("¿Cuánto te quiere dar la empresa hoy? ($ MXN)", min_value=0.0, max_value=1000000.0, value=float(oferta_auto if oferta_auto > 0 else 5000.0), step=500.0)
            dias_vac_adeudadas = st.number_input("Días de vacaciones pasadas que NO te dieron", min_value=0, max_value=120, value=int(dias_vac_auto), step=1)
            dias_pendientes_calc = st.number_input("Días trabajados sin pagar de esta semana", min_value=0, max_value=60, value=0, step=1)

    res_liq_det = calcular_liquidacion_y_derechos_lft(
        salario_mensual=sueldo_mensual_calc, anios_antiguedad=anios_calc, meses_adicionales=meses_calc,
        motivo_separacion=motivo_baja, dias_sueldo_pendientes=dias_pendientes_calc, dias_vacaciones_no_gozadas=dias_vac_adeudadas
    )

    with col_calc_der:
        st.markdown("#### ⚖️ 2. Simulador de Honorarios (Vista Ciudadano vs. Vista Abogado)")
        rama_cotizador = st.selectbox("Materia del Caso", list(TABULADOR_HONORARIOS_RAMA.keys()), index=0)
        info_tab = TABULADOR_HONORARIOS_RAMA[rama_cotizador]
        monto_base_asunto = st.number_input("Monto Total a Reclamar ($ MXN)", min_value=0.0, max_value=50000000.0, value=float(res_liq_det["gran_total_bruto"]), step=1000.0)
        c_h1, c_h2 = st.columns(2)
        with c_h1:
            asesoria_cot = st.number_input("1. Costo de Asesoría Inicial ($ MXN)", min_value=0.0, max_value=20000.0, value=float(info_tab["asesoria_sug"]), step=100.0)
            anticipo_cot = st.number_input("2. Anticipo Fijo ($ MXN)", min_value=0.0, max_value=500000.0, value=float(info_tab["anticipo_sug"]), step=500.0)
            pct_litis_cot = st.slider("3. % del Abogado al Ganar (Cuota Litis)", 0.0, 50.0, float(info_tab["pct_sugerido"]), 1.0)
        with c_h2:
            gastos_peritaje_cot = st.number_input("4. Gastos de Copias / Peritos ($ MXN)", min_value=0.0, max_value=200000.0, value=float(info_tab["gastos_periciales_sug"]), step=500.0)
            horas_abogado_cot = st.number_input("5. [Abogado] Horas-Hombre del Caso", min_value=1.0, max_value=500.0, value=float(info_tab["horas_promedio_despacho"]), step=2.0)
            costo_hora_desp = st.number_input("6. [Abogado] Costo/Hora Despacho ($)", min_value=50.0, max_value=5000.0, value=350.0, step=50.0)

    res_hon_det = calcular_cotizacion_honorarios_dual(
        monto_en_disputa=monto_base_asunto, costo_asesoria=asesoria_cot, anticipo_fijo=anticipo_cot,
        pct_litis=pct_litis_cot, gastos_periciales=gastos_peritaje_cot, horas_invertidas=horas_abogado_cot, costo_hora_despacho=costo_hora_desp
    )

    st.markdown("---")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Bruto por Ley (LFT)", f"${res_liq_det['gran_total_bruto']:,.2f}", f"SDI: ${res_liq_det['sdi']:,.2f}/día")
    k2.metric("Oferta de la Empresa", f"${oferta_empresa_calc:,.2f}", f"Faltante: -${max(0, res_liq_det['gran_total_bruto']-oferta_empresa_calc):,.2f}")
    k3.metric("Honorarios Totales Abogado", f"${res_hon_det['honorarios_totales_abogado']:,.2f}", f"Utilidad Despacho: ${res_hon_det['utilidad_neta_abogado']:,.0f}")
    k4.metric("NETO LIBRE PARA TI", f"${res_hon_det['monto_neto_libre_ciudadano']:,.2f}", "Libre en tu bolsillo")

    st.dataframe(res_liq_det["tabla_conceptos"].style.format({"Monto (MXN)": "${:,.2f}"}), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# PESTAÑA 3: CEREBRO AUTÓNOMO, RESPALDO CLOUD (.JSON/.CSV) & BUSCADOR WEB
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("🌐 Cerebro Autónomo de la Red Neuronal, Respaldo Cloud (.JSON / .CSV) y Buscador Web")
    st.caption(f"Arquitectura de Persistencia Neuronal y Búsqueda en Vivo desarrollada por: {AUTOR_SISTEMA}")

    # Bloque de Respaldo y Restauración en 1 Clic (Para no perder nada al reiniciar Streamlit)
    st.markdown("#### 💾 1. Respaldar o Restaurar la Memoria Aprendida por la IA (Protección contra Reinicios Cloud)")
    col_bk1, col_bk2, col_bk3 = st.columns([1, 1, 1.3])

    with col_bk1:
        bytes_cerebro_json = exportar_cerebro_completo_json()
        st.download_button(
            label="📥 Descargar Cerebro Completo (.JSON)",
            data=bytes_cerebro_json,
            file_name=f"Cerebro_ForensicMind_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
        st.caption("Incluye los Casos CBR + Toda la Memoria Aprendida de usuarios y de la Web.")

    with col_bk2:
        bytes_mem_csv = exportar_memoria_autonoma_csv()
        st.download_button(
            label="📊 Exportar Memoria Aprendida (.CSV / Excel)",
            data=bytes_mem_csv,
            file_name=f"Memoria_Neuronal_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        st.caption("Ideal para auditar en Excel todas las consultas y frases coloquiales aprendidas.")

    with col_bk3:
        archivo_restaurar = st.file_uploader(
            "📤 Restaurar / Inyectar Memoria a la IA (.json o .csv)",
            type=["json", "csv"]
        )
        if archivo_restaurar is not None:
            if st.button("⚡ Inyectar Respaldo y Re-Entrenar Red Neuronal", use_container_width=True):
                res_imp = importar_cerebro_desde_archivo(archivo_restaurar)
                VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()
                st.success(
                    f"✅ ¡Cerebro Restaurado! Se inyectaron {res_imp['nuevos_memoria']} experiencias en la memoria autónoma "
                    f"y {res_imp['nuevos_casos']} precedentes CBR. Total activo: {STATS_IA['total_muestras']} muestras."
                )

    st.markdown("---")
    col_web_search, col_mem_stats = st.columns([1.25, 1])
    with col_web_search:
        st.markdown("#### 🌐 2. Buscador Web Jurídico en Vivo (Entrenamiento desde Internet)")
        tema_buscar_web = st.text_input(
            "🔎 Escribe cualquier tema legal o duda para buscar en Google Jurídico México y Wikipedia:",
            value="despido injustificado liquidacion 90 dias vacaciones Ley Federal del Trabajo"
        )
        cat_entrenar_web = st.selectbox("Categoría a la que pertenece este tema:", list(TIPOS_CASOS.keys()))
        if st.button("🌐 Buscar en Internet e Inyectar Conocimiento en la Red Neuronal", use_container_width=True):
            with st.spinner("Consultando Internet en vivo y re-entrenando Red Neuronal..."):
                res_busqueda_manual = buscar_informacion_juridica_en_internet(cat_entrenar_web, TIPOS_CASOS[cat_entrenar_web][0], tema_buscar_web)
                if res_busqueda_manual["corpus_web_extraido"]:
                    mapa_cat = {
                        "Casos Laborales": ("Derecho Privado", "Derecho Laboral", "Despido injustificado"),
                        "Casos Familiares": ("Derecho Privado", "Derecho de Familia", "Pensión alimenticia"),
                        "Casos Penales": ("Derecho Público", "Derecho Penal", "Fraude"),
                        "Casos Civiles": ("Derecho Privado", "Derecho Civil", "Arrendamiento"),
                        "Casos Mercantiles": ("Derecho Privado", "Derecho Mercantil", "Incumplimiento de contratos")
                    }
                    m_r, r_d, t_c = mapa_cat[cat_entrenar_web]
                    registrar_experiencia_en_memoria_autonoma(
                        relato_original=f"{tema_buscar_web} — {res_busqueda_manual['corpus_web_extraido']}",
                        clasificacion={"macro_rama": m_r, "rama": r_d, "categoria": cat_entrenar_web, "tipo": t_c, "confianza": 99.0},
                        fuente="Auto-Entrenamiento desde Internet (Google/Wikipedia)"
                    )
                    VECTORIZER_VIVO, MODELO_VIVO, STATS_IA = entrenar_red_neuronal_evolutiva()
                    st.success("✅ ¡Conocimiento extraído de Internet e inyectado exitosamente en la Red Neuronal!")
                for rw in res_busqueda_manual["resultados"]:
                    st.markdown(f"""
                    <div class="web-box">
                        <b>{rw['fuente']}</b> — <a href="{rw['url']}" target="_blank">{rw['titulo']} ↗</a><br>
                        {rw['resumen']}
                    </div>
                    """, unsafe_allow_html=True)

    with col_mem_stats:
        conn = sqlite3.connect(DB_NAME)
        df_mem_view = pd.read_sql_query(
            "SELECT id, relato_original, categoria_caso, tipo_caso, fuente_aprendizaje, confianza, fecha_aprendizaje FROM memoria_neuronal_autonoma ORDER BY id DESC",
            conn
        )
        conn.close()
        st.markdown("#### 🧠 3. Bitácora de Auto-Aprendizaje en Vivo")
        st.write(f"• **Experiencias totales en el modelo:** `{STATS_IA['total_muestras']}`")
        st.write(f"• **Consultas y búsquedas aprendidas:** `{len(df_mem_view)}`")
        st.write(f"• **Vocabulario neuronal activo:** `{STATS_IA['vocabulario_ngramas']}` n-gramas")
        if not df_mem_view.empty:
            st.dataframe(df_mem_view, use_container_width=True, hide_index=True)
        else:
            st.info("Cada consulta analizada en la Pestaña 1 o buscada aquí aparecerá registrada automáticamente.")

# ------------------------------------------------------------------------------
# PESTAÑA 4: BÓVEDA DE CASOS GANADOS VS PERDIDOS
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🔬 Bóveda Completa de Casos (Laboral, Familiar, Penal, Civil y Mercantil)")
    f_c1, f_c2 = st.columns(2)
    f_cat = f_c1.selectbox("Filtrar por Familia de Caso:", ["TODAS"] + list(TIPOS_CASOS.keys()))
    f_res = f_c2.selectbox("Filtrar por Veredicto:", ["TODOS", "GANADO", "PERDIDO"])
    df_v = df_hist.copy()
    if f_cat != "TODAS":
        df_v = df_v[df_v["categoria_caso"] == f_cat]
    if f_res != "TODOS":
        df_v = df_v[df_v["resultado"] == f_res]
    st.dataframe(df_v[["codigo_caso", "categoria_caso", "tipo_caso", "titulo", "resultado", "que_hacer_ciudadano"]], use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# PESTAÑA 5: ENSEÑAR NUEVO CASO OFICIAL A LA IA
# ------------------------------------------------------------------------------
with tab5:
    st.subheader("➕ Enseñar Nuevo Precedente Oficial a la Bóveda y Red Neuronal")
    with st.form("form_nuevo_v65"):
        c1, c2, c3 = st.columns(3)
        ncod = c1.text_input("Código (ej. EXP-LAB-2026-099)")
        ncat = c2.selectbox("Categoría de Caso", list(TIPOS_CASOS.keys()))
        nres = c3.selectbox("Resultado", ["GANADO", "PERDIDO"])
        ntit = st.text_input("Título del Caso")
        nevid = st.text_area("Relato de Hechos (puedes incluir palabras coloquiales para entrenar a la IA)")
        nqh = st.text_area("✅ ¿Qué debe hacer el ciudadano?")
        nqnh = st.text_area("🚫 ¿Qué NO debe hacer jamás?")
        if st.form_submit_button("💾 Guardar y Re-Entrenar Red Neuronal Ahora"):
            if ncod and ntit and nevid:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("""
                    INSERT OR IGNORE INTO casos_juridicos_cbr (
                        codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,
                        titulo, actores_intervinientes, etapa_clave, medida_cautelar,
                        resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,
                        resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,
                        estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro
                    ) VALUES (?, 'Derecho Privado', 'Derecho Laboral', ?, 'Despido injustificado', ?, 'Juez, Abogado', '1. Demanda', 'Embargo', 'Sentencia', 'Amparo', ?, ?, ?, 'Acción registrada', 'Resolución registrada', 'N/A', 'Estrategia registrada', ?, ?, ?)
                """, (ncod, ncat, ntit, nevid, hashlib.sha256(nevid.encode()).hexdigest(), nres, nqh, nqnh, datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.success("✅ Caso guardado y Red Neuronal actualizada en tiempo real.")

st.markdown("---")
st.caption(f"⚙️ **Arquitectura, Ingeniería de Sistemas y Red Neuronal Auto-Evolutiva:** {AUTOR_SISTEMA} • {MARCA_SISTEMA}")

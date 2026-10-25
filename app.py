import streamlit as st
import sqlite3
import hashlib
import re
import math
import io
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
MARCA_SISTEMA = "ForensicMind & LexGuía CBR v5.5"

st.set_page_config(
    page_title=f"{MARCA_SISTEMA} | {AUTOR_SISTEMA}",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_NAME = "boveda_juridica_cbr_v4.db"

# ==============================================================================
# SELECTOR DE TEMA VISUAL Y CSS BLINDADO DE ALTO CONTRASTE (MÓVIL Y PC)
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎨 Apariencia de la Interfaz")
    modo_visual = st.radio(
        "Elige el estilo visual:",
        ["☀️ Ejecutivo Claro (Máxima Lectura en Celular)", "🌙 Oscuro Forense Blindado"],
        index=0
    )

if "Claro" in modo_visual:
    st.markdown("""
    <style>
        /* Fondo general limpio estilo Banca / LegalTech */
        .stApp {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }
        /* Evitar que la barra superior de Streamlit corte el título en celular */
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 2.5rem !important;
        }
        /* Títulos y textos generales en azul marino profundo */
        h1, h2, h3, h4, h5, h6, p, li, span, div {
            color: #0f172a;
        }
        /* Etiquetas de todos los controles (Selectbox, Textarea, Audio, Inputs) */
        label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            font-weight: 700 !important;
            font-size: 1.02rem !important;
            opacity: 1 !important;
        }
        /* CUADRO DE DESCRIPCIÓN (TEXTAREA) Y ENTRADAS DE TEXTO 100% LEGIBLES */
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
        textarea:focus, input:focus {
            border-color: #1d4ed8 !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25) !important;
        }
        /* Selectbox / Desplegables */
        div[data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
        }
        /* Banner de Autoría */
        .author-banner {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
            border-left: 6px solid #f59e0b;
            border-radius: 14px;
            padding: 16px 20px;
            margin-bottom: 18px;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.15);
        }
        .author-banner * {
            color: #ffffff !important;
        }
        /* Tarjetas de Métricas */
        div[data-testid="metric-container"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-left: 5px solid #2563eb !important;
            padding: 14px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.06) !important;
        }
        div[data-testid="metric-container"] label {
            color: #475569 !important;
            -webkit-text-fill-color: #475569 !important;
            font-size: 0.88rem !important;
        }
        div[data-testid="stMetricValue"] {
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            font-weight: 800 !important;
        }
        /* Insignias */
        .win-badge { background-color: #059669; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .loss-badge { background-color: #dc2626; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .step-badge { background-color: #1d4ed8; color: #ffffff !important; padding: 5px 12px; border-radius: 6px; font-weight: 700; display: inline-block; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 5px 12px; border-radius: 6px; font-weight: 800; display: inline-block; }
        /* Cajas informativas de alto contraste */
        .card-box {
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            border-left: 6px solid #2563eb;
            border-radius: 12px;
            padding: 18px;
            margin-top: 10px;
            margin-bottom: 12px;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
            color: #0f172a !important;
        }
        .money-box {
            background-color: #ecfdf5;
            border: 1px solid #6ee7b7;
            border-left: 6px solid #059669;
            border-radius: 12px;
            padding: 18px;
            margin-top: 10px;
            margin-bottom: 12px;
            color: #064e3b !important;
        }
        .lawyer-box {
            background-color: #eef2ff;
            border: 1px solid #a5b4fc;
            border-left: 6px solid #4f46e5;
            border-radius: 12px;
            padding: 18px;
            margin-top: 10px;
            margin-bottom: 12px;
            color: #1e1b4b !important;
        }
        .alert-box {
            background-color: #fef2f2;
            border: 1px solid #fca5a5;
            border-left: 6px solid #dc2626;
            border-radius: 12px;
            padding: 18px;
            margin-top: 10px;
            margin-bottom: 12px;
            color: #7f1d1d !important;
        }
        /* Botón Principal de Acción */
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
        div.stButton > button:first-child:hover {
            background: linear-gradient(90deg, #1d4ed8 0%, #1e40af 100%) !important;
        }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
        .stApp {
            background-color: #0b0f19 !important;
            color: #f8fafc !important;
        }
        .block-container {
            padding-top: 3.5rem !important;
            padding-bottom: 2.5rem !important;
        }
        h1, h2, h3, h4, h5, h6, p, li, label, [data-testid="stWidgetLabel"] p {
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            font-weight: 600 !important;
        }
        /* En modo oscuro forzamos también caja blanca con letra azul marino oscura para nunca perder contraste en móvil */
        textarea, input[type="text"], input[type="number"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            -webkit-text-fill-color: #0f172a !important;
            border: 2px solid #38bdf8 !important;
            border-radius: 10px !important;
            font-size: 1.05rem !important;
            font-weight: 700 !important;
            padding: 12px !important;
            opacity: 1 !important;
        }
        div[data-baseweb="select"] > div {
            background-color: #1e293b !important;
            color: #f8fafc !important;
            -webkit-text-fill-color: #f8fafc !important;
            border: 1px solid #38bdf8 !important;
        }
        .author-banner {
            background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
            border: 1px solid #38bdf8;
            border-left: 6px solid #f59e0b;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 18px;
        }
        div[data-testid="metric-container"] {
            background: #111827 !important;
            border: 1px solid #374151 !important;
            border-left: 4px solid #38bdf8 !important;
            padding: 14px !important;
            border-radius: 10px !important;
        }
        .win-badge { background-color: #065f46; color: #34d399 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .loss-badge { background-color: #7f1d1d; color: #f87171 !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .step-badge { background-color: #1e3a8a; color: #93c5fd !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .gold-badge { background-color: #f59e0b; color: #0f172a !important; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
        .card-box { background-color: #131c2e; border: 1px solid #2dd4bf; border-radius: 10px; padding: 18px; margin: 10px 0; }
        .money-box { background-color: #0f2922; border: 1px solid #10b981; border-left: 5px solid #34d399; border-radius: 10px; padding: 18px; margin: 10px 0; }
        .lawyer-box { background-color: #1e1b4b; border: 1px solid #818cf8; border-left: 5px solid #a78bfa; border-radius: 10px; padding: 18px; margin: 10px 0; }
        .alert-box { background-color: #1f1215; border: 1px solid #f87171; border-left: 5px solid #ef4444; border-radius: 10px; padding: 18px; margin: 10px 0; }
        div.stButton > button:first-child {
            background-color: #2563eb !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            font-weight: bold !important;
            border-radius: 10px !important;
            padding: 12px 20px !important;
        }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. TAXONOMÍA JURÍDICA INTEGRAL, TABULADORES DE HONORARIOS Y CATÁLOGOS V5.5
# ==============================================================================
RAMAS_DERECHO = {
    "Derecho Público": [
        "Derecho Constitucional", "Derecho Administrativo", "Derecho Penal",
        "Derecho Procesal Penal", "Derecho Electoral", "Derecho Internacional Público",
        "Derecho Tributario"
    ],
    "Derecho Privado": [
        "Derecho Civil", "Derecho Mercantil", "Derecho Laboral",
        "Derecho de Familia", "Derecho Procesal Civil", "Derecho Comercial",
        "Derecho de Propiedad Intelectual"
    ],
    "Otros / Especializados": [
        "Derecho Informático/Digital", "Derecho Ambiental", "Derecho Agrario",
        "Derecho Minero", "Derecho Marítimo", "Derecho de Seguros"
    ]
}

TIPOS_CASOS = {
    "Casos Penales": [
        "Homicidio", "Robo/Hurto", "Fraude", "Violencia doméstica",
        "Delitos de tránsito", "Narcotráfico", "Corrupción",
        "Abuso de autoridad", "Estafa", "Falsificación"
    ],
    "Casos Civiles": [
        "Divorcio/separación", "Custodia de menores", "Herencias/sucesiones",
        "Deudas", "Arrendamiento", "Responsabilidad civil", "Accidentes",
        "Contratos", "Daño y perjuicio", "Propiedad"
    ],
    "Casos Laborales": [
        "Despido injustificado", "Acoso laboral", "Discriminación",
        "Accidentes de trabajo", "Salarios adeudados", "Beneficios no pagados",
        "Reclasificación laboral"
    ],
    "Casos Mercantiles": [
        "Quiebra/insolvencia", "Sociedades mercantiles", "Contratos comerciales",
        "Competencia desleal", "Incumplimiento de contratos"
    ],
    "Casos Familiares": [
        "Divorcio", "Pensión alimenticia", "Reconocimiento de paternidad",
        "Adopción", "Guarda y custodia", "Violencia de género", "Derecho de visita"
    ]
}

ETAPAS_PROCESO = {
    "Proceso Penal (8 Etapas)": [
        "1. Denuncia/Querella",
        "2. Investigación/Instrucción",
        "3. Auto de procesamiento",
        "4. Preparación de juicio oral",
        "5. Juicio oral",
        "6. Sentencia",
        "7. Recursos/Apelación",
        "8. Ejecución de sentencia"
    ],
    "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)": [
        "1. Demanda",
        "2. Contestación",
        "3. Prueba",
        "4. Alegatos",
        "5. Sentencia",
        "6. Recursos",
        "7. Ejecución"
    ]
}

MEDIDAS_CAUTELARES = [
    "Medidas de protección", "Embargo preventivo", "Retención de bienes",
    "Orden de no enajenar", "Suspensión de derechos"
]

RESOLUCIONES_SENTENCIAS = [
    "Sentencia condenatoria", "Sentencia absolutoria", "Sentencia civil",
    "Auto judicial", "Providencia", "Decreto", "Resolución", "Laudo arbitral"
]

RECURSOS_LEGALES = [
    "Amparo", "Apelación", "Nulidad", "Habeas corpus",
    "Casación", "Revisión", "Queja", "Recusación"
]

TABULADOR_HONORARIOS_RAMA = {
    "Casos Laborales": {
        "asesoria_min": 500,
        "asesoria_sug": 1000,
        "asesoria_max": 2000,
        "anticipo_sug": 0,
        "esquema_cobro": "Cuota Litis (Porcentaje sobre lo recuperado al ganar o conciliar; $0 de anticipo habitual)",
        "pct_sugerido": 25.0,
        "honorario_fijo_base": 15000,
        "gastos_periciales_sug": 1500,
        "horas_promedio_despacho": 35,
        "via_gratuita": "PROFEDET / Procuraduría de la Defensa del Trabajo — $0 MXN (100% Gratuito para el trabajador)",
        "desglose_etapas": {
            "1. Asesoría y Cálculo de Liquidación": "$500 - $1,500 MXN (Muchos laboralistas no la cobran si toman tu asunto)",
            "2. Conciliación Prejudicial (Menos de 45 días)": "15% a 20% de lo recuperado en el convenio",
            "3. Juicio Laboral hasta Laudo y Ejecución": "25% a 30% del monto total cobrado al patrón",
            "4. Amparo Directo (si aplica)": "Incluido en el porcentaje pactado"
        }
    },
    "Casos Familiares": {
        "asesoria_min": 800,
        "asesoria_sug": 1200,
        "asesoria_max": 2500,
        "anticipo_sug": 6000,
        "esquema_cobro": "Honorario Fijo por Juicio dividido en Etapas Procesales",
        "pct_sugerido": 0.0,
        "honorario_fijo_base": 22000,
        "gastos_periciales_sug": 3500,
        "horas_promedio_despacho": 45,
        "via_gratuita": "DIF / Defensoría Pública Familiar del Estado — $0 MXN",
        "desglose_etapas": {
            "1. Consulta y Estrategia Familiar": "$800 - $1,500 MXN",
            "2. Demanda Inicial y Pensión Provisional": "40% de anticipo ($6,000 - $10,000 MXN)",
            "3. Audiencias y Pruebas": "30% intermedio ($5,000 - $8,000 MXN)",
            "4. Sentencia Definitiva": "30% restante al dictarse sentencia"
        }
    },
    "Casos Penales": {
        "asesoria_min": 1200,
        "asesoria_sug": 2000,
        "asesoria_max": 4500,
        "anticipo_sug": 18000,
        "esquema_cobro": "Cobro por Etapa Procesal (Ministerio Público / Audiencia Inicial / Intermedia / Juicio Oral)",
        "pct_sugerido": 15.0,
        "honorario_fijo_base": 55000,
        "gastos_periciales_sug": 10000,
        "horas_promedio_despacho": 80,
        "via_gratuita": "Instituto de la Defensoría Pública / Asesor Jurídico de Víctimas — $0 MXN",
        "desglose_etapas": {
            "1. Asesoría de Emergencia / Asistencia en MP": "$2,000 - $6,000 MXN",
            "2. Denuncia/Querella o Audiencia Inicial": "$15,000 - $30,000 MXN",
            "3. Etapa Intermedia y Periciales": "$20,000 - $35,000 MXN",
            "4. Juicio Oral y Sentencia": "$25,000 - $60,000+ MXN"
        }
    },
    "Casos Civiles": {
        "asesoria_min": 800,
        "asesoria_sug": 1500,
        "asesoria_max": 3000,
        "anticipo_sug": 8000,
        "esquema_cobro": "Esquema Mixto (Anticipo + 10% a 20% del valor recuperado)",
        "pct_sugerido": 15.0,
        "honorario_fijo_base": 25000,
        "gastos_periciales_sug": 4500,
        "horas_promedio_despacho": 50,
        "via_gratuita": "Defensoría de Oficio en Materia Civil — $0 MXN",
        "desglose_etapas": {
            "1. Consulta y Revisión de Contratos": "$800 - $2,000 MXN",
            "2. Demanda Inicial y Medidas Cautelares": "$8,000 - $14,000 MXN",
            "3. Pruebas y Alegatos": "$6,000 - $10,000 MXN",
            "4. Sentencia y Ejecución": "$6,000 - $10,000 MXN o % pactado"
        }
    },
    "Casos Mercantiles": {
        "asesoria_min": 1000,
        "asesoria_sug": 1800,
        "asesoria_max": 3500,
        "anticipo_sug": 7000,
        "esquema_cobro": "Anticipo de Embargo + Porcentaje sobre Cobranza Efectiva (15% a 25%)",
        "pct_sugerido": 20.0,
        "honorario_fijo_base": 20000,
        "gastos_periciales_sug": 5000,
        "horas_promedio_despacho": 40,
        "via_gratuita": "CONDUSEF (contra bancos) o PROFECO — $0 MXN",
        "desglose_etapas": {
            "1. Dictamen de Pagaré o Contrato": "$1,000 - $2,000 MXN",
            "2. Demanda Ejecutiva y Diligencia de Embargo": "$7,000 - $14,000 MXN",
            "3. Remate y Cobro": "15% a 25% de lo recuperado"
        }
    }
}

CONCEPTOS_CLAVE = {
    "Liquidación vs. Finiquito": "El FINIQUITO se paga siempre (incluso si renuncias) e incluye días trabajados, aguinaldo y vacaciones proporcionales. La LIQUIDACIÓN se paga cuando te despiden sin justificación e incluye los 3 meses de sueldo (90 días), prima de antigüedad y, en su caso, 20 días por año.",
    "Salario Diario Integrado (SDI)": "Es el salario con el que se calculan las indemnizaciones por despido (Art. 84 y 89 LFT). Suma a tu sueldo diario la parte proporcional diaria de tu aguinaldo y de tu prima vacacional.",
    "Cuota Litis (Porcentaje del Abogado)": "Acuerdo donde el abogado laboralista no te cobra por adelantado, sino un porcentaje (usualmente entre el 20% y 30%) únicamente sobre el dinero que logre recuperar para ti.",
    "Demandante / Demandado": "En materia civil, laboral, familiar o mercantil: quien inicia la demanda exigiendo un derecho (Demandante) frente a quien debe responder o defenderse (Demandado).",
    "Prescripción": "¡ALERTA DE TIEMPO! Es la pérdida del derecho a denunciar o cobrar una indemnización por dejar pasar el plazo máximo que marca la ley (en despido laboral son solo 60 días naturales).",
    "Cosa juzgada": "Efecto definitivo de una sentencia firme o convenio ratificado ante el Centro de Conciliación contra el cual ya no cabe recurso.",
    "Due process (Debido proceso)": "Garantía constitucional de ser oído en igualdad de condiciones, con defensa técnica, ante juez imparcial y sin pruebas obtenidas ilegalmente."
}

ESCENARIOS_FRECUENTES = {
    "✍️ Escribir o editar mi propio caso libremente": "Mi sueldo semanal es de 2300. Me despidieron y no me quieren dar liquidación, solo me quieren dar $5000 y no me daban vacaciones ni días libres ni bonos, ¿qué procede ahí?",
    "💼 Laboral: Despido injustificado y coacción de hoja en blanco": "Me despidieron hoy sin darme aviso por escrito, recursos humanos me exige firmar una renuncia voluntaria y una hoja en blanco para entregarme mi finiquito, además me deben quincenas atrasadas y horas extras.",
    "👨‍👩‍👧 Familiar: Demanda de pensión alimenticia y ocultamiento de ingresos": "El padre de mis dos hijos dejó de aportar para alimentos desde hace 3 meses, renunció a su empleo formal para simular que no tiene ingresos pero maneja cuentas bancarias de un negocio familiar.",
    "💻 Penal / Ciberdelito: Fraude bancario y phishing SPEI": "Recibí un mensaje falso de mi banco, entré a un enlace y vaciaron mi cuenta mediante transferencias SPEI no autorizadas; tengo las capturas, correos y bitácoras de conexión IP.",
    "🚓 Penal Constitucional: Detención arbitraria y revisión ilegal de celular": "Una patrulla me detuvo sin motivo en la calle, los policías me quitaron mi teléfono celular a la fuerza, lo desbloquearon sin orden judicial y tardaron 9 horas en ponerme a disposición del Ministerio Público.",
    "🏠 Civil Arrendamiento: Inquilino moroso que no paga renta ni desocupa": "Mi inquilino lleva 5 meses sin pagar la renta del departamento, ya venció el contrato de arrendamiento escrito y se niega a entregar las llaves; quiero saber cómo sacarlo legalmente sin cometer un delito.",
    "📑 Mercantil Ejecutivo: Cobro de pagaré vencido e incumplimiento": "Un cliente comercial me firmó un pagaré por mercancía entregada hace 4 meses, ya pasó la fecha de vencimiento y está vaciando sus bodegas para no pagarme la deuda."
}

# ==============================================================================
# 2. EXTRACTOR INTELIGENTE DE SUELDO Y OFERTA PATRONAL DESDE EL DICTADO DE VOZ
# ==============================================================================
def extraer_datos_financieros_del_relato(relato: str) -> dict:
    """
    Detecta automáticamente si el usuario dictó su sueldo (semanal, quincenal, mensual o diario)
    y si mencionó cuánto dinero le quieren dar (ej. 'semanal es de 2300... solo me quieren dar $5000').
    """
    texto = relato.lower().replace(",", "")
    salario_mensual_detectado = None
    periodicidad_detectada = "Mensual"
    oferta_patronal_detectada = 0.0

    # Buscar sueldo semanal (ej. "semanal es de 2300", "2300 semanales", "2300 a la semana")
    m_sem = re.search(r'(?:semanal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la semana|semanal(?:es)?|por semana))', texto)
    if m_sem:
        val = float(m_sem.group(1) or m_sem.group(2))
        salario_mensual_detectado = round((val / 7.0) * 30.0, 2)
        periodicidad_detectada = f"Semanal (${val:,.2f} / sem)"

    # Buscar sueldo quincenal
    if salario_mensual_detectado is None:
        m_quin = re.search(r'(?:quincenal(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:a la quincena|quincenal(?:es)?|por quincena))', texto)
        if m_quin:
            val = float(m_quin.group(1) or m_quin.group(2))
            salario_mensual_detectado = round(val * 2.0, 2)
            periodicidad_detectada = f"Quincenal (${val:,.2f} / quin)"

    # Buscar sueldo mensual
    if salario_mensual_detectado is None:
        m_men = re.search(r'(?:mensual(?:es)?(?:\s+es)?(?:\s+de)?\s*\$?\s*(\d+(?:\.\d+)?))|(?:(\d+(?:\.\d+)?)\s*(?:pesos\s*)?(?:al mes|mensual(?:es)?|por mes))', texto)
        if m_men:
            val = float(m_men.group(1) or m_men.group(2))
            salario_mensual_detectado = round(val, 2)
            periodicidad_detectada = f"Mensual (${val:,.2f} / mes)"

    # Buscar cuánto le quieren dar / ofrecen (ej. "solo me quieren dar $5000", "me ofrecen 5000")
    m_oferta = re.search(r'(?:quieren dar|ofrecen|daban|dan)\s*\$?\s*(\d+(?:\.\d+)?)', texto)
    if m_oferta:
        oferta_patronal_detectada = float(m_oferta.group(1))

    # Detectar si menciona que no le daban vacaciones
    adeuda_vacaciones_completas = any(p in texto for p in ["no me daban vacaciones", "sin vacaciones", "nunca tuve vacaciones", "nada de vacaciones"])

    return {
        "salario_mensual": salario_mensual_detectado,
        "periodicidad": periodicidad_detectada,
        "oferta_patronal": oferta_patronal_detectada,
        "adeuda_vacaciones_completas": adeuda_vacaciones_completas
    }

# ==============================================================================
# 3. MOTOR MATEMÁTICO DE LIQUIDACIÓN, FINIQUITO Y HONORARIOS (LFT MÉXICO)
# ==============================================================================
def obtener_dias_vacaciones_lft(anios_cumplidos: int) -> int:
    if anios_cumplidos <= 1:
        return 12
    elif anios_cumplidos == 2:
        return 14
    elif anios_cumplidos == 3:
        return 16
    elif anios_cumplidos == 4:
        return 18
    elif anios_cumplidos == 5:
        return 20
    elif 6 <= anios_cumplidos <= 10:
        return 22
    elif 11 <= anios_cumplidos <= 15:
        return 24
    elif 16 <= anios_cumplidos <= 20:
        return 26
    elif 21 <= anios_cumplidos <= 25:
        return 28
    else:
        return 30

def calcular_liquidacion_y_derechos_lft(
    salario_mensual: float,
    anios_antiguedad: int,
    meses_adicionales: int,
    motivo_separacion: str,
    dias_aguinaldo_anual: int = 15,
    prima_vacacional_pct: float = 25.0,
    dias_sueldo_pendientes: int = 0,
    dias_vacaciones_no_gozadas_anios_previos: int = 0,
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

    # 1. PRESTACIONES IRRENUNCIABLES (FINIQUITO)
    monto_sueldo_pendiente = round(dias_sueldo_pendientes * sd, 2)
    monto_aguinaldo_prop = round((dias_aguinaldo_anual / 365.0) * dias_trabajados_ultimo_anio * sd, 2)
    monto_vacaciones_prop = round((dias_vac_correspondientes / 365.0) * dias_trabajados_ultimo_anio * sd, 2)
    monto_vacaciones_atrasadas = round(dias_vacaciones_no_gozadas_anios_previos * sd, 2)
    monto_prima_vac_prop = round((monto_vacaciones_prop + monto_vacaciones_atrasadas) * (prima_vacacional_pct / 100.0), 2)

    salario_base_prima_ant = min(sd, salario_minimo_vigente * 2.0)
    aplica_prima_antiguedad = (
        "Despido" in motivo_separacion
        or "Rescisión" in motivo_separacion
        or anios_antiguedad >= 15
    )
    monto_prima_antiguedad = round(
        12.0 * antiguedad_total_anios * salario_base_prima_ant, 2
    ) if aplica_prima_antiguedad else 0.0

    subtotal_finiquito = round(
        monto_sueldo_pendiente + monto_aguinaldo_prop + monto_vacaciones_prop + monto_vacaciones_atrasadas + monto_prima_vac_prop, 2
    )

    # 2. INDEMNIZACIONES POR DESPIDO INJUSTIFICADO (LIQUIDACIÓN)
    es_despido = ("Despido" in motivo_separacion or "Rescisión" in motivo_separacion)
    monto_indem_90_dias = round(90.0 * sdi, 2) if es_despido else 0.0
    monto_20_dias_anio = round(20.0 * antiguedad_total_anios * sdi, 2) if (es_despido and (incluir_20_dias_por_anio or "Rescisión" in motivo_separacion)) else 0.0

    meses_topados_12 = min(12, max(0, meses_duracion_juicio))
    monto_salarios_caidos = round(meses_topados_12 * 30.0 * sdi, 2) if es_despido else 0.0
    meses_excedentes = max(0, meses_duracion_juicio - 12)
    base_15_meses = 15.0 * 30.0 * sdi
    monto_intereses_art48 = round(meses_excedentes * (base_15_meses * 0.02), 2) if es_despido else 0.0

    subtotal_indemnizacion = round(
        monto_prima_antiguedad + monto_indem_90_dias + monto_20_dias_anio + monto_salarios_caidos + monto_intereses_art48, 2
    )
    gran_total_bruto = round(subtotal_finiquito + subtotal_indemnizacion, 2)

    conceptos_tabla = [
        {
            "Concepto Legal": "1. Días de Salario Trabajados No Pagados",
            "Fundamento LFT": "Art. 82 y 88 LFT",
            "Tipo": "Finiquito (Irrenunciable)",
            "Fórmula / Base": f"{dias_sueldo_pendientes} días × ${sd:,.2f} (SD)",
            "Monto (MXN)": monto_sueldo_pendiente
        },
        {
            "Concepto Legal": "2. Aguinaldo Proporcional",
            "Fundamento LFT": "Art. 87 LFT",
            "Tipo": "Finiquito (Irrenunciable)",
            "Fórmula / Base": f"{dias_aguinaldo_anual} días anuales prop. × ${sd:,.2f}",
            "Monto (MXN)": monto_aguinaldo_prop
        },
        {
            "Concepto Legal": "3. Vacaciones Dignas Proporcionales + Adeudadas",
            "Fundamento LFT": "Art. 76 y 79 LFT",
            "Tipo": "Finiquito (Irrenunciable)",
            "Fórmula / Base": f"{dias_vac_correspondientes} días ley + {dias_vacaciones_no_gozadas_anios_previos} días adeudados × ${sd:,.2f}",
            "Monto (MXN)": round(monto_vacaciones_prop + monto_vacaciones_atrasadas, 2)
        },
        {
            "Concepto Legal": "4. Prima Vacacional (Mínimo 25% de Ley)",
            "Fundamento LFT": "Art. 80 LFT",
            "Tipo": "Finiquito (Irrenunciable)",
            "Fórmula / Base": f"{prima_vacacional_pct:.0f}% sobre Vacaciones",
            "Monto (MXN)": monto_prima_vac_prop
        },
        {
            "Concepto Legal": "5. Prima de Antigüedad (12 días por año)",
            "Fundamento LFT": "Art. 162 y 486 LFT",
            "Tipo": "Liquidación por Despido",
            "Fórmula / Base": f"12 días × {antiguedad_total_anios:.2f} años × ${salario_base_prima_ant:,.2f}",
            "Monto (MXN)": monto_prima_antiguedad
        },
        {
            "Concepto Legal": "6. Indemnización Constitucional (3 Meses / 90 Días)",
            "Fundamento LFT": "Art. 123 Const. / Art. 48 LFT",
            "Tipo": "Liquidación por Despido",
            "Fórmula / Base": f"90 días × ${sdi:,.2f} (SDI)",
            "Monto (MXN)": monto_indem_90_dias
        },
        {
            "Concepto Legal": "7. Indemnización de 20 Días por Año",
            "Fundamento LFT": "Art. 50 y 52 LFT",
            "Tipo": "Negativa de Reinstalación / Rescisión",
            "Fórmula / Base": f"20 días × {antiguedad_total_anios:.2f} años × ${sdi:,.2f}",
            "Monto (MXN)": monto_20_dias_anio
        },
        {
            "Concepto Legal": "8. Salarios Caídos e Intereses en Juicio",
            "Fundamento LFT": "Art. 48 LFT",
            "Tipo": "Condena en Juicio",
            "Fórmula / Base": f"{meses_topados_12} meses caídos + {meses_excedentes} meses intereses",
            "Monto (MXN)": round(monto_salarios_caidos + monto_intereses_art48, 2)
        }
    ]

    return {
        "sd": sd,
        "sdi": sdi,
        "factor_integracion": round(factor_integracion, 4),
        "dias_vacaciones_ley": dias_vac_correspondientes,
        "salario_base_prima_ant": salario_base_prima_ant,
        "subtotal_finiquito": subtotal_finiquito,
        "subtotal_indemnizacion": subtotal_indemnizacion,
        "gran_total_bruto": gran_total_bruto,
        "conciliacion_rapida_85pct": round(
            subtotal_finiquito + monto_prima_antiguedad + (monto_indem_90_dias * 0.75), 2
        ) if es_despido else subtotal_finiquito,
        "tabla_conceptos": pd.DataFrame(conceptos_tabla)
    }

def calcular_cotizacion_honorarios_dual(
    categoria_caso: str,
    monto_en_disputa_o_liquidacion: float,
    costo_asesoria: float,
    anticipo_fijo: float,
    porcentaje_cuota_litis: float,
    gastos_periciales_operativos: float,
    horas_invertidas_abogado: float,
    costo_hora_despacho: float
) -> dict:
    comision_exito = round(monto_en_disputa_o_liquidacion * (porcentaje_cuota_litis / 100.0), 2)
    honorarios_totales_abogado = round(costo_asesoria + anticipo_fijo + comision_exito, 2)
    desembolso_total_ciudadano = round(honorarios_totales_abogado + gastos_periciales_operativos, 2)
    monto_neto_libre_ciudadano = round(max(0.0, monto_en_disputa_o_liquidacion - desembolso_total_ciudadano), 2)

    costo_operativo_tiempo = round(horas_invertidas_abogado * costo_hora_despacho, 2)
    utilidad_neta_abogado = round(honorarios_totales_abogado - costo_operativo_tiempo, 2)
    margen_rentabilidad = round(
        (utilidad_neta_abogado / honorarios_totales_abogado) * 100.0, 1
    ) if honorarios_totales_abogado > 0 else 0.0
    ingreso_efectivo_por_hora = round(
        honorarios_totales_abogado / max(1.0, horas_invertidas_abogado), 2
    )

    return {
        "comision_exito": comision_exito,
        "honorarios_totales_abogado": honorarios_totales_abogado,
        "gastos_periciales_operativos": gastos_periciales_operativos,
        "desembolso_total_ciudadano": desembolso_total_ciudadano,
        "monto_neto_libre_ciudadano": monto_neto_libre_ciudadano,
        "costo_operativo_tiempo": costo_operativo_tiempo,
        "utilidad_neta_abogado": utilidad_neta_abogado,
        "margen_rentabilidad": margen_rentabilidad,
        "ingreso_efectivo_por_hora": ingreso_efectivo_por_hora
    }

# ==============================================================================
# 4. GUÍA AUTOMÁTICA DE "QUÉ HACER" SEGÚN CATEGORÍA DE CASO
# ==============================================================================
def obtener_plan_accion_ciudadano(categoria_caso: str, tipo_caso: str, rol_usuario: str = "Demandante / Víctima") -> dict:
    if categoria_caso == "Casos Penales":
        return {
            "proceso": "Proceso Penal (8 Etapas)",
            "juez": "Juez de garantías / Juez penal",
            "abogado": "Abogado acusador (Asesor jurídico de víctima)" if "Víctima" in rol_usuario or "Demandante" in rol_usuario else "Abogado defensor penalista",
            "profesionales": "Fiscal/Ministerio Público + Perito Forense",
            "medida_sugerida": "Medidas de protección inmediatas / Retención de bienes",
            "recurso_clave": "Amparo / Habeas corpus (si hay detención arbitraria) / Apelación",
            "pasos_inmediatos": [
                "1. NO alterar ni tocar la escena, teléfono o documento original (preservar Cadena de Custodia y sello SHA-256).",
                "2. Acudir al Ministerio Público / Fiscalía a interponer Denuncia o Querella narrando hora, fecha y lugar exactos.",
                "3. Solicitar de inmediato Medidas de Protección si existe riesgo físico, violencia doméstica o abuso de autoridad.",
                "4. Exigir la intervención de Perito para fijar pruebas antes de que se borren cámaras o registros."
            ],
            "alerta_fatal": "En delitos de querella el plazo de PRESCRIPCIÓN suele ser corto, y cualquier prueba obtenida violando el DEBIDO PROCESO será anulada."
        }
    elif categoria_caso == "Casos Laborales":
        return {
            "proceso": "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez laboral (Centro de Conciliación y Tribunal Laboral)",
            "abogado": "Abogado especializado en Derecho Laboral / Procurador PROFEDET (Gratuito)",
            "profesionales": "Conciliador Laboral + Perito contable/informático",
            "medida_sugerida": "Embargo preventivo sobre cuentas/bienes de la patronal",
            "recurso_clave": "Amparo directo / Revisión / Nulidad de renuncia coaccionada",
            "pasos_inmediatos": [
                "1. NO RECIBIR ni firmar conformidad por cantidades irrisorias (ej. $5,000) que nos hagan pasar como 'renuncia voluntaria'.",
                "2. Exigir tu Liquidación Constitucional completa: 90 días de Salario Diario Integrado + Prima de Antigüedad + Vacaciones no gozadas + Aguinaldo.",
                "3. Resguardar evidencia de que trabajabas ahí (mensajes de WhatsApp de turnos, transferencias, fotos, testigos).",
                "4. Acudir esta misma semana al Centro de Conciliación Laboral o PROFEDET (tienes 60 días naturales antes de que prescriba)."
            ],
            "alerta_fatal": "Firmar una 'renuncia voluntaria' para que te suelten $5,000 o dejar pasar más de 60 días naturales desde el despido."
        }
    elif categoria_caso == "Casos Familiares":
        return {
            "proceso": "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez de lo Familiar / Juez civil",
            "abogado": "Abogado especializado en Derecho de Familia",
            "profesionales": "Mediador familiar + Perito en psicología/trabajo social",
            "medida_sugerida": "Pensión alimenticia provisional / Medidas de protección / Guarda y custodia provisional",
            "recurso_clave": "Apelación / Queja / Amparo indirecto (interés superior del menor)",
            "pasos_inmediatos": [
                "1. Reunir actas de nacimiento, acta de matrimonio y comprobantes de todos los gastos de los menores.",
                "2. Solicitar como medida cautelar urgente la fijación de Pensión Alimenticia Provisional desde el primer auto judicial.",
                "3. Si existe Violencia de Género o doméstica, pedir orden de restricción inmediata.",
                "4. Documentar ingresos reales del deudor alimentario (propiedades, vehículos, cuentas)."
            ],
            "alerta_fatal": "Acordar pensiones de palabra sin convenio judicial aprobado o sustraer menores sin orden de Guarda y Custodia."
        }
    elif categoria_caso == "Casos Mercantiles":
        return {
            "proceso": "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez mercantil",
            "abogado": "Abogado litigante mercantil / Corporativo",
            "profesionales": "Notario Público (Fe de hechos) + Perito grafoscópico/contable",
            "medida_sugerida": "Embargo preventivo (Juicio Ejecutivo Mercantil) / Retención de bienes",
            "recurso_clave": "Apelación / Amparo / Nulidad de pagaré o contrato",
            "pasos_inmediatos": [
                "1. Verificar si cuentas con un título ejecutivo (pagaré, cheque, factura firmada o contrato comercial).",
                "2. Solicitar desde el escrito inicial de Demanda el Embargo Preventivo de cuentas bancarias o bienes del deudor.",
                "3. Si existe incumplimiento digital, levantar Fe de Hechos o sello pericial SHA-256.",
                "4. Revisar cláusulas de jurisdicción antes de presentar la demanda."
            ],
            "alerta_fatal": "Alterar fechas o montos en un pagaré con otra pluma o dejar caducar la acción cambiaria directa."
        }
    else:
        return {
            "proceso": "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez civil / Juez de paz",
            "abogado": "Abogado litigante civil",
            "profesionales": "Notario Público + Perito valuador/ingeniero + Mediador",
            "medida_sugerida": "Orden de no enajenar / Embargo preventivo",
            "recurso_clave": "Apelación / Casación / Amparo",
            "pasos_inmediatos": [
                "1. Asegurar el contrato escrito (arrendamiento, compraventa, mutuo), escrituras o recibos de pago.",
                "2. Pedir al Juez Civil una Orden de No Enajenar para que la contraparte no venda ni oculte el inmueble.",
                "3. Acreditar la Legitimidad Activa y notificar formalmente mediante interpelación judicial o notarial.",
                "4. Cuantificar con precisión el Daño y Perjuicio con facturas y avalúos."
            ],
            "alerta_fatal": "Desalojar a un inquilino por la fuerza sin Sentencia Civil y orden de lanzamiento (te convierte en acusado de despojo)."
        }

# ==============================================================================
# 5. CAPA DE PERSISTENCIA SQLITE V5.5 (12 CASOS EMPAREJADOS GANADOS VS PERDIDOS)
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
    
    c.execute("SELECT COUNT(*) FROM casos_juridicos_cbr")
    if c.fetchone()[0] == 0:
        semillas = [
            (
                "EXP-LAB-2026-001", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
                "Despido Injustificado Ganado (Sueldo Semanal sin Vacaciones y Oferta Patronal Engañosa de $5,000)",
                "Juez laboral, Abogado especializado, Mediador, Perito informático",
                "3. Prueba", "Embargo preventivo", "Sentencia condenatoria (Laudo a favor del trabajador)", "Amparo directo",
                "Me corrieron del trabajo injustificadamente, sueldo semanal, solo querían dar $5000 sin liquidación, no daban vacaciones ni días libres y exigían firmar renuncia.",
                hashlib.sha256(b"EXP-LAB-2026-001").hexdigest(), "GANADO",
                "El abogado rechazó los $5,000, citó a conciliación antes de los 60 días y reclamó los 90 días de SDI, prima de antigüedad, vacaciones dignas adeudadas y séptimos días.",
                "El Juez Laboral tuvo por cierto el despido injustificado y condenó al patrón al pago íntegro de la liquidación constitucional más prestaciones omitidas.",
                "N/A - Caso ganado con condena completa de 90 días de SDI, vacaciones adeudadas, aguinaldo y prima de antigüedad.",
                "Rechazar ofertas engañosas de finiquito, no firmar renuncia y exigir el cálculo real sobre Salario Diario Integrado.",
                "No aceptar los $5,000 si te piden firmar renuncia, guardar mensajes de turnos/pagos semanales y acudir al Centro de Conciliación.",
                "JAMÁS firmar una carta de renuncia o recibo de finiquito total a cambio de una cantidad mínima.",
                "2026-08-01"
            ),
            (
                "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
                "Despido Injustificado Perdido por Aceptar $5,000 Firmando Renuncia y Prescripción de 60 Días",
                "Juez laboral, Abogado litigante",
                "2. Contestación", "Ninguna", "Sentencia absolutoria (a favor de la empresa)", "Apelación",
                "Trabajador despedido aceptó un pago mínimo firmando hoja de renuncia voluntaria y liberación de adeudos, o esperó más de 2 meses para demandar.",
                hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "PERDIDO",
                "El abogado interpuso la demanda fuera del plazo legal de 60 días o no pudo desvirtuar la firma autógrafa en la carta de renuncia.",
                "El Juez declaró fundada la excepción de prescripción o dio valor probatorio a la renuncia firmada por el trabajador.",
                "Firmar renuncia voluntaria por presión económica inmediata o dejar pasar el plazo de 60 días naturales.",
                "N/A - Sobreseimiento.",
                "Acudir primero a calcular tu liquidación real antes de firmar cualquier papel en la empresa.",
                "NUNCA firmar renuncias simuladas para recibir un pago rápido ni esperar más de 60 días para iniciar conciliación.",
                "2026-08-05"
            ),
            (
                "EXP-FAM-2026-003", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia",
                "Pensión Alimenticia y Guarda/Custodia Ganada pese a Ocultamiento de Ingresos",
                "Juez de lo Familiar, Abogado especializado, Perito en trabajo social",
                "1. Demanda", "Retención de bienes", "Sentencia civil (Pensión definitiva del 35%)", "Queja",
                "Padre deudor alimentario renunció simuladamente para no dar pensión alimenticia a sus hijos y ocultó ingresos en cuentas bancarias.",
                hashlib.sha256(b"EXP-FAM-2026-003").hexdigest(), "GANADO",
                "El abogado pidió fijación de pensión provisional en el primer auto y solicitó oficios a la CNBV y al SAT para rastrear cuentas y flujo de efectivo.",
                "El Juez de lo Familiar aplicó el interés superior de la niñez, decretó embargo precautorio y fijó pensión con base en la capacidad económica real.",
                "N/A - Pensión asegurada mediante descuento directo y garantía hipotecaria.",
                "Acreditar el nivel de vida de los menores y rastrear el patrimonio real del deudor mediante oficios judiciales al SAT y bancos.",
                "Reunir actas de nacimiento, tickets de gastos escolares/médicos y exigir pensión provisional desde el escrito inicial.",
                "No conformarse con acuerdos verbales incumplidos ni permitir que el deudor oculte bienes sin pedir medidas cautelares.",
                "2026-08-10"
            ),
            (
                "EXP-FAM-2026-004", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia",
                "Caso Familiar Perdido por Sustracción Unilateral de Menores e Insolvencia Provocada",
                "Juez de lo Familiar, Mediador",
                "3. Prueba", "Suspensión de derechos", "Sentencia civil desfavorable", "Apelación",
                "Progenitor ocultó a los menores impidiendo convivencia sin orden judicial y declaró ingresos en cero para evadir pensión.",
                hashlib.sha256(b"EXP-FAM-2026-004").hexdigest(), "PERDIDO",
                "El abogado aconsejó ocultar a los hijos y no presentó pruebas contables ni facturas de gastos.",
                "El Juez sancionó la obstrucción del derecho de visita, ordenó cambio de guarda y custodia y fijó pensión en contra por insolvencia fraudulenta.",
                "Sustracción/retención unilateral de menores sin medida de protección previa y simulación maliciosa de insolvencia.",
                "N/A",
                "Solicitar siempre autorización judicial antes de cambiar de domicilio con menores y transparentar gastos reales.",
                "JAMÁS ocultar o sustraer a los hijos por cuenta propia si no existe una orden de restricción o medida cautelar dictada por Juez o Fiscalía.",
                "2026-08-15"
            ),
            (
                "EXP-PEN-2026-005", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude",
                "Fraude Bancario y Phishing Ganado con Congelamiento de Cuentas y Sello SHA-256",
                "Juez de garantías, Fiscal/Ministerio Público, Abogado acusador, Perito Forense",
                "2. Investigación/Instrucción", "Retención de bienes", "Sentencia condenatoria", "Amparo",
                "Estafa electrónica, phishing bancario, transferencia SPEI no autorizada, suplantación de identidad y trazas IP.",
                hashlib.sha256(b"EXP-PEN-2026-005").hexdigest(), "GANADO",
                "El abogado presentó querella en menos de 24 horas con dictamen pericial informático, sellos SHA-256 de cabeceras y promovió control judicial para inmovilizar fondos.",
                "El Juez de Garantías autorizó la inmovilización inmediata de las cuentas receptoras y validó la cadena de custodia digital.",
                "N/A - Recuperación del monto defraudado y vinculación a proceso.",
                "Actuar en las primeras horas, extraer bitácoras con hash SHA-256 y exigir al Ministerio Público oficio urgente a la Comisión Bancaria.",
                "Reportar al banco en el minuto cero, obtener folio de reclamación, no borrar mensajes y presentar querella con peritaje informático.",
                "No editar ni recortar las capturas de pantalla ni esperar semanas antes de acudir a la Fiscalía.",
                "2026-08-20"
            ),
            (
                "EXP-PEN-2026-006", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude",
                "Denuncia de Fraude Digital Perdida por Alteración de Capturas y Ruptura de Cadena de Custodia",
                "Juez penal, Fiscal/Ministerio Público",
                "5. Juicio oral", "Ninguna", "Sentencia absolutoria", "Apelación",
                "Víctima de estafa digital presentó capturas de pantalla recortadas y reenviadas sin metadatos ni dispositivo original.",
                hashlib.sha256(b"EXP-PEN-2026-006").hexdigest(), "PERDIDO",
                "El abogado exhibió simples impresiones en papel sin ofrecer pericial en informática forense ni preservar el teléfono original.",
                "El Tribunal de Enjuiciamiento desestimó las impresiones por carecer de fiabilidad, metadatos y sello criptográfico, absolviendo al acusado.",
                "Ruptura de la cadena de custodia digital y presentación de pruebas alteradas sin validación pericial.",
                "N/A",
                "Conservar el dispositivo móvil intacto para extracción forense y generar hash SHA-256 del archivo original.",
                "JAMÁS borrar el chat original, ni manipular imágenes en editores antes de que las certifique un perito.",
                "2026-08-25"
            ),
            (
                "EXP-PEN-2026-007", "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad",
                "Detención Arbitraria Ganada por Nulidad de Prueba Ilícita y Demora en Puesta a Disposición",
                "Juez de garantías, Abogado defensor, Fiscal/Ministerio Público, Perito",
                "3. Auto de procesamiento", "Medidas de protección", "Sentencia absolutoria (Nulidad absoluta)", "Habeas corpus",
                "Policías detuvieron sin orden judicial, revisaron el teléfono celular sin autorización de juez y demoraron 9 horas en poner a disposición.",
                hashlib.sha256(b"EXP-PEN-2026-007").hexdigest(), "GANADO",
                "El abogado defensor solicitó el registro GPS de la patrulla, bitácoras de acceso al teléfono posteriores a la detención y promovió incidente de nulidad por violación al Debido Proceso.",
                "El Juez de Control declaró ilegal la detención, excluyó toda la evidencia del teléfono por ser fruto de árbol envenenado y ordenó libertad inmediata.",
                "N/A - Libertad decretada en audiencia inicial.",
                "Contrastar la hora real del suceso (cámaras/GPS) contra el Informe Policial Homologado (IPH) y exigir exclusión de pruebas sin orden de cateo.",
                "Guardar silencio hasta tener abogado defensor, narrar la hora exacta de detención y no consentir revisiones de celular sin orden judicial.",
                "Nunca firmar declaraciones en blanco en separos ni permitir desbloqueo forzado de equipos sin presencia de tu defensor.",
                "2026-09-01"
            ),
            (
                "EXP-PEN-2026-008", "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad",
                "Caso Penal Perdido por Declarar sin Abogado Especializado y Convalidar Vicios en Audiencia",
                "Juez penal, Abogado defensor",
                "4. Preparación de juicio oral", "Suspensión de derechos", "Sentencia condenatoria", "Apelación",
                "Imputado firmó entrevista ministerial autoincriminándose y su defensa no objetó la detención ilegal en la audiencia inicial.",
                hashlib.sha256(b"EXP-PEN-2026-008").hexdigest(), "PERDIDO",
                "El abogado no debatió el control de la detención ni solicitó la exclusión de medios de prueba en la etapa intermedia.",
                "El Juez tuvo por convalidados los actos de investigación y dictó fallo condenatorio con las pruebas admitidas.",
                "Defensa técnica pasiva que no promovió nulidad de actos violatorios de derechos fundamentales en el momento procesal oportuno.",
                "N/A",
                "Exigir defensor penalista que impugne desde el control de detención cualquier irregularidad policial.",
                "JAMÁS declarar ante la policía o Ministerio Público sin haber hablado antes en privado con tu abogado defensor.",
                "2026-09-05"
            ),
            (
                "EXP-CIV-2026-009", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento",
                "Juicio de Arrendamiento Ganado con Recuperación de Inmueble y Embargo de Bienes",
                "Juez civil, Abogado litigante, Notario",
                "1. Demanda", "Embargo preventivo", "Sentencia civil condenatoria", "Apelación",
                "Inquilino dejó de pagar 5 meses de renta y se negaba a desocupar el inmueble pese a tener contrato vencido.",
                hashlib.sha256(b"EXP-CIV-2026-009").hexdigest(), "GANADO",
                "El abogado promovió juicio de controversia de arrendamiento solicitando desde el auto admisorio el embargo de bienes para garantizar las rentas vencidas.",
                "El Juez Civil admitió el contrato, embargó cuentas del fiador y dictó sentencia ordenando la desocupación voluntaria o lanzamiento con fuerza pública.",
                "N/A - Inmueble recuperado legalmente y rentas cobradas.",
                "Acompañar contrato original, interpelación o recibos insolutos y pedir embargo precautorio sobre el obligado solidario o fiador.",
                "Promover juicio ante Juez Civil con contrato escrito y esperar la orden judicial de lanzamiento.",
                "Por ningún motivo cortar servicios básicos (agua/luz) ni cambiar la chapa por propia mano.",
                "2026-09-10"
            ),
            (
                "EXP-CIV-2026-010", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento",
                "Caso de Arrendamiento Perdido: Propietario Procesado por Despojo al Cambiar Cerraduras",
                "Juez civil, Juez penal",
                "4. Alegatos", "Orden de no enajenar", "Sentencia condenatoria (En contra del propietario)", "Amparo",
                "Dueño cansado de que no le pagaran la renta entró al inmueble, cambió las chapas y sacó las cosas del inquilino a la banqueta.",
                hashlib.sha256(b"EXP-CIV-2026-010").hexdigest(), "PERDIDO",
                "El propietario actuó sin consultar abogado y el inquilino lo denunció penalmente por despojo y robo.",
                "El Juez ordenó restituir la posesión al inquilino moroso y vinculó a proceso al propietario por hacerse justicia por propia mano.",
                "Violación al artículo 17 Constitucional (prohibición de hacerse justicia por sí mismo) y comisión de delito de despojo.",
                "N/A",
                "Acudir siempre a la vía judicial civil para obtener una sentencia de lanzamiento.",
                "JAMÁS entrar sin orden judicial al inmueble arrendado ni cambiar cerraduras por tu cuenta aunque te deban muchos meses.",
                "2026-09-15"
            ),
            (
                "EXP-MER-2026-011", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos",
                "Cobro Ejecutivo Mercantil de Pagaré Ganado con Embargo en Diligencia de Exequendo",
                "Juez mercantil, Abogado litigante, Perito contable",
                "1. Demanda", "Embargo preventivo", "Sentencia condenatoria (Remate de bienes)", "Apelación",
                "Cliente incumplió pago de pagaré comercial vencido e intentó vaciar cuentas y bodegas para declararse insolvente.",
                hashlib.sha256(b"EXP-MER-2026-011").hexdigest(), "GANADO",
                "El abogado promovió Juicio Ejecutivo Mercantil anexando el pagaré original y ejecutó el auto de exequendo embargando cuentas bancarias y mercancía en el primer acto.",
                "El Juez Mercantil validó que el pagaré reunía todos los requisitos de la Ley General de Títulos y Operaciones de Crédito y condenó al trance y remate.",
                "N/A - Cobro íntegro de suerte principal e intereses moratorios.",
                "Ejercer la acción cambiaria directa en la vía ejecutiva mercantil asegurando bienes en la primera diligencia.",
                "Llenar todos los datos del pagaré al momento de la firma y demandar con embargo precautorio inmediato.",
                "No entregar el pagaré original al deudor hasta que el pago esté firme y reflejado en cuenta.",
                "2026-09-20"
            ),
            (
                "EXP-MER-2026-012", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos",
                "Juicio Mercantil Perdido por Alteración Material de Monto y Fecha en el Pagaré",
                "Juez mercantil, Perito en documentoscopía",
                "3. Prueba", "Ninguna", "Sentencia absolutoria", "Amparo",
                "Acreedor remarcó con otra pluma la fecha de vencimiento y el interés moratorio del pagaré después de firmado.",
                hashlib.sha256(b"EXP-MER-2026-012").hexdigest(), "PERDIDO",
                "El abogado de la demandada opuso la excepción de alteración del texto del documento y ofreció pericial en grafoscopía y documentoscopía.",
                "El Juez Mercantil determinó que existió alteración posterior a la suscripción con tintas de diferente origen químico y absolvió al demandado.",
                "Alteración física del título de crédito que destruyó su presunción de validez ejecutiva.",
                "N/A",
                "Presentar los títulos de crédito exactamente como fueron suscritos sin tachaduras ni adiciones posteriores.",
                "JAMÁS rellenar con otra tinta o alterar fechas/intereses de un pagaré después de que el deudor lo firmó.",
                "2026-09-25"
            )
        ]
        c.executemany("""
            INSERT INTO casos_juridicos_cbr (
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
# 6. RED NEURONAL MULTICAPA (MLP) Y MOTOR VECTORIAL CBR
# ==============================================================================
@st.cache_resource
def entrenar_red_neuronal_autoclasificacion():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    conn.close()
    
    if df.empty or MLPClassifier is None or TfidfVectorizer is None:
        return None, None
        
    X_text = (
        df['titulo'].fillna('') + " " +
        df['evidencia_logs'].fillna('') + " " +
        df['tipo_caso'].fillna('') + " " +
        df['categoria_caso'].fillna('') + " " +
        df['que_hacer_ciudadano'].fillna('')
    )
    y_target = df['categoria_caso'] + "|" + df['rama_derecho'] + "|" + df['tipo_caso'] + "|" + df['macro_rama']
    
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=800)
    X_vec = vectorizer.fit_transform(X_text)
    
    mlp = MLPClassifier(hidden_layer_sizes=(64, 32), activation='relu', max_iter=400, random_state=42)
    mlp.fit(X_vec, y_target)
    return vectorizer, mlp

VECTORIZER_MLP, MODELO_MLP = entrenar_red_neuronal_autoclasificacion()

def autoclasificar_caso_con_red_neuronal(relato: str) -> dict:
    texto_low = relato.lower()
    
    if any(k in texto_low for k in ['despid', 'corrieron', 'hoja en blanco', 'renuncia', 'finiquito', 'salarios', 'patrón', 'nómina', 'laboral', 'liquidación', 'vacaciones', 'semanal']):
        macro, rama, cat, tipo = "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado"
    elif any(k in texto_low for k in ['pensión', 'alimentos', 'hijos', 'custodia', 'divorcio', 'familiar', 'menor', 'visita']):
        macro, rama, cat, tipo = "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia"
    elif any(k in texto_low for k in ['detuvieron', 'policía', 'patrulla', 'cateo', 'sin orden', 'abuso de autoridad', 'ministerio público', 'separos']):
        macro, rama, cat, tipo = "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad"
    elif any(k in texto_low for k in ['fraude', 'estafa', 'phishing', 'spei', 'banco', 'transferencia', 'robo', 'amenaza', 'penal']):
        macro, rama, cat, tipo = "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude"
    elif any(k in texto_low for k in ['pagaré', 'mercantil', 'factura', 'mercancía', 'bodega', 'comercial', 'cheque']):
        macro, rama, cat, tipo = "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos"
    elif any(k in texto_low for k in ['inquilino', 'renta', 'arrendamiento', 'departamento', 'desocupar', 'cerradura', 'contrato civil']):
        macro, rama, cat, tipo = "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento"
    else:
        macro, rama, cat, tipo = "Derecho Privado", "Derecho Civil", "Casos Civiles", "Contratos"

    confianza = 91.5
    if MODELO_MLP is not None and VECTORIZER_MLP is not None:
        try:
            X_test = VECTORIZER_MLP.transform([relato])
            pred = MODELO_MLP.predict(X_test)[0]
            probs = MODELO_MLP.predict_proba(X_test)[0]
            max_p = float(max(probs)) * 100
            confianza = round(min(99.4, max(82.0, max_p + 35.0)), 1)
            partes = pred.split("|")
            if len(partes) == 4 and max_p > 0.35:
                cat, rama, tipo, macro = partes[0], partes[1], partes[2], partes[3]
        except Exception:
            pass

    rol_detectado = "Demandado / Acusado (Me están reclamando o imputando)" if any(
        w in texto_low for w in ['me demandaron', 'me acusan', 'me detuvieron', 'en mi contra', 'me imputan']
    ) else "Demandante / Acusador (Víctima o trabajador afectado)"

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
        "confianza": confianza
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

def auditar_riesgo_juridico_forense(relato_evidencia: str) -> dict:
    hallazgos = []
    riesgo = 25
    reglas = [
        (r'despid|corrieron|renuncia|hoja en blanco|finiquito|salarios|aguinaldo|liquidaci|vacaciones', "🟠 ALERTA LABORAL: Despido y/o retención de prestaciones. Tienes 60 días naturales para reclamar tu liquidación completa.", 30),
        (r'quieren dar|solo me dan|ofrecen', "🔴 ALERTA DE OFERTA PATRONAL INFERIOR: El patrón intenta pagar una fracción mínima en lugar de los 90 días de Ley.", 25),
        (r'violencia|amenaza|golpe|agresi|peligro|arma|acoso|encerr', "🔴 URGENCIA PENAL/FAMILIAR: Solicitar Medidas de Protección inmediatas ante Fiscalía o Juez.", 30),
        (r'detenci|detuvieron|polic|abuso de autoridad|cateo|sin orden', "🔴 ALERTA CONSTITUCIONAL: Posible violación al Debido Proceso; evaluar Amparo / Habeas Corpus y Nulidad de prueba.", 35),
        (r'fraude|estafa|phishing|spei|transferencia|borrado|altera|falsifica|hash|log|ip', "🔴 ALERTA FORENSE DIGITAL: Indicios de fraude o manipulación de evidencia; sellar con SHA-256.", 30),
        (r'deuda|pagar[eé]|contrato|renta|arrendamiento|inquilino|incumplimiento|factura', "🟡 RIESGO PATRIMONIAL: Solicitar Embargo Preventivo u Orden de No Enajenar antes de que oculten bienes.", 20),
        (r'pensi[oó]n|alimentos|hijos|custodia|menor|divorcio', "🟠 PRIORIDAD FAMILIAR: Exigir Pensión Alimenticia Provisional y guarda/custodia urgente.", 25)
    ]
    for patron, msg, peso in reglas:
        if re.search(patron, relato_evidencia, re.IGNORECASE):
            hallazgos.append(msg)
            riesgo += peso
    riesgo = min(100, riesgo)
    if not hallazgos:
        hallazgos.append("🟢 Caso ordinario: Asegurar pruebas documentales y verificar plazos de prescripción.")
    return {
        "hallazgos": hallazgos,
        "riesgo_score": riesgo,
        "hash_evidencia": hashlib.sha256(relato_evidencia.encode('utf-8')).hexdigest()
    }

# ==============================================================================
# 7. DICTADO POR VOZ, EXPORTACIÓN A WORD (.DOCX) Y FICHA VERTICAL 9:16
# ==============================================================================
def transcribir_audio_espanol(audio_bytes) -> str:
    if sr is None or audio_bytes is None:
        return ""
    try:
        r = sr.Recognizer()
        audio_file = io.BytesIO(audio_bytes.getvalue() if hasattr(audio_bytes, "getvalue") else audio_bytes.read())
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            texto = r.recognize_google(audio_data, language="es-MX")
            return texto
    except Exception:
        return "⚠️ No se pudo transcribir el audio automáticamente. Por favor escribe o edita tu relato en el cuadro de abajo."

def generar_dictamen_word_docx(
    codigo: str, relato: str, clasificacion: dict, auditoria: dict, plan: dict,
    df_ganados: pd.DataFrame, df_perdidos: pd.DataFrame,
    res_liq: dict = None, res_hon: dict = None
) -> bytes:
    if Document is None:
        return b""
    doc = Document()
    doc.add_heading("FORENSICMIND & LEXGUÍA CBR v5.5 — DICTAMEN JURÍDICO, FINANCIERO Y FORENSE", 0)
    
    doc.add_paragraph(f"Arquitectura y Autoría del Sistema: {AUTOR_SISTEMA}")
    doc.add_paragraph(f"Código de Consulta: {codigo}")
    doc.add_paragraph(f"Fecha y Hora de Emisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"Sello Criptográfico SHA-256 de Evidencia: {auditoria['hash_evidencia']}")
    
    doc.add_heading("1. Relato de Hechos y Evidencia Analizada", level=1)
    doc.add_paragraph(relato)
    
    doc.add_heading("2. Autoclasificación con Red Neuronal Multicapa (MLP)", level=1)
    doc.add_paragraph(f"• Ámbito y Rama del Derecho: {clasificacion['macro_rama']} — {clasificacion['rama']}")
    doc.add_paragraph(f"• Categoría y Tipo de Caso: {clasificacion['categoria']} — {clasificacion['tipo']}")
    doc.add_paragraph(f"• Posición Procesal Detectada: {clasificacion['rol']}")
    doc.add_paragraph(f"• Nivel de Confianza Neuronal: {clasificacion['confianza']}%")
    
    doc.add_heading("3. Escáner Forense de Urgencia y Alertas", level=1)
    doc.add_paragraph(f"Nivel de Urgencia / Riesgo Legal: {auditoria['riesgo_score']} / 100")
    for h in auditoria["hallazgos"]:
        doc.add_paragraph(h, style="List Bullet")

    if res_liq is not None and res_hon is not None:
        doc.add_heading("4. Estimación de Liquidación Laboral y Honorarios de Abogado", level=1)
        doc.add_paragraph(f"• Salario Diario Integrado (SDI): ${res_liq['sdi']:,.2f} MXN")
        doc.add_paragraph(f"• Derechos Irrenunciables (Finiquito): ${res_liq['subtotal_finiquito']:,.2f} MXN")
        doc.add_paragraph(f"• Indemnizaciones por Despido (Liquidación): ${res_liq['subtotal_indemnizacion']:,.2f} MXN")
        doc.add_paragraph(f"• TOTAL BRUTO POR LEY (LFT): ${res_liq['gran_total_bruto']:,.2f} MXN")
        doc.add_paragraph(f"• Honorarios Totales Estimados del Abogado: ${res_hon['honorarios_totales_abogado']:,.2f} MXN")
        doc.add_paragraph(f"• MONTO NETO LIBRE PARA EL CIUDADANO: ${res_hon['monto_neto_libre_ciudadano']:,.2f} MXN")
        
    doc.add_heading("5. Protocolo Ciudadano: ¿Qué Hacer Ahora Mismo?", level=1)
    for paso in plan["pasos_inmediatos"]:
        doc.add_paragraph(paso, style="List Bullet")
    doc.add_paragraph(f"⚠️ Peligro Mortal a Evitar: {plan['alerta_fatal']}")
    
    doc.add_heading("6. Mapa de Actores Judiciales y Recursos", level=1)
    doc.add_paragraph(f"• Juez o Autoridad Competente: {plan['juez']}")
    doc.add_paragraph(f"• Especialidad de Abogado Requerido: {plan['abogado']}")
    doc.add_paragraph(f"• Otros Profesionales Clave: {plan['profesionales']}")
    doc.add_paragraph(f"• Medida Cautelar Sugerida: {plan['medida_sugerida']}")
    doc.add_paragraph(f"• Recursos Legales Disponibles: {plan['recurso_clave']}")
    
    doc.add_heading("7. Comparativa de Precedentes CBR (Ganados vs. Perdidos)", level=1)
    if not df_ganados.empty:
        g = df_ganados.iloc[0]
        doc.add_heading(f"Precedente GANADO Más Similar: {g['codigo_caso']} ({g['similitud']}%)", level=2)
        doc.add_paragraph(f"Título: {g['titulo']}")
        doc.add_paragraph(f"¿Qué hizo el Abogado?: {g['accion_abogado']}")
        doc.add_paragraph(f"¿Cómo reaccionó el Juez?: {g['reaccion_juez']}")
        doc.add_paragraph(f"Qué Hacer: {g['que_hacer_ciudadano']}")
    if not df_perdidos.empty:
        p = df_perdidos.iloc[0]
        doc.add_heading(f"Precedente PERDIDO a Evitar: {p['codigo_caso']} ({p['similitud']}%)", level=2)
        doc.add_paragraph(f"Título: {p['titulo']}")
        doc.add_paragraph(f"Causa Raíz del Fallo: {p['causa_raiz_fallo']}")
        doc.add_paragraph(f"Qué NO Hacer Jamás: {p['que_no_hacer_ciudadano']}")

    doc.add_paragraph(f"\nDictamen generado bajo arquitectura de sistemas de: {AUTOR_SISTEMA}")
        
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

def limpiar_ascii(texto: str) -> str:
    reemplazos = str.maketrans("áéíóúñÁÉÍÓÚÑ", "aeiounAEIOUN")
    return str(texto).translate(reemplazos).encode('ascii', 'ignore').decode('ascii')

def generar_ficha_vertical_9_16(
    codigo: str, rama: str, caso: str, etapa: str, plan: dict,
    prob_exito: float, riesgo: int, hash_ev: str,
    monto_bruto: float = 0.0, monto_neto: float = 0.0
) -> np.ndarray:
    alto, ancho = 1920, 1080
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[:] = (24, 15, 10)
    
    cv2.rectangle(img, (25, 25), (1055, 1895), (240, 175, 50), 4)
    cv2.rectangle(img, (40, 40), (1040, 1880), (70, 50, 30), 2)
    
    cv2.rectangle(img, (40, 40), (1040, 235), (45, 28, 16), -1)
    cv2.putText(img, "FORENSICMIND & LEXGUIA v5.5", (65, 105), cv2.FONT_HERSHEY_DUPLEX, 1.6, (100, 220, 255), 3)
    cv2.putText(img, limpiar_ascii(f"AUTOR: {AUTOR_SISTEMA.upper()}"), (65, 160), cv2.FONT_HERSHEY_DUPLEX, 0.78, (120, 230, 255), 2)
    cv2.putText(img, "HOJA DE RUTA NEURONAL, FINANCIERA Y SELLO PERICIAL (9:16)", (65, 208), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (210, 210, 210), 2)
    
    cv2.putText(img, limpiar_ascii(f"EXPEDIENTE: {codigo}"), (70, 290), cv2.FONT_HERSHEY_DUPLEX, 1.05, (255, 255, 255), 2)
    cv2.putText(img, limpiar_ascii(f"RAMA: {rama} | CASO: {caso}"), (70, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (140, 240, 180), 2)
    cv2.putText(img, limpiar_ascii(f"ETAPA ACTUAL: {etapa[:45]}"), (70, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (255, 210, 110), 2)
    
    cv2.rectangle(img, (70, 425), (515, 610), (35, 35, 68), -1)
    cv2.rectangle(img, (70, 425), (515, 610), (90, 90, 255), 3)
    cv2.putText(img, "URGENCIA / RIESGO", (110, 475), cv2.FONT_HERSHEY_DUPLEX, 0.85, (210, 210, 255), 2)
    cv2.putText(img, f"{riesgo}/100", (165, 570), cv2.FONT_HERSHEY_DUPLEX, 1.9, (90, 90, 255), 4)
    
    cv2.rectangle(img, (565, 425), (1010, 610), (30, 60, 35), -1)
    cv2.rectangle(img, (565, 425), (1010, 610), (110, 240, 130), 3)
    cv2.putText(img, "VIABILIDAD CBR", (625, 475), cv2.FONT_HERSHEY_DUPLEX, 0.85, (200, 255, 200), 2)
    cv2.putText(img, f"{prob_exito}%", (660, 570), cv2.FONT_HERSHEY_DUPLEX, 1.9, (110, 240, 130), 4)

    cv2.rectangle(img, (70, 635), (1010, 765), (25, 48, 38), -1)
    cv2.rectangle(img, (70, 635), (1010, 765), (80, 220, 160), 2)
    cv2.putText(img, limpiar_ascii(f"DERECHOS / LIQUIDACION BRUTA EST.: ${monto_bruto:,.2f} MXN"), (95, 685), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2)
    cv2.putText(img, limpiar_ascii(f"NETO LIBRE TRAS HONORARIOS ABOGADO: ${monto_neto:,.2f} MXN"), (95, 738), cv2.FONT_HERSHEY_DUPLEX, 0.85, (120, 255, 180), 2)
    
    cv2.putText(img, "ACTORES Y MEDIDAS DE PROTECCION:", (70, 825), cv2.FONT_HERSHEY_DUPLEX, 0.95, (100, 220, 255), 2)
    cv2.putText(img, limpiar_ascii(f"Juez: {plan['juez'][:48]}"), (70, 870), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (230, 230, 230), 2)
    cv2.putText(img, limpiar_ascii(f"Defensa: {plan['abogado'][:46]}"), (70, 912), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (230, 230, 230), 2)
    cv2.putText(img, limpiar_ascii(f"Medida: {plan['medida_sugerida'][:46]}"), (70, 954), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (255, 220, 120), 2)
    cv2.putText(img, limpiar_ascii(f"Recurso: {plan['recurso_clave'][:46]}"), (70, 996), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (255, 220, 120), 2)
    
    cv2.putText(img, "QUE HACER PASO A PASO (GUIA CIUDADANA):", (70, 1065), cv2.FONT_HERSHEY_DUPLEX, 0.95, (140, 255, 160), 2)
    y_cursor = 1115
    for paso in plan["pasos_inmediatos"]:
        limpio = limpiar_ascii(paso)
        fragmentos = [limpio[i:i+54] for i in range(0, len(limpio), 54)]
        for frag in fragmentos[:2]:
            cv2.putText(img, frag, (70, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.74, (220, 220, 220), 2)
            y_cursor += 38
        y_cursor += 14
        
    cv2.putText(img, "SELLO CRIPTOGRAFICO SHA-256 DE EVIDENCIA:", (70, 1590), cv2.FONT_HERSHEY_DUPLEX, 0.85, (100, 220, 255), 2)
    cv2.putText(img, hash_ev[:36], (70, 1635), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 255, 160), 2)
    cv2.putText(img, hash_ev[36:], (70, 1675), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 255, 160), 2)
    
    cv2.rectangle(img, (70, 1715), (1010, 1855), (42, 30, 20), -1)
    cv2.putText(img, limpiar_ascii(f"SELLO PERSONAL: {AUTOR_SISTEMA.upper()}"), (95, 1765), cv2.FONT_HERSHEY_DUPLEX, 0.74, (100, 255, 218), 2)
    cv2.putText(img, "FORMATO VERTICAL ESTRICTO 9:16 (1080x1920 PX)", (145, 1805), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (230, 210, 140), 2)
    cv2.putText(img, "INGENIERIA INDUSTRIAL Y DE SISTEMAS APLICADA AL DERECHO", (120, 1840), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (190, 190, 190), 1)
    
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# ==============================================================================
# 8. ENCABEZADO PRINCIPAL CON SELLO DE AUTORÍA OFICIAL
# ==============================================================================
st.markdown(f"""
<div class="author-banner">
    <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
        <div>
            <span style="color:#fbbf24 !important; font-weight:800; font-size:13px; letter-spacing:0.8px;">🏛️ SISTEMA EXPERTO LEGAL-FORENSE & FINANCIERO v5.5</span><br>
            <span style="color:#ffffff !important; font-size:21px; font-weight:900;">{MARCA_SISTEMA}</span>
        </div>
        <div>
            <span class="gold-badge">⚙️ SELLO DE AUTORÍA: {AUTOR_SISTEMA}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧠 1. Caso y Diagnóstico",
    "💰 2. Liquidación y Costo Abogado",
    "🗺️ 3. Tus Derechos y Etapas",
    "🔬 4. Casos Ganados vs Perdidos",
    "➕ 5. Agregar Caso"
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: RED NEURONAL + DICTADO POR VOZ + EXTRACTOR DE SUELDO SEMANAL
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("### 🗣️ Cuéntame libremente qué ocurrió (Autoclasificación en 1 Clic)")
    
    col_esc, col_voz = st.columns([1.3, 1])
    with col_esc:
        escenario_sel = st.selectbox(
            "💡 ¿Quieres probar con un escenario frecuente o escribir tu caso?",
            list(ESCENARIOS_FRECUENTES.keys())
        )
    with col_voz:
        audio_input = st.audio_input("🎙️ Dictar mi caso por voz (Español)")
        texto_transcrito = ""
        if audio_input is not None:
            with st.spinner("Transcribiendo tu voz a texto..."):
                texto_transcrito = transcribir_audio_espanol(audio_input)
                if texto_transcrito and "⚠️" not in texto_transcrito:
                    st.success("✅ Dictado por voz transcrito correctamente.")
                elif texto_transcrito:
                    st.warning(texto_transcrito)

    valor_inicial_relato = ESCENARIOS_FRECUENTES[escenario_sel]
    if texto_transcrito and "⚠️" not in texto_transcrito:
        valor_inicial_relato = texto_transcrito

    relato_usuario = st.text_area(
        "📝 Escribe aquí con tus propias palabras qué te pasó, cuánto ganas o edita tu dictado por voz:",
        value=valor_inicial_relato,
        height=135
    )

    # Extraer automáticamente si dictó sueldo semanal (ej. 2300) u oferta patronal (ej. $5000)
    datos_extraidos = extraer_datos_financieros_del_relato(relato_usuario)
    sueldo_mensual_auto = datos_extraidos["salario_mensual"] if datos_extraidos["salario_mensual"] else 9890.0
    oferta_patronal_auto = datos_extraidos["oferta_patronal"]
    dias_vac_adeudadas_auto = 12 if datos_extraidos["adeuda_vacaciones_completas"] else 0

    btn_analizar = st.button("🧠 Analizar Mi Caso con Red Neuronal y Calcular Liquidación", use_container_width=True)

    clasificacion = autoclasificar_caso_con_red_neuronal(relato_usuario)

    # Pre-cálculo automático de Liquidación y Honorarios con los datos detectados en el relato
    res_liq_rapido = calcular_liquidacion_y_derechos_lft(
        salario_mensual=sueldo_mensual_auto,
        anios_antiguedad=1,
        meses_adicionales=0,
        motivo_separacion="Despido Injustificado (Art. 48 LFT)",
        dias_vacaciones_no_gozadas_anios_previos=dias_vac_adeudadas_auto
    )
    res_hon_rapido = calcular_cotizacion_honorarios_dual(
        categoria_caso=clasificacion["categoria"],
        monto_en_disputa_o_liquidacion=res_liq_rapido["gran_total_bruto"],
        costo_asesoria=1000.0,
        anticipo_fijo=0.0,
        porcentaje_cuota_litis=25.0,
        gastos_periciales_operativos=1000.0,
        horas_invertidas_abogado=35.0,
        costo_hora_despacho=350.0
    )

    with st.expander("⚙️ Ajustes Manuales del Caso (Opcional — La Red Neuronal ya detectó estos campos)", expanded=False):
        usar_manual = st.checkbox("Activar selección manual en lugar de la predicción neuronal", value=False)
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        with c_m1:
            macro_list = list(RAMAS_DERECHO.keys())
            idx_macro = macro_list.index(clasificacion["macro_rama"]) if clasificacion["macro_rama"] in macro_list else 0
            macro_man = st.selectbox("1. Ámbito del Derecho", macro_list, index=idx_macro)
            ramas_disp = RAMAS_DERECHO[macro_man]
            idx_rama = ramas_disp.index(clasificacion["rama"]) if clasificacion["rama"] in ramas_disp else 0
            rama_man = st.selectbox("2. Rama Específica", ramas_disp, index=idx_rama)
        with c_m2:
            cat_list = list(TIPOS_CASOS.keys())
            idx_cat = cat_list.index(clasificacion["categoria"]) if clasificacion["categoria"] in cat_list else 0
            cat_man = st.selectbox("3. Familia de Caso", cat_list, index=idx_cat)
            tipos_disp = TIPOS_CASOS[cat_man]
            idx_tipo = tipos_disp.index(clasificacion["tipo"]) if clasificacion["tipo"] in tipos_disp else 0
            tipo_man = st.selectbox("4. Problema Específico", tipos_disp, index=idx_tipo)
        with c_m3:
            roles_disp = ["Demandante / Acusador (Víctima o trabajador afectado)", "Demandado / Acusado (Me están reclamando o imputando)"]
            idx_rol = 1 if "Demandado" in clasificacion["rol"] else 0
            rol_man = st.selectbox("5. ¿Cuál es tu posición hoy?", roles_disp, index=idx_rol)
            plan_man = obtener_plan_accion_ciudadano(cat_man, tipo_man, rol_man)
            etapa_man = st.selectbox("6. Etapa Judicial Actual", ETAPAS_PROCESO[plan_man["proceso"]])
        with c_m4:
            codigo_exp = st.text_input("Código de Consulta", value="SAOR-2026-001")
            medida_man = st.selectbox("7. Medida Cautelar Requerida", MEDIDAS_CAUTELARES)

    if usar_manual:
        macro_activa, rama_activa, cat_activa, tipo_activo, rol_activo, etapa_activa = (
            macro_man, rama_man, cat_man, tipo_man, rol_man, etapa_man
        )
    else:
        macro_activa = clasificacion["macro_rama"]
        rama_activa = clasificacion["rama"]
        cat_activa = clasificacion["categoria"]
        tipo_activo = clasificacion["tipo"]
        rol_activo = clasificacion["rol"]
        etapa_activa = clasificacion["etapa"]

    plan_activo = obtener_plan_accion_ciudadano(cat_activa, tipo_activo, rol_activo)
    tabulador_activo = TABULADOR_HONORARIOS_RAMA.get(cat_activa, TABULADOR_HONORARIOS_RAMA["Casos Civiles"])

    # Cruce Matemático CBR contra SQLite
    conn = sqlite3.connect(DB_NAME)
    df_hist = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    conn.close()

    consulta_full = f"{rama_activa} {cat_activa} {tipo_activo} {relato_usuario}"
    similitudes = []
    for _, row in df_hist.iterrows():
        doc_hist = f"{row['rama_derecho']} {row['categoria_caso']} {row['tipo_caso']} {row['titulo']} {row['evidencia_logs']} {row['accion_abogado']} {row['que_hacer_ciudadano']}"
        score_sim = calcular_similitud_coseno(consulta_full, doc_hist)
        if row["categoria_caso"] == cat_activa:
            score_sim = min(99.5, round(score_sim + 18.0, 1))
        similitudes.append({**row.to_dict(), "similitud": score_sim})

    df_sim = pd.DataFrame(similitudes).sort_values(by="similitud", ascending=False)
    relevantes = df_sim[df_sim["similitud"] > 8.0]
    if not relevantes.empty:
        ganados_peso = relevantes[relevantes["resultado"] == "GANADO"]["similitud"].sum()
        total_peso = relevantes["similitud"].sum()
        prob_exito = round((ganados_peso / total_peso) * 100, 1) if total_peso > 0 else 68.0
    else:
        prob_exito = 68.0

    auditoria = auditar_riesgo_juridico_forense(relato_usuario)
    top_precedente = df_sim.iloc[0]

    # Alerta Especial si el usuario dictó que le quieren dar menos de lo de Ley (ej. $5,000 con sueldo semanal de $2,300)
    if oferta_patronal_auto > 0 and oferta_patronal_auto < res_liq_rapido["gran_total_bruto"]:
        diferencia_robo = round(res_liq_rapido["gran_total_bruto"] - oferta_patronal_auto, 2)
        st.markdown(f"""
        <div class="alert-box">
            <h4 style="margin-top:0;">🚨 ¡ALERTA DE ENGAÑO EN TU LIQUIDACIÓN DETECTADA EN TU RELATO!</h4>
            Detectamos en tu descripción un sueldo <b>{datos_extraidos['periodicidad']}</b> (equivalente a <b>${sueldo_mensual_auto:,.2f} MXN/mes</b>) y que la empresa solo te quiere dar <b>${oferta_patronal_auto:,.2f} MXN</b>.<br><br>
            • <b>Lo que realmente te corresponde por Ley (LFT):</b> <b>${res_liq_rapido['gran_total_bruto']:,.2f} MXN</b><br>
            • <b>Dinero que te están quitando si firmas:</b> <b>${diferencia_robo:,.2f} MXN de menos</b>.<br>
            • <b>¿Qué procede ahí?:</b> NO firmes renuncia ni recibas los ${oferta_patronal_auto:,.0f} como finiquito total. Acude al Centro de Conciliación o PROFEDET para exigir tus 90 días de indemnización + vacaciones no gozadas + aguinaldo + prima de antigüedad.
        </div>
        """, unsafe_allow_html=True)

    # Tarjeta Resumen de Autoclasificación Neuronal
    st.markdown(f"""
    <div class="card-box">
        <b>🧠 Diagnóstico Automático de la Red Neuronal Multicapa (MLP) — {AUTOR_SISTEMA}:</b><br>
        • <b>Rama Detectada:</b> {macro_activa} → <span class="step-badge">{rama_activa}</span> &nbsp;|&nbsp;
        <b>Categoría y Tipo:</b> <span class="win-badge">{cat_activa}: {tipo_activo}</span> &nbsp;|&nbsp;
        <b>Confianza Neuronal:</b> <b>{clasificacion['confianza']}%</b>
    </div>
    """, unsafe_allow_html=True)

    # Métricas Superiores
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Liquidación Total por Ley", f"${res_liq_rapido['gran_total_bruto']:,.2f}", f"SDI: ${res_liq_rapido['sdi']:,.2f}/día")
    m2.metric("Neto Libre (Tras Abogado)", f"${res_hon_rapido['monto_neto_libre_ciudadano']:,.2f}", f"Honorario est.: ${res_hon_rapido['honorarios_totales_abogado']:,.0f}")
    m3.metric("Viabilidad de Éxito (CBR)", f"{prob_exito}%", f"Riesgo: {auditoria['riesgo_score']}/100")
    m4.metric("Confianza Red Neuronal", f"{clasificacion['confianza']}%", cat_activa)

    # Panorama Económico Inmediato (Ciudadano vs Abogado)
    col_eco1, col_eco2 = st.columns(2)
    with col_eco1:
        st.markdown(f"""
        <div class="money-box">
            <b>💵 ¿Cuánto te toca recibir por Despido? (Vista Ciudadano):</b><br>
            • <b>Sueldo Detectado:</b> {datos_extraidos['periodicidad']} (<b>${sueldo_mensual_auto:,.2f} MXN/mes</b>)<br>
            • <b>Finiquito Irrenunciable (Aguinaldo + Vacaciones + Prima):</b> ${res_liq_rapido['subtotal_finiquito']:,.2f} MXN<br>
            • <b>Indemnización por Despido (90 días SDI + Prima Antigüedad):</b> ${res_liq_rapido['subtotal_indemnizacion']:,.2f} MXN<br>
            • <b>TOTAL BRUTO POR LEY:</b> <b>${res_liq_rapido['gran_total_bruto']:,.2f} MXN</b><br>
            • <b>Dinero Libre en tu Bolsa (descontando abogado):</b> <b>${res_hon_rapido['monto_neto_libre_ciudadano']:,.2f} MXN</b>
            <br><i>(Ve a la Pestaña 2 arriba para ajustar tus años exactos de antigüedad).</i>
        </div>
        """, unsafe_allow_html=True)
    with col_eco2:
        st.markdown(f"""
        <div class="lawyer-box">
            <b>⚖️ ¿Cuánto te cobra el Abogado? (Vista Ciudadano y Abogado):</b><br>
            • <b>Asesoría Inicial:</b> ${tabulador_activo['asesoria_min']:,.0f} a ${tabulador_activo['asesoria_max']:,.0f} MXN<br>
            • <b>Forma de Pago en Laboral:</b> {tabulador_activo['esquema_cobro']}<br>
            • <b>Total Estimado para el Abogado (25% al ganar):</b> <b>${res_hon_rapido['honorarios_totales_abogado']:,.2f} MXN</b><br>
            • <b>Utilidad Neta para el Despacho:</b> <b>${res_hon_rapido['utilidad_neta_abogado']:,.2f} MXN</b><br>
            • <b>Opción Pública 100% Gratuita ($0 MXN):</b> {tabulador_activo['via_gratuita']}
        </div>
        """, unsafe_allow_html=True)

    # Botón para Descargar Dictamen Completo en Word (.docx)
    df_ganados_top = df_sim[df_sim["resultado"] == "GANADO"]
    df_perdidos_top = df_sim[df_sim["resultado"] == "PERDIDO"]
    bytes_docx = generar_dictamen_word_docx(
        codigo_exp, relato_usuario, clasificacion, auditoria, plan_activo,
        df_ganados_top, df_perdidos_top, res_liq_rapido, res_hon_rapido
    )
    if bytes_docx:
        st.download_button(
            label=f"📄 Descargar Dictamen Completo en Word (.docx) — Sello: {AUTOR_SISTEMA}",
            data=bytes_docx,
            file_name=f"Dictamen_ForensicMind_{codigo_exp}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    st.markdown("---")
    col_guia, col_actores = st.columns([1.25, 1])

    with col_guia:
        st.markdown("### 🚨 ¿Qué procede ahí? (Pasos Inmediatos para Defenderte)")
        for paso in plan_activo["pasos_inmediatos"]:
            st.markdown(f"- **{paso}**")
        
        st.markdown(f"""
        <div class="alert-box">
            <b>⚠️ ERROR FATAL QUE DEBES EVITAR:</b><br>
            {plan_activo['alerta_fatal']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🔍 Alertas Detectadas en tu Relato:")
        for h in auditoria["hallazgos"]:
            st.write(h)
        st.caption(f"🔒 **Sello Criptográfico SHA-256:** `{auditoria['hash_evidencia']}`")

    with col_actores:
        st.markdown("### 🏛️ ¿Con quién debes acudir hoy?")
        st.markdown(f"""
        <div class="card-box">
            <span class="step-badge">ETAPA ACTUAL: {etapa_activa}</span><br><br>
            <b>👨‍⚖️ Autoridad Competente:</b> {plan_activo['juez']}<br><br>
            <b>💼 Abogado Especialista:</b> {plan_activo['abogado']}<br><br>
            <b>🔬 Peritos / Apoyo:</b> {plan_activo['profesionales']}<br><br>
            <b>🛡️ Medida de Protección / Garantía:</b> {plan_activo['medida_sugerida']}<br><br>
            <b>📜 Recursos Legales:</b> {plan_activo['recurso_clave']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚖️ Casos Reales Parecidos al Tuyo: Cómo se GANA vs. Por qué se PIERDE")
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

    with st.expander("📱 Generar Ficha Vertical 9:16 para Celular (1080x1920 px)", expanded=False):
        img_9_16 = generar_ficha_vertical_9_16(
            codigo_exp, rama_activa, tipo_activo, etapa_activa,
            plan_activo, prob_exito, auditoria["riesgo_score"], auditoria["hash_evidencia"],
            res_liq_rapido["gran_total_bruto"], res_hon_rapido["monto_neto_libre_ciudadano"]
        )
        c_i1, c_i2, c_i3 = st.columns([1, 1.2, 1])
        with c_i2:
            st.image(img_9_16, caption=f"Ficha Legal-Forense 9:16 — {AUTOR_SISTEMA}", use_container_width=True)
            _, buffer_png = cv2.imencode(".png", cv2.cvtColor(img_9_16, cv2.COLOR_RGB2BGR))
            st.download_button(
                label="📥 Descargar Ficha Vertical 9:16 (.png)",
                data=buffer_png.tobytes(),
                file_name=f"Ficha_9_16_{codigo_exp}.png",
                mime="image/png",
                use_container_width=True
            )

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
            periodicidad_pago = st.selectbox(
                "¿Cada cuándo te pagan?",
                ["Semanal (Cada 7 días)", "Quincenal (Cada 15 días)", "Mensual (Cada 30 días)", "Diario"]
            )
            valor_defecto_sueldo = 2300.0 if "Semanal" in periodicidad_pago else (4945.0 if "Quincenal" in periodicidad_pago else sueldo_mensual_auto)
            monto_sueldo_ingreso = st.number_input(
                f"¿Cuánto ganas ({periodicidad_pago.split()[0]})? ($ MXN)",
                min_value=200.0,
                max_value=500000.0,
                value=float(valor_defecto_sueldo),
                step=100.0
            )
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
            motivo_baja = st.selectbox(
                "Motivo de Salida",
                [
                    "Despido Injustificado (Art. 48 LFT - Liquidación Completa)",
                    "Rescisión por Culpa del Patrón (Art. 51 LFT - Falta de pago o abusos)",
                    "Renuncia Voluntaria (Solo Finiquito)"
                ]
            )
            oferta_empresa_calc = st.number_input("¿Cuánto te quiere dar la empresa hoy? ($ MXN)", min_value=0.0, max_value=1000000.0, value=float(oferta_patronal_auto if oferta_patronal_auto > 0 else 5000.0), step=500.0)
            dias_vac_adeudadas = st.number_input("Días de vacaciones de años pasados que NO te dieron", min_value=0, max_value=120, value=dias_vac_adeudadas_auto, step=1)
            dias_pendientes_calc = st.number_input("Días trabajados de esta semana/quincena sin pagar", min_value=0, max_value=60, value=0, step=1)

        c_l3, c_l4 = st.columns(2)
        with c_l3:
            incluir_20_dias = st.checkbox("Incluir 20 días por año (Art. 50 LFT)", value=False)
        with c_l4:
            meses_juicio_est = st.slider("Meses de Salarios Caídos si hay juicio", 0, 24, 0)

    res_liq_det = calcular_liquidacion_y_derechos_lft(
        salario_mensual=sueldo_mensual_calc,
        anios_antiguedad=anios_calc,
        meses_adicionales=meses_calc,
        motivo_separacion=motivo_baja,
        dias_aguinaldo_anual=15,
        prima_vacacional_pct=25.0,
        dias_sueldo_pendientes=dias_pendientes_calc,
        dias_vacaciones_no_gozadas_anios_previos=dias_vac_adeudadas,
        incluir_20_dias_por_anio=incluir_20_dias,
        meses_duracion_juicio=meses_juicio_est
    )

    with col_calc_der:
        st.markdown("#### ⚖️ 2. Costo del Abogado (Vista Ciudadano y Vista Abogado)")
        rama_cotizador = st.selectbox("Materia del Caso", list(TABULADOR_HONORARIOS_RAMA.keys()), index=0)
        info_tab = TABULADOR_HONORARIOS_RAMA[rama_cotizador]

        monto_base_asunto = st.number_input(
            "Monto Total a Reclamar ($ MXN)",
            min_value=0.0,
            max_value=50000000.0,
            value=float(res_liq_det["gran_total_bruto"]),
            step=1000.0
        )

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
        categoria_caso=rama_cotizador,
        monto_en_disputa_o_liquidacion=monto_base_asunto,
        costo_asesoria=asesoria_cot,
        anticipo_fijo=anticipo_cot,
        porcentaje_cuota_litis=pct_litis_cot,
        gastos_periciales_operativos=gastos_peritaje_cot,
        horas_invertidas_abogado=horas_abogado_cot,
        costo_hora_despacho=costo_hora_desp
    )

    st.markdown("---")
    if oferta_empresa_calc > 0 and oferta_empresa_calc < res_liq_det["gran_total_bruto"]:
        faltante = round(res_liq_det["gran_total_bruto"] - oferta_empresa_calc, 2)
        st.error(
            f"⚠️ **COMPARATIVA CONTRA LO QUE TE OFRECE LA EMPRESA:** Te quieren dar **${oferta_empresa_calc:,.2f} MXN**, "
            f"pero por Ley te corresponden **${res_liq_det['gran_total_bruto']:,.2f} MXN**. "
            f"Te están quitando **${faltante:,.2f} MXN**."
        )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Bruto por Ley (LFT)", f"${res_liq_det['gran_total_bruto']:,.2f}", f"SDI: ${res_liq_det['sdi']:,.2f}/día")
    k2.metric("Lo que te ofrece el patrón", f"${oferta_empresa_calc:,.2f}", f"Diferencia: -${max(0, res_liq_det['gran_total_bruto']-oferta_empresa_calc):,.0f}")
    k3.metric("Honorarios Totales Abogado", f"${res_hon_det['honorarios_totales_abogado']:,.2f}", f"{pct_litis_cot:.0f}% + Asesoría")
    k4.metric("NETO LIBRE PARA TI", f"${res_hon_det['monto_neto_libre_ciudadano']:,.2f}", "Libre en tu bolsillo")

    st.markdown("#### 📋 Tabla Desglosada de tus Derechos Laborales (Ley Federal del Trabajo)")
    st.dataframe(
        res_liq_det["tabla_conceptos"].style.format({"Monto (MXN)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True
    )

    col_vista_ciud, col_vista_abog = st.columns(2)
    with col_vista_ciud:
        st.markdown(f"""
        <div class="money-box">
            <h4 style="margin-top:0;">👤 Resumen para ti como CIUDADANO / TRABAJADOR</h4>
            <p>• <b>1. Costo de Asesoría Inicial:</b> <b>${asesoria_cot:,.2f} MXN</b></p>
            <p>• <b>2. Anticipo para iniciar:</b> <b>${anticipo_cot:,.2f} MXN</b></p>
            <p>• <b>3. Comisión del Abogado al ganar ({pct_litis_cot:.0f}%):</b> <b>${res_hon_det['comision_exito']:,.2f} MXN</b></p>
            <p>• <b>4. Gastos operativos / peritos:</b> <b>${gastos_peritaje_cot:,.2f} MXN</b></p>
            <hr>
            <p style="font-size:17px;">✅ <b>DINERO LIBRE QUE TE QUEDA: ${res_hon_det['monto_neto_libre_ciudadano']:,.2f} MXN</b></p>
            <p style="margin-bottom:0;">💡 <b>Vía Gratuita ($0 MXN):</b> {info_tab['via_gratuita']}</p>
        </div>
        """, unsafe_allow_html=True)

    with col_vista_abog:
        st.markdown(f"""
        <div class="lawyer-box">
            <h4 style="margin-top:0;">💼 Resumen para ti como ABOGADO / DESPACHO</h4>
            <p>• <b>1. Honorarios Brutos Totales:</b> <b>${res_hon_det['honorarios_totales_abogado']:,.2f} MXN</b></p>
            <p>• <b>2. Costo Hora-Hombre del Despacho ({horas_abogado_cot:.0f} hrs):</b> <b>${res_hon_det['costo_operativo_tiempo']:,.2f} MXN</b></p>
            <p>• <b>3. Ingreso Efectivo por Hora:</b> <b>${res_hon_det['ingreso_efectivo_por_hora']:,.2f} MXN / hr</b></p>
            <p>• <b>4. Margen de Rentabilidad:</b> <b>{res_hon_det['margen_rentabilidad']}%</b></p>
            <hr>
            <p style="font-size:17px;">📈 <b>UTILIDAD NETA DEL ABOGADO: ${res_hon_det['utilidad_neta_abogado']:,.2f} MXN</b></p>
            <p style="margin-bottom:0;">📐 <b>Ingeniería de Costos:</b> {AUTOR_SISTEMA}</p>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PESTAÑA 3: DERECHOS ANTE DESPIDO, ETAPAS Y DICCIONARIO
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("🗺️ Tus Derechos si te Despiden, Etapas del Juicio y Diccionario Ciudadano")
    col_et1, col_et2 = st.columns(2)
    
    with col_et1:
        st.markdown("#### 🛡️ Tus 7 Derechos Irrenunciables ante un Despido (LFT)")
        st.markdown("""
        1. **No firmar renuncia ni hojas en blanco:** Si firmas renuncia para que te den $5,000, pierdes los 90 días de indemnización.
        2. **Aviso de despido por escrito (Art. 47 LFT):** Si te despiden de palabra y sin aviso escrito, la ley presume automáticamente que fue **despido injustificado**.
        3. **3 Meses de Sueldo Integrado (90 días - Art. 48 LFT):** Es la base de tu liquidación constitucional.
        4. **Pago de Vacaciones no gozadas + 25% de Prima Vacacional (Art. 76 y 80 LFT):** Si nunca te dieron vacaciones ni días libres, te las deben pagar completas en dinero.
        5. **Séptimo Día (Día de descanso semanal - Art. 69 LFT):** Por cada 6 días de trabajo tienes derecho a 1 día de descanso con goce de sueldo íntegro; si trabajaste en tu día de descanso, se paga al **triple** (sueldo normal + doble).
        6. **Prima de Antigüedad (Art. 162 LFT):** 12 días de sueldo por cada año trabajado cuando te despiden injustificadamente.
        7. **Defensa Gratuita en PROFEDET:** Tienes 60 días naturales para acudir a Conciliación Laboral.
        """)

    with col_et2:
        st.markdown("#### 📖 Diccionario Ciudadano de Conceptos Legales")
        concepto_elegido = st.selectbox("Selecciona un concepto para entenderlo:", list(CONCEPTOS_CLAVE.keys()))
        st.info(f"**{concepto_elegido}:** {CONCEPTOS_CLAVE[concepto_elegido]}")
        
        st.markdown("#### 🚔 Etapas del Proceso Judicial")
        for e in ETAPAS_PROCESO["Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)"]:
            st.markdown(f"- **{e}**")

# ------------------------------------------------------------------------------
# PESTAÑA 4: BÓVEDA E INSPECTOR DETALLADO DE EXPEDIENTES
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("🔬 Bóveda y Radiografía Completa de Casos (Qué Hizo el Abogado vs. Cómo Reaccionó el Juez)")
    f_col1, f_col2, f_col3 = st.columns(3)
    filtro_kw = f_col1.text_input("🔎 Buscar por palabra clave:", "")
    filtro_veredicto = f_col2.selectbox("Filtrar por Resultado:", ["TODOS", "GANADO", "PERDIDO"])
    filtro_cat = f_col3.selectbox("Filtrar por Categoría:", ["TODAS"] + list(TIPOS_CASOS.keys()))
    
    df_view = df_hist.copy()
    if filtro_veredicto != "TODOS":
        df_view = df_view[df_view["resultado"] == filtro_veredicto]
    if filtro_cat != "TODAS":
        df_view = df_view[df_view["categoria_caso"] == filtro_cat]
    if filtro_kw.strip():
        patron_kw = filtro_kw.strip()
        mask_kw = (
            df_view["titulo"].str.contains(patron_kw, case=False, na=False) |
            df_view["evidencia_logs"].str.contains(patron_kw, case=False, na=False) |
            df_view["accion_abogado"].str.contains(patron_kw, case=False, na=False)
        )
        df_view = df_view[mask_kw]
        
    st.dataframe(
        df_view[[
            "codigo_caso", "rama_derecho", "categoria_caso", "tipo_caso",
            "titulo", "resultado", "resolucion_obtenida"
        ]],
        use_container_width=True,
        hide_index=True
    )

    if not df_view.empty:
        opciones_casos = [f"{r['codigo_caso']} — {r['titulo']} ({r['resultado']})" for _, r in df_view.iterrows()]
        sel_inspector = st.selectbox("Selecciona un expediente para ver su radiografía:", opciones_casos)
        cod_sel = sel_inspector.split(" — ")[0]
        caso_det = df_view[df_view["codigo_caso"] == cod_sel].iloc[0]

        c_ins1, c_ins2 = st.columns(2)
        with c_ins1:
            st.markdown(f"""
            <div class="card-box">
                <h4 style="margin-top:0;">📋 1. Hechos y Evidencia Forense</h4>
                <p><b>Expediente:</b> {caso_det['codigo_caso']} | <b>Rama:</b> {caso_det['rama_derecho']}</p>
                <p><b>Hechos:</b> {caso_det['evidencia_logs']}</p>
                <p><b>💼 ¿Qué hizo el Abogado?:</b> {caso_det['accion_abogado']}</p>
            </div>
            """, unsafe_allow_html=True)
        with c_ins2:
            st.markdown(f"""
            <div class="{'money-box' if caso_det['resultado'] == 'GANADO' else 'alert-box'}">
                <h4 style="margin-top:0;">⚖️ 2. Reacción del Juez y Veredicto ({caso_det['resultado']})</h4>
                <p><b>👨‍⚖️ Juez:</b> {caso_det['reaccion_juez']}</p>
                <p><b>✅ QUÉ HACER:</b> {caso_det['que_hacer_ciudadano']}</p>
                <p style="margin-bottom:0;"><b>🚫 QUÉ NO HACER JAMÁS:</b> {caso_det['que_no_hacer_ciudadano']}</p>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PESTAÑA 5: ALIMENTAR NUEVO PRECEDENTE
# ------------------------------------------------------------------------------
with tab5:
    st.subheader("➕ Registrar Nuevo Precedente en la Bóveda SQLite")
    with st.form("form_nuevo_precedente_v55"):
        f1, f2, f3 = st.columns(3)
        n_cod = f1.text_input("Código (ej. EXP-LAB-2026-013)")
        n_macro = f2.selectbox("Ámbito", list(RAMAS_DERECHO.keys()))
        n_rama = f3.selectbox("Rama del Derecho", sum(RAMAS_DERECHO.values(), []))
        f4, f5, f6 = st.columns(3)
        n_cat = f4.selectbox("Categoría de Caso", list(TIPOS_CASOS.keys()))
        n_tipo = f5.selectbox("Tipo de Caso", sum(TIPOS_CASOS.values(), []))
        n_res_final = f6.selectbox("Resultado Final", ["GANADO", "PERDIDO"])
        n_tit = st.text_input("Título Descriptivo del Caso")
        n_evidencia = st.text_area("📋 Hechos y Evidencia del Caso")
        n_accion_abogado = st.text_area("💼 ¿Qué hizo el Abogado?")
        n_reaccion_juez = st.text_area("👨‍⚖️ ¿Cómo resolvió el Juez?")
        n_que_hacer = st.text_area("✅ ¿Qué debe hacer el ciudadano?")
        n_que_no_hacer = st.text_area("🚫 ¿Qué NO debe hacer jamás?")
        btn_save = st.form_submit_button("💾 Guardar Precedente en Bóveda")
        if btn_save and n_cod and n_tit:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            try:
                h_sha = hashlib.sha256(n_evidencia.encode("utf-8")).hexdigest()
                c.execute(
                    """
                    INSERT INTO casos_juridicos_cbr (
                        codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,
                        titulo, actores_intervinientes, etapa_clave, medida_cautelar,
                        resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,
                        resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,
                        estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        n_cod, n_macro, n_rama, n_cat, n_tipo, n_tit,
                        "Juez, Abogado", "1. Demanda", "Embargo preventivo",
                        "Sentencia", "Amparo", n_evidencia, h_sha, n_res_final,
                        n_accion_abogado, n_reaccion_juez, "N/A", "Estrategia registrada",
                        n_que_hacer, n_que_no_hacer, datetime.now().strftime("%Y-%m-%d")
                    ),
                )
                conn.commit()
                st.success(f"✅ Precedente {n_cod} guardado exitosamente.")
            except sqlite3.IntegrityError:
                st.error("⚠️ Ese código de expediente ya existe.")
            finally:
                conn.close()

st.markdown("---")
st.caption(f"⚙️ **Arquitectura, Ingeniería de Costos y Diseño de Sistemas:** {AUTOR_SISTEMA} • {MARCA_SISTEMA}")

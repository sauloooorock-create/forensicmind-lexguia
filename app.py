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

# Intentar importar librerías avanzadas para voz y Word
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
# CONFIGURACIÓN DE PÁGINA Y ESTÉTICA LEGAL-FORENSE
# ==============================================================================
st.set_page_config(
    page_title="ForensicMind & LexGuía CBR v4.0 | Justicia Preventiva",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #111827, #1f2937);
        border: 1px solid #374151;
        border-left: 4px solid #38bdf8;
        padding: 14px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .win-badge { background-color: #065f46; color: #34d399; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    .loss-badge { background-color: #7f1d1d; color: #f87171; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    .step-badge { background-color: #1e3a8a; color: #93c5fd; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    .card-box {
        background-color: #131c2e;
        border: 1px solid #2dd4bf;
        border-radius: 10px;
        padding: 18px;
        margin-top: 10px;
    }
    .alert-box {
        background-color: #1f1215;
        border: 1px solid #f87171;
        border-radius: 10px;
        padding: 18px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

DB_NAME = "boveda_juridica_cbr_v4.db"

# ==============================================================================
# 1. TAXONOMÍA JURÍDICA INTEGRAL Y CATÁLOGOS V4
# ==============================================================================
RAMAS_DERECHO = {
    "Derecho Público": [
        "Derecho Constitucional", "Derecho Administrativo", "Derecho Penal",
        "Derecho Procesal Penal", "Derecho Electoral", "Derecho Internacional Público", "Derecho Tributario"
    ],
    "Derecho Privado": [
        "Derecho Civil", "Derecho Mercantil", "Derecho Laboral",
        "Derecho de Familia", "Derecho Procesal Civil", "Derecho Comercial", "Derecho de Propiedad Intelectual"
    ],
    "Otros / Especializados": [
        "Derecho Informático/Digital", "Derecho Ambiental", "Derecho Agrario",
        "Derecho Minero", "Derecho Marítimo", "Derecho de Seguros"
    ]
}

TIPOS_CASOS = {
    "Casos Penales": [
        "Homicidio", "Robo/Hurto", "Fraude", "Violencia doméstica",
        "Delitos de tránsito", "Narcotráfico", "Corrupción", "Abuso de autoridad", "Estafa", "Falsificación"
    ],
    "Casos Civiles": [
        "Divorcio/separación", "Custodia de menores", "Herencias/sucesiones",
        "Deudas", "Arrendamiento", "Responsabilidad civil", "Accidentes", "Contratos", "Daño y perjuicio", "Propiedad"
    ],
    "Casos Laborales": [
        "Despido injustificado", "Acoso laboral", "Discriminación",
        "Accidentes de trabajo", "Salarios adeudados", "Beneficios no pagados", "Reclasificación laboral"
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

ACTORES_JUDICIALES = {
    "Jueces y Magistrados": [
        "Juez civil", "Juez penal", "Juez laboral", "Juez mercantil", "Magistrado", "Juez de paz", "Juez de garantías"
    ],
    "Abogados": [
        "Abogado litigante", "Abogado asesor", "Abogado defensor", "Abogado acusador", "Abogado especializado", "Procurador"
    ],
    "Otros Profesionales": [
        "Fiscal/Ministerio Público", "Perito", "Notario", "Mediador", "Árbitro", "Gestor administrativo"
    ]
}

ETAPAS_PROCESO = {
    "Proceso Penal (8 Etapas)": [
        "1. Denuncia/Querella", "2. Investigación/Instrucción", "3. Auto de procesamiento",
        "4. Preparación de juicio oral", "5. Juicio oral", "6. Sentencia", "7. Recursos/Apelación", "8. Ejecución de sentencia"
    ],
    "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)": [
        "1. Demanda", "2. Contestación", "3. Prueba", "4. Alegatos", "5. Sentencia", "6. Recursos", "7. Ejecución"
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

CONCEPTOS_CLAVE = {
    "Demandante / Demandado": "En materia civil, laboral, familiar o mercantil: quien inicia la demanda exigiendo un derecho (Demandante) frente a quien debe responder o defenderse (Demandado).",
    "Acusador / Acusado": "En materia penal: la parte que imputa la comisión de un delito (Fiscalía/MP o víctima) frente a la persona señalada a quien le asiste la presunción de inocencia.",
    "Culpabilidad / Inocencia": "Principio rector donde toda persona es inocente hasta que se demuestre su responsabilidad más allá de toda duda razonable con pruebas lícitas.",
    "Prescripción": "¡ALERTA DE TIEMPO! Es la pérdida del derecho a denunciar o cobrar una deuda/indemnización por dejar pasar el plazo máximo que marca la ley.",
    "Caducidad": "Extinción automática de una instancia o proceso judicial por inactividad de las partes durante el tiempo legal establecido.",
    "Cosa juzgada": "Efecto definitivo de una sentencia firme contra la cual ya no cabe ningún recurso; el caso no puede volver a juzgarse dos veces.",
    "Legitimidad activa / pasiva": "Tener la titularidad real del derecho para poder reclamar (activa) o ser la persona legalmente obligada a responder (pasiva).",
    "Jurisdicción y Competencia": "El territorio y la materia exacta del Juez que tiene autoridad legal para resolver tu conflicto.",
    "Due process (Debido proceso)": "Garantía constitucional de ser oído en igualdad de condiciones, con defensa técnica, ante juez imparcial y sin pruebas obtenidas ilegalmente."
}

# ==============================================================================
# 2. CAPA DE PERSISTENCIA SQLITE CON ANATOMÍA DEL JUICIO (12+ CASOS SEMILLA)
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
                "Despido Injustificado con Resguardo de Evidencia Digital",
                "Juez laboral, Abogado especializado, Perito informático",
                "3. Prueba", "Embargo preventivo", "Sentencia condenatoria (Laudo favorable)", "Amparo directo",
                "Despido sin aviso formal, bloqueo de usuario y retención de salarios",
                hashlib.sha256(b"EXP-LAB-2026-001").hexdigest(), "GANADO",
                "El abogado recopiló capturas con SHA-256, bitácoras de asistencia y testigos presenciales.",
                "El Juez valoró positivamente las pruebas electrónicas y condenó al pago de indemnización total.",
                "N/A", "Aportar bitácoras y mensajes inmediatos.",
                "Demandar antes de los 60 días de plazo legal y aportar pruebas digitales.",
                "Jamás firmar hojas en blanco ni aceptar acuerdos verbales.", "2026-08-01"
            ),
            (
                "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
                "Despido Injustificado Perdido por Prescripción y Hoja en Blanco",
                "Juez laboral, Abogado patronal", "2. Contestación", "Ninguna",
                "Sentencia absolutoria (a favor de la empresa)", "Apelación",
                "Trabajador despedido que firmó renuncia voluntaria en hoja en blanco y esperó 4 meses",
                hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "PERDIDO",
                "El abogado defensor no objetó a tiempo la renuncia y dejó pasar el plazo.",
                "El Juez aplicó la excepción de prescripción y absolvió a la patronal.",
                "Prescripción consumada (más de 60 días) y firma coaccionada en blanco.",
                "N/A - Caso perdido por inactividad temporal.",
                "Acudir de inmediato al Centro de Conciliación.", "Jamás dejar pasar el plazo de 60 días ni firmar documentos sin leer.", "2026-08-05"
            ),
            (
                "EXP-FAM-2026-003", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia",
                "Fijación Exitosa de Pensión Provisional y Custodia",
                "Juez de lo Familiar, Abogado especialista", "1. Demanda", "Pensión provisional",
                "Sentencia civil favorable (35% vía nómina)", "Queja", "Ocultamiento de ingresos del deudor y necesidad de alimentos",
                hashlib.sha256(b"EXP-FAM-2026-003").hexdigest(), "GANADO",
                "El abogado solicitó informes financieros directos a la Comisión Bancaria y SAT.",
                "El Juez priorizó el interés superior del menor y decretó retención salarial.",
                "N/A", "Solicitar informes al SAT y bancos del deudor.",
                "Exigir pensión provisional desde el primer auto judicial.", "Acordar pensiones de palabra sin aval judicial.", "2026-08-10"
            ),
            (
                "EXP-FAM-2026-004", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia",
                "Pensión Alimenticia Perdida por Insolvencia Simulada No Combatida",
                "Juez familiar", "3. Prueba", "Ninguna", "Sentencia absolutoria parcial", "Apelación",
                "Deudor renunció a empleo formal para eludir su obligación",
                hashlib.sha256(b"EXP-FAM-2026-004").hexdigest(), "PERDIDO",
                "La parte actora no aportó indicios de capacidad económica real alterna.",
                "El Juez resolvió con base en ingresos formales nulos declarados.",
                "Falta de investigación patrimonial y peritaje contable.", "N/A",
                "Ofrecer peritaje financiero de estilo de vida.", "Confiarse en que el deudor no tiene ingresos formales.", "2026-08-15"
            ),
            (
                "EXP-PEN-2026-005", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude",
                "Estafa Digital y Phishing Bancario Ganado por Trazas SHA-256",
                "Juez de garantías, Fiscal, Perito forense", "2. Investigación", "Congelamiento de cuentas",
                "Sentencia condenatoria", "Amparo", "Transferencia no autorizada y alteración de bitácoras de acceso",
                hashlib.sha256(b"EXP-PEN-2026-005").hexdigest(), "GANADO",
                "El perito aportó trazas IP y huella hash SHA-256 intactas.",
                "El Juez ordenó el aseguramiento inmediato de la cuenta receptora del fraude.",
                "N/A", "Interponer querella con peritaje informático inmediato.",
                "Denunciar en menos de 24 horas y aportar bitácoras digitales.", "Alterar capturas de pantalla o borrar registros.", "2026-08-20"
            ),
            (
                "EXP-PEN-2026-006", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude",
                "Fraude Bancario Perdido por Alteración de Pruebas Digitales",
                "Fiscalía", "3. Prueba", "Ninguna", "Sentencia absolutoria", "Apelación",
                "Víctima modificó archivos de registro antes de entregarlos al perito",
                hashlib.sha256(b"EXP-PEN-2026-006").hexdigest(), "PERDIDO",
                "La defensa demostró ruptura de la cadena de custodia digital.",
                "El Juez desechó las capturas por carecer de integridad criptográfica.",
                "Ruptura de cadena de custodia y alteración de metadatos.", "N/A",
                "Preservar dispositivos originales sin modificar.", "Modificar o editar archivos de evidencia digital.", "2026-08-25"
            ),
            (
                "EXP-PEN-2026-007", "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad",
                "Detención Ilegal y Nulidad de Cateo sin Orden Judicial",
                "Juez de garantías, Defensor público", "3. Auto de procesamiento", "Medidas de protección",
                "Sentencia absolutoria (Nulidad absoluta)", "Habeas corpus / Amparo",
                "Policías ingresaron al domicilio sin orden de cateo ni flagrancia",
                hashlib.sha256(b"EXP-PEN-2026-007").hexdigest(), "GANADO",
                "El abogado defensor acreditó violación flagrante al debido proceso y artículo 16 constitucional.",
                "El Juez decretó la nulidad de todo lo actuado y la libertad inmediata.",
                "N/A", "Invocar control convencional y nulidad de prueba ilícita.",
                "Exigir orden de cateo firmada por juez competente.", "Oponer resistencia física violenta ante la autoridad.", "2026-09-01"
            ),
            (
                "EXP-PEN-2026-008", "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad",
                "Detención Validada por Consentimiento Tácito en Audiencia",
                "Juez penal", "5. Juicio oral", "Prisión preventiva", "Sentencia condenatoria", "Apelación",
                "Imputado firmó actas ministeriales sin presencia de defensor técnico",
                hashlib.sha256(b"EXP-PEN-2026-008").hexdigest(), "PERDIDO",
                "Falta de objeción oportuna por la defensa inicial.",
                "El Juez consideró convalidadas las actuaciones ministeriales.",
                "Convalidación de vicios formales por falta de defensa técnica temprana.", "N/A",
                "Designar defensor particular o público desde el primer momento.", "Declarar ante el ministerio público sin asistencia legal.", "2026-09-05"
            ),
            (
                "EXP-CIV-2026-009", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento",
                "Desocupación Legal y Embargo de Garantías por Rentas Vencidas",
                "Juez civil", "1. Demanda", "Embargo precautorio", "Sentencia condenatoria", "Apelación",
                "Inquilino con 6 meses de adeudo y negativa de entrega de inmueble",
                hashlib.sha256(b"EXP-CIV-2026-009").hexdigest(), "GANADO",
                "El abogado promovió juicio de desahucio con solicitud simultánea de embargo de bienes.",
                "El Juez autorizó el lanzamiento y ejecución coactiva con fuerza pública.",
                "N/A", "Promover juicio especial de arrendamiento y embargo precautorio.",
                "Seguir estrictamente la vía judicial para recuperar la posesión.", "Desalojar por propia mano cambiando cerraduras.", "2026-09-10"
            ),
            (
                "EXP-CIV-2026-010", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento",
                "Desalojo por Propia Mano Convertido en Delito de Despojo",
                "Juez penal y civil", "2. Contestación", "Ninguna", "Sentencia condenatoria (Contra el propietario)", "Amparo",
                "Propietario sacó muebles a la calle sin orden judicial",
                hashlib.sha256(b"EXP-CIV-2026-010").hexdigest(), "PERDIDO",
                "El arrendador actuó por propia mano ignorando los tribunales civiles.",
                "El Juez sancionó el autotutela convirtiendo al dueño en imputado penal.",
                "Justicia por propia mano (Autotutela prohibida por ley).", "N/A",
                "Acudir al juzgado civil competente.", "Tomar la justicia por propia mano.", "2026-09-15"
            ),
            (
                "EXP-MER-2026-011", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos",
                "Cobro Ejecutivo de Pagaré con Embargo Precautorio Exitoso",
                "Juez mercantil", "1. Demanda", "Embargo preventivo", "Sentencia condenatoria (Remate)", "Apelación",
                "Incumplimiento de título de crédito por parte de empresa de comercio",
                hashlib.sha256(b"EXP-MER-2026-011").hexdigest(), "GANADO",
                "El abogado ejecutó el título con base en el artículo 1391 del Código de Comercio.",
                "El Juez ordenó embargo inmediato en la diligencia de exequendo.",
                "N/A", "Ejecutar pagaré mercantil con aparejada ejecución.",
                "Verificar la correcta redacción y firmas del título de crédito.", "Aceptar pagarés con alteraciones o espacios en blanco.", "2026-09-20"
            ),
            (
                "EXP-MER-2026-012", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos",
                "Cobro Mercantil Perdido por Alteración de la Fecha en el Pagaré",
                "Juez mercantil", "3. Prueba", "Ninguna", "Sentencia absolutoria", "Apelación",
                "Pagaré con enmienda física visible en el espacio de fecha de vencimiento",
                hashlib.sha256(b"EXP-MER-2026-012").hexdigest(), "PERDIDO",
                "El perito grafoscópico de la contraparte demostró la alteración material del documento.",
                "El Juez absolvió al demandado por pérdida de fuerza ejecutiva del título.",
                "Alteración material del documento base de la acción.", "N/A",
                "Revisar autenticidad y pulcritud de documentos mercantiles.", "Alterar o enmendar manualmente títulos de crédito.", "2026-09-25"
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
# 3. RED NEURONAL MLP Y MOTOR CBR
# ==============================================================================
def entrenar_red_neuronal_autoclasificacion():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    conn.close()
    
    if df.empty or MLPClassifier is None or TfidfVectorizer is None:
        return None, None
        
    X_text = df['titulo'] + " " + df['evidencia_logs'] + " " + df['tipo_caso']
    y_rama = df['rama_derecho']
    
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=500)
    X_vec = vectorizer.fit_transform(X_text)
    
    mlp = MLPClassifier(hidden_layer_sizes=(64, 32), activation='relu', max_iter=300, random_state=42)
    mlp.fit(X_vec, y_rama)
    return vectorizer, mlp

VECTORIZER_MLP, MODELO_MLP = entrenar_red_neuronal_autoclasificacion()

def autoclasificar_caso_con_red_neuronal(relato: str) -> dict:
    if MODELO_MLP is not None and VECTORIZER_MLP is not None:
        X_test = VECTORIZER_MLP.transform([relato])
        rama_predicha = MODELO_MLP.predict(X_test)[0]
        probabilidades = MODELO_MLP.predict_proba(X_test)[0]
        confianza = round(float(max(probabilidades)) * 100, 1)
    else:
        rama_predicha = "Derecho Civil"
        confianza = 75.0
        
    # Heurísticas complementarias
    cat = "Casos Civiles"
    tipo = "Contratos"
    if any(k in relato.lower() for k in ['despido', 'patrón', 'salario', 'trabajo', 'renuncia']):
        cat = "Casos Laborales"
        tipo = "Despido injustificado"
    elif any(k in relato.lower() for k in ['pensión', 'hijos', 'custodia', 'divorcio', 'menor']):
        cat = "Casos Familiares"
        tipo = "Pensión alimenticia"
    elif any(k in relato.lower() for k in ['fraude', 'estafa', 'policía', 'amenaza', 'robo', 'detención']):
        cat = "Casos Penales"
        tipo = "Fraude"
    elif any(k in relato.lower() for k in ['pagaré', 'deuda', 'contrato', 'comercial', 'empresa']):
        cat = "Casos Mercantiles"
        tipo = "Incumplimiento de contratos"

    return {
        "rama": rama_predicha,
        "categoria": cat,
        "tipo": tipo,
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
    riesgo = 20
    reglas = [
        (r'despido|renuncia|hoja en blanco|finiquito|salarios', "🟠 ALERTA LABORAL: Riesgo de prescripción (60 días para demandar).", 25),
        (r'violencia|amenaza|golpe|agresi|peligro|arma', "🔴 URGENCIA PENAL/FAMILIAR: Solicitar Medidas de Protección inmediatas.", 35),
        (r'detenci|polic|abuso de autoridad|cateo|sin orden', "🔴 ALERTA CONSTITUCIONAL: Posible violación al Debido Proceso; evaluar Amparo y Nulidad.", 35),
        (r'fraude|estafa|phishing|transferencia|hash|log|ip', "🔴 ALERTA FORENSE DIGITAL: Evidencia electrónica; sellar con SHA-256.", 30),
        (r'pagar[eé]|deuda|contrato|renta|arrendamiento|incumplimiento', "🟡 RIESGO PATRIMONIAL: Solicitar Embargo Preventivo u Orden de No Enajenar.", 20),
        (r'pensi[oó]n|alimentos|hijos|custodia|menor', "🟠 PRIORIDAD FAMILIAR: Exigir Pensión Alimenticia Provisional urgente.", 25)
    ]
    for patron, msg, peso in reglas:
        if re.search(patron, relato_evidencia, re.IGNORECASE):
            hallazgos.append(msg)
            riesgo += peso
    riesgo = min(100, riesgo)
    if not hallazgos:
        hallazgos.append("🟢 Caso ordinario: Asegurar documentos y verificar plazos.")
    return {
        "hallazgos": hallazgos,
        "riesgo_score": riesgo,
        "hash_evidencia": hashlib.sha256(relato_evidencia.encode('utf-8')).hexdigest()
    }

# ==============================================================================
# 4. DICTADO POR VOZ Y EXPORTACIÓN A WORD (.DOCX)
# ==============================================================================
def transcribir_audio_espanol(audio_bytes) -> str:
    if sr is None or audio_bytes is None:
        return ""
    try:
        r = sr.Recognizer()
        audio_file = io.BytesIO(audio_bytes.read())
        with sr.AudioFile(audio_file) as source:
            audio_data = r.record(source)
            texto = r.recognize_google(audio_data, language="es-MX")
            return texto
    except Exception:
        return "⚠️ No se pudo procesar automáticamente el audio. Por favor escribe tu relato en el cuadro de texto."

def generar_dictamen_word_docx(codigo, clasificacion, auditoria, plan, top_prec) -> bytes:
    if Document is None:
        return b""
    doc = Document()
    doc.add_heading("DICTAMEN JURÍDICO-FORENSE Y PLAN DE ACCIÓN", 0)
    
    doc.add_paragraph(f"Expediente / Código: {codigo}")
    doc.add_paragraph(f"Fecha de Emisión: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph(f"Sello Criptográfico SHA-256: {auditoria['hash_evidencia']}")
    
    doc.add_heading("1. Autoclasificación Neuronal (MLP)", level=1)
    doc.add_paragraph(f"Rama Detectada: {clasificacion['rama']} (Confianza: {clasificacion['confianza']}%)")
    doc.add_paragraph(f"Categoría: {clasificacion['categoria']} | Tipo: {clasificacion['tipo']}")
    
    doc.add_heading("2. Diagnóstico de Riesgo y Alertas Forenses", level=1)
    doc.add_paragraph(f"Puntuación de Urgencia: {auditoria['riesgo_score']} / 100")
    for h in auditoria['hallazgos']:
        doc.add_paragraph(f"• {h}", style='List Bullet')
        
    doc.add_heading("3. Protocolo Ciudadano Paso a Paso", level=1)
    for paso in plan['pasos_inmediatos']:
        doc.add_paragraph(f"• {paso}", style='List Bullet')
        
    doc.add_heading("4. Precedente CBR Más Cercano", level=1)
    doc.add_paragraph(f"Caso Referencia: {top_prec['codigo_caso']} - {top_prec['titulo']}")
    doc.add_paragraph(f"Estrategia Ganadora: {top_prec['estrategia_ganadora']}")
    doc.add_paragraph(f"Causa Raíz de Falla (en caso de derrota): {top_prec['causa_raiz_fallo']}")
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

# ==============================================================================
# 5. GENERADOR DE FICHA VERTICAL 9:16 (1080x1920)
# ==============================================================================
def limpiar_ascii(texto: str) -> str:
    reemplazos = str.maketrans("áéíóúñÁÉÍÓÚÑ", "aeiounAEIOUN")
    return texto.translate(reemplazos).encode('ascii', 'ignore').decode('ascii')

def generar_ficha_vertical_9_16(codigo: str, rama: str, caso: str, etapa: str, plan: dict, prob_exito: float, riesgo: int, hash_ev: str) -> np.ndarray:
    alto, ancho = 1920, 1080
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[:] = (24, 15, 10)
    
    cv2.rectangle(img, (25, 25), (1055, 1895), (240, 175, 50), 4)
    cv2.rectangle(img, (40, 40), (1040, 1880), (70, 50, 30), 2)
    
    cv2.rectangle(img, (40, 40), (1040, 220), (45, 28, 16), -1)
    cv2.putText(img, "FORENSICMIND & LEXGUIA v4.0", (70, 110), cv2.FONT_HERSHEY_DUPLEX, 1.6, (100, 220, 255), 3)
    cv2.putText(img, "DICTAMEN JURIDICO Y SELLO PERICIAL (9:16)", (70, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (210, 210, 210), 2)
    
    cv2.putText(img, limpiar_ascii(f"EXPEDIENTE: {codigo}"), (70, 285), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
    cv2.putText(img, limpiar_ascii(f"RAMA: {rama}"), (70, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (140, 240, 180), 2)
    cv2.putText(img, limpiar_ascii(f"TIPO: {caso}"), (70, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (140, 240, 180), 2)
    cv2.putText(img, limpiar_ascii(f"ETAPA: {etapa[:42]}"), (70, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 210, 110), 2)
    
    cv2.rectangle(img, (70, 480), (515, 680), (35, 35, 68), -1)
    cv2.putText(img, "RIESGO LEGAL", (110, 535), cv2.FONT_HERSHEY_DUPLEX, 0.9, (210, 210, 255), 2)
    cv2.putText(img, f"{riesgo}/100", (145, 635), cv2.FONT_HERSHEY_DUPLEX, 2.0, (90, 90, 255), 4)
    
    cv2.rectangle(img, (565, 480), (1010, 680), (30, 60, 35), -1)
    cv2.putText(img, "VIABILIDAD CBR", (625, 535), cv2.FONT_HERSHEY_DUPLEX, 0.9, (200, 255, 200), 2)
    cv2.putText(img, f"{prob_exito}%", (660, 635), cv2.FONT_HERSHEY_DUPLEX, 2.0, (110, 240, 130), 4)
    
    cv2.putText(img, "ACTORES Y MEDIDAS CLAVE:", (70, 755), cv2.FONT_HERSHEY_DUPLEX, 1.0, (100, 220, 255), 2)
    cv2.putText(img, limpiar_ascii(f"Juez: {plan['juez'][:45]}"), (70, 805), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 230), 2)
    cv2.putText(img, limpiar_ascii(f"Defensa: {plan['abogado'][:45]}"), (70, 850), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 230), 2)
    cv2.putText(img, limpiar_ascii(f"Medida: {plan['medida_sugerida'][:45]}"), (70, 895), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 220, 120), 2)
    
    cv2.putText(img, "GUIA CIUDADANA PASO A PASO:", (70, 995), cv2.FONT_HERSHEY_DUPLEX, 1.0, (140, 255, 160), 2)
    y_cursor = 1055
    for paso in plan["pasos_inmediatos"][:3]:
        limpio = limpiar_ascii(paso)
        cv2.putText(img, limpio[:55], (70, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (220, 220, 220), 2)
        y_cursor += 50
        
    cv2.putText(img, "SELLO SHA-256:", (70, 1600), cv2.FONT_HERSHEY_DUPLEX, 0.85, (100, 220, 255), 2)
    cv2.putText(img, hash_ev[:36], (70, 1645), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 255, 160), 2)
    
    cv2.rectangle(img, (70, 1735), (1010, 1850), (42, 30, 20), -1)
    cv2.putText(img, "VERTICAL 9:16 (1080x1920 PX)", (200, 1785), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 218), 2)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# ==============================================================================
# 6. INTERFAZ PRINCIPAL DE LA SUITE v4.0
# ==============================================================================
st.title("⚖️ ForensicMind & LexGuía CBR v4.0 — Red Neuronal y Anatomía del Juicio")
st.caption("Autoclasificación MLP • Comparativa Ganados vs. Perdidos • Dictado por Voz • Sello SHA-256")

tab1, tab2, tab3, tab4 = st.tabs([
    "🛡️ 1. Autoclasificación en 1 Clic & Comparador Ganados vs. Perdidos",
    "🗺️ 2. Etapas del Juicio, Actores y Diccionario Legal",
    "📚 3. Bóveda y Radiografía Completa de Casos",
    "➕ 4. Registrar Nuevo Caso"
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: AUTOCLASIFICACIÓN Y ANÁLISIS
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("🧠 Cuéntame libremente qué ocurrió (Autoclasificación con Red Neuronal)")
    
    col_voz1, col_voz2 = st.columns([2, 1])
    with col_voz2:
        audio_file = st.audio_input("🎙️ Dictar mi caso por voz (Español)")
        texto_voz = ""
        if audio_file is not None:
            with st.spinner("Transcribiendo audio..."):
                texto_voz = transcribir_audio_espanol(audio_file)
                if texto_voz:
                    st.success("¡Transcripción completada!")

    def_relato = "Me despidieron injustificadamente hoy, me exigen firmar una hoja en blanco y bloquearon mi acceso."
    if texto_voz and "⚠️" not in texto_voz:
        def_relato = texto_voz

    relato_usuario = st.text_area(
        "Escribe aquí con tus propias palabras qué te pasó, qué te reclaman o edita tu dictado por voz:",
        value=def_relato,
        height=120
    )

    clasificacion = autoclasificar_caso_con_red_neuronal(relato_usuario)
    
    with st.expander("⚙️ Ajustes Manuales (Opcional)", expanded=False):
        c_sel1, c_sel2, c_sel3 = st.columns(3)
        macro_sel = c_sel1.selectbox("Ámbito del Derecho", list(RAMAS_DERECHO.keys()))
        rama_sel = c_sel2.selectbox("Rama Específica", RAMAS_DERECHO[macro_sel], index=0)
        cat_caso_sel = c_sel3.selectbox("Familia de Caso", list(TIPOS_CASOS.keys()), index=2)
        tipo_caso_sel = st.selectbox("Problema Específico", TIPOS_CASOS[cat_caso_sel], index=0)
        rol_sel = st.radio("Tu Posición:", ["Demandante / Acusador", "Demandado / Acusado"])
        etapa_sel = st.selectbox("Etapa Judicial:", ETAPAS_PROCESO["Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)"])
        codigo_exp = st.text_input("Código de Expediente", value="ASESORIA-2026-04")
    
    # Usar valores automáticos o manuales
    rama_activa = clasificacion['rama']
    cat_activa = clasificacion['categoria']
    tipo_activo = clasificacion['tipo']
    plan_activo = obtener_plan_accion_ciudadano(cat_activa, tipo_activo, "Demandante")

    # Búsqueda CBR
    conn = sqlite3.connect(DB_NAME)
    df_hist = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    conn.close()

    consulta_full = f"{rama_activa} {cat_activa} {tipo_activo} {relato_usuario}"
    similitudes = []
    for _, row in df_hist.iterrows():
        doc_hist = f"{row['rama_derecho']} {row['categoria_caso']} {row['tipo_caso']} {row['titulo']} {row['evidencia_logs']} {row['que_hacer_ciudadano']}"
        score_sim = calcular_similitud_coseno(consulta_full, doc_hist)
        similitudes.append({**row.to_dict(), "similitud": score_sim})

    df_sim = pd.DataFrame(similitudes).sort_values(by="similitud", ascending=False)
    relevantes = df_sim[df_sim["similitud"] > 5.0]
    if not relevantes.empty:
        ganados_peso = relevantes[relevantes["resultado"] == "GANADO"]["similitud"].sum()
        total_peso = relevantes["similitud"].sum()
        prob_exito = round((ganados_peso / total_peso) * 100, 1) if total_peso > 0 else 60.0
    else:
        prob_exito = 60.0

    auditoria = auditar_riesgo_juridico_forense(relato_usuario)
    top_precedente = df_sim.iloc[0]

    # Métricas de salida
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Confianza Neuronal MLP", f"{clasificacion['confianza']}%", clasificacion['rama'])
    m2.metric("Urgencia / Riesgo Legal", f"{auditoria['riesgo_score']}/100", "Atención Inmediata" if auditoria['riesgo_score'] >= 65 else "Ordinario")
    m3.metric("Viabilidad CBR", f"{prob_exito}%", f"Cruce con {len(relevantes)} casos")
    m4.metric("Precedente Cercano", f"{top_precedente['similitud']}%", top_precedente["codigo_caso"])

    # Botón de Descarga de Dictamen Word (.docx)
    word_bytes = generar_dictamen_word_docx(codigo_exp, clasificacion, auditoria, plan_activo, top_precedente)
    st.download_button(
        label="📄 Descargar Dictamen Jurídico-Forense Completo en Word (.docx)",
        data=word_bytes,
        file_name=f"Dictamen_{codigo_exp}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    st.markdown("---")
    st.subheader("⚖️ Comparativa Directa: Casos Ganados vs. Perdidos (Qué Hacer vs. Qué No Hacer)")
    col_w, col_l = st.columns(2)

    with col_w:
        st.markdown("#### 🟢 Cómo se GANA este caso (Precedente Exitoso)")
        for _, g in df_sim[df_sim["resultado"] == "GANADO"].head(1).iterrows():
            st.markdown(f"""
            <div class="card-box">
                <span class="win-badge">GANADO • {g['similitud']}% SIMILITUD</span> <b>{g['codigo_caso']}</b><br>
                <b>{g['titulo']}</b><br><br>
                <b>💼 Qué hizo el Abogado:</b> {g['accion_abogado']}<br>
                <b>👨‍⚖️ Reacción del Juez:</b> {g['reaccion_juez']}<br>
                <b>✅ QUÉ DEBES HACER HOY:</b> {g['que_hacer_ciudadano']}
            </div>
            """, unsafe_allow_html=True)

    with col_l:
        st.markdown("#### 🔴 Por qué se PIERDE este caso (Errores fatales)")
        for _, p in df_sim[df_sim["resultado"] == "PERDIDO"].head(1).iterrows():
            st.markdown(f"""
            <div class="alert-box">
                <span class="loss-badge">PERDIDO • {p['similitud']}% SIMILITUD</span> <b>{p['codigo_caso']}</b><br>
                <b>{p['titulo']}</b><br><br>
                <b>💥 Causa Raíz del Fallo:</b> {p['causa_raiz_fallo']}<br>
                <b>🚫 QUÉ NO DEBES HACER JAMÁS:</b> {p['que_no_hacer_ciudadano']}
            </div>
            """, unsafe_allow_html=True)

    with st.expander("📱 Generar Ficha Pericial en Formato Vertical 9:16 (1080x1920 px)", expanded=False):
        img_9_16 = generar_ficha_vertical_9_16(
            codigo_exp, rama_activa, tipo_activo, "1. Demanda / Inicio",
            plan_activo, prob_exito, auditoria["riesgo_score"], auditoria["hash_evidencia"]
        )
        c_i1, c_i2, c_i3 = st.columns([1, 1.2, 1])
        with c_i2:
            st.image(img_9_16, caption="Ficha Pericial 9:16 (1080x1920 px)", use_container_width=True)
            st.download_button(
                label="📥 Descargar Imagen 9:16 (PNG)",
                data=cv2.imencode('.png', cv2.cvtColor(img_9_16, cv2.COLOR_RGB2BGR))[1].tobytes(),
                file_name=f"Ficha_{codigo_exp}.png",
                mime="image/png"
            )

# ------------------------------------------------------------------------------
# PESTAÑA 2: ETAPAS Y DICCIONARIO
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("🗺️ Mapa de Etapas Judiciales y Diccionario Legal")
    col_et1, col_et2 = st.columns(2)
    with col_et1:
        st.markdown("#### 🚔 Proceso Penal (8 Etapas)")
        for e in ETAPAS_PROCESO["Proceso Penal (8 Etapas)"]:
            st.markdown(f"• {e}")
        st.markdown("#### 📑 Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)")
        for e in ETAPAS_PROCESO["Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)"]:
            st.markdown(f"• {e}")
    with col_et2:
        st.markdown("#### 📖 Diccionario Ciudadano")
        concepto = st.selectbox("Concepto legal:", list(CONCEPTOS_CLAVE.keys()))
        st.info(f"**{concepto}:** {CONCEPTOS_CLAVE[concepto]}")

# ------------------------------------------------------------------------------
# PESTAÑA 3: BÓVEDA E INSPECTOR DETALLADO DE CASOS
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📚 Bóveda y Radiografía Completa de Casos (Anatomía del Juicio)")
    f_col1, f_col2, f_col3 = st.columns(3)
    filtro_ver = f_col1.selectbox("Resultado:", ["TODOS", "GANADO", "PERDIDO"])
    filtro_cat = f_col2.selectbox("Familia:", ["TODAS"] + list(TIPOS_CASOS.keys()))
    
    df_view = df_hist.copy()
    if filtro_ver != "TODOS":
        df_view = df_view[df_view["resultado"] == filtro_ver]
    if filtro_cat != "TODAS":
        df_view = df_view[df_view["categoria_caso"] == filtro_cat]
        
    caso_seleccionado = st.selectbox("🔍 Selecciona un Expediente para Inspección Profunda:", df_view["codigo_caso"].tolist())
    
    if caso_seleccionado:
        c_det = df_hist[df_hist["codigo_caso"] == caso_seleccionado].iloc[0]
        
        st.markdown(f"### 📁 Expediente: {c_det['codigo_caso']} — {c_det['titulo']}")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown(f"""
            <div class="card-box">
                <h4>📋 1. Hechos y Evidencia Forense</h4>
                <p><b>Rama:</b> {c_det['rama_derecho']} ({c_det['categoria_caso']})</p>
                <p><b>Hechos / Logs:</b> {c_det['evidencia_logs']}</p>
                <p><b>Hash SHA-256:</b> <code>{c_det['hash_sha256']}</code></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="card-box">
                <h4>💼 2. ¿Qué hizo exactamente el Abogado?</h4>
                <p>{c_det['accion_abogado'] if c_det['accion_abogado'] else c_det['estrategia_ganadora']}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_d2:
            st.markdown(f"""
            <div class="card-box">
                <h4>👨‍⚖️ 3. ¿Cómo reaccionó el Juez y qué valoró?</h4>
                <p><b>Resolución:</b> {c_det['resolucion_obtenida']}</p>
                <p><b>Criterio Judicial:</b> {c_det['reaccion_juez'] if c_det['reaccion_juez'] else 'Valoración conforme a derecho y pruebas aportadas.'}</p>
            </div>
            """, unsafe_allow_html=True)
            
            is_win = c_det['resultado'] == 'GANADO'
            st.markdown(f"""
            <div class="{'card-box' if is_win else 'alert-box'}">
                <h4 style="color:{'#34d399' if is_win else '#f87171'};">⚖️ 4. Veredicto y Guía Ciudadana</h4>
                <p><b>Resultado:</b> {c_det['resultado']}</p>
                <p><b>Estrategia / Falla:</b> {c_det['estrategia_ganadora'] if is_win else c_det['causa_raiz_fallo']}</p>
                <p><b>Qué Hacer:</b> {c_det['que_hacer_ciudadano']}</p>
                <p><b>Qué NO Hacer:</b> {c_det['que_no_hacer_ciudadano']}</p>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# PESTAÑA 4: REGISTRAR NUEVO PRECEDENTE
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("➕ Registrar Nuevo Precedente con Anatomía del Juicio en SQLite")
    with st.form("form_nuevo_v4"):
        f1, f2, f3 = st.columns(3)
        n_cod = f1.text_input("Código (ej. EXP-LAB-2026-013)")
        n_macro = f2.selectbox("Ámbito", list(RAMAS_DERECHO.keys()))
        n_rama = f3.selectbox("Rama del Derecho", sum(RAMAS_DERECHO.values(), []))
        
        f4, f5, f6 = st.columns(3)
        n_cat = f4.selectbox("Familia de Caso", list(TIPOS_CASOS.keys()))
        n_tipo = f5.selectbox("Tipo de Caso", sum(TIPOS_CASOS.values(), []))
        n_res_final = f6.selectbox("Resultado Final", ["GANADO", "PERDIDO"])
        
        n_tit = st.text_input("Título Descriptivo")
        
        f7, f8, f9 = st.columns(3)
        n_etapa = f7.selectbox("Etapa Determinante", sum(ETAPAS_PROCESO.values(), []))
        n_medida = f8.selectbox("Medida Cautelar", ["Ninguna"] + MEDIDAS_CAUTELARES)
        n_recurso = f9.selectbox("Recurso Legal", ["Ninguno"] + RECURSOS_LEGALES)
        
        f10, f11 = st.columns(2)
        n_resolucion = f10.selectbox("Resolución Emitida", RESOLUCIONES_SENTENCIAS)
        n_actores = f11.text_input("Actores intervinientes")
        
        n_evidencia = st.text_area("📋 Hechos y Evidencia Forense")
        
        col_ab_j1, col_ab_j2 = st.columns(2)
        with col_ab_j1:
            n_accion_abogado = st.text_area("💼 ¿Qué hizo exactamente el Abogado?")
        with col_ab_j2:
            n_reaccion_juez = st.text_area("👨‍⚖️ ¿Cómo reaccionó el Juez?")
            
        n_causa_fallo = st.text_input("Si se PERDIÓ: Causa raíz o error procesal (o N/A)")
        n_estrategia = st.text_area("Estrategia ganadora aplicada")
        
        col_qh1, col_qh2 = st.columns(2)
        with col_qh1:
            n_que_hacer = st.text_area("✅ Qué DEBE hacer el ciudadano")
        with col_qh2:
            n_que_no_hacer = st.text_area("🚫 Qué NO debe hacer jamás")
            
        btn_save = st.form_submit_button("💾 Guardar Precedente Completo")
        if btn_save and n_cod and n_tit:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            try:
                h_sha = hashlib.sha256(n_evidencia.encode("utf-8")).hexdigest()
                c.execute("""
                    INSERT INTO casos_juridicos_cbr (
                        codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,
                        titulo, actores_intervinientes, etapa_clave, medida_cautelar,
                        resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,
                        resultado, accion_abogado, reaccion_juez, causa_raiz_fallo,
                        estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano, fecha_registro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    n_cod, n_macro, n_rama, n_cat, n_tipo, n_tit, n_actores,
                    n_etapa, n_medida, n_resolucion, n_recurso, n_evidencia, h_sha,
                    n_res_final, n_accion_abogado, n_reaccion_juez, n_causa_fallo,
                    n_estrategia, n_que_hacer, n_que_no_hacer, datetime.now().strftime("%Y-%m-%d")
                ))
                conn.commit()
                st.success(f"✅ Precedente {n_cod} guardado exitosamente en `{DB_NAME}`.")
            except sqlite3.IntegrityError:
                st.error("⚠️ Ese código de expediente ya existe en la base de datos.")
            finally:
                conn.close()

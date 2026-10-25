
import streamlit as st
import sqlite3
import hashlib
import re
import math
from collections import Counter
from datetime import datetime
import pandas as pd
import numpy as np
import cv2

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTÉTICA LEGAL-FORENSE
# ==============================================================================
st.set_page_config(
    page_title="ForensicMind & LexGuía CBR v3.0 | Justicia Preventiva",
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

DB_NAME = "boveda_juridica_cbr_v3.db"

# ==============================================================================
# 1. TAXONOMÍA JURÍDICA INTEGRAL (BASE DE CONOCIMIENTO ESTRUCTURADA)
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

ACTORES_JUDICIALES = {
    "Jueces y Magistrados": [
        "Juez civil", "Juez penal", "Juez laboral", "Juez mercantil",
        "Magistrado", "Juez de paz", "Juez de garantías"
    ],
    "Abogados": [
        "Abogado litigante", "Abogado asesor", "Abogado defensor",
        "Abogado acusador", "Abogado especializado", "Procurador"
    ],
    "Otros Profesionales": [
        "Fiscal/Ministerio Público", "Perito", "Notario",
        "Mediador", "Árbitro", "Gestor administrativo"
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

CONCEPTOS_CLAVE = {
    "Demandante / Demandado": "En materia civil, laboral, familiar o mercantil: quien inicia la demanda exigiendo un derecho (Demandante) frente a quien debe responder o defenderse (Demandado).",
    "Acusador / Acusado": "En materia penal: la parte que imputa la comisión de un delito (Fiscalía/MP o víctima) frente a la persona señalada a quien le asiste la presunción de inocencia.",
    "Culpabilidad / Inocencia": "Principio rector donde toda persona es inocente hasta que se demuestre su responsabilidad más allá de toda duda razonable con pruebas lícitas.",
    "Prescripción": "¡ALERTA DE TIEMPO! Es la pérdida del derecho a denunciar o cobrar una deuda/indemnización por dejar pasar el plazo máximo que marca la ley.",
    "Caducidad": "Extinción automática de una instancia o proceso judicial por inactividad de las partes durante el tiempo legal establecido.",
    "Cosa juzgada": "Efecto definitivo de una sentencia firme contra la cual ya no cabe ningún recurso; el caso no puede volver a juzgarse dos veces.",
    "Legitimidad activa / pasiva": "Tener la titularidad real del derecho para poder reclamar (activa) o ser la persona legalmente obligada a responder (pasiva).",
    "Jurisdicción y Competencia": "El territorio y la materia exacta del Juez que tiene autoridad legal para resolver tu conflicto (ej. no llevar un despido ante un juez civil).",
    "Due process (Debido proceso)": "Garantía constitucional de ser oído en igualdad de condiciones, con defensa técnica, ante juez imparcial y sin pruebas obtenidas ilegalmente."
}

# ==============================================================================
# 2. GUÍA AUTOMÁTICA DE "QUÉ HACER" SEGÚN CATEGORÍA DE CASO
# ==============================================================================
def obtener_plan_accion_ciudadano(categoria_caso: str, tipo_caso: str, rol_usuario: str) -> dict:
    if categoria_caso == "Casos Penales":
        return {
            "proceso": "Proceso Penal (8 Etapas)",
            "juez": "Juez de garantías / Juez penal",
            "abogado": "Abogado acusador (Asesor jurídico de víctima)" if "Víctima" in rol_usuario else "Abogado defensor penalista",
            "profesionales": "Fiscal/Ministerio Público + Perito Forense",
            "medida_sugerida": "Medidas de protección inmediatas / Retención de bienes",
            "recurso_clave": "Amparo / Habeas corpus (si hay detención arbitraria) / Apelación",
            "pasos_inmediatos": [
                "1. NO alterar ni tocar la escena, teléfono o documento original (preservar Cadena de Custodia y sello SHA-256).",
                "2. Acudir al Ministerio Público / Fiscalía a interponer Denuncia o Querella narrando hora, fecha y lugar exactos (o exigir lectura de derechos y Abogado Defensor si eres el imputado).",
                "3. Solicitar de inmediato Medidas de Protección si existe riesgo físico, violencia doméstica o abuso de autoridad.",
                "4. Exigir la intervención de Perito para fijar pruebas antes de que se borren cámaras o registros."
            ],
            "alerta_fatal": "En delitos de querella el plazo de PRESCRIPCIÓN suele ser corto, y cualquier prueba obtenida violando el DEBIDO PROCESO será anulada."
        }
    elif categoria_caso == "Casos Laborales":
        return {
            "proceso": "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez laboral (Centro de Conciliación y Tribunal Laboral)",
            "abogado": "Abogado especializado en Derecho Laboral / Procurador de la Defensa del Trabajo",
            "profesionales": "Mediador (Conciliador) + Perito contable/informático",
            "medida_sugerida": "Embargo preventivo (precautorio sobre cuentas/bienes de la patronal)",
            "recurso_clave": "Amparo directo / Revisión / Nulidad de actuaciones",
            "pasos_inmediatos": [
                "1. JAMÁS firmar hojas en blanco ni 'renuncias voluntarias' bajo presión si se trata de un Despido Injustificado.",
                "2. Resguardar recibos de nómina, transferencias, mensajes de WhatsApp, correos y bitácoras de entrada/salida con sello forense.",
                "3. Solicitar cita obligatoria ante el Centro de Conciliación Laboral antes de presentar la Demanda.",
                "4. ¡CUIDADO CON LA PRESCRIPCIÓN! En materia laboral los plazos para demandar despido suelen vencer en 60 días (2 meses)."
            ],
            "alerta_fatal": "Dejar pasar el plazo de prescripción o aceptar un finiquito simulado sin desglose de indemnización constitucional."
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
                "1. Reunir actas de nacimiento, acta de matrimonio y comprobantes de todos los gastos de los menores (educación, salud, alimentación).",
                "2. Solicitar como medida cautelar urgente la fijación de Pensión Alimenticia Provisional (descuento vía nómina) desde el primer auto judicial.",
                "3. Si existe Violencia de Género o doméstica, pedir orden de restricción y salida inmediata del agresor del domicilio.",
                "4. Documentar ingresos reales del deudor alimentario (propiedades, vehículos, actividad comercial)."
            ],
            "alerta_fatal": "Acordar pensiones de palabra sin convenio judicial aprobado (Cosa Juzgada) o sustraer menores sin orden de Guarda y Custodia."
        }
    elif categoria_caso == "Casos Mercantiles":
        return {
            "proceso": "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez mercantil",
            "abogado": "Abogado litigante mercantil / Corporativo",
            "profesionales": "Notario Público (Fe de hechos) + Perito grafoscópico/contable + Árbitro",
            "medida_sugerida": "Embargo preventivo (Juicio Ejecutivo Mercantil) / Retención de bienes",
            "recurso_clave": "Apelación / Amparo / Nulidad de pagaré o contrato",
            "pasos_inmediatos": [
                "1. Verificar si cuentas con un título que traiga aparejada ejecución (pagaré, cheque, factura firmada o contrato comercial).",
                "2. Solicitar desde el escrito inicial de Demanda el Embargo Preventivo de cuentas bancarias o bienes del deudor.",
                "3. Si existe incumplimiento digital o competencia desleal, levantar Fe de Hechos con Notario o sello pericial SHA-256 de correos y ERP.",
                "4. Revisar cláusulas de arbitraje o jurisdicción antes de presentar la demanda."
            ],
            "alerta_fatal": "Alterar fechas o montos en un pagaré (provoca absolución por falsificación) o dejar caducar la acción cambiaria directa."
        }
    else: # Casos Civiles
        return {
            "proceso": "Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)",
            "juez": "Juez civil / Juez de paz",
            "abogado": "Abogado litigante civil",
            "profesionales": "Notario Público + Perito valuador/ingeniero + Mediador",
            "medida_sugerida": "Orden de no enajenar (Anotación preventiva en Registro Público) / Embargo preventivo",
            "recurso_clave": "Apelación / Casación / Amparo",
            "pasos_inmediatos": [
                "1. Asegurar el contrato escrito (arrendamiento, compraventa, mutuo), escrituras o recibos de pago.",
                "2. Si el conflicto es por Propiedad o Deudas, pedir al Juez Civil una Orden de No Enajenar para que la contraparte no venda ni oculte el inmueble.",
                "3. Acreditar la Legitimidad Activa (que tú eres el titular del derecho) y notificar formalmente mediante interpelación judicial o notarial.",
                "4. Cuantificar con precisión el Daño y Perjuicio con facturas, dictámenes periciales y avalúos."
            ],
            "alerta_fatal": "Desalojar a un inquilino por la fuerza sin Sentencia Civil y orden de lanzamiento (te convierte en acusado de despojo)."
        }

# ==============================================================================
# 3. CAPA DE PERSISTENCIA SQLITE Y CASOS SEMILLA MULTIDISCIPLINARIOS
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
            causa_raiz_fallo TEXT,
            estrategia_ganadora TEXT,
            que_hacer_ciudadano TEXT,
            fecha_registro TEXT
        )
    """)
    
    c.execute("SELECT COUNT(*) FROM casos_juridicos_cbr")
    if c.fetchone()[0] == 0:
        semillas = [
            (
                "EXP-PEN-2026-001", "Derecho Público", "Derecho Penal", "Casos Penales", "Fraude",
                "Estafa Digital, Suplantación Bancaria y Alteración de Bitácoras",
                "Juez de garantías, Fiscal/Ministerio Público, Abogado acusador, Perito Forense",
                "2. Investigación/Instrucción", "Retención de bienes / Congelamiento de cuentas",
                "Sentencia condenatoria", "Amparo (para forzar aseguramiento de cuentas)",
                "Transferencia SPEI no autorizada, phishing, acceso IP 192.168.1.50, borrado de logs auth.log, fraude electrónico",
                hashlib.sha256(b"EXP-PEN-2026-001").hexdigest(), "GANADO",
                "N/A - Evidencia admitida con cadena de custodia intacta.",
                "Se sellaron los estados de cuenta, cabeceras de correo y bitácoras de acceso con hash SHA-256 en el minuto cero y se promovió control judicial ante Juez de Garantías para congelar la cuenta receptora.",
                "Presentar querella inmediata ante Fiscalía, aportar dictamen pericial informático de las trazas y exigir oficio de inmovilización de fondos.",
                "2026-08-10"
            ),
            (
                "EXP-LAB-2026-002", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Despido injustificado",
                "Despido Injustificado con Coacción de Firma y Salarios Adeudados",
                "Juez laboral, Abogado especializado, Mediador, Perito en documentoscopía",
                "3. Prueba", "Embargo preventivo",
                "Sentencia condenatoria (Laudo a favor del trabajador)", "Amparo directo",
                "Despido sin aviso de rescisión, bloqueo de acceso biométrico, adeudo de horas extras y aguinaldo, coacción para firmar hoja en blanco",
                hashlib.sha256(b"EXP-LAB-2026-002").hexdigest(), "GANADO",
                "N/A - Condena al pago de indemnización constitucional y salarios caídos.",
                "El trabajador se negó a firmar la renuncia, conservó capturas de WhatsApp donde el jefe le notificaba la baja y el Perito demostró alteración del registro de asistencia SQLite de la empresa.",
                "No firmar renuncia, acudir antes de 60 días al Centro de Conciliación y respaldar mensajes de trabajo y recibos CFDI.",
                "2026-08-22"
            ),
            (
                "EXP-LAB-2026-003", "Derecho Privado", "Derecho Laboral", "Casos Laborales", "Salarios adeudados",
                "Reclamo de Despido y Prestaciones Perdido por Prescripción",
                "Juez laboral, Abogado litigante",
                "2. Contestación", "Ninguna",
                "Sentencia absolutoria (a favor de la empresa)", "Apelación / Amparo (Desestimado)",
                "Trabajador despedido verbalmente que esperó 4 meses creyendo en promesas de pago antes de acudir al tribunal laboral",
                hashlib.sha256(b"EXP-LAB-2026-003").hexdigest(), "PERDIDO",
                "PRESCRIPCIÓN CONSUMADA: El ciudadano dejó pasar el término legal de 2 meses (60 días) para demandar el despido injustificado por confiar en acuerdos verbales.",
                "N/A - Caso sobreseído por excepción de prescripción opuesta por el demandado.",
                "JAMÁS esperar promesas verbales del patrón; el reloj de prescripción corre desde el día siguiente a la separación.",
                "2026-09-02"
            ),
            (
                "EXP-FAM-2026-004", "Derecho Privado", "Derecho de Familia", "Casos Familiares", "Pensión alimenticia",
                "Fijación de Pensión Alimenticia, Guarda y Custodia y Ocultamiento de Ingresos",
                "Juez de lo Familiar, Abogado especializado, Perito en trabajo social",
                "1. Demanda", "Retención de bienes / Descuento directo por nómina",
                "Sentencia civil (Pensión definitiva del 35%)", "Queja (por suspensión de pensión provisional)",
                "Deudor alimentario renunció simuladamente para no pagar pensión a dos menores, ocultando ingresos en cuentas mercantiles secundarias",
                hashlib.sha256(b"EXP-FAM-2026-004").hexdigest(), "GANADO",
                "N/A - Sentencia favorable para los menores.",
                "Se solicitó al Juez requerir informes a la Comisión Bancaria y al SAT (Derecho Tributario), acreditando el flujo real de dinero del demandado.",
                "Pedir pensión provisional desde el día 1 de la demanda y solicitar oficios de investigación patrimonial al SAT y bancos.",
                "2026-09-15"
            ),
            (
                "EXP-PEN-2026-005", "Derecho Público", "Derecho Procesal Penal", "Casos Penales", "Abuso de autoridad",
                "Detención Arbitraria e Intrusión Ilegal a Teléfono Móvil sin Orden Judicial",
                "Juez de garantías, Abogado defensor, Fiscal/Ministerio Público, Perito",
                "3. Auto de procesamiento", "Medidas de protección",
                "Sentencia absolutoria (Nulidad de prueba ilícita)", "Habeas corpus / Amparo / Nulidad",
                "Policías revisaron teléfono y base de datos privada del ciudadano sin orden de cateo ni control judicial, rompiendo cadena de custodia y debido proceso",
                hashlib.sha256(b"EXP-PEN-2026-005").hexdigest(), "GANADO",
                "N/A - Se declaró la nulidad absoluta de las pruebas por violación al Debido Proceso (Due Process).",
                "El Abogado Defensor y el Perito demostraron que los archivos del teléfono fueron abiertos y modificados después de la hora de detención sin hash SHA-256 ni orden de Juez de Garantías.",
                "Exigir respeto al Debido Proceso: ninguna autoridad puede revisar tu teléfono o domicilio sin orden judicial escrita.",
                "2026-09-28"
            ),
            (
                "EXP-CIV-2026-006", "Derecho Privado", "Derecho Civil", "Casos Civiles", "Arrendamiento",
                "Incumplimiento de Contrato de Arrendamiento y Desalojo por Propia Mano",
                "Juez civil, Abogado litigante, Notario",
                "4. Alegatos", "Orden de no enajenar / Embargo preventivo",
                "Sentencia condenatoria (En contra del propietario por cambiar chapas)", "Apelación",
                "Inquilino debía 4 meses de renta; el dueño rompió cerraduras y sacó los muebles a la calle sin juicio previo ni orden de juez civil",
                hashlib.sha256(b"EXP-CIV-2026-006").hexdigest(), "PERDIDO",
                "Justicia por propia mano y violación de domicilio/despojo: El propietario pasó de ser Demandante civil a Acusado penal por no esperar la Sentencia y etapa de Ejecución.",
                "N/A - Se perdió la ventaja procesal por actuar fuera de la vía judicial.",
                "Aunque te deban renta o invadan un contrato, NUNCA cambies cerraduras por tu cuenta; promueve juicio de desahucio y embargo de bienes.",
                "2026-10-05"
            ),
            (
                "EXP-MER-2026-007", "Derecho Privado", "Derecho Mercantil", "Casos Mercantiles", "Incumplimiento de contratos",
                "Cobro de Pagarés y Facturas Comerciales con Embargo Precautorio",
                "Juez mercantil, Abogado litigante, Perito contable",
                "1. Demanda", "Embargo preventivo",
                "Sentencia condenatoria (Remate de bienes embargados)", "Apelación",
                "Proveedor entregó mercancía industrial, cliente incumplió contrato comercial y pretendió vaciar bodegas para declararse en insolvencia",
                hashlib.sha256(b"EXP-MER-2026-007").hexdigest(), "GANADO",
                "N/A - Recuperación del 100% de la suerte principal más intereses moratorios.",
                "Se promovió Juicio Ejecutivo Mercantil ejecutando el embargo preventivo en el mismo acto de notificación antes de que el deudor ocultara activos.",
                "Documentar entregas con pagarés o facturas firmadas de recibido y solicitar embargo precautorio desde el primer auto.",
                "2026-10-18"
            )
        ]
        c.executemany("""
            INSERT INTO casos_juridicos_cbr (
                codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,
                titulo, actores_intervinientes, etapa_clave, medida_cautelar,
                resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,
                resultado, causa_raiz_fallo, estrategia_ganadora, que_hacer_ciudadano, fecha_registro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, semillas)
        conn.commit()
    conn.close()

init_db()

# ==============================================================================
# 4. MOTOR MATEMÁTICO CBR Y ESCÁNER HEURÍSTICO JURÍDICO-FORENSE
# ==============================================================================
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
        (r'despido|renuncia|hoja en blanco|finiquito|salarios|aguinaldo', "🟠 ALERTA LABORAL: Posible coacción patronal o riesgo de prescripción (60 días para demandar).", 25),
        (r'violencia|amenaza|golpe|agresi|peligro|arma|acoso', "🔴 URGENCIA PENAL/FAMILIAR: Solicitar Medidas de Protección inmediatas ante Fiscalía o Juez.", 35),
        (r'detenci|polic|abuso de autoridad|cateo|sin orden', "🔴 ALERTA CONSTITUCIONAL: Posible violación al Debido Proceso; evaluar Amparo / Habeas Corpus y Nulidad de prueba.", 35),
        (r'sed\s+-i|rm\s+-rf|shred|borrado|altera|falsifica|hash|log|ip\s+\d+', "🔴 ALERTA FORENSE DIGITAL: Indicios de manipulación de evidencia o fraude informático; sellar con SHA-256.", 30),
        (r'deuda|pagar[eé]|contrato|renta|arrendamiento|incumplimiento|factura', "🟡 RIESGO PATRIMONIAL: Solicitar Embargo Preventivo u Orden de No Enajenar antes de que oculten bienes.", 20),
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
# 5. GENERADOR DE FICHA CIUDADANA Y PERICIAL EN FORMATO ESTRICTO 9:16 (1080x1920)
# ==============================================================================
def limpiar_ascii(texto: str) -> str:
    reemplazos = str.maketrans("áéíóúñÁÉÍÓÚÑ", "aeiounAEIOUN")
    return texto.translate(reemplazos).encode('ascii', 'ignore').decode('ascii')

def generar_ficha_vertical_9_16(codigo: str, rama: str, caso: str, etapa: str, plan: dict, prob_exito: float, riesgo: int, hash_ev: str) -> np.ndarray:
    # Formato vertical estricto 9:16 (1080 de ancho x 1920 de alto)
    alto, ancho = 1920, 1080
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[:] = (24, 15, 10)
    
    # Marcos
    cv2.rectangle(img, (25, 25), (1055, 1895), (240, 175, 50), 4)
    cv2.rectangle(img, (40, 40), (1040, 1880), (70, 50, 30), 2)
    
    # Cabecera
    cv2.rectangle(img, (40, 40), (1040, 220), (45, 28, 16), -1)
    cv2.putText(img, "FORENSICMIND & LEXGUIA v3.0", (70, 110), cv2.FONT_HERSHEY_DUPLEX, 1.7, (100, 220, 255), 3)
    cv2.putText(img, "HOJA DE RUTA JURIDICA Y SELLO PERICIAL (9:16)", (70, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (210, 210, 210), 2)
    
    # Clasificación del Caso
    cv2.putText(img, limpiar_ascii(f"EXPEDIENTE: {codigo}"), (70, 285), cv2.FONT_HERSHEY_DUPLEX, 1.1, (255, 255, 255), 2)
    cv2.putText(img, limpiar_ascii(f"RAMA: {rama}"), (70, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (140, 240, 180), 2)
    cv2.putText(img, limpiar_ascii(f"TIPO DE CASO: {caso}"), (70, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (140, 240, 180), 2)
    cv2.putText(img, limpiar_ascii(f"ETAPA ACTUAL: {etapa[:45]}"), (70, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 210, 110), 2)
    
    # Cajas de Métricas
    cv2.rectangle(img, (70, 480), (515, 680), (35, 35, 68), -1)
    cv2.rectangle(img, (70, 480), (515, 680), (90, 90, 255), 3)
    cv2.putText(img, "URGENCIA / RIESGO", (110, 535), cv2.FONT_HERSHEY_DUPLEX, 0.9, (210, 210, 255), 2)
    cv2.putText(img, f"{riesgo}/100", (165, 635), cv2.FONT_HERSHEY_DUPLEX, 2.0, (90, 90, 255), 4)
    
    cv2.rectangle(img, (565, 480), (1010, 680), (30, 60, 35), -1)
    cv2.rectangle(img, (565, 480), (1010, 680), (110, 240, 130), 3)
    cv2.putText(img, "VIABILIDAD CBR", (625, 535), cv2.FONT_HERSHEY_DUPLEX, 0.9, (200, 255, 200), 2)
    cv2.putText(img, f"{prob_exito}%", (660, 635), cv2.FONT_HERSHEY_DUPLEX, 2.0, (110, 240, 130), 4)
    
    # Actores y Escudos
    cv2.putText(img, "ACTORES Y MEDIDAS DE PROTECCION:", (70, 755), cv2.FONT_HERSHEY_DUPLEX, 1.0, (100, 220, 255), 2)
    cv2.putText(img, limpiar_ascii(f"Juez: {plan['juez'][:48]}"), (70, 805), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 230), 2)
    cv2.putText(img, limpiar_ascii(f"Defensa: {plan['abogado'][:46]}"), (70, 850), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 230, 230), 2)
    cv2.putText(img, limpiar_ascii(f"Medida: {plan['medida_sugerida'][:46]}"), (70, 895), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 220, 120), 2)
    cv2.putText(img, limpiar_ascii(f"Recurso: {plan['recurso_clave'][:46]}"), (70, 940), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 220, 120), 2)
    
    # Plan de Acción Ciudadano
    cv2.putText(img, "QUE HACER PASO A PASO (GUIA CIUDADANA):", (70, 1025), cv2.FONT_HERSHEY_DUPLEX, 1.0, (140, 255, 160), 2)
    y_cursor = 1085
    for paso in plan["pasos_inmediatos"]:
        limpio = limpiar_ascii(paso)
        fragmentos = [limpio[i:i+54] for i in range(0, len(limpio), 54)]
        for frag in fragmentos[:2]:
            cv2.putText(img, frag, (70, y_cursor), cv2.FONT_HERSHEY_SIMPLEX, 0.76, (220, 220, 220), 2)
            y_cursor += 42
        y_cursor += 18
        
    # Sello SHA-256
    cv2.putText(img, "SELLO CRIPTOGRAFICO SHA-256 DE EVIDENCIA:", (70, 1600), cv2.FONT_HERSHEY_DUPLEX, 0.85, (100, 220, 255), 2)
    cv2.putText(img, hash_ev[:36], (70, 1645), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 255, 160), 2)
    cv2.putText(img, hash_ev[36:], (70, 1685), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 255, 160), 2)
    
    # Pie de Ficha 9:16
    cv2.rectangle(img, (70, 1735), (1010, 1850), (42, 30, 20), -1)
    cv2.putText(img, "FORMATO VERTICAL ESTRICTO 9:16 (1080x1920 PX)", (145, 1785), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 218), 2)
    cv2.putText(img, "JUSTICIA PREVENTIVA - ASESORIA JURIDICA Y FORENSE", (135, 1828), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (190, 190, 190), 1)
    
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# ==============================================================================
# 6. INTERFAZ PRINCIPAL DE LA SUITE REESTRUCTURADA
# ==============================================================================
st.title("⚖️ ForensicMind & LexGuía CBR v3.0 — Justicia Preventiva y Asesoría Ciudadana")
st.caption("Orientación Jurídica Paso a Paso • Razonamiento Basado en Casos (Ganados vs. Perdidos) • Peritaje Forense SHA-256")

tab1, tab2, tab3, tab4 = st.tabs([
    "🛡️ 1. Asesor Ciudadano ('Qué Hacer') & Diagnóstico CBR",
    "🗺️ 2. Etapas del Juicio, Actores y Diccionario Legal",
    "📚 3. Bóveda de Jurisprudencia (Ganados vs. Perdidos)",
    "➕ 4. Registrar Nuevo Caso / Post-Mortem"
])

# ------------------------------------------------------------------------------
# PESTAÑA 1: ASESOR CIUDADANO Y MOTOR CBR
# ------------------------------------------------------------------------------
with tab1:
    st.subheader("🧭 Diagnóstico del Problema y Plan de Acción Inmediato")
    c_sel1, c_sel2, c_sel3, c_sel4 = st.columns(4)
    
    with c_sel1:
        macro_sel = st.selectbox("1. Ámbito del Derecho", list(RAMAS_DERECHO.keys()))
        rama_sel = st.selectbox("2. Rama Específica", RAMAS_DERECHO[macro_sel])
    with c_sel2:
        cat_caso_sel = st.selectbox("3. Familia de Caso", list(TIPOS_CASOS.keys()))
        tipo_caso_sel = st.selectbox("4. Problema Específico", TIPOS_CASOS[cat_caso_sel])
    with c_sel3:
        rol_sel = st.selectbox(
            "5. ¿Cuál es tu posición hoy?",
            ["Demandante / Acusador (Víctima o afectado)", "Demandado / Acusado (Me están reclamando o imputando)"]
        )
        plan_activo = obtener_plan_accion_ciudadano(cat_caso_sel, tipo_caso_sel, rol_sel)
        etapa_sel = st.selectbox("6. Etapa Judicial Actual", ETAPAS_PROCESO[plan_activo["proceso"]])
    with c_sel4:
        codigo_exp = st.text_input("Código de Consulta", value="ASESORIA-2026-01")
        medida_sel = st.selectbox("7. Medida Cautelar Requerida", MEDIDAS_CAUTELARES)

    relato_usuario = st.text_area(
        "📝 Describe qué ocurrió y pega aquí cualquier evidencia (mensajes, cláusulas de contrato, bitácoras o hechos):",
        height=140,
        value="Me despidieron injustificadamente hoy, me exigen firmar una hoja en blanco para darme mi finiquito, me deben salarios y bloquearon mi usuario en la base de datos de asistencia."
    )

    # Cruce Matemático CBR contra SQLite
    conn = sqlite3.connect(DB_NAME)
    df_hist = pd.read_sql_query("SELECT * FROM casos_juridicos_cbr", conn)
    conn.close()

    consulta_full = f"{rama_sel} {cat_caso_sel} {tipo_caso_sel} {relato_usuario}"
    similitudes = []
    for _, row in df_hist.iterrows():
        doc_hist = f"{row['rama_derecho']} {row['categoria_caso']} {row['tipo_caso']} {row['titulo']} {row['evidencia_logs']} {row['que_hacer_ciudadano']}"
        score_sim = calcular_similitud_coseno(consulta_full, doc_hist)
        similitudes.append({**row.to_dict(), "similitud": score_sim})

    df_sim = pd.DataFrame(similitudes).sort_values(by="similitud", ascending=False)
    relevantes = df_sim[df_sim["similitud"] > 8.0]
    if not relevantes.empty:
        ganados_peso = relevantes[relevantes["resultado"] == "GANADO"]["similitud"].sum()
        total_peso = relevantes["similitud"].sum()
        prob_exito = round((ganados_peso / total_peso) * 100, 1) if total_peso > 0 else 55.0
    else:
        prob_exito = 55.0

    auditoria = auditar_riesgo_juridico_forense(relato_usuario)
    top_precedente = df_sim.iloc[0]

    # Métricas Superiores
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Urgencia / Riesgo Legal", f"{auditoria['riesgo_score']}/100", "Atención Inmediata" if auditoria['riesgo_score'] >= 65 else "Ordinario")
    m2.metric("Viabilidad de Éxito (CBR)", f"{prob_exito}%", f"Cruce con {len(relevantes)} casos")
    m3.metric("Precedente Más Cercano", f"{top_precedente['similitud']}%", top_precedente["codigo_caso"])
    m4.metric("Juez Competente", plan_activo["juez"].split("/")[0], rama_sel)

    # Bloque Central: Qué Hacer Paso a Paso + Actores y Recursos
    col_guia, col_actores = st.columns([1.25, 1])

    with col_guia:
        st.markdown("### 🚨 ¿Qué debes hacer ahora mismo? (Protocolo Ciudadano Paso a Paso)")
        for paso in plan_activo["pasos_inmediatos"]:
            st.markdown(f"- **{paso}**")
        
        st.markdown(f"""
        <div class="alert-box">
            <b>⚠️ PELIGRO LEGAL MORTAL A EVITAR (Prescripción / Caducidad / Debido Proceso):</b><br>
            {plan_activo['alerta_fatal']}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 🔍 Alertas Detectadas por el Escáner Forense en tu Relato:")
        for h in auditoria["hallazgos"]:
            st.write(h)
        st.caption(f"🔒 **Sello Criptográfico SHA-256 de tu Evidencia:** `{auditoria['hash_evidencia']}`")

    with col_actores:
        st.markdown("### 🏛️ Mapa de Actores, Medidas y Recursos para tu Caso")
        st.markdown(f"""
        <div class="card-box">
            <span class="step-badge">ETAPA ACTUAL: {etapa_sel}</span><br><br>
            <b>👨‍⚖️ Juez o Autoridad que resuelve:</b> {plan_activo['juez']}<br>
            <b>💼 Abogado que necesitas:</b> {plan_activo['abogado']}<br>
            <b>🔬 Otros Profesionales Clave:</b> {plan_activo['profesionales']}<br>
            <b>🛡️ Medida Cautelar para protegerte hoy:</b> {plan_activo['medida_sugerida']}<br>
            <b>📜 Recursos Legales disponibles:</b> {plan_activo['recurso_clave']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🧠 Comparativa de Jurisprudencia CBR: Cómo se Ganan y por qué se Pierden Casos como el Tuyo")
    col_w, col_l = st.columns(2)

    with col_w:
        st.markdown("#### 🏆 Casos Similares GANADOS (Tácticas que funcionaron)")
        for _, g in df_sim[df_sim["resultado"] == "GANADO"].head(2).iterrows():
            st.markdown(f"""
            <div class="card-box">
                <span class="win-badge">GANADO • {g['similitud']}% SIMILITUD</span> <b>{g['codigo_caso']} ({g['tipo_caso']})</b><br>
                <b>{g['titulo']}</b><br><br>
                <b>🎯 Estrategia Ganadora:</b> {g['estrategia_ganadora']}<br>
                <b>🏛️ Resolución / Recurso:</b> {g['resolucion_obtenida']} | {g['recurso_utilizado']}<br>
                <b>💡 Consejo Ciudadano:</b> {g['que_hacer_ciudadano']}
            </div>
            """, unsafe_allow_html=True)

    with col_l:
        st.markdown("#### ❌ Casos Similares PERDIDOS (Errores que debes evitar)")
        for _, p in df_sim[df_sim["resultado"] == "PERDIDO"].head(2).iterrows():
            st.markdown(f"""
            <div class="alert-box">
                <span class="loss-badge">PERDIDO • {p['similitud']}% SIMILITUD</span> <b>{p['codigo_caso']} ({p['tipo_caso']})</b><br>
                <b>{p['titulo']}</b><br><br>
                <b>💥 Causa Raíz de la Derrota:</b> {p['causa_raiz_fallo']}<br>
                <b>🏛️ Resolución Emitida:</b> {p['resolucion_obtenida']}<br>
                <b>🛡️ Cómo Blindarte Hoy:</b> {p['que_hacer_ciudadano']}
            </div>
            """, unsafe_allow_html=True)

    with st.expander("📱 Generar Ficha Ciudadana y Pericial en Formato Vertical Estricto 9:16 (1080x1920 px)", expanded=False):
        img_9_16 = generar_ficha_vertical_9_16(
            codigo_exp, rama_sel, tipo_caso_sel, etapa_sel,
            plan_activo, prob_exito, auditoria["riesgo_score"], auditoria["hash_evidencia"]
        )
        c_i1, c_i2, c_i3 = st.columns([1, 1.2, 1])
        with c_i2:
            st.image(img_9_16, caption="Ficha Legal-Forense 9:16 (1080x1920 px)", use_container_width=True)

# ------------------------------------------------------------------------------
# PESTAÑA 2: SIMULADOR DE ETAPAS Y DICCIONARIO CIUDADANO
# ------------------------------------------------------------------------------
with tab2:
    st.subheader("🗺️ Mapa de Etapas Judiciales y Traductor de Conceptos Legales Clave")
    col_et1, col_et2 = st.columns(2)
    
    with col_et1:
        st.markdown("#### 🚔 Las 8 Etapas del Proceso Penal")
        for e in ETAPAS_PROCESO["Proceso Penal (8 Etapas)"]:
            st.markdown(f"**{e}**")
        st.markdown("#### 📑 Las 7 Etapas del Proceso Civil / Laboral / Familiar / Mercantil")
        for e in ETAPAS_PROCESO["Proceso Civil / Laboral / Familiar / Mercantil (7 Etapas)"]:
            st.markdown(f"**{e}**")

    with col_et2:
        st.markdown("#### 📖 Diccionario Ciudadano de Conceptos Legales Clave")
        concepto_elegido = st.selectbox("Selecciona un concepto para entender cómo afecta tu caso:", list(CONCEPTOS_CLAVE.keys()))
        st.info(f"**{concepto_elegido}:** {CONCEPTOS_CLAVE[concepto_elegido]}")
        
        st.markdown("#### ⚖️ Tipos de Resoluciones y Recursos Legales")
        st.write("**Resoluciones y Sentencias:** " + ", ".join(RESOLUCIONES_SENTENCIAS))
        st.write("**Recursos para Impugnar:** " + ", ".join(RECURSOS_LEGALES))
        st.write("**Medidas Cautelares:** " + ", ".join(MEDIDAS_CAUTELARES))

# ------------------------------------------------------------------------------
# PESTAÑA 3: BÓVEDA DE JURISPRUDENCIA CBR
# ------------------------------------------------------------------------------
with tab3:
    st.subheader("📚 Bóveda Histórica Multidisciplinaria (Casos Ganados vs. Perdidos)")
    f_col1, f_col2 = st.columns(2)
    filtro_veredicto = f_col1.selectbox("Filtrar por Resultado:", ["TODOS", "GANADO", "PERDIDO"])
    filtro_cat = f_col2.selectbox("Filtrar por Familia de Caso:", ["TODAS"] + list(TIPOS_CASOS.keys()))
    
    df_view = df_hist.copy()
    if filtro_veredicto != "TODOS":
        df_view = df_view[df_view["resultado"] == filtro_veredicto]
    if filtro_cat != "TODAS":
        df_view = df_view[df_view["categoria_caso"] == filtro_cat]
        
    st.dataframe(
        df_view[[
            "codigo_caso", "rama_derecho", "tipo_caso", "titulo",
            "resultado", "resolucion_obtenida", "recurso_utilizado",
            "causa_raiz_fallo", "estrategia_ganadora", "que_hacer_ciudadano"
        ]],
        use_container_width=True,
        hide_index=True
    )

# ------------------------------------------------------------------------------
# PESTAÑA 4: ALIMENTAR NUEVO PRECEDENTE
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("➕ Registrar Nuevo Precedente Jurídico-Forense en la Base de Conocimiento")
    with st.form("form_nuevo_precedente"):
        f1, f2, f3 = st.columns(3)
        n_cod = f1.text_input("Código (ej. EXP-CIV-2026-008)")
        n_macro = f2.selectbox("Ámbito", list(RAMAS_DERECHO.keys()))
        n_rama = f3.selectbox("Rama del Derecho", sum(RAMAS_DERECHO.values(), []))
        
        f4, f5, f6 = st.columns(3)
        n_cat = f4.selectbox("Categoría de Caso", list(TIPOS_CASOS.keys()))
        n_tipo = f5.selectbox("Tipo de Caso", sum(TIPOS_CASOS.values(), []))
        n_res_final = f6.selectbox("Resultado Final", ["GANADO", "PERDIDO"])
        
        n_tit = st.text_input("Título Descriptivo del Caso")
        
        f7, f8, f9 = st.columns(3)
        n_etapa = f7.selectbox("Etapa Determinante", sum(ETAPAS_PROCESO.values(), []))
        n_medida = f8.selectbox("Medida Cautelar Aplicada", ["Ninguna"] + MEDIDAS_CAUTELARES)
        n_recurso = f9.selectbox("Recurso Legal Utilizado", ["Ninguno"] + RECURSOS_LEGALES)
        
        f10, f11 = st.columns(2)
        n_resolucion = f10.selectbox("Tipo de Resolución Emitida", RESOLUCIONES_SENTENCIAS)
        n_actores = f11.text_input("Actores que intervinieron (ej. Juez laboral, Perito, Abogado defensor)")
        
        n_evidencia = st.text_area("Evidencia, Hechos y Trazas Forenses del Caso")
        n_causa_fallo = st.text_input("Si se PERDIÓ: ¿Cuál fue el error o causa raíz? (Prescripción, Caducidad, Prueba ilícita, etc.)")
        n_estrategia = st.text_area("Estrategia Jurídica y Pericial que dio la victoria (o que faltó aplicar)")
        n_consejo = st.text_area("Guía Ciudadana: ¿Qué debe hacer una persona ante un caso idéntico?")
        
        btn_save = st.form_submit_button("💾 Guardar Precedente en Bóveda SQLite")
        if btn_save and n_cod and n_tit:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            try:
                h_sha = hashlib.sha256(n_evidencia.encode('utf-8')).hexdigest()
                c.execute("""
                    INSERT INTO casos_juridicos_cbr (
                        codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso,
                        titulo, actores_intervinientes, etapa_clave, medida_cautelar,
                        resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256,
                        resultado, causa_raiz_fallo, estrategia_ganadora, que_hacer_ciudadano, fecha_registro
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    n_cod, n_macro, n_rama, n_cat, n_tipo, n_tit, n_actores,
                    n_etapa, n_medida, n_resolucion, n_recurso, n_evidencia,
                    h_sha, n_res_final, n_causa_fallo, n_estrategia, n_consejo,
                    datetime.now().strftime("%Y-%m-%d")
                ))
                conn.commit()
                st.success(f"✅ Precedente {n_cod} guardado. El motor CBR ya lo utiliza para asesorar nuevos casos.")
            except sqlite3.IntegrityError:
                st.error("⚠️ Ese código de expediente ya existe.")
            finally:
                conn.close()

He integrado ForensicMind & LexGuía CBR v3.0 | Justicia Preventiva dentro de app.py (disponible tanto en el menú lateral como en la Pestaña 11 de LegalTech) y he iniciado la validación de compilación y prueba de ejecución. Enseguida te confirmo el resultado final.

¡Listo! Se ha integrado y validado sin errores ForensicMind & LexGuía CBR v3.0 — Justicia Preventiva y Asesoría Ciudadana dentro de app.py, manteniendo intactos todos los módulos anteriores:

✅ Resumen de lo Incorporado en app.py
Taxonomía Jurídica Integral y Guía Ciudadana:
Catálogos RAMAS_DERECHO, TIPOS_CASOS, ACTORES_JUDICIALES, ETAPAS_PROCESO, MEDIDAS_CAUTELARES, RESOLUCIONES_SENTENCIAS, RECURSOS_LEGALES y CONCEPTOS_CLAVE.
Función obtener_plan_accion_ciudadano para generar la hoja de ruta paso a paso en casos Penales, Laborales, Familiares, Mercantiles y Civiles.
Bóveda SQLite Multidisciplinaria (boveda_juridica_cbr_v3.db):
init_db_lexguia: Tabla casos_juridicos_cbr con los 7 precedentes semilla (EXP-PEN-2026-001 a EXP-MER-2026-007).
auditar_riesgo_juridico_forense: Escáner heurístico de urgencia/riesgo legal y sello criptográfico SHA-256.
generar_ficha_vertical_9_16: Generador de Ficha Ciudadana y Pericial en formato vertical estricto 9:16 (1080×1920 px) con botón de descarga directa en .png.
Doble Acceso en la Interfaz (render_modulo_lexguia_cbr_v3):
En el Menú Lateral Izquierdo como "⚖️ ForensicMind & LexGuía CBR v3.0 | Justicia Preventiva".
Dentro del módulo LegalTech como la Pestaña 11 ("⚖️ LexGuía CBR v3.0 (Justicia Preventiva & 9:16)").
🌐 Servidor Activo y Validado (LEXGUIA_CBR_V3_OK: 18)
URL Local: http://localhost:8501
URL de Red: http://192.168.1.70:8501
PIN de Acceso (Barra Lateral): 2026
Por favor, actualiza el archivo app.py para que contenga ÚNICAMENTE la suite "ForensicMind & LexGuía v3.0 | Justicia Preventiva". 

Elimina por completo el menú lateral de selección (st.sidebar.radio) y cualquier código rezagado de los módulos anteriores:
- Sistema Experto Legaltech
- ForensicMind CBR v2.0 (Inteligencia Pericial)
- Suite ERP Contable e Industrial
- Planta Purificadora de Agua

La aplicación debe arrancar de forma directa y exclusiva con la interfaz de Justicia Preventiva v3.0, manteniendo sus 4 pestañas operativas (1. Asesor Ciudadano y Motor CBR, 2. Mapa de Etapas y Diccionario Legal, 3. Bóveda de Jurisprudencia, 4. Registro de Nuevos Casos) y utilizando la base de datos SQLite "boveda_juridica_cbr_v3.db". Asegúrate de que el código esté limpio, integrado en un solo archivo y listo para ejecutarse sin opciones múltiples obsoletas.

¡Listo! El archivo app.py ha sido actualizado para contener únicamente la suite "ForensicMind & LexGuía CBR v3.0 | Justicia Preventiva" en un solo archivo limpio y sin ningún módulo ni menú lateral obsoleto:

✅ Cambios Aplicados y Verificados
Eliminación total de módulos rezagados y menú lateral (st.sidebar.radio):
Se removió todo el código antiguo de Sistema Experto LegalTech, ForensicMind CBR v2.0, Suite ERP Contable e Industrial y Planta Purificadora de Agua.
Inicio Directo y Exclusivo en ForensicMind & LexGuía CBR v3.0 (app.py):
Pestaña 1: 🛡️ 1. Asesor Ciudadano ('Qué Hacer') & Diagnóstico CBR (incluye generador de Ficha Vertical 9:16 de 1080×1920 px con generar_ficha_vertical_9_16).
Pestaña 2: 🗺️ 2. Etapas del Juicio, Actores y Diccionario Legal.
Pestaña 3: 📚 3. Bóveda de Jurisprudencia (Ganados vs. Perdidos).
Pestaña 4: ➕ 4. Registrar Nuevo Caso / Post-Mortem.
Conectado exclusivamente a la base de datos SQLite boveda_juridica_cbr_v3.db (init_db).
Validación:
Compilación (py_compile) y ejecución de prueba (AppTest) verificadas con código 0 (LEXGUIA_STANDALONE_OK: 4).
Servidor activo en http://localhost:8501.
Por favor, actualiza app.py en la suite "ForensicMind & LexGuía CBR" para implementar la versión definitiva con Red Neuronal, Autoclasificación en 1 Clic y Bóveda Detallada de Casos (Qué hizo el Abogado y Cómo reaccionó el Juez):

1. BASE DE DATOS SQLITE AMPLIADA CON ANATOMÍA DEL JUICIO (boveda_juridica_cbr_v4.db):
   - Crea la tabla con campos detallados incluyendo: codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso, titulo, actores_intervinientes, etapa_clave, medida_cautelar, resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256, resultado (GANADO/PERDIDO), accion_abogado (qué hizo exactamente el abogado paso a paso), reaccion_juez (cómo reaccionó el juez, qué valoró y cómo resolvió), causa_raiz_fallo, estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano y fecha_registro.
   - Precarga al menos 12 casos semilla emparejados (GANADOS y PERDIDOS de los mismos temas: Despido injustificado ganado vs. perdido por prescripción/hoja en blanco; Pensión alimenticia ganada vs. perdida; Fraude/Estafa digital ganado vs. perdido por alterar pruebas; Detención/Abuso policial ganado por nulidad vs. perdido; Arrendamiento/Deuda civil ganado vs. perdido por desalojo propio; Cobro mercantil de pagaré ganado vs. perdido por alteración).

2. RED NEURONAL MULTICAPA (MLP) + AUTOCLASIFICACIÓN EN 1 CLIC (Pestaña 1):
   - Coloca al inicio de la Pestaña 1 un cuadro de texto amplio donde el usuario solo escriba libremente qué le pasó (ej. "Me corrieron del trabajo", "Me demandaron por pensión alimenticia", "Me hicieron un fraude bancario").
   - Añade el botón principal: "🧠 Analizar Mi Caso con Red Neuronal y Comparar Precedentes".
   - Entrena en memoria una Red Neuronal Multicapa (MLP con scikit-learn o NumPy con capas densas, ReLU y Softmax) junto con el motor vectorial CBR para que, sin mover selectores, detecte automáticamente: Rama del Derecho, Categoría, Tipo de Caso, Rol (Demandante/Víctima vs. Demandado/Acusado), Etapa Judicial, Medida Cautelar y Nivel de Confianza Neuronal (%). Deja los selectores manuales dentro de un st.expander("⚙️ Ajustes Manuales (Opcional)").

3. COMPARATIVA DIRECTA GANADOS VS. PERDIDOS ("QUÉ HACER VS. QUÉ NO HACER"):
   - En la Pestaña 1, al analizar el caso, muestra un cuadro comparativo directo enfrentando los casos similares GANADOS contra los PERDIDOS de la base de datos:
     * Columna Verde (Cómo se GANA este caso): Qué hizo el abogado ganador, cómo reaccionó favorablemente el juez y QUÉ DEBES HACER HOY.
     * Columna Roja (Por qué se PIERDE este caso): Qué error cometió el abogado o ciudadano perdedor, por qué el juez rechazó su postura y QUÉ NO DEBES HACER JAMÁS.
   - Mantén el generador de Ficha Vertical estricta 9:16 (1080x1920 px) con sello SHA-256 y botón de descarga PNG (st.download_button).

4. APARTADO DE INSPECCIÓN PROFUNDA DE CASOS (Pestaña 3: "Bóveda y Radiografía Completa de Casos"):
   - Permite filtrar y buscar entre todos los casos de la bóveda (por palabra clave, rama, tipo de caso o resultado GANADO/PERDIDO).
   - Añade un "🔬 Inspector Detallado de Expediente": al seleccionar cualquier caso de la lista, despliega tarjetas completas con toda la información:
     * 📋 Hechos y Evidencia Forense (con su Hash SHA-256).
     * 💼 ¿Qué hizo el Abogado? (Estrategia, pruebas aportadas, medidas cautelares o errores procesales).
     * 👨‍⚖️ ¿Cómo reaccionó el Juez? (Criterio judicial, valoración de pruebas, respeto al debido proceso y sentencia dictada).
     * ⚖️ Veredicto Final, Qué Hacer y Qué NO Hacer en un caso igual.

Se ha actualizado app.py con la versión definitiva de ForensicMind & LexGuía CBR v4.0 (Red Neuronal, Autoclasificación en 1 Clic y Anatomía Completa de Casos):

Cambios Implementados

Base de Datos SQLite Ampliada (boveda_juridica_cbr_v4.db):

init_db() crea la tabla casos_juridicos_cbr con los 21 campos forenses y procesales (codigo_caso, macro_rama, rama_derecho, categoria_caso, tipo_caso, titulo, actores_intervinientes, etapa_clave, medida_cautelar, resolucion_obtenida, recurso_utilizado, evidencia_logs, hash_sha256, resultado, accion_abogado, reaccion_juez, causa_raiz_fallo, estrategia_ganadora, que_hacer_ciudadano, que_no_hacer_ciudadano y fecha_registro).
Precarga 12 expedientes semilla emparejados (6 GANADOS vs. 6 PERDIDOS) sobre los mismos escenarios jurídicos:
Laboral: Despido injustificado (EXP-LAB-2026-001 ganado vs. EXP-LAB-2026-002 perdido por hoja en blanco y prescripción).
Familiar: Pensión alimenticia y custodia (EXP-FAM-2026-003 ganado vs. EXP-FAM-2026-004 perdido por insolvencia provocada y sustracción).
Penal Ciberdelitos: Fraude / Phishing bancario (EXP-PEN-2026-005 ganado vs. EXP-PEN-2026-006 perdido por capturas alteradas sin cadena de custodia).
Penal Constitucional: Detención ilegal / Abuso policial (EXP-PEN-2026-007 ganado por nulidad de puesta a disposición vs. EXP-PEN-2026-008 perdido por convalidación en audiencia).
Civil Arrendamiento: Desocupación y rentas vencidas (EXP-CIV-2026-009 ganado vs. EXP-CIV-2026-010 perdido por desalojo por propia mano).
Mercantil Ejecutivo: Cobro de pagaré (EXP-MER-2026-011 ganado con embargo precautorio vs. EXP-MER-2026-012 perdido por alteración del texto).

Red Neuronal Multicapa (MLPClassifier) + Autoclasificación en 1 Clic (Pestaña 1):

entrenar_red_neuronal_autoclasificacion() y autoclasificar_caso_con_red_neuronal() entrenan en memoria un clasificador neuronal MLPClassifier(hidden_layer_sizes=(64, 32), activation="relu") junto con vectorización TfidfVectorizer(ngram_range=(1, 2)) para detectar automáticamente:
Macro-rama, Rama del Derecho, Categoría, Subtipo de caso, Rol procesal (Demandante/Víctima vs. Demandado/Acusado), Etapa judicial, Medida cautelar sugerida y Nivel de Confianza Neuronal (%).
Los selectores manuales quedaron encapsulados dentro de st.expander("⚙️ Ajustes Manuales (Opcional)", expanded=False) para quien desee refinar manualmente los parámetros.

Comparador Directo GANADOS vs. PERDIDOS y Ficha Vertical 9:16 (Pestaña 1):

Muestra frente a frente los precedentes más similares divididos en columna verde (Cómo se GANA este caso) y columna roja (Por qué se PIERDE este caso), detallando en cada uno: ¿Qué hizo el Abogado?, ¿Cómo reaccionó el Juez?, Resolución / Causa raíz y Qué Hacer vs. Qué NO Hacer.
generar_ficha_vertical_9_16() genera la infografía ejecutiva en formato 9:16 (1080×1920 px) con sello criptográfico SHA-256 y botón de descarga directa en PNG.

Bóveda y Radiografía Completa de Casos (Pestaña 3):

Filtros combinados por palabra clave, resultado (TODOS / GANADO / PERDIDO), categoría y rama del derecho.
Inspector Detallado de Expediente con 4 tarjetas dedicadas para cualquier caso seleccionado:
📋 1. Hechos y Evidencia Forense (con su Hash SHA-256)
💼 2. ¿Qué hizo exactamente el Abogado?
👨‍⚖️ 3. ¿Cómo reaccionó el Juez y qué valoró?
⚖️ 4. Veredicto Final, Qué Hacer y Qué NO Hacer

El servidor Streamlit se encuentra activo en http://localhost:8501.

Por favor, realiza estos ajustes finales para subir la app a Streamlit Community Cloud:
1. Agrega en la Pestaña 1 de app.py la entrada de dictado por voz con st.audio_input (procesada con SpeechRecognition en español) y el botón st.download_button para descargar el dictamen completo en formato Word (.docx) usando python-docx en memoria (io.BytesIO).
2. Crea en la misma carpeta de app.py el archivo "requirements.txt" con estas líneas exactas (usando opencv-python-headless para servidores Linux en la nube):
streamlit
pandas
numpy
opencv-python-headless
scikit-learn
python-docx
SpeechRecognition

Instalando SpeechRecognition en el entorno local y ejecutando la validación de compilación y prueba automatizada (AppTest) de app.py; te confirmo en cuanto termine.

Se han aplicado y validado los ajustes finales para desplegar la aplicación en Streamlit Community Cloud:

Dictado por Voz (st.audio_input) y Descarga de Dictamen en Word (.docx) en la Pestaña 1 de app.py:

Dictado por Voz en Español: Se incorporó st.audio_input("🎙️ Dictar mi caso por voz (Español)") junto con la función transcribir_audio_espanol(), que procesa el audio en memoria (io.BytesIO) mediante speech_recognition (language="es-MX") y vuelca automáticamente el texto transcrito en el cuadro de relato para su análisis neuronal.
Exportación a Word (.docx) en Memoria: Se implementó generar_dictamen_word_docx() utilizando python-docx y io.BytesIO, conectada al botón st.download_button("📄 Descargar Dictamen Jurídico-Forense Completo en Word (.docx)") en la Pestaña 1. Incluye la ficha de autoclasificación neuronal (MLP), el sello criptográfico SHA-256, las alertas forenses, el protocolo ciudadano paso a paso, el mapa de actores judiciales y la comparativa de precedentes ganados vs. perdidos.

Archivo requirements.txt optimizado para servidores Linux en la nube:

text
streamlit
pandas
numpy
opencv-python-headless
scikit-learn
python-docx
SpeechRecognition
        st.markdown(
            f"""
            <div class="{'card-box' if caso_det['resultado'] == 'GANADO' else 'alert-box'}">
                <h4 style="margin-top:0; color:{'#34d399' if caso_det['resultado'] == 'GANADO' else '#f87171'};">
                    ⚖️ 4. Veredicto Final, Qué Hacer y Qué NO Hacer
                </h4>
                <p><b>🎯 Estrategia / Causa Raíz:</b> {caso_det['estrategia_ganadora'] if caso_det['resultado'] == 'GANADO' else caso_det['causa_raiz_fallo']}</p>
                <p style="color:#6ee7b7;"><b>✅ QUÉ HACER en un caso igual:</b> {caso_det['que_hacer_ciudadano']}</p>
                <p style="color:#fca5a5; margin-bottom:0;"><b>🚫 QUÉ NO HACER JAMÁS:</b> {caso_det['que_no_hacer_ciudadano']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
# ------------------------------------------------------------------------------
# PESTAÑA 4: ALIMENTAR NUEVO PRECEDENTE CON ANATOMÍA DEL JUICIO
# ------------------------------------------------------------------------------
with tab4:
    st.subheader("➕ Registrar Nuevo Precedente Jurídico-Forense en `boveda_juridica_cbr_v4.db`")
    with st.form("form_nuevo_precedente_v4"):
        f1, f2, f3 = st.columns(3)
        n_cod = f1.text_input("Código (ej. EXP-LAB-2026-013)")
        n_macro = f2.selectbox("Ámbito", list(RAMAS_DERECHO.keys()))
        n_rama = f3.selectbox("Rama del Derecho", sum(RAMAS_DERECHO.values(), []))
        f4, f5, f6 = st.columns(3)
        n_cat = f4.selectbox("Categoría de Caso", list(TIPOS_CASOS.keys()))
        n_tipo = f5.selectbox("Tipo de Caso", sum(TIPOS_CASOS.values(), []))
        n_res_final = f6.selectbox("Resultado Final", ["GANADO", "PERDIDO"])
        n_tit = st.text_input("Título Descriptivo del Caso")
        f7, f8, f9 = st.columns(3)
        n_etapa = f7.selectbox("Etapa Determinante", sum(ETAPAS_PROCESO.values(), []))
        n_medida = f8.selectbox("Medida Cautelar Aplicada", ["Ninguna"] + MEDIDAS_CAUTELARES)
        n_recurso = f9.selectbox("Recurso Legal Utilizado", ["Ninguno"] + RECURSOS_LEGALES)
        f10, f11 = st.columns(2)
        n_resolucion = f10.selectbox("Tipo de Resolución Emitida", RESOLUCIONES_SENTENCIAS)
        n_actores = f11.text_input("Actores que intervinieron (ej. Juez laboral, Perito, Abogado defensor)")
        n_evidencia = st.text_area("📋 Hechos y Evidencia Forense del Caso")
        col_ab_juez1, col_ab_juez2 = st.columns(2)
        with col_ab_juez1:
            n_accion_abogado = st.text_area("💼 ¿Qué hizo exactamente el Abogado paso a paso?")
        with col_ab_juez2:
            n_reaccion_juez = st.text_area("👨⚖️ ¿Cómo reaccionó el Juez, qué valoró y cómo resolvió?")
        n_causa_fallo = st.text_input("Si se PERDIÓ: ¿Cuál fue el error o causa raíz? (Si se ganó, pon N/A)")
        n_estrategia = st.text_area("Estrategia Jurídica y Pericial que dio la victoria (o que faltó aplicar)")
        col_qh1, col_qh2 = st.columns(2)
        with col_qh1:
            n_que_hacer = st.text_area("✅ Guía Ciudadana: ¿QUÉ DEBE HACER una persona ante un caso idéntico?")
        with col_qh2:
            n_que_no_hacer = st.text_area("🚫 Alerta Ciudadana: ¿QUÉ NO DEBE HACER JAMÁS una persona en este caso?")

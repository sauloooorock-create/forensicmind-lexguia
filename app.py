"""ForensicMind & LexGuía CBR v11 — interfaz Streamlit.

Toda la lógica vive en el paquete ``forensicmind``; este archivo solo dibuja la interfaz.
"""
from __future__ import annotations

import hashlib
import inspect
import io
import json
import logging
import urllib.parse
from datetime import date, datetime

import pandas as pd
import streamlit as st

from forensicmind import (
    base_legal, config, db, docs, extraction, extraction_llm, guias, honorarios, lft, ml, security, sync, triage, web,
)
from forensicmind.security import esc, fmt_inline
from forensicmind import control_admin

log = logging.getLogger("forensicmind")

st.set_page_config(
    page_title=f"{config.MARCA_SISTEMA} | {config.AUTOR_SISTEMA}",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

AJUSTES = config.cargar_ajustes()

def _compat(func):
    """Traduce use_container_width a width='stretch' si la versión de Streamlit ya no lo acepta."""
    if "use_container_width" in inspect.signature(func).parameters:
        return func

    def inner(*args, use_container_width=None, **kwargs):
        if use_container_width:
            kwargs["width"] = "stretch"
        return func(*args, **kwargs)

    return inner


ui_button = _compat(st.button)
ui_download = _compat(st.download_button)
ui_dataframe = _compat(st.dataframe)
ui_image = _compat(st.image)
ui_submit = _compat(st.form_submit_button)



# ==============================================================================
# Utilidades de render
# ==============================================================================
def mk(texto) -> str:
    """Escapa '$' para que st.markdown no lo trate como fórmula LaTeX."""
    return str(texto).replace("$", "\\$")


def dinero(x: float) -> str:
    return f"${x:,.2f}"


def caja(clase: str, html_interno: str) -> None:
    st.markdown(f"<div class='{clase}'>{html_interno}</div>", unsafe_allow_html=True)


# ==============================================================================
# Arranque (una vez por proceso) y cachés
# ==============================================================================
@st.cache_resource(show_spinner=False)
def arranque() -> dict:
    db.init_db()
    try:
        return sync.restaurar(AJUSTES)
    except Exception:  # el respaldo nunca debe impedir que la app abra
        log.exception("Fallo al restaurar respaldo")
        return {}


@st.cache_resource(show_spinner=False)
def modelo_cacheado(version: tuple):
    return ml.entrenar_desde_db()


@st.cache_data(ttl=3600, show_spinner=False)
def web_cacheado(categoria: str, tipo: str) -> list:
    return web.buscar_informacion(categoria, tipo)


def version_datos() -> tuple:
    with db.conexion() as conn:
        casos = conn.execute("SELECT COUNT(*) FROM casos_juridicos_cbr").fetchone()[0]
        aprobadas = conn.execute("SELECT COUNT(*) FROM memoria_aprendizaje WHERE estado='aprobado'").fetchone()[0]
    return (casos, aprobadas)


arranque()
MODELO = modelo_cacheado(version_datos())

st.session_state.setdefault("es_admin", False)
st.session_state.setdefault("relato", "")
st.session_state.setdefault("buzon_envios", 0)

if not st.session_state.get("visita_registrada"):
    st.session_state["visita_registrada"] = True
    try:
        db.registrar_visita()
    except Exception:
        log.exception("No se pudo registrar la visita")

try:
    sync.sincronizar_pendiente(AJUSTES)
except Exception:
    log.exception("Sincronización pendiente falló")

def _bloque_admin() -> None:
    """Acceso del administrador: contraseña o aviso de configuración."""
    st.markdown("### 🔐 Administrador")
    habilitado, motivo_admin = security.estado_admin(AJUSTES.admin_password)
    if not st.session_state["es_admin"]:
        if not habilitado:
            st.info(motivo_admin)
        else:
            clave = st.text_input("Contraseña:", type="password", key="clave_admin")
            if ui_button("🔓 Desbloquear panel", use_container_width=True):
                acceso, mensaje_login = False, ""
                with db.conexion() as conn:
                    espera = security.segundos_bloqueo(conn)
                    if espera > 0:
                        mensaje_login = f"Demasiados intentos fallidos. Intenta de nuevo en {espera // 60 + 1} min."
                    elif security.verificar_password(clave, AJUSTES.admin_password):
                        security.limpiar_intentos(conn)
                        acceso = True
                    else:
                        security.registrar_fallo(conn)
                        mensaje_login = "Contraseña incorrecta."
                if acceso:  # st.rerun() fuera del bloque de la base de datos para no perder el commit
                    st.session_state["es_admin"] = True
                    st.rerun()
                else:
                    st.error(mensaje_login)
            if motivo_admin:
                st.caption(motivo_admin)
    else:
        st.success("✅ Modo administrador activo")
        if ui_button("🔒 Cerrar sesión", use_container_width=True):
            st.session_state["es_admin"] = False
            st.rerun()


# ==============================================================================
# Barra lateral
# ==============================================================================
with st.sidebar:
    st.markdown("### 🎨 Apariencia")
    modo_visual = st.radio("Modo de lectura:", ["☀️ Claro (fácil lectura en celular)", "🌙 Oscuro"], index=0)
    buscar_web = st.checkbox("🌐 Consultar noticias y criterios en internet", value=True)
    usar_llm = False
    if AJUSTES.anthropic_key:
        usar_llm = st.checkbox(
            "🤖 Leer mejor mi caso con IA (envía tu texto anonimizado a Anthropic)", value=False,
            help="Opcional. Se quitan nombres, teléfonos, cuentas y datos de identificación antes de enviar.",
        )

    st.markdown("---")
    st.markdown("---")
    if st.session_state.get("ver_admin"):
        st.caption("🔐 El panel de administrador está en la pantalla principal.")
    else:
        _bloque_admin()

ES_ADMIN = bool(st.session_state["es_admin"])

# ==============================================================================
# Estilos
# ==============================================================================
_PALETAS = {
    "claro": {
        "bg": "#f1f5f9", "txt": "#0f172a", "input_bg": "#ffffff", "input_txt": "#0f172a", "input_borde": "#2563eb",
        "triage_bg": "#fff1f2", "triage_bd": "#f43f5e", "triage_ac": "#be123c",
        "card_bg": "#ffffff", "card_bd": "#cbd5e1", "card_ac": "#2563eb",
        "money_bg": "#ecfdf5", "money_bd": "#6ee7b7", "money_ac": "#059669",
        "law_bg": "#eef2ff", "law_bd": "#a5b4fc", "law_ac": "#4f46e5",
        "alert_bg": "#fef2f2", "alert_bd": "#fca5a5", "alert_ac": "#dc2626",
        "script_bg": "#fffbeb", "script_bd": "#fcd34d", "script_ac": "#d97706",
        "web_bg": "#f0f9ff", "web_bd": "#7dd3fc", "web_ac": "#0284c7",
        "aviso_bg": "#fef9c3", "aviso_bd": "#facc15",
        "hero_ini": "#6d28d9", "hero_mid": "#db2777", "hero_fin": "#f59e0b", "tab_ac": "#7c3aed",
        "paso_bg": "#ffffff", "paso_bd": "#c4b5fd", "paso_on": "#7c3aed",
    },
    "oscuro": {
        "bg": "#0b0f19", "txt": "#f8fafc", "input_bg": "#ffffff", "input_txt": "#0f172a", "input_borde": "#38bdf8",
        "triage_bg": "#2a1215", "triage_bd": "#f43f5e", "triage_ac": "#e11d48",
        "card_bg": "#131c2e", "card_bd": "#2dd4bf", "card_ac": "#2dd4bf",
        "money_bg": "#0f2922", "money_bd": "#10b981", "money_ac": "#34d399",
        "law_bg": "#1e1b4b", "law_bd": "#818cf8", "law_ac": "#a78bfa",
        "alert_bg": "#1f1215", "alert_bd": "#f87171", "alert_ac": "#ef4444",
        "script_bg": "#272011", "script_bd": "#f59e0b", "script_ac": "#fbbf24",
        "web_bg": "#0c192c", "web_bd": "#38bdf8", "web_ac": "#0284c7",
        "aviso_bg": "#3a3210", "aviso_bd": "#facc15",
        "hero_ini": "#4c1d95", "hero_mid": "#9d174d", "hero_fin": "#b45309", "tab_ac": "#c4b5fd",
        "paso_bg": "#131c2e", "paso_bd": "#6d28d9", "paso_on": "#c4b5fd",
    },
}
_CSS = """
<style>
.stApp { background-color: %(bg)s !important; color: %(txt)s !important; }
.block-container { padding-top: 3.2rem !important; padding-bottom: 2.5rem !important; }
h1, h2, h3, h4, h5, h6, p, li, label, span, div { color: %(txt)s; }
textarea, input[type='text'], input[type='number'], input[type='password'], .stDateInput input {
  background-color: %(input_bg)s !important; color: %(input_txt)s !important;
  -webkit-text-fill-color: %(input_txt)s !important; border: 2px solid %(input_borde)s !important;
  border-radius: 10px !important; font-weight: 600 !important;
}
.author-banner { background: linear-gradient(135deg, #0f172a 0%%, #1e3a8a 100%%); border-left: 6px solid #f59e0b;
  border-radius: 14px; padding: 16px 20px; margin-bottom: 12px; }
.author-banner, .author-banner * { color: #ffffff !important; }
.aviso-box { background: %(aviso_bg)s; border: 1px solid %(aviso_bd)s; border-radius: 10px; padding: 10px 14px; margin-bottom: 14px; font-size: 0.92rem; }
.badge { padding: 4px 11px; border-radius: 6px; font-weight: 800; display: inline-block; color: #ffffff !important; margin-right: 6px; }
.win-badge { background: #059669; } .loss-badge { background: #dc2626; } .step-badge { background: #1d4ed8; }
.ilus-badge { background: #64748b; } .gold-badge { background: #f59e0b; color: #0f172a !important; }
.triage-box, .card-box, .money-box, .lawyer-box, .alert-box, .script-box, .web-box { border-radius: 12px; padding: 16px 18px; margin: 10px 0; border: 1px solid; border-left-width: 6px; }
.triage-box { background: %(triage_bg)s; border-color: %(triage_bd)s; border-left-color: %(triage_ac)s; border-width: 2px; border-left-width: 8px; }
.card-box { background: %(card_bg)s; border-color: %(card_bd)s; border-left-color: %(card_ac)s; }
.money-box { background: %(money_bg)s; border-color: %(money_bd)s; border-left-color: %(money_ac)s; }
.lawyer-box { background: %(law_bg)s; border-color: %(law_bd)s; border-left-color: %(law_ac)s; }
.alert-box { background: %(alert_bg)s; border-color: %(alert_bd)s; border-left-color: %(alert_ac)s; }
.script-box { background: %(script_bg)s; border-color: %(script_bd)s; border-left-color: %(script_ac)s; }
.web-box { background: %(web_bg)s; border-color: %(web_bd)s; border-left-color: %(web_ac)s; }
div[data-testid='stMetric'] { background: %(card_bg)s !important; border: 1px solid %(card_bd)s !important;
  border-left: 5px solid %(card_ac)s !important; padding: 12px !important; border-radius: 12px !important; }
div.stButton > button:first-child, div.stDownloadButton > button:first-child {
  background: linear-gradient(90deg, #2563eb 0%%, #1d4ed8 100%%) !important; color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important; font-weight: 800 !important; border-radius: 10px !important; padding: 10px 18px !important; }
.wa-link { background-color: #059669; color: #ffffff !important; padding: 12px 24px; border-radius: 10px; font-weight: 800; text-decoration: none; display: inline-block; }
.ob-hero { background: linear-gradient(120deg, %(hero_ini)s 0%%, %(hero_mid)s 55%%, %(hero_fin)s 100%%);
  border-radius: 18px; padding: 20px 22px; margin-bottom: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.18); }
.ob-hero, .ob-hero * { color: #ffffff !important; }
.ob-hero h2 { margin: 0 0 4px 0; font-size: 1.5rem; font-weight: 900; }
.ob-pasos { display: flex; flex-wrap: wrap; gap: 10px; margin: 4px 0 14px 0; }
.ob-paso { flex: 1 1 200px; background: %(paso_bg)s; border: 2px solid %(paso_bd)s; border-radius: 14px;
  padding: 10px 14px; font-weight: 700; }
.ob-paso b { color: %(paso_on)s !important; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; flex-wrap: wrap; }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; font-weight: 700; padding: 10px 14px; }
.stTabs [aria-selected="true"] { color: %(tab_ac)s !important; }
.stTabs [data-baseweb="tab-highlight"] { background: linear-gradient(90deg, %(hero_ini)s, %(hero_mid)s) !important; height: 4px !important; }
.stButton > button, .stDownloadButton > button { min-height: 48px; font-weight: 800 !important; border-radius: 12px !important;
  transition: transform .15s ease, box-shadow .15s ease; }
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,0,0,.15); }
.stButton > button[kind="primary"] { background: linear-gradient(90deg, %(hero_ini)s, %(hero_mid)s) !important; border: none !important; }
.stButton > button[kind="primary"], .stButton > button[kind="primary"] * { color: #ffffff !important; }
@media (max-width: 640px) {
  .ob-hero h2 { font-size: 1.2rem; }
  .block-container { padding-left: 16px !important; padding-right: 16px !important; }
  .stTabs [data-baseweb="tab"] { padding: 8px 10px; font-size: 0.9rem; }
}
</style>
"""
st.markdown(_CSS % _PALETAS["claro" if "Claro" in modo_visual else "oscuro"], unsafe_allow_html=True)

# ==============================================================================
# Encabezado
# ==============================================================================
st.markdown(
    "<div class='author-banner'><div style='display:flex; flex-wrap:wrap; justify-content:space-between; gap:10px;'>"
    "<div><span style='color:#fbbf24 !important; font-weight:800; font-size:13px;'>🏛️ TRIAGE LEGAL MULTI-MATERIA • DESPACHO • AUTO-SYNC</span><br>"
    f"<span style='font-size:21px; font-weight:900;'>{esc(config.MARCA_SISTEMA)}</span></div>"
    f"<div><span class='badge gold-badge'>⚙️ {esc(config.AUTOR_SISTEMA)}</span></div></div></div>",
    unsafe_allow_html=True,
)
caja("ob-hero", "<h2>🧭 Entiende tus derechos en 3 pasos</h2>"
    "<div>Cuéntanos qué te pasó, revisa qué te corresponde y decide tu siguiente paso. Es orientación preliminar, no sustituye a un abogado.</div>")
caja("ob-pasos", "<div class='ob-paso'><b>Paso 1</b> · Cuéntanos tu caso</div>"
    "<div class='ob-paso'><b>Paso 2</b> · Calcula tu liquidación</div>"
    "<div class='ob-paso'><b>Paso 3</b> · Decide tu siguiente paso</div>")
_c = config.leyes()["contactos"]
caja(
    "aviso-box",
    f"⚠️ {esc(config.AVISO_LEGAL)}<br>🚨 <b>Emergencia: {esc(_c['emergencias'])}</b> · Denuncia anónima: <b>{esc(_c['denuncia_anonima'])}</b>",
)
with st.expander("🔒 Aviso de privacidad"):
    st.markdown(mk(config.AVISO_PRIVACIDAD))

if not ES_ADMIN:
    if st.session_state.get("ver_admin"):
        with st.container(border=True):
            _bloque_admin()
            if ui_button("⬅️ Ocultar panel de administrador", key="ocultar_admin"):
                st.session_state["ver_admin"] = False
                st.rerun()
    elif ui_button("🔐 Ir al panel de administrador", key="ir_admin"):
        st.session_state["ver_admin"] = True
        st.rerun()

problemas_leyes = config.validar_leyes()
if problemas_leyes and ES_ADMIN:
    for p in problemas_leyes:
        st.warning("⚙️ Reglas legales: " + mk(p))

if ES_ADMIN:
    t_guia, t_calc, t_casos, t_fuentes, t_sistema, t_revision, t_ensenar, t_cotiz, t_trafico, t_control = st.tabs([
        "🗣️ 1. Cuéntame tu caso", "💰 2. ¿Cuánto me toca?", "🏆 3. Casos parecidos", "📚 4. Leyes y fuentes",
        "☁️ 5. [ADMIN] Sistema y respaldo", "✅ 6. [ADMIN] Revisión y buzón", "➕ 7. [ADMIN] Enseñar caso",
        "🛠️ 8. [ADMIN] Cotizador", "👥 9. [ADMIN] Tráfico y calidad", "🛡️ 10. [ADMIN] Control total",
    ])
else:
    t_guia, t_calc, t_casos, t_fuentes = st.tabs([
        "🗣️ 1. Cuéntame tu caso", "💰 2. ¿Cuánto me toca?",
        "🏆 3. Casos parecidos", "📚 4. Leyes y fuentes",
    ])


# ==============================================================================
# Calculadora laboral reutilizable (pestañas 1 y 2)
# ==============================================================================
def render_calculadora(prefijo: str, d: dict, firma: str = "") -> tuple:
    """Dibuja los datos laborales y el resultado. Devuelve (resultado|None, datos_lft|None, oferta, plazo|None)."""
    k = lambda n: f"{prefijo}_{n}_{firma}"  # noqa: E731
    per_ini = d.get("periodicidad") or "Semanal"
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 👷 1. Tu sueldo y tu trabajo")
        periodicidad = st.selectbox("¿Cada cuándo te pagan?", list(lft.PERIODOS_DIAS), index=list(lft.PERIODOS_DIAS).index(per_ini), key=k("per"))
        monto = st.number_input("¿Cuánto ganas en ese periodo? ($ MXN)", min_value=0.0, max_value=1_000_000.0,
                                value=float(d.get("salario_monto") or 0.0), step=100.0, key=k("monto"))
        anios = st.number_input("Años cumplidos trabajando ahí", min_value=0, max_value=60, value=int(d.get("anios") or 0), step=1, key=k("anios"))
        meses = st.number_input("Meses adicionales", min_value=0, max_value=11, value=int(d.get("meses") or 0), step=1, key=k("meses"))
        conoce_fecha = st.checkbox("Conozco la fecha del despido o de mi salida", value=d.get("fecha_separacion") is not None, key=k("cf"))
        fecha = None
        if conoce_fecha:
            fecha = st.date_input("Fecha del despido o separación", value=d.get("fecha_separacion") or date.today(),
                                  max_value=date.today(), key=k("fecha"))
    with c2:
        st.markdown("##### 📋 2. Qué te deben y qué te ofrecen")
        motivo = st.selectbox("¿Por qué saliste del trabajo?", list(lft.MOTIVOS), format_func=lambda x: lft.MOTIVOS[x], key=k("motivo"))
        oferta = st.number_input("¿Cuánto dinero te quiere dar el patrón hoy? ($ MXN)", min_value=0.0, max_value=10_000_000.0,
                                 value=float(d.get("oferta_patronal") or 0.0), step=500.0, key=k("oferta"))
        pend = st.number_input("Días ya trabajados que no te han pagado", min_value=0, max_value=720,
                               value=int(d.get("dias_sueldo_pendientes") or 0), step=1, key=k("pend"))
        vac_sug = lft.vacaciones_no_gozadas_sugeridas(int(anios)) if d.get("sin_vacaciones") else 0
        vac = st.number_input("Días de vacaciones ya ganadas que nunca gozaste ni te pagaron", min_value=0, max_value=600,
                              value=int(vac_sug), step=1, key=k("vac"),
                              help="Si cumpliste años completos y nunca tuviste vacaciones, suma los días de cada año (12, 14, 16...).")
        desc = st.number_input("Días de descanso que trabajaste sin pago doble", min_value=0, max_value=600, value=0, step=1, key=k("desc"))
        frontera = st.checkbox("Trabajo en la zona libre de la frontera norte", value=False, key=k("front"))

    if monto <= 0:
        st.info("✍️ Escribe tu sueldo para calcular cuánto te corresponde.")
        return None, None, oferta, None
    try:
        sd = lft.salario_diario(monto, periodicidad)
        datos = lft.DatosLaborales(
            salario_diario=sd, anios=int(anios), meses=int(meses), motivo=motivo, fecha_separacion=fecha,
            dias_sueldo_pendientes=float(pend), dias_vacaciones_vencidas=float(vac), dias_descanso_trabajados=float(desc),
            zona_frontera=bool(frontera),
        )
        res = lft.calcular_liquidacion(datos)
    except ValueError as exc:
        st.error(f"Revisa tus datos: {exc}")
        return None, None, oferta, None

    st.info(f"📌 Tu sueldo diario equivale a **{mk(dinero(sd))}** (≈ {mk(dinero(sd * 30))} al mes). Salario diario integrado: {mk(dinero(res.sdi))}.")
    plazo = lft.plazo_reclamo(fecha) if fecha else None
    if plazo:
        {"vigente": st.success, "urgente": st.error, "vencido": st.error, "futuro": st.warning}[plazo["estado"]](mk(plazo["mensaje"]))

    cmp_ = lft.comparar_oferta(res.total_liquidacion, oferta)
    k1, k2, k3 = st.columns(3)
    k1.metric("Lo que marca la ley (estimado)", dinero(res.total_liquidacion))
    k2.metric("Lo que te ofrece la empresa", dinero(oferta))
    k3.metric("Dinero que te estarían quitando", dinero(cmp_["diferencia"]))
    if cmp_["oferta_menor"]:
        caja("alert-box", f"🚨 <b>La oferta es solo el {cmp_['pct_de_lo_legal']:.0f}% de lo estimado por ley.</b> "
                          "No firmes renuncia ni finiquito sin que lo revise la PROFEDET o el Centro de Conciliación.")

    filas = [{"Concepto": c["concepto"], "Fundamento": c["fundamento"], "Monto (MXN)": dinero(c["monto"]), "Cómo se calculó": c["nota"]} for c in res.conceptos]
    ui_dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)
    if res.es_despido:
        with st.expander("⚖️ ¿Y si el caso llega a juicio? (salarios vencidos)"):
            st.markdown(mk(f"Si ganas el juicio, además puedes reclamar **salarios vencidos** (Art. 48 LFT) por hasta 12 meses: "
                           f"≈ **{dinero(res.salarios_vencidos_max)}**. Total posible: **{dinero(res.total_con_salarios_vencidos)}**. "
                           "Es un máximo teórico: los juicios tardan y no están garantizados."))
    with st.expander("🧾 Notas e impuestos (informativo)"):
        for n in res.notas:
            st.markdown("- " + mk(n))
        st.markdown(mk(
            f"- Pagos por separación estimados: {dinero(res.isr_pago_separacion)}; exento de ISR (90 UMA por año de servicio): "
            f"{dinero(res.isr_tope_exento)}; posible parte gravable: {dinero(res.isr_gravable_estimado)}. El cálculo real lo hace el patrón."
        ))
        st.caption(mk(f"Valores usados: salario mínimo {dinero(config.leyes()['salario_minimo']['general'])}, UMA {dinero(config.leyes()['uma']['diaria'])} "
                      f"(verificados el {config.leyes()['salario_minimo']['verificado']})."))
    return res, datos, oferta, plazo


# ==============================================================================
# Análisis del caso
# ==============================================================================
def transcribir(audio_bytes: bytes) -> str:
    try:
        import speech_recognition as sr
    except ImportError:
        return ""
    try:
        r = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as fuente:
            return r.recognize_google(r.record(fuente), language="es-MX")
    except Exception:
        return ""


def ejecutar_analisis(relato: str, consentimiento: bool) -> dict:
    t = triage.diagnosticar(relato, MODELO)
    datos = extraction.extraer_datos(relato)
    if usar_llm and AJUSTES.anthropic_key:
        extra = extraction_llm.extraer_con_llm(relato, AJUSTES.anthropic_key, AJUSTES.anthropic_model)
        if extra:
            datos = extraction_llm.fusionar(datos, extra)
    web_res = []
    if buscar_web and not t["indeterminado"]:
        web_res = web_cacheado(t["categoria"], t["tipo"])
    guardado = False
    if consentimiento:
        try:
            guardado = db.guardar_memoria_pendiente(relato, t, "Consulta ciudadana")
            if guardado:
                sync.sincronizar(AJUSTES)
        except Exception:
            log.exception("No se pudo guardar la memoria pendiente")
    folio = f"{config.FOLIO_BASE}-{datetime.now():%Y%m%d}-{hashlib.sha256(relato.encode()).hexdigest()[:6].upper()}"
    return {
        "relato": relato, "triage": t, "datos": datos, "web": web_res, "guardado": guardado, "folio": folio,
        "firma": hashlib.sha256(relato.encode()).hexdigest()[:8],
    }


def mostrar_modulo(idx: int, mod: dict, guia: dict, expandido: bool) -> None:
    cat = mod["categoria"]
    tab_h = honorarios.tabulador_rama(cat)
    with st.expander(mod["titulo_prioridad"], expanded=expandido):
        caja("card-box", f"<span class='badge step-badge'>MÓDULO {idx}: {esc(cat.upper())}</span>"
                         f"<span class='badge ilus-badge'>Confianza {esc(mod['nivel'])} ({mod['confianza']:.0f}%)</span><br><br>"
                         f"<b>🔍 Diagnóstico directo:</b><br>{fmt_inline(guia['radiografia'])}")
        st.markdown("##### 💡 Explicación en español sencillo")
        for e in guia["explicacion_sencilla"]:
            st.markdown(mk(e))
        st.markdown("##### 🧭 Guía cronológica paso a paso")
        c1, c2, c3 = st.columns(3)
        for col, titulo, pasos in ((c1, "⏱️ PASO A: Hoy mismo", guia["fase_1_hoy"]), (c2, "📅 PASO B: Esta semana", guia["fase_2_semana"]),
                                   (c3, "🏛️ PASO C: Ante la autoridad", guia["fase_3_autoridad"])):
            with col:
                st.markdown(f"**{titulo}**")
                for p in pasos:
                    st.markdown("- " + mk(p))
        caja("script-box", fmt_inline(guia["guion"]))
        e1, e2 = st.columns([1.2, 1])
        with e1:
            st.markdown("**🚫 Errores que debes evitar:**")
            for er in guia["errores_fatales"]:
                st.markdown("- " + mk(er))
        with e2:
            caja("lawyer-box", f"<b>🏢 Dónde acudir:</b><br>{fmt_inline(guia['autoridad'])}<br><br>"
                               f"<b>⚖️ Especialista:</b><br>{fmt_inline(guia['abogado_req'])}<br><br>"
                               f"<b>💚 Vía gratuita:</b><br>{fmt_inline(tab_h['via_gratuita'])}")
        fund = base_legal.fundamentos_para(cat)
        if fund:
            st.markdown("##### 📚 Fundamento legal de referencia")
            for f in fund:
                enlace = f" — [texto oficial]({f['url']})" if security.url_segura(f.get("url", "")) != "#" else ""
                st.markdown(mk(f"- **{f['ley']}, Art. {f['articulo']} — {f['tema']}:** {f['resumen']}") + enlace)
            st.caption(base_legal.aviso())


def mostrar_analisis(a: dict) -> None:
    t, datos, relato = a["triage"], a["datos"], a["relato"]

    for alerta in t["alertas"]:
        st.error(mk(alerta["mensaje"]))

    if t["indeterminado"]:
        g = guias.obtener_guia("Indeterminado")
        caja("card-box", f"<b>🔍 {fmt_inline(g['radiografia'])}</b>")
        for e in g["explicacion_sencilla"]:
            st.markdown(mk(e))
        st.caption("Agrega detalles en el recuadro de arriba (por ejemplo: qué autoridad, empresa o institución, cuánto dinero y qué fecha) y vuelve a analizar.")
        return

    if t["es_multimateria"]:
        etiquetas = "<br>".join(f"• <b>{esc(m['titulo_prioridad'])}</b>" for m in t["modulos_triage"])
        caja("triage-box", f"<h4 style='margin-top:0;'>🚨 TRIAGE MULTI-DISCIPLINARIO: DETECTÉ {len(t['modulos_triage'])} ÁREAS EN TU CASO</h4>"
                           "Para que no mezcles trámites, las ordené por <b>urgencia</b> (primero tu libertad e integridad, luego "
                           f"tus cuentas e identidad, después tu trabajo y tu patrimonio):<br><br>{etiquetas}")
    st.caption(f"Confianza del análisis: {t['confianza']:.0f}% ({t['nivel_confianza']}) · origen: {t['origen']}.")
    if t["requiere_mas_detalle"]:
        st.info("🔎 Con lo que escribiste la detección es de confianza media/baja. Agrega más detalle (fechas, montos, quién y qué hizo) para una guía más precisa.")
    if a["guardado"]:
        st.caption("✅ Guardé una versión anonimizada de tu caso para revisión del administrador. Gracias por ayudar a mejorar el sistema.")

    # ---- Componente laboral / escudo no laboral ---------------------------------
    resultado, datos_lft, oferta, plazo = None, None, float(datos.get("oferta_patronal") or 0.0), None
    if t["tiene_componente_laboral"]:
        st.markdown("#### 💼 Tu reclamo laboral (Ley Federal del Trabajo)")
        if datos["faltan_datos"]:
            st.caption("No pude leer con seguridad: " + ", ".join(datos["faltan_datos"]) + ". Complétalos abajo para un cálculo exacto.")
        if datos.get("sin_descansos"):
            st.caption("Mencionaste días libres o descansos: indica abajo cuántos días trabajaste sin el pago doble.")
        resultado, datos_lft, oferta, plazo = render_calculadora("t1", datos, a["firma"])
    else:
        _cat_p = t["categoria"]
        extra = ""
        for m in datos.get("montos_otros", []):
            if m["tipo"] == "policial" and "Tránsito y Abuso Policial" in t["categorias_ordenadas"]:
                extra += f"• Los policías te piden <b>&#36;{m['monto']:,.2f}</b>: <b>no pagues</b>; denuncia en Asuntos Internos/Fiscalía.<br>"
            if m["tipo"] == "cobranza" and "Acoso de Cobranza y Deudas" in t["categorias_ordenadas"]:
                extra += f"• Te cobran <b>&#36;{m['monto']:,.2f}</b>: no deposites a cuentas personales; exige carta convenio y verifica el REDECO.<br>"
        caja("money-box", "<h4 style='margin-top:0;'>🛡️ ESCUDO CIUDADANO (CASO NO LABORAL)</h4>"
                          "• Aquí <b>no aplica una liquidación laboral</b>: lo importante es proteger tu libertad, tus cuentas y tu patrimonio.<br>"
                          "• Lo que debes pagar en mordidas o extorsiones: <b>&#36;0.00 MXN</b> (exige boleta oficial o denuncia).<br>"
                          f"{extra}• Vía gratuita: {fmt_inline(honorarios.tabulador_rama(_cat_p)['via_gratuita'])}")

    # ---- Guías por módulo -----------------------------------------------------------
    guias_acum = []
    for idx, mod in enumerate(t["modulos_triage"], 1):
        g = guias.obtener_guia(mod["categoria"], datos, resultado, oferta, plazo)
        guias_acum.append({"categoria": mod["categoria"], "titulo_prioridad": mod["titulo_prioridad"], "guia": g})
        mostrar_modulo(idx, mod, g, expandido=(idx == 1 or not t["es_multimateria"]))

    # ---- Contratación privada ------------------------------------------------------
    cat_p = t["categoria"]
    tab_p = honorarios.tabulador_rama(cat_p)
    st.markdown("---")
    st.markdown("### ⚖️ Asesoría profesional privada (opcional)")
    st.write("Si prefieres que un abogado lleve tu caso, esta es una referencia transparente. Puedes empezar por la vía gratuita.")
    cc1, cc2 = st.columns(2)
    with cc1:
        caja("lawyer-box", f"<b>💼 Esquema de referencia ({esc(cat_p)}):</b><br>"
                           f"• <b>Asesoría inicial:</b> &#36;{tab_p['asesoria_sug']:,.2f} MXN<br>"
                           f"• <b>Anticipo inicial:</b> &#36;{tab_p['anticipo_sug']:,.2f} MXN<br>"
                           f"• <b>Esquema:</b> {esc(tab_p['esquema_cobro'])}<br>"
                           f"• <b>Vía gratuita:</b> {esc(tab_p['via_gratuita'])}<br>"
                           "<small>Valores de referencia, no una tarifa fija: pacta siempre por escrito.</small>")
    with cc2:
        msg = f"Hola, analicé mi caso en ForensicMind (Folio: {a['folio']} | Materia: {cat_p}). Me interesa agendar una asesoría privada."
        wa = AJUSTES.whatsapp_valido
        if wa:
            enlace = f"https://wa.me/{wa}?text={urllib.parse.quote(msg)}"
            caja("money-box", "<b>💬 ¿Atención personalizada?</b><br>Envía solo tu folio y la materia (no tu relato) al WhatsApp del despacho.<br><br>"
                              f"<a class='wa-link' href='{esc(enlace)}' target='_blank' rel='noopener noreferrer'>📱 Contactar por WhatsApp ↗</a>")
        else:
            correo = f"mailto:{AJUSTES.admin_email}?subject={urllib.parse.quote('Asesoría ' + a['folio'])}&body={urllib.parse.quote(msg)}"
            caja("money-box", "<b>📧 ¿Atención personalizada?</b><br>Escribe al despacho indicando tu folio y la materia (no tu relato completo).<br><br>"
                              f"<a class='wa-link' href='{esc(correo)}'>✉️ Escribir al despacho</a>")

    if buscar_web and a["web"]:
        st.markdown("---")
        st.markdown("#### 🌐 Información pública relacionada")
        for rw in a["web"][:5]:
            caja("web-box", f"<b>{esc(rw['fuente'])}</b> — <a href='{esc(security.url_segura(rw['url']))}' target='_blank' rel='noopener noreferrer'>"
                            f"{esc(rw['titulo'])} ↗</a><br><span>{esc(rw['resumen'])}</span>")
        st.caption("Resultados automáticos de fuentes públicas: sirven de contexto, no son asesoría ni criterio oficial.")

    # ---- Descargas ------------------------------------------------------------------
    st.markdown("---")
    hash_ev = hashlib.sha256(relato.encode("utf-8")).hexdigest()
    fund_all = base_legal.fundamentos_para(t["categorias_ordenadas"])
    d1, d2 = st.columns(2)
    with d1:
        try:
            bytes_docx = docs.generar_docx(a["folio"], relato, t, guias_acum, resultado, oferta, fund_all, hash_ev)
        except Exception:
            log.exception("Error generando .docx")
            bytes_docx = b""
        if bytes_docx:
            ui_download("📄 Descargar manual completo (.docx)", bytes_docx, file_name=f"Manual_{a['folio']}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True, key=f"dl_docx_{a['firma']}")
    with d2:
        with st.expander("📱 Ficha resumen 9:16 para celular"):
            try:
                png = docs.generar_ficha_png(a["folio"], t, guias_acum[0]["guia"], resultado, oferta, hash_ev)
            except Exception:
                log.exception("Error generando PNG")
                png = b""
            if png:
                ui_image(png, use_container_width=True)
                ui_download("📥 Descargar imagen (.png)", png, file_name=f"Ficha_{a['folio']}.png", mime="image/png",
                                   use_container_width=True, key=f"dl_png_{a['firma']}")

    # ---- Retroalimentación ------------------------------------------------------------
    st.markdown("---")
    clave_fb = f"fb_{a['firma']}"
    if st.session_state.get(clave_fb):
        st.success("¡Gracias por tu opinión! Nos ayuda a mejorar.")
    else:
        st.markdown("**¿Te sirvió esta guía?**")
        f1, f2, _ = st.columns([1, 1, 3])
        if f1.button("👍 Sí", key=f"fb_si_{a['firma']}"):
            db.registrar_feedback(t["categoria"], True)
            st.session_state[clave_fb] = True
            st.rerun()
        if f2.button("👎 No", key=f"fb_no_{a['firma']}"):
            db.registrar_feedback(t["categoria"], False)
            st.session_state[clave_fb] = True
            st.rerun()


# ==============================================================================
# PESTAÑA 1
# ==============================================================================
def _cargar_escenario() -> None:
    st.session_state["relato"] = config.ESCENARIOS_FRECUENTES[st.session_state["escenario"]]


with t_guia:
    st.markdown("### 🗣️ Paso 1 de 3 · Cuéntame qué te pasó")
    st.caption("Puedes mezclar varios problemas. Entre más detalles des (fechas, qué te dijeron, qué firmaste), mejor será la guía.")
    col_esc, col_voz = st.columns([1.3, 1])
    with col_esc:
        st.selectbox("💡 Elige un ejemplo o escribe tu caso:", list(config.ESCENARIOS_FRECUENTES), key="escenario", on_change=_cargar_escenario)
    with col_voz:
        audio = st.audio_input("🎙️ Dictar mi problema por voz") if hasattr(st, "audio_input") else None
        st.caption("Si dictas, el audio se envía a Google para transcribirse.")
    if audio is not None:
        audio_bytes = audio.getvalue()
        h_audio = hashlib.sha256(audio_bytes).hexdigest()
        if st.session_state.get("ultimo_audio") != h_audio:
            st.session_state["ultimo_audio"] = h_audio
            with st.spinner("Transcribiendo tu voz..."):
                texto_voz = transcribir(audio_bytes)
            if texto_voz:
                st.session_state["relato"] = texto_voz
                st.success("✅ Voz transcrita. Revisa el texto y pulsa «Analizar».")
            else:
                st.warning("No pude transcribir el audio. Escribe tu caso en el recuadro.")

    st.text_area("📝 Escribe con tus palabras qué ocurrió", key="relato", height=150, max_chars=4000,
                 placeholder="Ej.: Me despidieron el 3 de octubre sin pagarme finiquito ni vacaciones...",
                 help="Evita nombres y datos personales; el texto se anonimiza antes de guardarse.")
    consentimiento = st.checkbox(
        "Autorizo guardar una versión anonimizada de mi caso para que el administrador la revise y mejore el sistema (opcional)",
        key="consent_guardar",
    )
    if ui_button("🧠 Analizar mi caso y generar plan de acción", use_container_width=True, key="btn_analizar"):
        texto = st.session_state["relato"].strip()
        if len(texto) < 20:
            st.warning("Cuéntame un poco más (al menos una o dos frases) para poder orientarte.")
        else:
            with st.spinner("Analizando tu caso..."):
                try:
                    st.session_state["analisis"] = ejecutar_analisis(texto, bool(consentimiento))
                except Exception:
                    log.exception("Error en el análisis")
                    st.session_state.pop("analisis", None)
                    st.error("Ocurrió un error al analizar tu caso. Intenta de nuevo o envíalo por el buzón.")

    if st.session_state.get("analisis"):
        mostrar_analisis(st.session_state["analisis"])
    else:
        st.info("👆 Escribe o dicta tu caso y pulsa **Analizar**. Te diré qué hacer hoy, esta semana y ante qué autoridad.")

    # ---- Buzón -----------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📬 ¿No encontraste tu problema o tienes una duda especial?")
    st.write(f"Envíale tu caso al **{config.AUTOR_SISTEMA}** para que lo revise.")
    with st.form("form_buzon", clear_on_submit=True):
        b1, b2 = st.columns(2)
        nom_bz = b1.text_input("Tu nombre o apodo (opcional):")
        con_bz = b2.text_input("Correo o WhatsApp para responderte (opcional):")
        duda_bz = st.text_area("Explícanos qué te sucedió y qué información necesitas:", max_chars=4000)
        st.caption("Tu contacto solo lo ve el administrador y nunca se sube a GitHub. El texto se guarda anonimizado.")
        enviar = ui_submit("📨 Enviar al administrador", use_container_width=True)
    if enviar:
        if st.session_state["buzon_envios"] >= 5:
            st.warning("Alcanzaste el máximo de envíos en esta sesión.")
        elif len(duda_bz.strip()) < 10:
            st.warning("Por favor escribe una breve descripción de tu duda.")
        elif db.guardar_buzon(nom_bz, con_bz, duda_bz):
            st.session_state["buzon_envios"] += 1
            try:
                sync.sincronizar(AJUSTES)
            except Exception:
                log.exception("Sync tras buzón")
            st.success("✅ Tu caso quedó guardado en el buzón del administrador.")
        else:
            st.info("Ese mensaje ya se había enviado.")

# ==============================================================================
# PESTAÑA 2
# ==============================================================================
with t_calc:
    st.subheader("💰 Paso 2 de 3 · ¿Cuánto me toca?")
    st.write("Para asuntos de trabajo: estima cuánto te corresponde por despido o renuncia según la LFT.")
    res2, datos2, oferta2, plazo2 = render_calculadora("t2", {"periodicidad": "Semanal"}, "")
    if res2 is not None:
        st.markdown("#### 🧮 ¿Cuánto me quedaría si contrato a un abogado?")
        tab_l = honorarios.tabulador_rama("Casos Laborales")
        try:
            h = honorarios.calcular_cotizacion(res2.total_liquidacion, float(tab_l["asesoria_sug"]), float(tab_l["anticipo_sug"]),
                                               float(tab_l["pct_sugerido"]), float(tab_l["gastos_periciales_sug"]))
            m1, m2, m3 = st.columns(3)
            m1.metric("Honorarios estimados (abogado particular)", dinero(h["honorarios_totales_abogado"]))
            m2.metric("Neto estimado para ti", dinero(h["monto_neto_libre_ciudadano"]))
            m3.metric("Vía gratuita", "PROFEDET: $0")
            st.caption("Referencia con el esquema habitual de porcentaje al ganar. La PROFEDET atiende gratis a trabajadores.")
        except ValueError as exc:
            st.warning(str(exc))

# ==============================================================================
# PESTAÑA 3: casos
# ==============================================================================
with t_casos:
    st.subheader("🏆 Paso 3 · Casos parecidos: qué funcionó y qué no")
    st.write("Casos **ilustrativos** (construidos para orientar; no son sentencias reales) que comparan qué acciones ayudan y qué errores perjudican.")
    cat_comp = st.selectbox("Tema a comparar:", list(config.TIPOS_CASOS), key="filtro_comp")
    casos = db.listar_casos(cat_comp)
    if not casos:
        st.info("Aún no hay registros para esta categoría.")
    else:
        ganados = [c for c in casos if c["resultado"] == "GANADO"]
        perdidos = [c for c in casos if c["resultado"] == "PERDIDO"]
        cg, cp = st.columns(2)

        def etiqueta(c):
            return "<span class='badge ilus-badge'>CASO ILUSTRATIVO</span>" if c.get("ilustrativo") else "<span class='badge step-badge'>CASO DOCUMENTADO</span>"

        with cg:
            st.markdown("#### 🟢 Estrategia del caso ganado")
            for g in ganados or []:
                caja("money-box", f"<span class='badge win-badge'>ÉXITO</span>{etiqueta(g)}<br><br><b>📌 {esc(g['titulo'])}</b><br><br>"
                                  f"<b>🗣️ Qué ocurrió:</b><br>{fmt_inline(g['evidencia_logs'])}<br><br>"
                                  f"<b>💼 Estrategia:</b><br>{fmt_inline(g['accion_abogado'])}<br><br>"
                                  f"<b>👨‍⚖️ Resolución:</b><br>{fmt_inline(g['reaccion_juez'])}<br><br>"
                                  f"<b>✅ Qué hacer:</b><br>{fmt_inline(g['que_hacer_ciudadano'])}")
            if not ganados:
                st.info("Aún no hay un caso ganado en esta categoría.")
        with cp:
            st.markdown("#### 🔴 Error del caso perdido")
            for p in perdidos or []:
                caja("alert-box", f"<span class='badge loss-badge'>FRACASO</span>{etiqueta(p)}<br><br><b>📌 {esc(p['titulo'])}</b><br><br>"
                                  f"<b>🗣️ Qué ocurrió:</b><br>{fmt_inline(p['evidencia_logs'])}<br><br>"
                                  f"<b>💥 Error que causó la derrota:</b><br>{fmt_inline(p['causa_raiz_fallo'])}<br><br>"
                                  f"<b>🚫 Qué NUNCA hacer:</b><br>{fmt_inline(p['que_no_hacer_ciudadano'])}")
            if not perdidos:
                st.info("Aún no hay un caso perdido en esta categoría.")

# ==============================================================================
# PESTAÑA 4: fuentes
# ==============================================================================
with t_fuentes:
    L = config.leyes()
    st.subheader("📚 Datos legales usados y fuentes oficiales")
    st.markdown(mk(
        f"- **Salario mínimo general {L['vigencia_anio']}:** {dinero(L['salario_minimo']['general'])} diarios · **Zona libre frontera norte:** {dinero(L['salario_minimo']['frontera_norte'])} "
        f"(vigente desde {L['salario_minimo']['vigente_desde']}; fuente: {L['salario_minimo']['fuente']}).\n"
        f"- **UMA {L['vigencia_anio']}:** {dinero(L['uma']['diaria'])} diaria (vigente desde {L['uma']['vigente_desde']}; fuente: {L['uma']['fuente']}).\n"
        f"- **Última verificación de datos:** {L['salario_minimo']['verificado']} · versión de reglas {L['version']}."
    ))
    st.markdown("#### Contactos (verifica en los sitios oficiales)")
    ct = L["contactos"]
    st.markdown(mk(
        f"- Emergencias: **{ct['emergencias']}** · Denuncia anónima: **{ct['denuncia_anonima']}**\n- PROFEDET: {ct['profedet']}\n- CONDUSEF: {ct['condusef']}\n"
        f"- Policía Cibernética: {ct['policia_cibernetica']}\n- CNDH: {ct['cndh']}\n- Línea de la Vida (apoyo emocional): {ct['linea_de_la_vida']}\n\n*{ct['nota']}*"
    ))
    st.markdown("#### Fuentes oficiales")
    for f in L["fuentes_oficiales"]:
        st.markdown(f"- [{f['nombre']}]({f['url']})")
    st.info(config.AVISO_LEGAL)

# ==============================================================================
# PESTAÑAS DE ADMINISTRADOR
# ==============================================================================
if ES_ADMIN:
    # ---------------------------------------------------------------- Sistema y respaldo
    with t_sistema:
        st.subheader("☁️ Sistema, modelo y respaldo")
        conteos = db.contar_tablas()
        mem_pend = len(db.listar_memoria("pendiente"))
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Casos en la base", conteos["casos_juridicos_cbr"])
        s2.metric("Memorias pendientes", mem_pend)
        s3.metric("Memorias aprobadas", len(db.listar_memoria("aprobado")))
        s4.metric("Mensajes en buzón", conteos["buzon_casos"])

        st.markdown("#### 🧠 Modelo estadístico de apoyo")
        stt = MODELO["stats"]
        st.write(f"Disponible: **{'sí' if stt['disponible'] else 'no'}** · muestras: **{stt['muestras']}** · categorías: **{stt['clases']}** · "
                 f"vocabulario: **{stt['vocabulario']}** · exactitud validada: **{stt['cv_accuracy'] if stt['cv_accuracy'] is not None else 'sin validar'}**")
        if stt["advertencia"]:
            st.warning(stt["advertencia"])
        st.caption("El triage principal usa reglas con pesos; el modelo solo apoya cuando las reglas no detectan nada y solo aprende de casos APROBADOS por ti.")

        st.markdown("#### ☁️ GitHub")
        st.write(f"Repositorio: `{AJUSTES.gh_repo or 'no configurado'}` · rama `{AJUSTES.gh_branch}` · token: {'configurado' if AJUSTES.gh_token else 'no configurado'}")
        with db.conexion() as conn:
            st.caption(f"Último resultado: {db.get_meta(conn, 'ultimo_sync_msg', 'sin sincronizaciones todavía')} · "
                       f"pendiente: {'sí' if db.get_meta(conn, 'sync_pendiente', '0') == '1' else 'no'}")
        g1, g2, g3 = st.columns(3)
        if g1.button("🔎 Verificar que el repo sea privado", use_container_width=True):
            if AJUSTES.gh_repo and AJUSTES.gh_token:
                priv = sync.repo_es_privado(AJUSTES.gh_repo, AJUSTES.gh_token)
                (st.success if priv else st.error)("Repositorio privado ✅" if priv else ("Repositorio PÚBLICO ⚠️" if priv is False else "No pude verificarlo."))
            else:
                st.warning("Configura GITHUB_REPO y GITHUB_TOKEN en los secretos.")
        if g2.button("☁️ Forzar sincronización", use_container_width=True):
            r = sync.sincronizar(AJUSTES, forzar=True)
            (st.success if r.get("github_ok") else st.warning)(mk(r["msg"]))
        if g3.button("♻️ Restaurar desde respaldo", use_container_width=True):
            r = sync.restaurar(AJUSTES)
            st.success(f"Importados: {r['casos']} casos, {r['memoria']} memorias (pendientes), {r['buzon']} mensajes.")
        ui_download("💾 Descargar respaldo completo (.json, sin datos de contacto)",
                           data=json.dumps(db.exportar_respaldo(), ensure_ascii=False, indent=2).encode("utf-8"),
                           file_name=config.BACKUP_JSON_FILE, mime="application/json")

        st.markdown("#### ⚙️ Estado de las reglas legales")
        if problemas_leyes:
            for p in problemas_leyes:
                st.error(mk(p))
        else:
            st.success(f"Reglas legales al día (versión {config.leyes()['version']}).")
        st.caption("La base SQLite local es temporal en algunos hosting (Streamlit Cloud): el respaldo en GitHub privado es lo que la reconstruye.")

    # ---------------------------------------------------------------- Revisión y buzón
    with t_revision:
        st.subheader("✅ Revisión del aprendizaje (supervisada)")
        st.caption("Nada entra al modelo sin tu aprobación. Los textos ya están anonimizados.")
        pendientes = db.listar_memoria("pendiente")
        if not pendientes:
            st.info("No hay memorias pendientes.")
        for m in pendientes[:15]:
            with st.container(border=True):
                st.markdown(f"**#{m['id']}** · {esc(m['fecha'])} · sugerida: `{m['categoria']}` ({m['confianza']:.0f}%)")
                st.write(m["relato_anonimo"])
                cats = list(config.CATEGORIAS)
                cat_sel = st.selectbox("Categoría correcta:", cats, index=cats.index(m["categoria"]) if m["categoria"] in cats else 0, key=f"cat_mem_{m['id']}")
                b1, b2 = st.columns(2)
                if b1.button("✅ Aprobar y entrenar", key=f"ok_mem_{m['id']}"):
                    db.resolver_memoria(m["id"], "aprobado", cat_sel)
                    sync.sincronizar(AJUSTES)
                    st.rerun()
                if b2.button("🗑️ Rechazar", key=f"no_mem_{m['id']}"):
                    db.resolver_memoria(m["id"], "rechazado")
                    st.rerun()

        st.markdown("---")
        st.subheader("📬 Buzón ciudadano")
        buzon = db.listar_buzon()
        if not buzon:
            st.info("Aún no hay mensajes.")
        else:
            ui_dataframe(pd.DataFrame(buzon)[["id", "nombre", "contacto", "relato_anonimo", "estado", "fecha_envio"]], use_container_width=True, hide_index=True)
            with st.form("form_buzon_admin"):
                id_sel = st.selectbox("ID del mensaje:", [b["id"] for b in buzon])
                cat_bz = st.selectbox("Categoría:", list(config.CATEGORIAS))
                reco = st.text_area("Recomendación oficial para casos como este:",
                                    value="Acudir a la autoridad competente con pruebas documentales, sin firmar renuncias ni entregar efectivo.")
                convertir = ui_submit("🚀 Convertir en caso de aprendizaje")
            if convertir:
                fila = next(b for b in buzon if b["id"] == id_sel)
                macro, rama, tipo = config.MAPA_MATERIA[cat_bz]
                db.agregar_caso({
                    "codigo_caso": f"EXP-BUZON-{id_sel}-{datetime.now():%H%M}", "macro_rama": macro, "rama_derecho": rama, "categoria_caso": cat_bz,
                    "tipo_caso": tipo, "titulo": f"Caso ciudadano del buzón #{id_sel}", "actores_intervinientes": "Autoridad competente",
                    "etapa_clave": "1. Atención inicial", "medida_cautelar": "Protección ciudadana", "resolucion_obtenida": "Atendido",
                    "recurso_utilizado": "Vía oficial", "evidencia_logs": fila["relato_anonimo"], "resultado": "GANADO",
                    "accion_abogado": reco, "reaccion_juez": "N/A", "causa_raiz_fallo": "N/A", "estrategia_ganadora": reco,
                    "que_hacer_ciudadano": reco, "que_no_hacer_ciudadano": "No entregar dinero sin recibo ni firmar documentos en blanco.",
                    "ilustrativo": 0, "origen": "buzon",
                })
                db.marcar_buzon(id_sel, "Integrado al aprendizaje")
                sync.sincronizar(AJUSTES)
                st.success(f"Caso #{id_sel} integrado.")
                st.rerun()

    # ---------------------------------------------------------------- Enseñar caso
    with t_ensenar:
        st.subheader("➕ Enseñar un caso nuevo")
        with st.form("form_admin_caso"):
            a1, a2, a3 = st.columns(3)
            ncod = a1.text_input("Código (ej. EXP-TRA-2026-099)")
            ncat = a2.selectbox("Categoría", list(config.TIPOS_CASOS))
            nres = a3.selectbox("Resultado", ["GANADO", "PERDIDO"])
            nreal = st.checkbox("Es un caso real y documentado (si no, se rotula como ilustrativo)")
            ntit = st.text_input("Título del caso")
            nevid = st.text_area("Relato de hechos (usa palabras coloquiales; sin datos personales)")
            naccion = st.text_area("Estrategia o acción aplicada")
            nresol = st.text_area("Resolución de la autoridad")
            ncausa = st.text_area("Causa del fracaso (si aplica)")
            nqh = st.text_area("✅ Qué debe hacer el ciudadano")
            nqnh = st.text_area("🚫 Qué NO debe hacer el ciudadano")
            guardar = ui_submit("💾 Guardar caso")
        if guardar:
            if ncod and ntit and nevid:
                macro, rama, tipo = config.MAPA_MATERIA[ncat]
                ok = db.agregar_caso({
                    "codigo_caso": ncod.strip(), "macro_rama": macro, "rama_derecho": rama, "categoria_caso": ncat, "tipo_caso": config.TIPOS_CASOS[ncat][0],
                    "titulo": ntit, "actores_intervinientes": "Autoridad", "etapa_clave": "1. Inicio", "medida_cautelar": "N/A", "resolucion_obtenida": nresol or "N/A",
                    "recurso_utilizado": "N/A", "evidencia_logs": security.anonimizar(nevid), "resultado": nres, "accion_abogado": naccion or "N/A",
                    "reaccion_juez": nresol or "N/A", "causa_raiz_fallo": ncausa or "N/A", "estrategia_ganadora": naccion or "N/A",
                    "que_hacer_ciudadano": nqh or "N/A", "que_no_hacer_ciudadano": nqnh or "N/A", "ilustrativo": 0 if nreal else 1, "origen": "admin",
                })
                if ok:
                    r = sync.sincronizar(AJUSTES)
                    st.success("✅ Caso guardado. " + mk(r["msg"]))
                else:
                    st.warning("Ese código ya existe.")
            else:
                st.warning("Código, título y relato son obligatorios.")

    # ---------------------------------------------------------------- Cotizador
    with t_cotiz:
        st.subheader("🛠️ Cotizador privado de honorarios")
        st.caption(config.tabulador()["aviso"])
        mat = st.selectbox("Materia:", list(config.tabulador()["ramas"]))
        tab_a = honorarios.tabulador_rama(mat)
        q1, q2 = st.columns(2)
        monto_disp = q1.number_input("Monto aproximado en disputa ($ MXN):", min_value=0.0, value=50000.0, step=5000.0)
        pct = q2.number_input("Cuota litis (%):", min_value=0.0, max_value=50.0, value=float(tab_a["pct_sugerido"]), step=1.0)
        q3, q4 = st.columns(2)
        anticipo = q3.number_input("Anticipo ($ MXN):", min_value=0.0, value=float(tab_a["anticipo_sug"]), step=500.0)
        asesoria = q4.number_input("Asesoría ($ MXN):", min_value=0.0, value=float(tab_a["asesoria_sug"]), step=100.0)
        gastos = st.number_input("Gastos y periciales ($ MXN):", min_value=0.0, value=float(tab_a["gastos_periciales_sug"]), step=250.0)
        try:
            cot = honorarios.calcular_cotizacion(monto_disp, asesoria, anticipo, pct, gastos, float(tab_a["horas_promedio_despacho"]))
            caja("money-box", "<b>📊 Propuesta económica:</b><br>"
                              f"• Anticipo: &#36;{anticipo:,.2f}<br>• Comisión por éxito ({pct:g}%): &#36;{cot['comision_exito']:,.2f}<br>"
                              f"• Honorarios totales: &#36;{cot['honorarios_totales_abogado']:,.2f}<br>• Gastos: &#36;{gastos:,.2f}<br>"
                              f"• <b>Neto para el cliente: &#36;{cot['monto_neto_libre_ciudadano']:,.2f}</b> ({cot['pct_honorarios_sobre_monto']}% en honorarios)<br>"
                              f"• Costo interno estimado: &#36;{cot['costo_interno_despacho']:,.2f} · utilidad: &#36;{cot['utilidad_neta_abogado']:,.2f}")
            for adv in cot["advertencias"]:
                st.warning(mk(adv))
            st.text_area("📋 Texto para enviar al cliente:", value=honorarios.texto_propuesta(mat, asesoria, anticipo, pct), height=170)
        except ValueError as exc:
            st.error(str(exc))

    # ---------------------------------------------------------------- Tráfico
    with t_trafico:
        st.subheader("👥 Tráfico y calidad")
        por_dia, total, hoy_n = db.visitas_por_dia(30)
        v1, v2 = st.columns(2)
        v1.metric("Visitas totales", total)
        v2.metric("Visitas hoy", hoy_n)
        if por_dia:
            st.bar_chart(pd.DataFrame(por_dia).set_index("dia"))
        fb = db.resumen_feedback()
        st.markdown("#### 👍 Utilidad de la guía")
        if fb["total"]:
            st.metric("Aprobación", f"{fb['pct_util']}%", f"{fb['total']} opiniones")
        else:
            st.info("Aún no hay opiniones.")

st.markdown("---")
st.caption(f"⚙️ Arquitectura y desarrollo: {config.AUTOR_SISTEMA} · {config.MARCA_SISTEMA} · reglas legales v{config.leyes()['version']}")


# ==============================================================================
# CONTROL TOTAL (solo administrador)
# ==============================================================================
if ES_ADMIN:
    with t_control:
        control_admin.render()

"""Triage multi-materia: detecta qué áreas del derecho toca el relato y las ordena por urgencia.

Enfoque: reglas con pesos sobre texto normalizado (sin acentos, con límites de palabra) y,
solo como apoyo, un clasificador estadístico (ver ml.py). Si no hay evidencia suficiente,
devuelve «Indeterminado» en lugar de adivinar una materia.
"""
from __future__ import annotations

import math
import re

from . import config
from .extraction import norm

UMBRAL_ACTIVACION = 2.0
UMBRAL_ML = 0.60

# (regex sobre texto normalizado, peso)
REGLAS: dict[str, list[tuple[str, float]]] = {
    "Tránsito y Abuso Policial": [
        (r"\bpatrullas?\b", 3), (r"\bpolicias?\b", 2.5), (r"\bmordidas?\b", 3), (r"\bcorralon(?:es)?\b", 3),
        (r"\bgrua\b", 2), (r"\btransito\b", 2), (r"\bagentes? de transito\b", 3), (r"\bsembr(?:aron|ar|aban)\b", 2.5),
        (r"\bsustancias? ilicitas?\b", 2.5), (r"\b(?:me detuvo|me detuvieron|me pararon)\b", 2),
        (r"\basuntos internos\b", 3), (r"\binfracci(?:on|ones)\b", 1.5), (r"\bmultas?\b", 1),
        (r"\bplacas?\b", 1), (r"\bretenes?\b", 1.5), (r"\boficiales?\b", 0.5), (r"\bme quitaron (?:la )?moto\b", 2),
    ],
    "Casos Penales y Fraudes": [
        (r"\bfraudes?\b", 3), (r"\bestafa\w*\b", 3), (r"\bphishing\b", 3), (r"\bvaciaron\b", 3),
        (r"\bclonaron\b", 2.5), (r"\bspei\b", 2), (r"\b(?:robo|usurpacion|suplantacion) de identidad\b", 3),
        (r"\b(?:usaron|use|utilizaron) mi ine\b|\bcopia de mi ine\b", 3), (r"\bmi ine\b", 1.5),
        (r"\bcriptomonedas?\b|\bcripto\b|\bbitcoin\b", 2), (r"\bllaves privadas\b|\bfrase semilla\b|\bwallet\b|\bbilletera\b", 2),
        (r"\b(?:me )?(?:quitaron|robaron|me robaron) (?:el |mi )?(?:celular|telefono)\b", 2.5),
        (r"\bsin mi (?:consentimiento|permiso|autorizacion)\b", 1.5),
        (r"\bcreditos? a mi nombre\b|\babrir creditos\b|\bsacar creditos\b", 2.5),
        (r"\btransferencias? (?:\w+ )?(?:no autorizadas?|que yo nunca)\b", 2.5), (r"\bsacaron (?:mi )?dinero\b", 2.5),
        (r"\bextorsi(?:on|ones)\b", 2), (r"\bamenazas? de muerte\b", 3), (r"\be\.?firma\b", 1.5),
        (r"\bhackeo\b|\bhackearon\b", 3), (r"\bcargos? no reconocidos?\b", 2.5), (r"\bparecia de mi banco\b|\bmensaje de mi banco\b", 2),
    ],
    "Casos Laborales": [
        (r"\bdespid\w*\b", 3), (r"\bme (?:corrieron|corren|echaron|sacaron del trabajo)\b", 3), (r"\bliquidacion\b", 3),
        (r"\bfiniquito\b", 3), (r"\bsueldo\b", 2), (r"\bsalarios?\b", 2), (r"\bquincenas?\b", 1.5),
        (r"\bsemanal(?:es)?\b", 1), (r"\bvacaciones\b", 1.5), (r"\baguinaldo\b", 2), (r"\bpatron(?:es)?\b", 2),
        (r"\brenuncia\b", 2), (r"\bhoja en blanco\b", 2), (r"\brecursos humanos\b", 2), (r"\bimss\b", 1.5),
        (r"\bchamba\b", 2), (r"\bempleo\b", 1.5), (r"\b(?:trabajaba|trabaje|trabajando|trabajo)\b", 1),
        (r"\bempresa\b", 1), (r"\b(?:jefe|encargado|supervisor)\b", 1), (r"\bdias? (?:libres?|de descanso)\b", 1.5),
        (r"\bboletin\w*\b", 1.5),
        # Daños ocasionados en el trabajo (producto, mercancía o cliente) y descuentos al sueldo
        (r"\bdanos?\b", 1.5), (r"\bgerencia\b|\bgerente\b", 2), (r"\bmercancias?\b|\brefri\w*\b", 1.5),
        (r"\bse me (?:cayo|callo|rompio|quebro)\b|\bse (?:cayo|callo|rompio|quebro)\b", 2),
        (r"\b(?:cargador|acomodador|diablito|montacargas|rampa)\b", 1.5),
        (r"\bme (?:quiere|quieren|cobrar|cobren|descontar|descuenten)\b|\bcobrar(?:me)? (?:los )?danos?\b", 2.5),
        (r"\bdescuent\w* (?:de|del|por) (?:mi )?(?:sueldo|salario|quincena|pago)\b", 3),
        (r"\bcorrerme\b|\bme (?:van|quieren) (?:a )?(?:correr|despedir)\b|\bamenazan? con (?:correr|despedir)\w*\b", 3),
    ],
    "Acoso de Cobranza y Deudas": [
        (r"\bcobranza\b", 3), (r"\bembarg\w+\b", 2.5), (r"\bapps? de prestamos?\b|\bmontadeudas\b|\bprestamos? en linea\b", 3),
        (r"\bprestamos?\b", 1.5), (r"\bromper (?:la )?cerradura\b|\brompan\b", 2), (r"\bburo de credito\b", 1.5),
        (r"\bcredito que (?:jamas|nunca) (?:pedi|solicite)\b|\bque no pedi\b", 2.5),
        (r"\bllaman a mis contactos\b|\bhostig\w+\b|\bacoso\b", 2), (r"\bdeuda\w*\b", 1), (r"\bdebo\b", 1),
    ],
    "Casos Familiares": [
        (r"\bpension(?: alimenticia)?\b", 3), (r"\balimentos\b", 2),
        (r"\b(?:papa|mama|padre|madre) de mis hijos\b", 3), (r"\bcustodia\b", 3), (r"\bdivorcio\b", 3),
        (r"\bvisitas\b", 1), (r"\bmanutencion\b", 2), (r"\b(?:mis hijos|mis ninos|los ninos|mi hijo|mi hija)\b", 1.5),
    ],
    "Casos Civiles y Mercantiles": [
        (r"\binquilin\w+\b", 3), (r"\brentas?\b", 1.5), (r"\barrendamiento\b|\barrendador\w*\b|\barrendatari\w+\b", 3),
        (r"\bpagares?\b", 3), (r"\b(?:desocupar|desalojo|desalojar)\b", 2.5), (r"\bprestado\b", 1.5),
        (r"\b(?:fiador|aval)\b", 2), (r"\b(?:casero|propietario)\b", 1.5),
    ],
}
_REGLAS_COMPILADAS = {
    cat: [(re.compile(p), w) for p, w in reglas] for cat, reglas in REGLAS.items()
}

DANOS_EVENTO = re.compile(r"\bdanos?\b|\bse (?:me )?(?:cayo|callo|rompio|quebro)\b|\bcobrar(?:me)?\b")
CONTEXTO_TRABAJO = re.compile(
    r"\b(?:cliente|clientes|mercancias?|refri\w*|producto|gerencia|gerente|diablito|cargador|acomodador|"
    r"rampa|propinas?|apoyo)\b")


def subtipo_laboral(relato: str) -> str | None:
    """Subtipo dentro de «Casos Laborales». Hoy: daños ocurridos al apoyar en el trabajo (propinas o sin contrato)."""
    t = norm(relato)
    if DANOS_EVENTO.search(t) and CONTEXTO_TRABAJO.search(t):
        return "danos_en_trabajo"
    return None


ALERTAS_URGENCIA = [
    ("peligro", re.compile(r"\b(?:me van a matar|amenazas? de muerte|me amenazan de muerte|secuestr\w+|me (?:golpe\w+|agred\w+)|violencia|con (?:un )?arma|me apunt\w+)\b"),
     "Si tú o alguien más está en peligro inmediato, llama al **911**. Para denuncia anónima: **089**."),
    ("agresion_cliente", re.compile(r"\b(?:golpear(?:me)?|madrear(?:me)?|agredir(?:me)?|pegarme|me pegue|me va a pegar|me quiere pegar|me van a pegar)\b"),
     "Tu seguridad va primero: **aléjate**, busca a seguridad de la tienda o a un compañero y no te quedes a solas con la persona. Si hay golpes o amenazas inmediatas, llama al **911**. No respondas con violencia. Guarda evidencia (fotos, testigos, grabaciones de cámaras) y denuncia ante el Ministerio Público si te agreden."),
    ("detencion", re.compile(r"\b(?:estoy detenid[oa]|me tienen detenid[oa]|me detuvieron|me llevaron (?:a la|al) (?:comandancia|ministerio|mp|carcel))\b"),
     "Si estás detenido: tienes derecho a guardar silencio, a una llamada y a un defensor. **No firmes nada** sin abogado. Avisa a un familiar tu ubicación. Emergencias: **911**."),
    ("fraude_en_curso", re.compile(r"\b(?:me estan (?:vaciando|robando)|acaban de (?:vaciar|robar|clonar)|hace (?:unos? )?(?:minutos|una hora))\b"),
     "Si el fraude es reciente, **llama ahora mismo a tu banco** (número al reverso de tu tarjeta) para bloquear tarjetas y banca móvil: cada minuto cuenta."),
    ("crisis", re.compile(r"\b(?:quitarme la vida|suicid\w+|ya no quiero vivir|no quiero seguir viviendo|hacerme dano)\b"),
     "Lo que estás viviendo es muy pesado y **no tienes que cargarlo solo/a**. Puedes llamar gratis a la **Línea de la Vida: 800 911 2000** (24 h). Si estás en peligro inmediato, llama al **911**."),
]


def detectar_alertas(relato: str) -> list[dict]:
    t = norm(relato)
    return [{"tipo": tipo, "mensaje": msg} for tipo, rx, msg in ALERTAS_URGENCIA if rx.search(t)]


def puntuar(relato: str) -> dict[str, float]:
    """Puntaje por categoría (suma de pesos; las repeticiones suman un poco más)."""
    t = norm(relato)
    puntajes: dict[str, float] = {}
    for cat, reglas in _REGLAS_COMPILADAS.items():
        total = 0.0
        for rx, peso in reglas:
            n = len(rx.findall(t))
            if n:
                total += peso + min(1.0, 0.25 * (n - 1))
        if total > 0:
            puntajes[cat] = round(total, 2)
    return puntajes


def confianza_desde_puntaje(puntaje: float) -> float:
    return round(min(97.0, 100.0 * (1.0 - math.exp(-puntaje / 4.0))), 1)


def nivel_confianza(puntaje: float) -> str:
    if puntaje >= 6:
        return "alta"
    if puntaje >= 3.5:
        return "media"
    return "baja"


def diagnosticar(relato: str, ml=None) -> dict:
    """Clasifica el relato. ``ml`` es el modelo de ml.py (opcional)."""
    from . import ml as ml_mod

    puntajes = puntuar(relato)
    activas = {c: p for c, p in puntajes.items() if p >= UMBRAL_ACTIVACION}
    ml_cat, ml_prob = ml_mod.predecir(ml, relato) if ml else (None, 0.0)

    origen = "reglas"
    if not activas and ml_cat and ml_prob >= UMBRAL_ML:
        activas = {ml_cat: round(-4.0 * math.log(1 - min(ml_prob, 0.97)), 2)}
        origen = "modelo estadístico"

    if not activas:
        return {
            "indeterminado": True, "macro_rama": "", "rama": "No determinada", "categoria": "Indeterminado",
            "tipo": "", "confianza": 0.0, "nivel_confianza": "baja", "es_multimateria": False,
            "tiene_componente_laboral": False, "categorias_ordenadas": [], "modulos_triage": [],
            "puntajes": puntajes, "origen": "ninguno", "ml": {"categoria": ml_cat, "prob": ml_prob},
            "requiere_mas_detalle": True, "alertas": detectar_alertas(relato),
        }

    ordenadas = sorted(activas, key=lambda c: (config.PRIORIDAD_TRIAGE[c][0], -activas[c]))
    principal = ordenadas[0]
    macro, rama, tipo = config.MAPA_MATERIA[principal]
    modulos = []
    for c in ordenadas:
        m_i, r_i, t_i = config.MAPA_MATERIA[c]
        num, titulo = config.PRIORIDAD_TRIAGE[c]
        modulos.append({
            "categoria": c, "macro_rama": m_i, "rama": r_i, "tipo": t_i, "prioridad_num": num,
            "titulo_prioridad": titulo, "puntaje": activas[c],
            "confianza": confianza_desde_puntaje(activas[c]), "nivel": nivel_confianza(activas[c]),
        })
    conf_p = modulos[0]["confianza"]
    return {
        "indeterminado": False, "macro_rama": macro,
        "rama": rama if len(ordenadas) == 1 else f"Multi-Materia ({len(ordenadas)} áreas detectadas)",
        "categoria": principal, "tipo": tipo, "confianza": conf_p, "nivel_confianza": modulos[0]["nivel"],
        "es_multimateria": len(ordenadas) > 1, "tiene_componente_laboral": "Casos Laborales" in ordenadas,
        "categorias_ordenadas": ordenadas, "modulos_triage": modulos, "puntajes": puntajes, "origen": origen,
        "ml": {"categoria": ml_cat, "prob": ml_prob},
        "requiere_mas_detalle": min(m["puntaje"] for m in modulos) < 3.5 and len(modulos) == 1,
        "alertas": detectar_alertas(relato),
    }

"""Extracción de datos del relato (sueldo, oferta, antigüedad, fechas...) sin servicios externos.

Principio: si un dato no se puede leer con seguridad, se devuelve ``None`` y se pide al usuario
que lo confirme. Nunca se inventan montos.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
    "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
NUMEROS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
    "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "quince": 15, "veinte": 20,
}
_NUM_PAL = "|".join(NUMEROS)


def norm(texto: str) -> str:
    """Minúsculas, sin acentos, espacios colapsados."""
    t = unicodedata.normalize("NFKD", str(texto or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[ \t]+", " ", t)


def _a_entero(tok: str) -> int | None:
    tok = tok.strip()
    if tok.isdigit():
        return int(tok)
    return NUMEROS.get(tok)


# --------------------------------------------------------------------------- montos
_NUM = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?"
_UNIDAD_TIEMPO = r"(?:quincenas?|semanas?|meses|mes|anos?|dias?|horas?|veces|años?)\b|%"
_MONTO = re.compile(
    rf"(?P<signo>\$\s*)?(?P<num>{_NUM})(?P<mil>\s*(?:mil|k)\b)?(?P<pesos>\s*(?:pesos|mxn|varos)\b)?(?!\s*(?:{_UNIDAD_TIEMPO}))",
    re.I,
)


def encontrar_montos(texto: str) -> list[dict]:
    """Devuelve montos en dinero: [{'valor', 'inicio', 'fin'}]. Descarta fechas, años y cantidades chicas."""
    res = []
    for m in _MONTO.finditer(texto):
        num = m.group("num")
        valor = float(num.replace(",", ""))
        if m.group("mil"):
            valor *= 1000.0
        explicito = bool(m.group("signo") or m.group("pesos") or m.group("mil"))
        if not explicito:
            if valor < 100:
                continue
            previo = texto[max(0, m.start() - 8):m.start()]
            if re.fullmatch(r"(19|20)\d\d", num) and re.search(r"(de|del|ano|desde|en)\s*$", previo):
                continue  # es un año
        res.append({"valor": round(valor, 2), "inicio": m.start(), "fin": m.end()})
    return res


_PERIODOS = [
    ("Semanal", re.compile(r"\b(semanal(?:es)?|a la semana|por semana|cada semana|a la sem)\b")),
    ("Quincenal", re.compile(r"\b(quincenal(?:es)?|a la quincena|por quincena|cada quincena)\b")),
    ("Mensual", re.compile(r"\b(mensual(?:es)?|al mes|por mes|cada mes)\b")),
    ("Diario", re.compile(r"\b(diario|diarios|al dia|por dia|cada dia)\b")),
]
_TRIGGER_SALARIO = re.compile(r"\b(sueldo|salario|gano|ganaba|ganaban|me pagaban|me pagan|cobraba|cobro|percibia|raya|me pagaba)\b")
_TRIGGER_OFERTA = re.compile(
    r"(quieren dar(?:me)?|me dan|me daran|me van a dar|ofrecen|me ofrecen|ofrecieron|ofrece|proponen|me quieren pagar|"
    r"solo me (?:dan|daran|pagan)|soltar|me pagarian|finiquito de|liquidacion de)"
)


def _oraciones(t: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.;!?\n]+", t) if s.strip()]


def extraer_oferta(t: str) -> tuple[float, list[tuple[int, int]]]:
    """Busca la cantidad que ofrece el patrón. Devuelve (oferta, spans_usados)."""
    for m in _TRIGGER_OFERTA.finditer(t):
        ventana = t[m.end(): m.end() + 45]
        montos = encontrar_montos(ventana)
        if montos:
            primero = montos[0]
            return primero["valor"], [(m.end() + primero["inicio"], m.end() + primero["fin"])]
    return 0.0, []


def _enmascarar(t: str, spans: list[tuple[int, int]]) -> str:
    chars = list(t)
    for a, b in spans:
        for i in range(a, min(b, len(chars))):
            chars[i] = " "
    return "".join(chars)


def extraer_salario(t: str) -> dict:
    """Sueldo y periodicidad. Si falta la periodicidad, se pide confirmar."""
    for s in _oraciones(t):
        gatillo = _TRIGGER_SALARIO.search(s)
        if not gatillo:
            continue
        montos = [m for m in encontrar_montos(s) if m["inicio"] >= gatillo.start() - 2] or encontrar_montos(s)
        if not montos:
            continue
        periodo = None
        for nombre, rx in _PERIODOS:
            if rx.search(s):
                periodo = nombre
                break
        return {"monto": montos[0]["valor"], "periodicidad": periodo}
    return {"monto": None, "periodicidad": None}


def _num_a_dias(cantidad: int, unidad: str) -> int:
    if unidad.startswith("quincena"):
        return cantidad * 15
    if unidad.startswith("semana"):
        return cantidad * 7
    if unidad.startswith("mes"):
        return cantidad * 30
    return cantidad


def extraer_pendientes(t: str) -> tuple[int, str]:
    """Días de sueldo no pagados (quincenas/semanas/meses/días retenidos)."""
    patron = re.compile(rf"\b(\d+|{_NUM_PAL})\s+(quincenas?|semanas?|meses|mes|dias?)\b")
    for s in _oraciones(t):
        if not re.search(r"(pag|deb|retien|adeud|pendient|sin cobrar|no me han)", s):
            continue
        if re.search(r"(llevaba|trabaj\w+|antiguedad)\s+\w*\s*\d+\s+(meses|mes)", s) and not re.search(r"(sin pagar|no me|deben|adeud|retien)", s):
            continue
        m = patron.search(s)
        if m:
            cantidad = _a_entero(m.group(1))
            if cantidad:
                return _num_a_dias(cantidad, m.group(2)), m.group(0)
    return 0, ""


def extraer_antiguedad(t: str, referencia: date) -> dict:
    """Años y meses de antigüedad. Fuente: texto explícito o fecha de ingreso ('desde marzo de 2024')."""
    for s in _oraciones(t):
        if not re.search(r"(trabaj|llevaba|antiguedad|labor|estuve|tenia|durante|laboraba)", s):
            continue
        m = re.search(rf"\b(\d+|{_NUM_PAL})\s+anos?(?:\s+y\s+(medio|(\d+)\s+mes(?:es)?))?", s)
        if m:
            anios = _a_entero(m.group(1))
            if anios is not None:
                meses = 0
                if m.group(2):
                    meses = 6 if m.group(2) == "medio" else int(m.group(3))
                return {"anios": anios, "meses": min(meses, 11), "fuente": "texto"}
        m = re.search(rf"\b(llevaba|trabaje|trabaj[eé] durante|estuve)\D{{0,12}}(\d+|{_NUM_PAL})\s+meses\b", s)
        if m:
            total = _a_entero(m.group(2)) or 0
            if total:
                return {"anios": total // 12, "meses": total % 12, "fuente": "texto"}
    m = re.search(r"desde\s+(?:el\s+)?(?:(\d{1,2})\s+de\s+)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s*(?:de\s*)?(\d{4})", t)
    if m:
        ingreso = date(int(m.group(3)), MESES[m.group(2)], min(int(m.group(1) or 1), 28))
        return _antig_desde(ingreso, referencia)
    m = re.search(r"desde\s+(?:el\s+ano\s+|el\s+|)(20\d\d|19\d\d)\b", t)
    if m:
        return _antig_desde(date(int(m.group(1)), 1, 1), referencia)
    return {"anios": None, "meses": None, "fuente": None}


def _antig_desde(ingreso: date, referencia: date) -> dict:
    if ingreso > referencia:
        return {"anios": None, "meses": None, "fuente": None}
    meses_tot = (referencia.year - ingreso.year) * 12 + (referencia.month - ingreso.month)
    if referencia.day < ingreso.day:
        meses_tot -= 1
    meses_tot = max(0, meses_tot)
    return {"anios": meses_tot // 12, "meses": meses_tot % 12, "fuente": "fecha de ingreso"}


def extraer_fecha_separacion(t: str, hoy: date) -> date | None:
    gatillos = r"(despid|corri|echaron|separ|liquid|ultimo dia|dejo de trabajar|me sacaron|renunci|rescind)"
    for s in _oraciones(t):
        if not re.search(gatillos, s):
            continue
        if re.search(r"\bhoy\b", s):
            return hoy
        if re.search(r"\b(anteayer|antier)\b", s):
            return hoy - timedelta(days=2)
        if re.search(r"\bayer\b", s):
            return hoy - timedelta(days=1)
        m = re.search(rf"hace\s+(\d+|{_NUM_PAL})\s+(dias?|semanas?|meses|mes)\b", s)
        if m:
            n = _a_entero(m.group(1))
            if n:
                return hoy - timedelta(days=_num_a_dias(n, m.group(2)))
        m = re.search(r"el\s+(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")(?:\s+de(?:l)?\s+(\d{4}))?", s)
        if m:
            anio = int(m.group(3)) if m.group(3) else hoy.year
            try:
                f = date(anio, MESES[m.group(2)], int(m.group(1)))
            except ValueError:
                continue
            if f > hoy and not m.group(3):
                f = date(anio - 1, f.month, f.day)
            return f if f <= hoy else None
    return None


def extraer_montos_contexto(t: str, excluir: list[tuple[int, int]] | None = None) -> list[dict]:
    """Montos exigidos por policías o cobradores (para alertar: NO pagar)."""
    excluir = excluir or []
    salida = []
    patrones = [
        ("policial", r"(pedir(?:me)?|piden|pidieron|piden|exigen|exigieron|mordida de|extorsion de)"),
        ("cobranza", r"(cobra(?:n)?|cobrar|exigen|exigian|me reclaman|debo|deuda de|adeudo de)"),
    ]
    for tipo, rx in patrones:
        for m in re.finditer(rx, t):
            ventana = t[m.end(): m.end() + 45]
            for monto in encontrar_montos(ventana):
                a = m.end() + monto["inicio"]
                if any(x <= a < y for x, y in excluir):
                    continue
                par = {"tipo": tipo, "monto": monto["valor"]}
                if par not in salida:
                    salida.append(par)
                break
    return salida


def extraer_datos(relato: str, hoy: date | None = None) -> dict:
    """Extrae todos los datos útiles del relato. ``None`` = no se pudo leer con seguridad."""
    hoy = hoy or date.today()
    t = norm(relato)

    oferta, spans = extraer_oferta(t)
    t_sin_oferta = _enmascarar(t, spans)
    sal = extraer_salario(t_sin_oferta)
    dias_pend, texto_pend = extraer_pendientes(t)
    fecha_sep = extraer_fecha_separacion(t, hoy)
    antig = extraer_antiguedad(t, fecha_sep or hoy)

    faltas = {
        "sin_vacaciones": bool(re.search(r"(no me daban vacaciones|sin vacaciones|nunca (?:me )?(?:dieron|di[oó]) vacaciones|nunca tome vacaciones|no tenia vacaciones)", t)),
        "sin_aguinaldo": bool(re.search(r"(sin aguinaldo|no me daban aguinaldo|nunca (?:me )?(?:dieron|pagaron) aguinaldo|ni aguinaldo|no me pagaron aguinaldo)", t)),
        "sin_descansos": bool(re.search(r"(dias libres|dias de descanso|nunca descansaba|sin descanso|sin dia libre|trabajaba (?:los )?domingos|siete dias)", t)),
        "sin_contrato": bool(re.search(r"(sin contrato|no tenia contrato|no firme contrato|ni contrato)", t)),
        "sin_imss": bool(re.search(r"(\bsin (?:contrato,? )?(?:ni )?imss\b|\bni imss\b|no me dieron de alta|no tenia imss|sin seguro social|no me afiliaron)", t)),
        "jornada_larga": bool(re.search(r"\b(1[0-9]|9)\s*horas\b", t)),
    }
    salario_diario = None
    if sal["monto"] and sal["periodicidad"]:
        from .lft import salario_diario as _sd
        salario_diario = _sd(sal["monto"], sal["periodicidad"])

    faltan = []
    if not sal["monto"]:
        faltan.append("sueldo")
    elif not sal["periodicidad"]:
        faltan.append("periodicidad del sueldo")
    if antig["anios"] is None:
        faltan.append("antigüedad")
    if fecha_sep is None:
        faltan.append("fecha del despido")

    return {
        "salario_monto": sal["monto"],
        "periodicidad": sal["periodicidad"],
        "salario_diario": salario_diario,
        "oferta_patronal": oferta,
        "dias_sueldo_pendientes": dias_pend,
        "pendientes_texto": texto_pend,
        "anios": antig["anios"],
        "meses": antig["meses"],
        "antiguedad_fuente": antig["fuente"],
        "fecha_separacion": fecha_sep,
        **faltas,
        "montos_otros": extraer_montos_contexto(t, spans),
        "faltan_datos": faltan,
    }

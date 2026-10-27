"""Seguridad y privacidad: escape HTML, anonimización, contraseñas y bloqueo de intentos."""
from __future__ import annotations

import hashlib
import hmac
import html
import re
import secrets
import sqlite3
import time
from urllib.parse import urlparse

# --------------------------------------------------------------------------------------
# Escape / render seguro
# --------------------------------------------------------------------------------------


def esc(valor) -> str:
    """Escapa cualquier valor para incrustarlo con seguridad en HTML."""
    return html.escape("" if valor is None else str(valor), quote=True)


def fmt_inline(texto) -> str:
    """Escapa y convierte **negritas**, *cursivas* y saltos de línea a HTML seguro."""
    t = esc(texto)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t, flags=re.S)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t, flags=re.S)
    # '$' como entidad HTML: evita que Streamlit lo interprete como fórmula LaTeX
    return t.replace("$", "&#36;").replace("\n", "<br>")


def quitar_markdown(texto) -> str:
    t = re.sub(r"\*+", "", str(texto or ""))
    return t.strip()


def url_segura(url: str) -> str:
    """Devuelve la URL solo si es http(s); si no, '#'. (Evita javascript: y similares.)"""
    try:
        p = urlparse(str(url).strip())
        if p.scheme in ("http", "https") and p.netloc:
            return str(url).strip()
    except Exception:
        pass
    return "#"


# --------------------------------------------------------------------------------------
# Anonimización
# --------------------------------------------------------------------------------------
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_RE_URL = re.compile(r"https?://\S+|www\.\S+", re.I)
_RE_CURP = re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", re.I)
_RE_RFC = re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b", re.I)
_RE_CLAVE_ELECTOR = re.compile(r"\b[A-Z]{6}\d{8}[HM]\d{3}\b", re.I)
_RE_NUMEROS_LARGOS = re.compile(r"(?<![\d,.])(?:\d[ -]?){13,19}(?![\d])")
_RE_TEL_10 = re.compile(r"(?<![\d,.$])(?:\+?52[\s.-]?)?\d{10}(?![\d,.])")
_RE_TEL_AGRUPADO = re.compile(r"(?<![\d,.$])\(?\d{2,3}\)?[\s.-]\d{3,4}[\s.-]\d{4}(?![\d])")
_RE_NOMBRE = re.compile(
    r"((?i:me llamo|mi nombre es|soy|mi nombre completo es)\s+)"
    r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:de\s+|del\s+|la\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,3})"
)
_RE_PLACA = re.compile(r"((?i:placas?)\s*(?:es|son|:)?\s*)([A-Z0-9]{2,4}[- ]?[A-Z0-9]{2,4})\b")
_RE_DOMICILIO = re.compile(
    r"\b(?i:calle|avenida|av\.|colonia|col\.|privada|cerrada|fraccionamiento)\s+[^,.;\n]{2,45}"
)


def _reemplazo_numero_largo(m: re.Match) -> str:
    digitos = re.sub(r"\D", "", m.group(0))
    if len(digitos) == 18:
        return "[CLABE]"
    if 15 <= len(digitos) <= 16:
        return "[TARJETA]"
    return "[NÚMERO DE CUENTA/ID]"


def anonimizar_detallado(texto: str) -> tuple[str, dict]:
    """Quita datos personales detectables. Devuelve (texto_anonimo, conteo_por_tipo)."""
    t = str(texto or "")
    conteo: dict[str, int] = {}

    def sub(patron, repl, nombre):
        nonlocal t
        t, n = patron.subn(repl, t)
        if n:
            conteo[nombre] = conteo.get(nombre, 0) + n

    sub(_RE_EMAIL, "[CORREO]", "correo")
    sub(_RE_URL, "[ENLACE]", "enlace")
    sub(_RE_CURP, "[CURP]", "curp")
    sub(_RE_CLAVE_ELECTOR, "[CLAVE DE ELECTOR]", "clave_elector")
    sub(_RE_RFC, "[RFC]", "rfc")
    sub(_RE_NUMEROS_LARGOS, _reemplazo_numero_largo, "numero_largo")
    sub(_RE_TEL_10, "[TELÉFONO]", "telefono")
    sub(_RE_TEL_AGRUPADO, "[TELÉFONO]", "telefono")
    sub(_RE_PLACA, lambda m: m.group(1) + "[PLACA]", "placa")
    sub(_RE_NOMBRE, lambda m: m.group(1) + "[NOMBRE]", "nombre")
    sub(_RE_DOMICILIO, "[DOMICILIO]", "domicilio")
    return t, conteo


def anonimizar(texto: str) -> str:
    return anonimizar_detallado(texto)[0]


def hash_texto(texto: str) -> str:
    """Hash SHA-256 del texto normalizado (para deduplicar sin guardar el original)."""
    base = re.sub(r"\s+", " ", str(texto or "").strip().lower())
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------
# Contraseñas
# --------------------------------------------------------------------------------------
PASSWORDS_PROHIBIDAS = {
    "admin", "admin2026", "admin123", "password", "contraseña", "12345678", "123456", "1234",
    "forensicmind", "lexguia", "saul", "root", "changeme", "cambiame",
}
_ITER = 240_000


def hash_password(password: str, iteraciones: int = _ITER) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iteraciones)
    return f"pbkdf2_sha256${iteraciones}${salt}${dk.hex()}"


def verificar_password(candidata: str, guardada: str) -> bool:
    """Compara en tiempo constante. Acepta hash pbkdf2 (recomendado) o texto plano robusto."""
    if not candidata or not guardada:
        return False
    if guardada.startswith("pbkdf2_sha256$"):
        try:
            _, it, salt, esperado = guardada.split("$")
            dk = hashlib.pbkdf2_hmac("sha256", candidata.encode("utf-8"), bytes.fromhex(salt), int(it))
            return hmac.compare_digest(dk.hex(), esperado)
        except (ValueError, TypeError):
            return False
    return hmac.compare_digest(candidata.encode("utf-8"), guardada.encode("utf-8"))


def estado_admin(guardada: str) -> tuple[bool, str]:
    """¿Está permitido el panel admin con la clave configurada? (habilitado, motivo)."""
    if not guardada:
        return False, "Panel de administrador deshabilitado: define ADMIN_PASSWORD_HASH en los secretos."
    if guardada.startswith("pbkdf2_sha256$"):
        return True, ""
    if guardada.lower() in PASSWORDS_PROHIBIDAS or len(guardada) < 12:
        return False, (
            "La contraseña configurada es débil o conocida (usa mínimo 12 caracteres). "
            "Genera un hash con: python -m forensicmind.security"
        )
    return True, "Consejo: guarda ADMIN_PASSWORD_HASH (pbkdf2) en vez de la clave en texto plano."


# --------------------------------------------------------------------------------------
# Bloqueo de intentos de acceso (persistente, global: hay un solo administrador)
# --------------------------------------------------------------------------------------
MAX_INTENTOS = 5
VENTANA_SEG = 900  # 15 minutos


def registrar_fallo(conn: sqlite3.Connection, ahora: float | None = None) -> None:
    conn.execute("INSERT INTO intentos_login (ts) VALUES (?)", (ahora if ahora is not None else time.time(),))


def segundos_bloqueo(conn: sqlite3.Connection, ahora: float | None = None) -> int:
    ahora = ahora if ahora is not None else time.time()
    filas = conn.execute(
        "SELECT ts FROM intentos_login WHERE ts > ? ORDER BY ts DESC", (ahora - VENTANA_SEG,)
    ).fetchall()
    if len(filas) < MAX_INTENTOS:
        return 0
    ultimo = float(filas[0][0])
    return max(0, int(ultimo + VENTANA_SEG - ahora))


def limpiar_intentos(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM intentos_login")


if __name__ == "__main__":  # python -m forensicmind.security
    import getpass

    pw = getpass.getpass("Nueva contraseña de administrador (mínimo 12 caracteres): ")
    if len(pw) < 12:
        raise SystemExit("Muy corta: usa al menos 12 caracteres.")
    print("\nPega esto en .streamlit/secrets.toml (o en Secrets de Streamlit Cloud):\n")
    print(f'ADMIN_PASSWORD_HASH = "{hash_password(pw)}"')

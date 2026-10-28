"""Capa de base de datos SQLite: esquema, semillas, aprendizaje supervisado y respaldos sin PII."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from . import config
from .security import anonimizar, hash_texto

SCHEMA_VERSION = 2

CAMPOS_CASO = [
    "codigo_caso", "macro_rama", "rama_derecho", "categoria_caso", "tipo_caso", "titulo",
    "actores_intervinientes", "etapa_clave", "medida_cautelar", "resolucion_obtenida",
    "recurso_utilizado", "evidencia_logs", "hash_sha256", "resultado", "accion_abogado",
    "reaccion_juez", "causa_raiz_fallo", "estrategia_ganadora", "que_hacer_ciudadano",
    "que_no_hacer_ciudadano", "fecha_registro", "ilustrativo", "origen",
]

_DDL = [
    """CREATE TABLE IF NOT EXISTS casos_juridicos_cbr (
        id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_caso TEXT UNIQUE,
        macro_rama TEXT, rama_derecho TEXT, categoria_caso TEXT, tipo_caso TEXT,
        titulo TEXT, actores_intervinientes TEXT, etapa_clave TEXT, medida_cautelar TEXT,
        resolucion_obtenida TEXT, recurso_utilizado TEXT, evidencia_logs TEXT, hash_sha256 TEXT,
        resultado TEXT, accion_abogado TEXT, reaccion_juez TEXT, causa_raiz_fallo TEXT,
        estrategia_ganadora TEXT, que_hacer_ciudadano TEXT, que_no_hacer_ciudadano TEXT,
        fecha_registro TEXT, ilustrativo INTEGER DEFAULT 1, origen TEXT DEFAULT 'semilla')""",
    """CREATE TABLE IF NOT EXISTS memoria_aprendizaje (
        id INTEGER PRIMARY KEY AUTOINCREMENT, relato_anonimo TEXT NOT NULL, categoria TEXT,
        categorias_json TEXT, confianza REAL, estado TEXT DEFAULT 'pendiente', fuente TEXT,
        hash_consulta TEXT UNIQUE, fecha TEXT)""",
    """CREATE TABLE IF NOT EXISTS buzon_casos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, contacto TEXT,
        relato_anonimo TEXT NOT NULL, relato_hash TEXT UNIQUE, estado TEXT DEFAULT 'Pendiente de revisión',
        fecha_envio TEXT)""",
    "CREATE TABLE IF NOT EXISTS visitas_pagina (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT)",
    """CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, categoria TEXT, util INTEGER, comentario TEXT)""",
    "CREATE TABLE IF NOT EXISTS intentos_login (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL)",
    "CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor TEXT)",
]


def ahora_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def conexion():
    conn = sqlite3.connect(config.db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columnas(conn, tabla: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}


def init_db() -> None:
    """Crea el esquema (idempotente) e inserta los casos semilla."""
    with conexion() as conn:
        for ddl in _DDL:
            conn.execute(ddl)
        cols = _columnas(conn, "casos_juridicos_cbr")
        if "ilustrativo" not in cols:
            conn.execute("ALTER TABLE casos_juridicos_cbr ADD COLUMN ilustrativo INTEGER DEFAULT 1")
        if "origen" not in cols:
            conn.execute("ALTER TABLE casos_juridicos_cbr ADD COLUMN origen TEXT DEFAULT 'semilla'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_casos_cat ON casos_juridicos_cbr(categoria_caso)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_estado ON memoria_aprendizaje(estado)")
        set_meta(conn, "schema_version", str(SCHEMA_VERSION))
        insertar_semillas(conn)


def insertar_semillas(conn) -> int:
    n = 0
    for caso in config.cargar_json_datos("casos_semilla.json"):
        caso = dict(caso)
        caso["hash_sha256"] = hashlib.sha256(caso["codigo_caso"].encode()).hexdigest()
        caso["ilustrativo"] = 1
        caso["origen"] = "semilla"
        n += _insertar_caso(conn, caso)
    return n


def _insertar_caso(conn, caso: dict) -> int:
    valores = [caso.get(c) for c in CAMPOS_CASO]
    # valores por defecto razonables para campos opcionales
    defaults = {"resultado": "GANADO", "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
                "ilustrativo": 0, "origen": "admin"}
    for i, c in enumerate(CAMPOS_CASO):
        if valores[i] in (None, "") and c in defaults:
            valores[i] = defaults[c]
    if not valores[0]:
        return 0
    marcas = ",".join("?" * len(CAMPOS_CASO))
    cur = conn.execute(
        f"INSERT OR IGNORE INTO casos_juridicos_cbr ({','.join(CAMPOS_CASO)}) VALUES ({marcas})", valores
    )
    return cur.rowcount


# ----------------------------------------------------------------------------- meta
def get_meta(conn, clave: str, default: str = "") -> str:
    fila = conn.execute("SELECT valor FROM meta WHERE clave=?", (clave,)).fetchone()
    return fila[0] if fila else default


def set_meta(conn, clave: str, valor: str) -> None:
    conn.execute(
        "INSERT INTO meta (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor",
        (clave, str(valor)),
    )


# ----------------------------------------------------------------------------- casos
def listar_casos(categoria: str | None = None) -> list[dict]:
    with conexion() as conn:
        if categoria:
            filas = conn.execute(
                "SELECT * FROM casos_juridicos_cbr WHERE categoria_caso=? ORDER BY id", (categoria,)
            ).fetchall()
        else:
            filas = conn.execute("SELECT * FROM casos_juridicos_cbr ORDER BY id").fetchall()
    return [dict(f) for f in filas]


def agregar_caso(caso: dict) -> bool:
    with conexion() as conn:
        c = dict(caso)
        c["hash_sha256"] = c.get("hash_sha256") or hashlib.sha256(str(c.get("evidencia_logs", "")).encode()).hexdigest()
        return bool(_insertar_caso(conn, c))


ACTUALIZABLES_CASO = [
    "titulo", "categoria_caso", "tipo_caso", "resultado", "evidencia_logs", "accion_abogado",
    "resolucion_obtenida", "causa_raiz_fallo", "estrategia_ganadora",
    "que_hacer_ciudadano", "que_no_hacer_ciudadano", "ilustrativo",
]
_TEXTOS_CASO = {"evidencia_logs", "accion_abogado", "resolucion_obtenida", "causa_raiz_fallo",
                "estrategia_ganadora", "que_hacer_ciudadano", "que_no_hacer_ciudadano", "titulo"}


def obtener_caso(id_caso: int) -> dict | None:
    with conexion() as conn:
        fila = conn.execute("SELECT * FROM casos_juridicos_cbr WHERE id=?", (int(id_caso),)).fetchone()
    return dict(fila) if fila else None


def actualizar_caso(id_caso: int, cambios: dict) -> bool:
    """Edita solo campos permitidos. Los textos libres se anonimizan antes de guardarse."""
    limpios = {}
    for k, v in cambios.items():
        if k not in ACTUALIZABLES_CASO:
            continue
        if k in _TEXTOS_CASO:
            v = anonimizar(str(v or "")).strip()
        limpios[k] = v
    if not limpios:
        return False
    sets = ", ".join(f"{k}=?" for k in limpios)
    with conexion() as conn:
        cur = conn.execute(f"UPDATE casos_juridicos_cbr SET {sets} WHERE id=?", [*limpios.values(), int(id_caso)])
        return cur.rowcount > 0


def eliminar_caso(id_caso: int) -> bool:
    """Borra un caso. Los casos semilla vuelven a crearse al reiniciar (son parte del catálogo)."""
    with conexion() as conn:
        return conn.execute("DELETE FROM casos_juridicos_cbr WHERE id=?", (int(id_caso),)).rowcount > 0


def eliminar_memoria(id_mem: int) -> bool:
    with conexion() as conn:
        return conn.execute("DELETE FROM memoria_aprendizaje WHERE id=?", (int(id_mem),)).rowcount > 0


def eliminar_buzon(id_bz: int) -> bool:
    with conexion() as conn:
        return conn.execute("DELETE FROM buzon_casos WHERE id=?", (int(id_bz),)).rowcount > 0


# ----------------------------------------------------------------------------- visitas / feedback
def registrar_visita() -> None:
    with conexion() as conn:
        conn.execute("INSERT INTO visitas_pagina (fecha_hora) VALUES (?)", (ahora_str(),))


def visitas_por_dia(dias: int = 30) -> tuple[list[dict], int, int]:
    desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
    with conexion() as conn:
        filas = conn.execute(
            "SELECT substr(fecha_hora,1,10) AS dia, COUNT(*) AS visitas FROM visitas_pagina "
            "WHERE substr(fecha_hora,1,10) >= ? GROUP BY dia ORDER BY dia", (desde,)
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM visitas_pagina").fetchone()[0]
        hoy = conn.execute(
            "SELECT COUNT(*) FROM visitas_pagina WHERE substr(fecha_hora,1,10)=?",
            (datetime.now().strftime("%Y-%m-%d"),),
        ).fetchone()[0]
    return [{"dia": f["dia"], "visitas": f["visitas"]} for f in filas], total, hoy


def registrar_feedback(categoria: str, util: bool, comentario: str = "") -> None:
    with conexion() as conn:
        conn.execute(
            "INSERT INTO feedback (fecha, categoria, util, comentario) VALUES (?,?,?,?)",
            (ahora_str(), categoria, 1 if util else 0, anonimizar(comentario)[:500]),
        )


def resumen_feedback() -> dict:
    with conexion() as conn:
        fila = conn.execute("SELECT COUNT(*), COALESCE(SUM(util),0) FROM feedback").fetchone()
    total, utiles = int(fila[0]), int(fila[1])
    return {"total": total, "utiles": utiles, "pct_util": round(100 * utiles / total, 1) if total else None}


# ----------------------------------------------------------------------------- memoria (supervisada)
def guardar_memoria_pendiente(relato: str, triage: dict, fuente: str = "Consulta ciudadana") -> bool:
    """Guarda SOLO texto anonimizado y en estado 'pendiente' (requiere aprobación humana)."""
    anon = anonimizar(relato).strip()
    if len(anon) < 20:
        return False
    with conexion() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO memoria_aprendizaje "
            "(relato_anonimo, categoria, categorias_json, confianza, estado, fuente, hash_consulta, fecha) "
            "VALUES (?,?,?,?, 'pendiente', ?,?,?)",
            (
                anon[:4000], triage.get("categoria"), json.dumps(triage.get("categorias_ordenadas", []), ensure_ascii=False),
                float(triage.get("confianza", 0.0)), fuente, hash_texto(anon), ahora_str(),
            ),
        )
        return cur.rowcount > 0


def listar_memoria(estado: str | None = None) -> list[dict]:
    with conexion() as conn:
        if estado:
            filas = conn.execute("SELECT * FROM memoria_aprendizaje WHERE estado=? ORDER BY id DESC", (estado,)).fetchall()
        else:
            filas = conn.execute("SELECT * FROM memoria_aprendizaje ORDER BY id DESC").fetchall()
    return [dict(f) for f in filas]


def resolver_memoria(id_mem: int, estado: str, categoria: str | None = None) -> None:
    if estado not in ("aprobado", "rechazado", "pendiente"):
        raise ValueError("Estado inválido")
    with conexion() as conn:
        if categoria:
            conn.execute("UPDATE memoria_aprendizaje SET estado=?, categoria=? WHERE id=?", (estado, categoria, int(id_mem)))
        else:
            conn.execute("UPDATE memoria_aprendizaje SET estado=? WHERE id=?", (estado, int(id_mem)))


def datos_entrenamiento() -> tuple[list[str], list[str]]:
    """Textos y etiquetas (categoría) de casos semilla/admin y memorias APROBADAS."""
    textos, etiquetas = [], []
    with conexion() as conn:
        for r in conn.execute("SELECT * FROM casos_juridicos_cbr").fetchall():
            textos.append(f"{r['titulo']} {r['evidencia_logs']} {r['tipo_caso']} {r['que_hacer_ciudadano']}")
            etiquetas.append(r["categoria_caso"])
        for r in conn.execute("SELECT * FROM memoria_aprendizaje WHERE estado='aprobado'").fetchall():
            textos.append(r["relato_anonimo"])
            etiquetas.append(r["categoria"])
    return textos, etiquetas


# ----------------------------------------------------------------------------- buzón
def guardar_buzon(nombre: str, contacto: str, relato: str) -> bool:
    anon = anonimizar(relato).strip()
    if len(anon) < 10:
        return False
    with conexion() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO buzon_casos (nombre, contacto, relato_anonimo, relato_hash, estado, fecha_envio) "
            "VALUES (?,?,?,?, 'Pendiente de revisión', ?)",
            ((nombre or "Ciudadano anónimo")[:80], (contacto or "Sin contacto")[:120], anon[:4000], hash_texto(anon), ahora_str()),
        )
        return cur.rowcount > 0


def listar_buzon() -> list[dict]:
    with conexion() as conn:
        return [dict(f) for f in conn.execute("SELECT * FROM buzon_casos ORDER BY id DESC").fetchall()]


def marcar_buzon(id_bz: int, estado: str) -> None:
    with conexion() as conn:
        conn.execute("UPDATE buzon_casos SET estado=? WHERE id=?", (estado, int(id_bz)))


# ----------------------------------------------------------------------------- respaldo (sin PII)
def exportar_respaldo() -> dict:
    """Payload de respaldo. NO incluye nombre ni contacto del buzón ni intentos de login."""
    with conexion() as conn:
        casos = [dict(r) for r in conn.execute("SELECT * FROM casos_juridicos_cbr").fetchall()]
        mem = [dict(r) for r in conn.execute("SELECT * FROM memoria_aprendizaje").fetchall()]
        buz = [
            {"relato_anonimo": r["relato_anonimo"], "relato_hash": r["relato_hash"], "estado": r["estado"], "fecha_envio": r["fecha_envio"]}
            for r in conn.execute("SELECT * FROM buzon_casos").fetchall()
        ]
        fb = [dict(r) for r in conn.execute("SELECT fecha, categoria, util, comentario FROM feedback").fetchall()]
    for lista in (casos, mem):
        for r in lista:
            r.pop("id", None)
    return {
        "formato": "forensicmind-respaldo-v11",
        "autor_arquitectura": config.AUTOR_SISTEMA,
        "sistema": config.MARCA_SISTEMA,
        "fecha_respaldo": ahora_str(),
        "totales": {"casos": len(casos), "memoria": len(mem), "buzon": len(buz), "feedback": len(fb)},
        "casos_juridicos_cbr": casos,
        "memoria_aprendizaje": mem,
        "buzon_casos": buz,
        "feedback": fb,
        "ajustes_legales": config.ajustes_legales_actuales(),
    }


def importar_respaldo(data: dict) -> dict:
    """Importa un respaldo v11 o v10. Todo texto se anonimiza y la memoria NUNCA entra aprobada."""
    nuevos = {"casos": 0, "memoria": 0, "buzon": 0}
    if not isinstance(data, dict):
        return nuevos
    with conexion() as conn:
        for cs in data.get("casos_juridicos_cbr", []) or []:
            if not isinstance(cs, dict) or not cs.get("codigo_caso"):
                continue
            c = {k: cs.get(k) for k in CAMPOS_CASO}
            c["hash_sha256"] = c.get("hash_sha256") or hashlib.sha256(str(c["codigo_caso"]).encode()).hexdigest()
            c["evidencia_logs"] = anonimizar(c.get("evidencia_logs") or "")
            c["ilustrativo"] = cs.get("ilustrativo", 0 if cs.get("origen") == "admin" else 1)
            c["origen"] = cs.get("origen") or "respaldo"
            nuevos["casos"] += _insertar_caso(conn, c)

        memorias = list(data.get("memoria_aprendizaje", []) or []) + list(data.get("memoria_neuronal_autonoma", []) or [])
        for m in memorias:
            if not isinstance(m, dict):
                continue
            texto = anonimizar(m.get("relato_anonimo") or m.get("relato_original") or "").strip()
            if len(texto) < 20:
                continue
            cat = m.get("categoria") or m.get("categoria_caso")
            estado = m.get("estado") if m.get("estado") in ("rechazado",) else "pendiente"
            cur = conn.execute(
                "INSERT OR IGNORE INTO memoria_aprendizaje "
                "(relato_anonimo, categoria, categorias_json, confianza, estado, fuente, hash_consulta, fecha) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (texto[:4000], cat, m.get("categorias_json"), float(m.get("confianza") or 0), estado,
                 m.get("fuente") or m.get("fuente_aprendizaje") or "Respaldo", hash_texto(texto),
                 m.get("fecha") or m.get("fecha_aprendizaje") or ahora_str()),
            )
            nuevos["memoria"] += cur.rowcount

        buzones = list(data.get("buzon_casos", []) or []) + list(data.get("buzon_casos_usuarios", []) or [])
        for b in buzones:
            if not isinstance(b, dict):
                continue
            texto = anonimizar(b.get("relato_anonimo") or b.get("relato_duda") or "").strip()
            if len(texto) < 10:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO buzon_casos (nombre, contacto, relato_anonimo, relato_hash, estado, fecha_envio) "
                "VALUES ('Ciudadano anónimo','Sin contacto',?,?,?,?)",
                (texto[:4000], hash_texto(texto), b.get("estado") or "Pendiente de revisión", b.get("fecha_envio") or ahora_str()),
            )
            nuevos["buzon"] += cur.rowcount
    ajustes = data.get("ajustes_legales")
    nuevos["ajustes_legales"] = False
    if isinstance(ajustes, dict) and ajustes:
        # Solo se aceptan si pasan la misma validación que el formulario del administrador.
        nuevos["ajustes_legales"] = not config.guardar_ajustes_legales(ajustes)
    return nuevos


def contar_tablas() -> dict:
    with conexion() as conn:
        return {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("casos_juridicos_cbr", "memoria_aprendizaje", "buzon_casos", "visitas_pagina", "feedback")
        }

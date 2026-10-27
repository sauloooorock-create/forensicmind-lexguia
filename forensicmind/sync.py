"""Respaldo y restauración con GitHub (solo datos anonimizados) con control de privacidad y reintentos."""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request

from . import config, db

API = "https://api.github.com"
INTERVALO_MIN_SEG = 60


def _request(metodo: str, url: str, token: str, cuerpo: dict | None = None, timeout: float = 8.0) -> tuple[int, dict | None]:
    """Llamada HTTP a la API de GitHub. Devuelve (status, json|None). status=0 si no hubo conexión."""
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ForensicMindAutoSync/11.0",
    }
    data = None
    if cuerpo is not None:
        data = json.dumps(cuerpo).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw.decode("utf-8")) if raw else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, None
    except Exception as e:  # sin red, DNS, timeout...
        return 0, {"error": str(e)[:120]}


def _url_contenido(repo: str) -> str:
    return f"{API}/repos/{repo.strip()}/contents/{config.BACKUP_JSON_FILE}"


def repo_es_privado(repo: str, token: str) -> bool | None:
    """True/False según GitHub; None si no se pudo verificar."""
    status, data = _request("GET", f"{API}/repos/{repo.strip()}", token)
    if status == 200 and isinstance(data, dict) and "private" in data:
        return bool(data["private"])
    return None


def descargar_respaldo(repo: str, token: str, branch: str = "main") -> dict:
    if not repo or not token:
        return {}
    status, data = _request("GET", f"{_url_contenido(repo)}?ref={branch.strip()}", token, timeout=6.0)
    if status != 200 or not isinstance(data, dict):
        return {}
    try:
        contenido = base64.b64decode(data.get("content", "")).decode("utf-8")
        return json.loads(contenido)
    except Exception:
        return {}


def escribir_respaldo_local(payload: dict) -> bool:
    try:
        ruta = config.DATA_DIR / config.BACKUP_JSON_FILE
        ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def subir_respaldo(ajustes: config.Ajustes, payload: dict) -> dict:
    """Sube el respaldo a GitHub. Resultado: {'local_ok','github_ok','msg'}."""
    local_ok = escribir_respaldo_local(payload)
    repo, token, branch = ajustes.gh_repo, ajustes.gh_token, ajustes.gh_branch
    if not repo or not token:
        return {"local_ok": local_ok, "github_ok": False, "msg": "Respaldo local actualizado (GitHub no configurado)."}

    privado = repo_es_privado(repo, token)
    if privado is None:
        return {"local_ok": local_ok, "github_ok": False,
                "msg": "No pude verificar si el repositorio es privado (revisa token/conexión): no subí nada por seguridad."}
    if privado is False and not ajustes.permitir_repo_publico:
        return {"local_ok": local_ok, "github_ok": False,
                "msg": "⚠️ El repositorio es PÚBLICO: no se sube el respaldo. Hazlo privado o define PERMITIR_REPO_PUBLICO=true bajo tu responsabilidad."}

    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    total = payload.get("totales", {})
    cuerpo = {
        "message": f"Auto-Sync ForensicMind v11 ({total.get('memoria', 0)} memorias | {total.get('casos', 0)} casos)",
        "content": base64.b64encode(raw).decode("utf-8"),
        "branch": branch,
    }
    ultimo = "sin respuesta"
    for _ in range(3):  # reintenta si el sha quedó viejo (409/422)
        st_get, datos = _request("GET", f"{_url_contenido(repo)}?ref={branch}", token)
        if st_get == 200 and isinstance(datos, dict) and datos.get("sha"):
            cuerpo["sha"] = datos["sha"]
        else:
            cuerpo.pop("sha", None)
        status, resp = _request("PUT", _url_contenido(repo), token, cuerpo, timeout=10.0)
        if status in (200, 201):
            return {"local_ok": local_ok, "github_ok": True, "msg": "☁️ Respaldo sincronizado en tu GitHub privado."}
        ultimo = f"HTTP {status}" + (f" — {str((resp or {}).get('message', ''))[:80]}" if resp else "")
        if status not in (409, 422):
            break
    return {"local_ok": local_ok, "github_ok": False, "msg": f"Guardado local OK; GitHub no aceptó el respaldo ({ultimo})."}


def sincronizar(ajustes: config.Ajustes, forzar: bool = False) -> dict:
    """Sincroniza respetando un intervalo mínimo para no saturar GitHub (el cambio queda 'pendiente')."""
    with db.conexion() as conn:
        ultimo = float(db.get_meta(conn, "ultimo_sync_ts", "0") or 0)
        if not forzar and time.time() - ultimo < INTERVALO_MIN_SEG:
            db.set_meta(conn, "sync_pendiente", "1")
            return {"local_ok": True, "github_ok": None, "msg": "Sincronización programada (se agrupan los cambios)."}
    res = subir_respaldo(ajustes, db.exportar_respaldo())
    with db.conexion() as conn:
        db.set_meta(conn, "ultimo_sync_ts", str(time.time()))
        db.set_meta(conn, "sync_pendiente", "0" if res.get("github_ok") or not (ajustes.gh_repo and ajustes.gh_token) else "1")
        db.set_meta(conn, "ultimo_sync_msg", res["msg"])
    return res


def sincronizar_pendiente(ajustes: config.Ajustes) -> dict | None:
    with db.conexion() as conn:
        pendiente = db.get_meta(conn, "sync_pendiente", "0") == "1"
        ultimo = float(db.get_meta(conn, "ultimo_sync_ts", "0") or 0)
    if pendiente and time.time() - ultimo >= INTERVALO_MIN_SEG:
        return sincronizar(ajustes, forzar=True)
    return None


def restaurar(ajustes: config.Ajustes) -> dict:
    """Importa respaldo local y de GitHub (todo anonimizado; la memoria entra como 'pendiente')."""
    total = {"casos": 0, "memoria": 0, "buzon": 0}
    ruta = config.DATA_DIR / config.BACKUP_JSON_FILE
    fuentes = []
    try:
        if ruta.exists():
            fuentes.append(json.loads(ruta.read_text(encoding="utf-8")))
    except Exception:
        pass
    if ajustes.gh_repo and ajustes.gh_token:
        remoto = descargar_respaldo(ajustes.gh_repo, ajustes.gh_token, ajustes.gh_branch)
        if remoto:
            fuentes.append(remoto)
    for data in fuentes:
        nuevos = db.importar_respaldo(data)
        for k in total:
            total[k] += nuevos.get(k, 0)
    return total

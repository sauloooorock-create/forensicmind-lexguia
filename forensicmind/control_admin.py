"""Control total de la aplicación para el administrador.

Todo lo editable vive aquí: cifras legales (con validación), contactos, casos del catálogo,
memorias y mensajes del buzón. Los cambios se guardan en la base de datos o en
data/ajustes_legales.json, y ambos entran en el respaldo de GitHub.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from forensicmind import config, db

# Campos numéricos editables de leyes.json: (ruta con puntos, etiqueta, tipo)
CAMPOS_LEY = [
    ("salario_minimo.general", "Salario mínimo general ($/día)", float),
    ("salario_minimo.frontera_norte", "Salario mínimo frontera norte ($/día)", float),
    ("uma.diaria", "UMA diaria ($)", float),
    ("uma.mensual", "UMA mensual ($)", float),
    ("uma.anual", "UMA anual ($)", float),
    ("aguinaldo_dias_minimos", "Aguinaldo mínimo (días)", int),
    ("prima_vacacional_pct", "Prima vacacional (%)", float),
    ("indemnizacion.dias_constitucional", "Indemnización constitucional (días)", int),
    ("indemnizacion.dias_por_anio_art50", "20 días por año, art. 50 (días)", int),
    ("indemnizacion.prima_antiguedad_dias_por_anio", "Prima de antigüedad (días por año)", int),
    ("indemnizacion.prima_antiguedad_tope_veces_minimo", "Tope de prima (veces salario mínimo)", float),
    ("descanso_trabajado_pago_extra_veces", "Descanso trabajado (veces el salario)", float),
    ("isr.exento_uma_por_anio_servicio", "ISR exento (UMA por año de servicio)", float),
]


def _leer(d: dict, ruta: str):
    for parte in ruta.split("."):
        d = d[parte]
    return d


def _poner(d: dict, ruta: str, valor) -> None:
    partes = ruta.split(".")
    for parte in partes[:-1]:
        d = d.setdefault(parte, {})
    d[partes[-1]] = valor


def _texto_limpio(valor: str) -> str:
    """Quita caracteres de etiqueta para que un contacto no inyecte HTML."""
    return str(valor or "").replace("<", "").replace(">", "").strip()


def _cifras() -> None:
    st.markdown("#### 💰 Cifras y reglas legales")
    st.caption("Estas cifras se usan en la calculadora y en los dictámenes. Cada cambio se valida "
               "antes de guardarse; si algo no cuadra, la app no guarda nada.")
    base = config.leyes_base()
    actual = config.leyes()

    cols = st.columns(3)
    nuevos: dict[str, float | int] = {}
    for i, (ruta, etiqueta, tipo) in enumerate(CAMPOS_LEY):
        with cols[i % 3]:
            valor = _leer(actual, ruta)
            if tipo is int:
                nuevos[ruta] = int(st.number_input(etiqueta, value=int(valor), step=1, key=f"ley_{ruta}"))
            else:
                nuevos[ruta] = float(st.number_input(etiqueta, value=float(valor), step=0.01,
                                                     format="%.2f", key=f"ley_{ruta}"))

    st.markdown("##### 📞 Contactos de ayuda")
    claves = [k for k in actual["contactos"] if k != "nota"]
    cc = st.columns(3)
    contactos_nuevos = {}
    for i, clave in enumerate(claves):
        with cc[i % 3]:
            contactos_nuevos[clave] = _texto_limpio(
                st.text_input(clave.replace("_", " ").capitalize(), value=actual["contactos"][clave],
                              key=f"ctc_{clave}"))

    st.markdown("##### 📊 Tabla de vacaciones (art. 76 LFT)")
    st.caption("Cada fila es un tramo de años de servicio. Agrega o quita filas; los tramos deben "
               "ser continuos y los días deben aumentar.")
    tabla = st.data_editor(pd.DataFrame(actual["vacaciones_dias"]), num_rows="dynamic",
                           hide_index=True, key="ley_vacaciones")

    confirmo = st.checkbox(
        f"Confirmo que estas cifras son las oficiales vigentes para {date.today().year} "
        "(las revisé en DOF, CONASAMI, INEGI o la Ley Federal del Trabajo)",
        key="ley_confirmo")
    b1, b2 = st.columns(2)
    guardar = b1.button("💾 Guardar cifras", type="primary", disabled=not confirmo,
                        use_container_width=True, key="ley_guardar")
    restaurar = b2.button("↩️ Volver a los valores de leyes.json", use_container_width=True,
                          key="ley_restaurar")

    if restaurar:
        config.restablecer_ajustes_legales()
        st.success("Se restablecieron las cifras de data/leyes.json.")
        return
    if not guardar:
        return

    cambios: dict = {}
    rutas_cambiadas: list[str] = []
    for ruta, _, _ in CAMPOS_LEY:
        if nuevos[ruta] != _leer(base, ruta):
            _poner(cambios, ruta, nuevos[ruta])
            rutas_cambiadas.append(ruta)
    if any(r.startswith("salario_minimo") for r in rutas_cambiadas):
        _poner(cambios, "salario_minimo.verificado", date.today().isoformat())
    if any(r.startswith("uma.") for r in rutas_cambiadas):
        _poner(cambios, "uma.verificado", date.today().isoformat())
    cambios_contactos = {k: v for k, v in contactos_nuevos.items() if v != base["contactos"].get(k)}
    if cambios_contactos:
        cambios["contactos"] = cambios_contactos
    filas = [{"desde": int(r["desde"]), "hasta": int(r["hasta"]), "dias": int(r["dias"])}
             for r in tabla.to_dict("records") if pd.notna(r.get("desde")) and pd.notna(r.get("hasta"))
             and pd.notna(r.get("dias"))]
    if filas and filas != base["vacaciones_dias"]:
        cambios["vacaciones_dias"] = filas

    if not cambios:
        st.info("No hay cambios que guardar.")
        return
    cambios["vigencia_anio"] = date.today().year
    cambios["version"] = date.today().isoformat()
    problemas = config.guardar_ajustes_legales(cambios)
    if problemas:
        st.error("No se guardó. Corrige esto primero:\n\n" + "\n".join(f"- {p}" for p in problemas))
    else:
        st.success("Cifras guardadas. Ya se usan en la calculadora y se incluirán en el respaldo.")


def _casos() -> None:
    st.markdown("#### 🔬 Casos del catálogo")
    casos = db.listar_casos()
    if not casos:
        st.info("No hay casos en la base.")
        return
    opciones = {c["id"]: f"#{c['id']} · {c['codigo_caso']} · {(c['titulo'] or '')[:60]}" for c in casos}
    sel = st.selectbox("Caso a editar", list(opciones), format_func=lambda i: opciones[i], key="ctl_caso")
    c = next(x for x in casos if x["id"] == sel)

    k1, k2, k3 = st.columns([3, 2, 1])
    titulo = k1.text_input("Título", value=c["titulo"] or "", key=f"ctl_tit_{sel}")
    categorias = list(config.TIPOS_CASOS)
    cat_actual = c["categoria_caso"] if c["categoria_caso"] in categorias else categorias[0]
    categoria = k2.selectbox("Categoría", categorias, index=categorias.index(cat_actual), key=f"ctl_cat_{sel}")
    resultado = k3.selectbox("Resultado", ["GANADO", "PERDIDO"],
                             index=1 if c["resultado"] == "PERDIDO" else 0, key=f"ctl_res_{sel}")
    ilustrativo = st.checkbox("Caso ilustrativo (no es un expediente real)", value=bool(c["ilustrativo"]),
                              key=f"ctl_ilu_{sel}")
    campos = [
        ("evidencia_logs", "Hechos (sin datos personales)"),
        ("estrategia_ganadora", "Estrategia que funcionó"),
        ("accion_abogado", "Acción del abogado"),
        ("resolucion_obtenida", "Resolución de la autoridad"),
        ("causa_raiz_fallo", "Causa del fracaso (si aplica)"),
        ("que_hacer_ciudadano", "Qué debe hacer el ciudadano"),
        ("que_no_hacer_ciudadano", "Qué NO debe hacer el ciudadano"),
    ]
    valores = {}
    for clave, etiqueta in campos:
        valores[clave] = st.text_area(etiqueta, value=c[clave] or "", key=f"ctl_{clave}_{sel}")

    if st.button("💾 Guardar cambios del caso", type="primary", key=f"ctl_guardar_{sel}"):
        db.actualizar_caso(sel, {"titulo": titulo, "categoria_caso": categoria, "resultado": resultado,
                                 "ilustrativo": 1 if ilustrativo else 0, **valores})
        st.success("Caso actualizado. Los textos libres se anonimizaron al guardar.")

    confirmo = st.checkbox("Confirmo que quiero borrar este caso", key=f"ctl_del_c_{sel}")
    if st.button("🗑️ Borrar caso", disabled=not confirmo, key=f"ctl_borrar_c_{sel}"):
        db.eliminar_caso(sel)
        st.success("Caso borrado.")
    if c["origen"] == "semilla":
        st.caption("Este caso es semilla: volverá a aparecer al reiniciar la app.")


def _memoria() -> None:
    st.markdown("#### 🧠 Memorias del aprendizaje")
    memorias = db.listar_memoria()
    if not memorias:
        st.info("No hay memorias guardadas.")
        return
    opciones = {m["id"]: f"#{m['id']} · {m['estado']} · {m['categoria']} · {m['fecha']}" for m in memorias}
    sel = st.selectbox("Memoria", list(opciones), format_func=lambda i: opciones[i], key="ctl_mem")
    m = next(x for x in memorias if x["id"] == sel)
    st.text_area("Relato anonimizado", value=m["relato_anonimo"] or "", disabled=True, key=f"ctl_mem_t_{sel}")
    confirmo = st.checkbox("Confirmo que quiero borrar esta memoria", key=f"ctl_del_m_{sel}")
    if st.button("🗑️ Borrar memoria", disabled=not confirmo, key=f"ctl_borrar_m_{sel}"):
        db.eliminar_memoria(sel)
        st.success("Memoria borrada.")


def _buzon() -> None:
    st.markdown("#### 📬 Mensajes del buzón")
    mensajes = db.listar_buzon()
    if not mensajes:
        st.info("El buzón está vacío.")
        return
    opciones = {b["id"]: f"#{b['id']} · {b['estado']} · {b['fecha_envio']}" for b in mensajes}
    sel = st.selectbox("Mensaje", list(opciones), format_func=lambda i: opciones[i], key="ctl_bz")
    b = next(x for x in mensajes if x["id"] == sel)
    st.text_area("Relato", value=b["relato_anonimo"] or "", disabled=True, key=f"ctl_bz_t_{sel}")
    confirmo = st.checkbox("Confirmo que quiero borrar este mensaje", key=f"ctl_del_b_{sel}")
    if st.button("🗑️ Borrar mensaje", disabled=not confirmo, key=f"ctl_borrar_b_{sel}"):
        db.eliminar_buzon(sel)
        st.success("Mensaje borrado.")


def render() -> None:
    st.subheader("🛡️ Control total de la aplicación")
    st.caption("Todo lo editable está en esta página. Los cambios se guardan en la base y entran en el "
               "respaldo de GitHub.")
    _cifras()
    st.divider()
    _casos()
    st.divider()
    _memoria()
    st.divider()
    _buzon()

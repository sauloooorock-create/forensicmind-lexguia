# ForensicMind & LexGuía CBR v11

Orientación jurídica preliminar para México (laboral, tránsito, cobranza, familiar, penal/fraude, civil). **No sustituye a un abogado.**
Autor: Ing. Saúl Ángel Ortiz Rogel.

## Estructura
- `app.py` interfaz Streamlit · `forensicmind/` lógica (LFT, triage, extracción, BD, respaldo, documentos) · `data/*.json` reglas legales y contenido editable · `tests/` pruebas.

## Despliegue (Streamlit Cloud)
1. Sube este proyecto a un repo (puede ser público; no contiene secretos ni datos).
2. Crea un **repo PRIVADO** aparte para el respaldo y un token con permiso *Contents: read/write* solo a ese repo.
3. Genera el hash de tu contraseña: `python -m forensicmind.security` y copia el resultado.
4. En *Settings > Secrets* pega el contenido de `.streamlit/secrets.toml.example` ya llenado.
5. La app se niega a subir respaldos a un repo público (salvo `PERMITIR_REPO_PUBLICO`) y bloquea contraseñas débiles (admin queda deshabilitado).

## Mantenimiento anual
Cada enero actualiza `data/leyes.json` (salario mínimo, UMA, `vigencia_anio`, `version`). La prueba `test_leyes_vigentes_al_dia_actual` y el CI semanal fallan si se te olvida.

## Pruebas
`pip install -r requirements.txt pytest && python -m pytest tests -q`

## Privacidad
Los relatos se anonimizan (correo, teléfono, CURP, RFC, CLABE, nombres, domicilios…) antes de guardarse; solo se guardan con consentimiento y quedan *pendientes* hasta que un admin los apruebe. El respaldo no incluye datos de contacto del buzón.

## Limitaciones conocidas
- La interfaz se probó con una simulación de Streamlit, no con Streamlit real: haz una revisión visual al desplegar.
- No hay RAG con LLM; se usa `data/base_legal.json` (citas parafraseadas). Verifica artículos, teléfonos y montos con fuentes oficiales.
- Con pocos casos el modelo ML es débil y solo apoya al triage por reglas.
- SQLite es efímero en Streamlit Cloud; el respaldo privado en GitHub lo restaura.
- La extracción asistida con la API de Anthropic no se probó contra el servicio real.

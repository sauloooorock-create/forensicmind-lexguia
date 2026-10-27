"""Clasificador estadístico de apoyo (TF-IDF + regresión logística) con confianza real.

Honestidad técnica: con pocos casos el modelo NO generaliza bien; por eso solo se usa como
respaldo cuando las reglas no detectan nada, y las métricas se muestran en el panel admin.
"""
from __future__ import annotations

from collections import Counter

from . import db
from .extraction import norm

MIN_MUESTRAS = 8


def entrenar(textos: list[str], etiquetas: list[str]) -> dict:
    """Entrena el modelo. Devuelve {'vectorizer','modelo','stats'} (modelo=None si no es viable)."""
    stats = {
        "disponible": False, "muestras": len(textos), "clases": 0, "vocabulario": 0,
        "por_clase": dict(Counter(etiquetas)), "cv_accuracy": None, "advertencia": "",
    }
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score
    except ImportError:
        stats["advertencia"] = "scikit-learn no está instalado: el triage usa solo reglas."
        return {"vectorizer": None, "modelo": None, "stats": stats}

    clases = set(etiquetas)
    stats["clases"] = len(clases)
    if len(textos) < MIN_MUESTRAS or len(clases) < 2:
        stats["advertencia"] = f"Datos insuficientes (mínimo {MIN_MUESTRAS} muestras y 2 categorías)."
        return {"vectorizer": None, "modelo": None, "stats": stats}

    limpios = [norm(t) for t in textos]
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    X = vec.fit_transform(limpios)
    modelo = LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced")
    modelo.fit(X, etiquetas)

    stats.update({"disponible": True, "vocabulario": len(vec.vocabulary_)})
    minimo_clase = min(stats["por_clase"].values())
    if minimo_clase >= 3:
        try:
            scores = cross_val_score(LogisticRegression(max_iter=2000, C=5.0, class_weight="balanced"), X, etiquetas, cv=3)
            stats["cv_accuracy"] = round(float(scores.mean()) * 100, 1)
        except Exception:
            pass
    if stats["cv_accuracy"] is None:
        stats["advertencia"] = "Muy pocos ejemplos por categoría para validar el modelo (se necesitan ≥3 por categoría)."
    return {"vectorizer": vec, "modelo": modelo, "stats": stats}


def entrenar_desde_db() -> dict:
    textos, etiquetas = db.datos_entrenamiento()
    return entrenar(textos, etiquetas)


def predecir(m: dict | None, texto: str) -> tuple[str | None, float]:
    """(categoría, probabilidad real). (None, 0.0) si no hay modelo."""
    if not m or not m.get("modelo") or not m.get("vectorizer"):
        return None, 0.0
    try:
        X = m["vectorizer"].transform([norm(texto)])
        probs = m["modelo"].predict_proba(X)[0]
        i = int(probs.argmax())
        return str(m["modelo"].classes_[i]), round(float(probs[i]), 3)
    except Exception:
        return None, 0.0

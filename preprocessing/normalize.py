from __future__ import annotations

"""---------------------------------------------------"""
"""      Normalización de Entidades, Ramos y Fechas    """
"""---------------------------------------------------"""
"""

Funciones de limpieza reutilizables, extendidas a partir de la lógica
ya presente en pipeline_agrupado.py y pipeline_motivo.py (construcción
de fecha, limpieza de nombres de ramo, tipificación de cantidades).
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config import CODIGO_A_ENTIDAD

# Limpieza de nombres de ramo: quita el prefijo "Seguro de "/"Seguro " y
# agrupa variantes equivalentes, igual que en pipeline_agrupado.py.
RAMO_RENAME = {
    "Seguro de hogar": "hogar",
    "Seguro de salud": "salud",
    "Seguro de vida individual": "vida_individual",
    "Seguro de vida grupo": "vida_grupo",
    "Seguro colectivo de vida": "vida_grupo",
    "Seguro de riesgos laborales": "arl",
    "Seguro de automóviles": "automoviles",
}


def normalize_entidad(df: pd.DataFrame, tipo_col: str = "tipo_entidad", codigo_col: str = "codigo_entidad") -> pd.DataFrame:
    """Añade la columna 'entidad' con el nombre canónico (Bolivar/SURA/Colsanitas)
    a partir de columnas separadas tipo_entidad y codigo_entidad (formato del
    dataset de quejas, xyy7-rn7p)."""
    df = df.copy()
    clave = df[tipo_col].astype(str) + "-" + df[codigo_col].astype(str).str.zfill(2)
    df["entidad"] = clave.map(CODIGO_A_ENTIDAD)
    return df


def normalize_entidad_compuesto(df: pd.DataFrame, codigo_col: str = "codigo_entidad") -> pd.DataFrame:
    """Añade la columna 'entidad' cuando el código ya viene compuesto como
    'tipo-codigo' (ej. '13-27'), como en el dataset F290 (e967-4a8r)."""
    df = df.copy()
    df["entidad"] = df[codigo_col].astype(str).map(CODIGO_A_ENTIDAD)
    return df


def normalize_ramo(series: pd.Series) -> pd.Series:
    """Limpia los nombres de ramo/producto. Los que no están en RAMO_RENAME
    (ej. productos de crédito que no son seguros) se dejan en minúsculas y
    con guiones bajos para mantener consistencia, sin inventar categorías."""
    limpio = series.replace(RAMO_RENAME)
    desconocidos = ~limpio.isin(RAMO_RENAME.values())
    limpio.loc[desconocidos] = (
        limpio.loc[desconocidos]
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return limpio


def normalize_motivo(series: pd.Series) -> pd.Series:
    """Limpia espacios redundantes en el motivo sin alterar el texto original
    (el dataset ya trae los motivos en categorías consistentes)."""
    return series.str.strip().str.replace(r"\s+", " ", regex=True)


def build_fecha(anio_col: pd.Series, mes_col: pd.Series) -> pd.Series:
    """Construye una columna de fecha (primer día del mes) a partir de
    columnas separadas de año y mes, igual que en los pipelines base."""
    return pd.to_datetime(
        anio_col.astype(str) + "-" + mes_col.astype(str) + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    ).dt.date


def drop_duplicates_report(df: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    """Elimina duplicados exactos por 'subset' e informa cuántos se quitaron."""
    antes = len(df)
    df = df.drop_duplicates(subset=subset)
    quitados = antes - len(df)
    if quitados:
        print(f"Duplicados eliminados ({subset}): {quitados}")
    return df


def fechas_incompletas_al_final(totales_por_fecha: pd.Series, umbral_pct: float = 0.5, ventana: int = 6) -> list:
    """Identifica meses incompletos al final de una serie de tiempo mensual,
    causados por rezago de publicación de la fuente (el mes más reciente
    llega con muy pocas filas y se termina de completar en una corrida
    futura del pipeline). Ejemplo real: 2026-07 llegó con 466 quejas en el
    sector completo, contra ~14.000 de un mes normal.

    Un mes se marca como incompleto si su total cae por debajo de
    `umbral_pct` del promedio de los `ventana` meses anteriores, Y está en
    la cola de la serie: se recorre de más reciente a más antiguo y se
    detiene en el primer mes que sí luce completo, así que un mes "raro"
    en medio del historial (una caída real, no un problema de reporte) NO
    se toca — ese es un problema distinto al que resuelve esta función
    (ver build_joined en build_dataset.py para huecos de un mes completo).

    Devuelve la lista de fechas a excluir (puede estar vacía)."""
    serie = totales_por_fecha.sort_index()
    incompletas = []
    for fecha in reversed(serie.index):
        anteriores = serie.loc[:fecha].iloc[:-1].tail(ventana)
        if anteriores.empty:
            break
        if serie[fecha] < umbral_pct * anteriores.mean():
            incompletas.append(fecha)
        else:
            break
    return incompletas

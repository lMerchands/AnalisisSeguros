from __future__ import annotations

"""---------------------------------------------------"""
"""            Análisis Descriptivo de PQRS            """
"""---------------------------------------------------"""
"""

Funciones de agregación pura (sin gráficos) sobre las tablas limpias,
pensadas para poder inspeccionarse directamente como DataFrames desde
un notebook o la consola.
"""

import pandas as pd


def volumen_por_entidad_mes(df_agrupado: pd.DataFrame, ramo: str | None = None) -> pd.DataFrame:
    """Tabla pivote: filas=fecha, columnas=entidad, valores=cantidad_quejas_recibidas.
    Si se pasa ramo, filtra a ese ramo (ej. 'salud'); si no, suma todos los ramos."""
    df = df_agrupado if ramo is None else df_agrupado[df_agrupado["ramo"] == ramo]
    return df.pivot_table(
        index="fecha", columns="entidad", values="cantidad_quejas_recibidas", aggfunc="sum", fill_value=0
    )


def volumen_por_trimestre(df_agrupado: pd.DataFrame, ramo: str | None = None) -> pd.DataFrame:
    """Igual que volumen_por_entidad_mes pero agregado por trimestre calendario."""
    df = df_agrupado if ramo is None else df_agrupado[df_agrupado["ramo"] == ramo]
    df = df.copy()
    df["trimestre"] = pd.PeriodIndex(pd.to_datetime(df["fecha"]), freq="Q").astype(str)
    return df.pivot_table(
        index="trimestre", columns="entidad", values="cantidad_quejas_recibidas", aggfunc="sum", fill_value=0
    )


def distribucion_por_ramo(df_agrupado: pd.DataFrame) -> pd.DataFrame:
    """Total de quejas por entidad y ramo (todo el periodo extraído), ordenado
    de mayor a menor por el total combinado de las entidades."""
    tabla = df_agrupado.pivot_table(
        index="ramo", columns="entidad", values="cantidad_quejas_recibidas", aggfunc="sum", fill_value=0
    )
    return tabla.loc[tabla.sum(axis=1).sort_values(ascending=False).index]


def distribucion_motivo(df_motivo: pd.DataFrame, ramo: str | None = None, entidad: str | None = None, top_n: int = 15) -> pd.DataFrame:
    """Top N motivos de queja, opcionalmente filtrado por ramo y/o entidad."""
    df = df_motivo
    if ramo is not None:
        df = df[df["ramo"] == ramo]
    if entidad is not None:
        df = df[df["entidad"] == entidad]

    tabla = df.pivot_table(
        index="motivo", columns="entidad", values="cantidad_quejas_recibidas", aggfunc="sum", fill_value=0
    )
    tabla["total"] = tabla.sum(axis=1)
    return tabla.sort_values("total", ascending=False).head(top_n)


def resumen_ejecutivo(df_agrupado: pd.DataFrame, ramo: str = "salud") -> pd.DataFrame:
    """Tabla resumen: total de quejas, promedio mensual y participación (%)
    por entidad, para el ramo indicado."""
    df = df_agrupado[df_agrupado["ramo"] == ramo]
    n_meses = df["fecha"].nunique()
    resumen = df.groupby("entidad", as_index=False)["cantidad_quejas_recibidas"].sum()
    resumen = resumen.rename(columns={"cantidad_quejas_recibidas": "total_quejas"})
    resumen["promedio_mensual"] = (resumen["total_quejas"] / n_meses).round(1)
    resumen["participacion_pct"] = (resumen["total_quejas"] / resumen["total_quejas"].sum() * 100).round(1)
    return resumen.sort_values("total_quejas", ascending=False)

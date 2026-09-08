from __future__ import annotations

"""---------------------------------------------------"""
"""   Concentración y Desproporción de Quejas (Sector) """
"""---------------------------------------------------"""
"""

Pregunta central del proyecto: dado que cada aseguradora tiene un
tamaño distinto (medido en pólizas vigentes), ¿qué entidades
concentran una proporción de las quejas del sector mayor a la que les
correspondería por su tamaño?

Esto es deliberadamente distinto de comparar 2-3 marcas puntuales: al
mirar el sector completo (ver config.ENTIDADES), una entidad pequeña
con pocas quejas en términos absolutos puede tener un índice de
desproporción alto (muchas quejas para su tamaño), y una entidad
grande con muchas quejas absolutas puede tener un índice bajo (quejas
proporcionales a su participación de mercado). El índice de
desproporción es lo que separa ambos efectos.

                         participación en quejas del sector
indice_desproporcion =  ------------------------------------
                         participación en pólizas del sector

- indice > 1: la entidad concentra más quejas de las que le
  correspondería por su tamaño (peor de lo esperado).
- indice < 1: concentra menos quejas de las que le correspondería
  (mejor de lo esperado).
- indice ≈ 1: quejas proporcionales a su tamaño.

Todas las funciones reciben la tabla "joined" (quejas + F290, ver
preprocessing/build_dataset.py) y agregan sobre todo el periodo
extraído, no mes a mes, para evitar que meses con muy pocas pólizas
reportadas produzcan índices erráticos (ver limitación de datos en
README.md sobre polizas_total).
"""

import pandas as pd


def _agregado_por_entidad(df_joined: pd.DataFrame, ramo: str) -> pd.DataFrame:
    """Suma quejas y pólizas totales por entidad, para un ramo, sobre todo
    el periodo disponible. Excluye filas sin dato de pólizas totales
    (polizas_total == 0), porque no todas las entidades reportan ese dato
    todos los meses (ver limitación en README.md)."""
    df = df_joined[(df_joined["ramo"] == ramo) & (df_joined["polizas_total"] > 0)]
    return df.groupby("entidad", as_index=False).agg(
        total_quejas=("cantidad_quejas_recibidas", "sum"),
        total_polizas=("polizas_total", "sum"),
    )


def indice_desproporcion(df_joined: pd.DataFrame, ramo: str, min_polizas: int = 0) -> pd.DataFrame:
    """Tabla por entidad con participación de mercado (pólizas), participación
    en quejas y el índice de desproporción entre ambas, para un ramo.

    min_polizas descarta entidades con muy pocas pólizas acumuladas en el
    periodo (evita que una entidad casi sin operación en el ramo, con 1-2
    quejas, aparezca con un índice extremo sin ser representativa).
    """
    agregado = _agregado_por_entidad(df_joined, ramo)
    agregado = agregado[agregado["total_polizas"] >= min_polizas]
    if agregado.empty:
        return agregado.assign(
            participacion_quejas_pct=[], participacion_polizas_pct=[], indice_desproporcion=[]
        )

    total_quejas_sector = agregado["total_quejas"].sum()
    total_polizas_sector = agregado["total_polizas"].sum()

    agregado["participacion_quejas_pct"] = (agregado["total_quejas"] / total_quejas_sector * 100).round(2)
    agregado["participacion_polizas_pct"] = (agregado["total_polizas"] / total_polizas_sector * 100).round(2)
    agregado["indice_desproporcion"] = (
        agregado["participacion_quejas_pct"] / agregado["participacion_polizas_pct"]
    ).round(2)

    return agregado.sort_values("indice_desproporcion", ascending=False).reset_index(drop=True)


def ranking_peores(df_joined: pd.DataFrame, ramo: str, top_n: int = 10, min_polizas: int = 0) -> pd.DataFrame:
    """Top N entidades con mayor índice de desproporción (más quejas de
    las que les corresponde por tamaño) para un ramo."""
    tabla = indice_desproporcion(df_joined, ramo, min_polizas=min_polizas)
    return tabla.head(top_n)


def ranking_mejores(df_joined: pd.DataFrame, ramo: str, top_n: int = 10, min_polizas: int = 0) -> pd.DataFrame:
    """Top N entidades con menor índice de desproporción (menos quejas de
    las que les corresponde por tamaño) para un ramo."""
    tabla = indice_desproporcion(df_joined, ramo, min_polizas=min_polizas)
    return tabla.sort_values("indice_desproporcion", ascending=True).head(top_n)


def tendencia_sector(df_agrupado: pd.DataFrame, ramo: str) -> pd.DataFrame:
    """Serie de tiempo del total de quejas del sector (todas las entidades
    sumadas) para un ramo, útil para ver si el sector completo está
    empeorando/mejorando, más allá de cualquier entidad puntual."""
    df = df_agrupado[df_agrupado["ramo"] == ramo]
    return (
        df.groupby("fecha", as_index=False)["cantidad_quejas_recibidas"]
        .sum()
        .rename(columns={"cantidad_quejas_recibidas": "total_quejas_sector"})
        .sort_values("fecha")
    )


def ramo_con_mayor_crecimiento(df_agrupado: pd.DataFrame, anio_desde: int, anio_hasta: int) -> pd.DataFrame:
    """Compara el total de quejas del sector por ramo entre dos años y
    calcula el crecimiento porcentual, para identificar qué ramo se está
    deteriorando más rápido (no solo qué entidad)."""
    df = df_agrupado.copy()
    df["anio"] = pd.to_datetime(df["fecha"]).dt.year

    tabla = df[df["anio"].isin([anio_desde, anio_hasta])].pivot_table(
        index="ramo", columns="anio", values="cantidad_quejas_recibidas", aggfunc="sum", fill_value=0
    )
    if anio_desde not in tabla.columns or anio_hasta not in tabla.columns:
        return tabla

    tabla["crecimiento_pct"] = (
        (tabla[anio_hasta] - tabla[anio_desde]) / tabla[anio_desde].replace(0, pd.NA) * 100
    ).round(1)
    return tabla.sort_values("crecimiento_pct", ascending=False)

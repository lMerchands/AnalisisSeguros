from __future__ import annotations

"""---------------------------------------------------"""
"""     Construcción de Datasets Limpios de PQRS       """
"""---------------------------------------------------"""
"""

Extiende la lógica de limpieza de pipeline_agrupado.py y
pipeline_motivo.py para dejar dos tablas tidy, reutilizables
tanto para el nivel "agrupado" (sin motivo) como el nivel
"motivo" (con detalle de motivo de la queja):

- quejas: fecha, entidad, ramo, motivo, departamento, municipio, cantidad
- f290:   fecha, entidad, ramo, primas_*, polizas_*

Cada función puede correrse de forma independiente.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd

from extraction.extract_pqrs import extract_f290, extract_quejas
from preprocessing.normalize import (
    build_fecha,
    drop_duplicates_report,
    fechas_incompletas_al_final,
    normalize_entidad,
    normalize_entidad_compuesto,
    normalize_motivo,
    normalize_ramo,
)

# Ramos del F290 que tienen contraparte directa en el dataset de quejas
# (mismos nombres usados en pipeline_agrupado.py).
RAMOS_F290_COMPARABLES = [
    "automoviles",
    "hogar_mes",
    "vida_indivudual_mes",
    "vida_grupo_mes",
    "riesgos_profesionales_mes",
    "salud_mes",
]

SUBCUENTA_RENAME = {
    "CANC Y-O ANULAC PRIMAS EMIT DIR Y COA": "primas_canceladas",
    "POLIZAS CANCELADAS Y-O VENCIDAS": "polizas_canceladas",
    "POLIZAS EMITIDAS NUEVAS": "polizas_emitidas",
    "POLIZAS REHABILITADAS": "polizas_rehabilitadas",
    "PRIMAS ACEPTADAS EN COASEGURO": "primas_coaseguro",
    "PRIMAS EMITIDAS DIRECTAS": "primas_emitidas",
    "TOTAL POLIZAS VIGENTES FINAL EJERCIC": "polizas_total",
}


def clean_quejas(df: pd.DataFrame, nivel: str = "agrupado") -> pd.DataFrame:
    """Limpia el dataset crudo de quejas (xyy7-rn7p) a una tabla tidy.

    nivel controla la granularidad de la tabla resultante:
    - "agrupado": fecha, entidad, ramo (nacional). Es la granularidad que
      se une con F290 para calcular tasas por póliza, y debe quedar con
      una sola fila por combinación fecha/entidad/ramo.
    - "motivo": agrega también el motivo de la queja (detalle por causa).
    - "geografico": agrega también departamento y municipio (detalle geográfico).
    """
    if nivel not in {"agrupado", "motivo", "geografico"}:
        raise ValueError("nivel debe ser 'agrupado', 'motivo' o 'geografico'")

    df = df.copy()

    # Descarta duplicados exactos de fila cruda (mismas columnas originales,
    # incluida instancia_recepcion) antes de reducir granularidad: esto sí
    # es un duplicado real y no debe sumarse dos veces.
    columnas_crudas = [c for c in df.columns if c != "cantidad_quejas_recibidas"]
    df = drop_duplicates_report(df, subset=columnas_crudas)

    df = normalize_entidad(df)
    df["fecha"] = build_fecha(df["a_o_creacion"], df["mes_creacion"])
    df["ramo"] = normalize_ramo(df["producto"])
    df["motivo"] = normalize_motivo(df["motivo"])
    df["departamento"] = df["departamento"].fillna("No informado")
    df["municipio"] = df["municipio"].fillna("No informado")
    df["cantidad_quejas_recibidas"] = df["cantidad_quejas_recibidas"].astype(int)

    # Quita SOAT: no tiene contraparte de pólizas en RAMOS_F290_COMPARABLES
    # (ver abajo), así que no se puede calcular una tasa por póliza para ese
    # ramo con el mapeo actual del F290. Podría añadirse como ramo aparte en
    # el futuro si se mapea su subcuenta correspondiente.
    df = df[df["producto"] != "Seguro Obligatorio de Accidentes de Tránsito (SOAT)"]

    # Quita meses incompletos al final de la serie (rezago de publicación de
    # la fuente: el mes más reciente llega con muy pocas filas y se termina
    # de completar en una corrida futura). Se calcula sobre el total del
    # sector completo (todas las entidades/ramos), no por combinación
    # puntual, para no confundir "esta entidad no tuvo quejas este mes" (dato
    # real) con "el mes todavía no se ha terminado de publicar".
    totales_por_fecha = df.groupby("fecha")["cantidad_quejas_recibidas"].sum()
    fechas_incompletas = fechas_incompletas_al_final(totales_por_fecha)
    if fechas_incompletas:
        print(f"Excluyendo meses incompletos al final de la serie de quejas (reporte parcial): {sorted(fechas_incompletas)}")
        df = df[~df["fecha"].isin(fechas_incompletas)]

    # Agrupa (sumando cantidad_quejas_recibidas) a la granularidad pedida. Es
    # necesario sumar, no solo seleccionar columnas, porque varias filas crudas
    # (ej. con distinta instancia_recepcion, o distinto motivo/geografía si se
    # piden a un nivel más agregado) comparten la misma combinación de columnas
    # tidy y sus conteos deben acumularse, nunca descartarse.
    columnas_grupo = ["fecha", "entidad", "ramo"]
    if nivel == "motivo":
        columnas_grupo.append("motivo")
    elif nivel == "geografico":
        columnas_grupo += ["departamento", "municipio"]

    df = df.groupby(columnas_grupo, as_index=False)["cantidad_quejas_recibidas"].sum()
    return df


def clean_f290(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia el dataset crudo de Formato 290 (e967-4a8r) a una tabla tidy
    de primas y pólizas por entidad/ramo/mes, igual que pipeline_agrupado.py."""
    df = df.copy()
    df["fecha"] = build_fecha(df["a_o"], df["mes"])

    df = df[
        ((df["subcuenta"].isin(["5", "10", "15"])) & (df["unidad_de_captura"] == "1"))
        | ((df["subcuenta"].isin(["10", "15", "20", "999"])) & (df["unidad_de_captura"] == "20"))
    ]

    df = normalize_entidad_compuesto(df)

    df = df[["fecha", "entidad", "nombre_subcuenta", *RAMOS_F290_COMPARABLES]].melt(
        id_vars=["fecha", "entidad", "nombre_subcuenta"],
        value_vars=RAMOS_F290_COMPARABLES,
        var_name="ramo",
        value_name="valor",
    ).pivot_table(
        index=["fecha", "entidad", "ramo"],
        columns="nombre_subcuenta",
        values="valor",
        aggfunc="first",
    ).reset_index().rename(columns=SUBCUENTA_RENAME)

    df["ramo"] = normalize_ramo(df["ramo"].str.replace("_mes", "", regex=False).replace({
        "vida_indivudual": "vida_individual",
        "riesgos_profesionales": "arl",
    }))

    # Garantiza que las 7 columnas de primas/pólizas existan siempre, incluso si
    # alguna subcuenta no aparece para el rango de fechas/entidades consultado.
    columnas_num = list(SUBCUENTA_RENAME.values())
    for col in columnas_num:
        if col not in df.columns:
            df[col] = 0
    # Se pasa por to_numeric antes de redondear a entero: al ampliar el
    # alcance a las 38 entidades del sector completo aparecen subcuentas con
    # valores decimales (ej. primas con centavos, "3221686840.86"), que
    # rompían un astype("int64") directo pensado para el alcance original
    # de 2-3 entidades (donde por coincidencia todos los valores eran enteros).
    df[columnas_num] = (
        df[columnas_num]
        .apply(lambda col: pd.to_numeric(col, errors="coerce"))
        .fillna(0)
        .round()
        .astype("int64")
    )

    columnas = ["fecha", "entidad", "ramo", *columnas_num]
    return df[columnas]


def build_joined(df_quejas_sin_motivo: pd.DataFrame, df_f290: pd.DataFrame) -> pd.DataFrame:
    """Une quejas (agregadas, sin motivo) con primas/pólizas para poder
    calcular tasas normalizadas (ej. quejas por cada 1000 pólizas vigentes).

    El merge es "left" desde F290: cuando una entidad/ramo/mes existe en
    F290 pero no tiene fila en quejas, se asume 0 quejas (dato real: esa
    entidad no fue reportada con quejas ese mes). Pero eso solo es válido
    si el dataset de quejas sí tiene datos para ese mes en general — si el
    mes completo no aparece en df_quejas_sin_motivo (hueco de reporte de
    la fuente, no "cero quejas"), rellenar con 0 inventaría que las 38
    entidades y los 6 ramos tuvieron 0 quejas ese mes, lo cual no es
    cierto: simplemente no hay dato. Por eso esos meses se excluyen del
    join en vez de rellenarse (visto en la práctica: 2026-02 tiene F290
    completo pero cero filas en el dataset de quejas)."""
    meses_con_dato_quejas = set(df_quejas_sin_motivo["fecha"].unique())
    meses_excluidos = sorted(set(df_f290["fecha"].unique()) - meses_con_dato_quejas)
    if meses_excluidos:
        print(f"Excluyendo del join meses sin ningún dato de quejas en la fuente: {meses_excluidos}")
    df_f290 = df_f290[df_f290["fecha"].isin(meses_con_dato_quejas)]

    df = df_f290.merge(
        df_quejas_sin_motivo, on=["fecha", "entidad", "ramo"], how="left"
    )
    df["cantidad_quejas_recibidas"] = df["cantidad_quejas_recibidas"].fillna(0).astype(int)
    df["quejas_por_1000_polizas"] = (
        (df["cantidad_quejas_recibidas"] / df["polizas_total"].replace(0, pd.NA)) * 1000
    )
    return df


def build_full_dataset(anio_desde: int | None = None) -> dict[str, pd.DataFrame]:
    """Corre extracción + limpieza completa. Devuelve un diccionario con
    las tablas listas para almacenar/analizar."""
    print("Extrayendo quejas...")
    df_quejas_raw = extract_quejas(anio_desde=anio_desde)
    print("Extrayendo F290...")
    df_f290_raw = extract_f290(anio_desde=anio_desde)

    print("Limpiando quejas (agrupado)...")
    df_quejas_agrupado = clean_quejas(df_quejas_raw, nivel="agrupado")
    print("Limpiando quejas (con motivo)...")
    df_quejas_motivo = clean_quejas(df_quejas_raw, nivel="motivo")
    print("Limpiando quejas (geográfico)...")
    df_quejas_geografico = clean_quejas(df_quejas_raw, nivel="geografico")
    print("Limpiando F290...")
    df_f290 = clean_f290(df_f290_raw)
    print("Uniendo quejas + F290...")
    df_joined = build_joined(df_quejas_agrupado, df_f290)

    return {
        "quejas_agrupado": df_quejas_agrupado,
        "quejas_motivo": df_quejas_motivo,
        "quejas_geografico": df_quejas_geografico,
        "f290": df_f290,
        "joined": df_joined,
    }


if __name__ == "__main__":
    tablas = build_full_dataset()
    for nombre, df in tablas.items():
        print(f"{nombre}: {df.shape}")

from __future__ import annotations  # permite "int | None" en Python 3.9

"""---------------------------------------------------"""
"""     Extracción Parametrizable de PQRS y F290       """
"""---------------------------------------------------"""
"""

Extiende load_dataset.py (load_full_socrata_dataset, soql_in_str) para
traer, de forma reproducible, los datos de quejas y Formato 290 de las
entidades definidas en config.py.

Cada función puede llamarse de forma independiente (extracción por
etapa) y acepta filtros adicionales de año para extracciones
incrementales o acotadas.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config import (
    DATASET_F290,
    DATASET_QUEJAS,
    PARES_TIPO_CODIGO,
    TIPOS_ENTIDAD,
)
from load_dataset import load_full_socrata_dataset, soql_in_str


def extract_quejas(anio_desde: int | None = None, app_token: str | None = None) -> pd.DataFrame:
    """Extrae quejas (dataset xyy7-rn7p) para las entidades en alcance.

    anio_desde: si se pasa, filtra desde ese año en adelante (extracción incremental).

    El alcance es "todo el sector" (tipo_entidad in ('13','14'): seguros
    generales y de vida), no una lista fija de códigos de entidad. Esto
    simplifica el filtro frente a una versión anterior que solo traía
    2-3 aseguradoras elegidas a mano (filtradas por pares exactos
    tipo/código); ahora config.ENTIDADES sirve únicamente para nombrar
    y agrupar entidades en normalize.py, no para filtrar la extracción.
    """
    where = f"tipo_entidad IN {soql_in_str(TIPOS_ENTIDAD)}"
    if anio_desde is not None:
        where += f" AND a_o_creacion >= '{anio_desde}'"

    df = load_full_socrata_dataset(
        dataset_id=DATASET_QUEJAS,
        where=where,
        app_token=app_token,
        chunk_size=50_000,
    )
    return df


def extract_f290(anio_desde: int | None = None, app_token: str | None = None) -> pd.DataFrame:
    """Extrae Formato 290 (dataset e967-4a8r) para las entidades en alcance.

    En este dataset la entidad se identifica con "codigo_entidad" en
    formato compuesto "tipo-codigo" (ej. "13-27"), a diferencia del
    dataset de quejas que trae tipo y código en columnas separadas y
    puede filtrarse con un simple "tipo_entidad IN ('13','14')". Aquí
    no hay una columna de tipo separada para filtrar por sector
    completo, así que se sigue usando la lista explícita de códigos
    compuestos de config.ENTIDADES (que sí cubre las 38 entidades del
    sector, no una lista corta de competidores).
    Se filtra también por unidad_de_captura y subcuenta relevantes para
    pólizas/primas de todos los ramos, igual que en pipeline_agrupado.py.
    """
    codigos_compuestos = [f"{tipo}-{codigo}" for tipo, codigo in PARES_TIPO_CODIGO]
    where = (
        f"codigo_entidad IN {soql_in_str(codigos_compuestos)} "
        f"AND unidad_de_captura IN {soql_in_str(('1', '20'))} "
        f"AND subcuenta IN {soql_in_str(('5', '10', '15', '20', '999'))}"
    )
    if anio_desde is not None:
        where += f" AND a_o >= '{anio_desde}'"

    df = load_full_socrata_dataset(
        dataset_id=DATASET_F290,
        where=where,
        app_token=app_token,
        chunk_size=50_000,
    )
    return df


if __name__ == "__main__":
    df_quejas = extract_quejas()
    df_f290 = extract_f290()
    print(f"Quejas extraídas: {df_quejas.shape}")
    print(f"F290 extraído: {df_f290.shape}")

from __future__ import annotations  # permite "str | None" en Python 3.9

"""---------------------------------------------------"""
"""           Funciones Auxiliares Pipeline           """
"""---------------------------------------------------"""
"""

Este archivo contiene las funciones auxiliares para el
Pipeline de Extracción y Limpieza de datos.

Creado por: Juan Merchán - Practicante.
"""

# Librerías
import os
import time

import pandas as pd
from dotenv import load_dotenv
from sodapy import Socrata

load_dotenv()  # Carga variables de entorno desde .env si existe

# Función de extracción de datos de Datos Abiertos
def load_full_socrata_dataset(
    dataset_id: str,
    domain: str = "www.datos.gov.co",
    app_token: str | None = None,
    username: str | None = None,
    password: str | None = None,
    select: str | None = None,
    where: str | None = None,
    chunk_size: int = 50_000,   # Socrata max is usually 50k per request
    order_by: str | None = None, # e.g. ":id" or a stable column name
    max_retries: int = 3,
    retry_backoff_seconds: float = 2.0,
) -> pd.DataFrame:
    # Si no se pasa credencial explícita, se usa la de las variables de entorno (.env)
    app_token = app_token or os.getenv("SOCRATA_APP_TOKEN")
    username = username or os.getenv("SOCRATA_USERNAME")
    password = password or os.getenv("SOCRATA_PASSWORD")

    client = Socrata(domain, app_token, username=username, password=password, timeout=60)

    all_rows = []
    offset = 0

    while True:
        params = {"select": select, "where": where,"limit": chunk_size, "offset": offset}
        if order_by:
            params["order"] = order_by

        # Reintentos con backoff exponencial ante fallos transitorios de red/API
        for attempt in range(1, max_retries + 1):
            try:
                rows = client.get(dataset_id, **params)
                break
            except Exception:
                if attempt == max_retries:
                    client.close()
                    raise
                time.sleep(retry_backoff_seconds * attempt)

        if not rows:
            break

        all_rows.append(pd.DataFrame.from_records(rows))
        offset += chunk_size

    if not all_rows:
        client.close()
        return pd.DataFrame()

    df = pd.concat(all_rows, ignore_index=True)

    # Optional: basic type cleanup (Socrata returns strings for many fields)
    # df = df.convert_dtypes()

    client.close()
    return df

# Auxiliar para extraer datos "más bonito"
def soql_in_str(values):
    return "(" + ",".join(f"'{v}'" for v in values) + ")"
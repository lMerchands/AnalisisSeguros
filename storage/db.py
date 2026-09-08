from __future__ import annotations

"""---------------------------------------------------"""
"""      Almacenamiento: SQLite + Parquet/CSV          """
"""---------------------------------------------------"""
"""

Guarda las tablas limpias en una base SQLite local (para consultas SQL
ad-hoc) y además exporta cada tabla a Parquet y CSV (para consumo desde
otras herramientas o notebooks), sin depender de un motor de base de
datos externo.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "pqrs_seguros.db"


def save_tables(tablas: dict[str, pd.DataFrame], db_path: Path = DB_PATH) -> None:
    """Guarda cada DataFrame como tabla SQLite (reemplazando su contenido)
    y como archivo Parquet + CSV en data/."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        for nombre, df in tablas.items():
            df.to_sql(nombre, conn, if_exists="replace", index=False)
            print(f"Tabla '{nombre}' guardada en SQLite ({len(df)} filas)")

    for nombre, df in tablas.items():
        df.to_parquet(DATA_DIR / f"{nombre}.parquet", index=False)
        df.to_csv(DATA_DIR / f"{nombre}.csv", index=False)

    print(f"Base de datos SQLite: {db_path}")
    print(f"Parquet/CSV exportados en: {DATA_DIR}")


def load_table(nombre: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    """Lee una tabla desde la base SQLite local."""
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(f"SELECT * FROM {nombre}", conn)

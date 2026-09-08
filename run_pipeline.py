from __future__ import annotations

"""---------------------------------------------------"""
"""      Orquestador del Pipeline PQRS Seguros          """
"""---------------------------------------------------"""
"""

Punto de entrada único para correr el pipeline completo o por etapas
independientes:

    python run_pipeline.py --stage all
    python run_pipeline.py --stage extract-clean
    python run_pipeline.py --stage store
    python run_pipeline.py --stage analyze

--anio-desde limita la extracción (ej. --anio-desde 2023) para correr
más rápido o hacer una actualización incremental acotada. Sin este
parámetro se trae el histórico completo disponible en el dataset.
"""

import argparse

from analysis.comparativo import generar_reporte_comparativo
from analysis.concentracion import ranking_peores
from analysis.descriptive import distribucion_por_ramo, resumen_ejecutivo
from config import RAMO_EJEMPLO
from preprocessing.build_dataset import build_full_dataset
from storage.db import load_table, save_tables


def run(stage: str, anio_desde: int | None, ramo: str) -> None:
    if stage in ("all", "extract-clean", "store"):
        tablas = build_full_dataset(anio_desde=anio_desde)

    if stage == "extract-clean":
        for nombre, df in tablas.items():
            print(f"{nombre}: {df.shape}")

    if stage in ("all", "store"):
        save_tables(tablas)

    if stage == "analyze":
        tablas = {
            "quejas_agrupado": load_table("quejas_agrupado"),
            "quejas_motivo": load_table("quejas_motivo"),
            "joined": load_table("joined"),
        }

    if stage in ("all", "analyze"):
        print(f"\n--- Resumen ejecutivo (ramo {ramo}) ---")
        print(resumen_ejecutivo(tablas["quejas_agrupado"], ramo=ramo).to_string(index=False))

        print(f"\n--- Índice de desproporción quejas/pólizas (ramo {ramo}, top 10) ---")
        print(ranking_peores(tablas["joined"], ramo=ramo, top_n=10).to_string(index=False))

        print("\n--- Quejas totales por ramo (todas las entidades) ---")
        print(distribucion_por_ramo(tablas["quejas_agrupado"]).sum(axis=1).to_string())

        generar_reporte_comparativo(tablas, ramo=ramo)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline de PQRS del sector asegurador colombiano (generales + vida, ~38 entidades vigiladas)"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "extract-clean", "store", "analyze"],
        default="all",
        help="Etapa a ejecutar. 'analyze' reutiliza lo que ya esté guardado en SQLite.",
    )
    parser.add_argument(
        "--anio-desde",
        type=int,
        default=None,
        help="Año desde el cual extraer (ej. 2023). Si no se pasa, trae todo el histórico.",
    )
    parser.add_argument(
        "--ramo",
        default=RAMO_EJEMPLO,
        help=f"Ramo a analizar (ver config.RAMOS_DISPONIBLES). Por defecto: {RAMO_EJEMPLO}.",
    )
    args = parser.parse_args()
    run(stage=args.stage, anio_desde=args.anio_desde, ramo=args.ramo)

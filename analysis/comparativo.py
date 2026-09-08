from __future__ import annotations

"""------------------------------------------------------"""
"""      Visualizaciones: Tendencia y Concentración      """
"""------------------------------------------------------"""
"""

Genera las visualizaciones clave del análisis y las guarda como PNG en
analysis/output/. Cada función puede llamarse de forma independiente
pasándole las tablas ya limpias (ver preprocessing).

plot_tendencia_salud y plot_motivos_top vienen de la primera versión
del proyecto (comparación de 2-3 entidades puntuales) y siguen siendo
útiles para "zoom in" en una entidad o un grupo pequeño que se le pase
explícitamente. Para el sector completo (38 entidades, ver
config.ENTIDADES) un gráfico de líneas por entidad es ilegible, así
que el análisis principal usa plot_ranking_desproporcion en su lugar
(barras horizontales top N, ver analysis/concentracion.py).
"""

import sys
import textwrap
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from analysis.concentracion import ranking_peores, tendencia_sector
from analysis.descriptive import distribucion_motivo, volumen_por_entidad_mes
from config import COLOR_POR_RAMO, COLOR_RAMO_DEFAULT

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _color_ramo(ramo: str) -> str:
    """Color consistente por ramo en todas las gráficas del proyecto
    (ver config.COLOR_POR_RAMO). Cae a COLOR_RAMO_DEFAULT si el ramo no
    tiene color asignado."""
    return COLOR_POR_RAMO.get(ramo, COLOR_RAMO_DEFAULT)


def _wrap_labels(labels, width: int = 28) -> list[str]:
    """Envuelve etiquetas largas en varias líneas, cortando en espacios
    (con textwrap, no a la mitad de una palabra como un slice manual)."""
    return [textwrap.fill(str(label), width=width) for label in labels]


def plot_tendencia_sector(df_agrupado: pd.DataFrame, ramo: str = "salud") -> Path:
    """Serie de tiempo mensual del total de quejas del sector (todas las
    entidades sumadas) en el ramo indicado. Es la vista de "salud
    regulatoria" del ramo, independiente de cualquier entidad puntual."""
    tabla = tendencia_sector(df_agrupado, ramo=ramo).set_index("fecha")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    tabla.plot(ax=ax, marker="o", legend=False, color=_color_ramo(ramo))
    ax.set_title(f"Total de quejas mensuales del sector - ramo {ramo}")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Cantidad de quejas (todas las entidades)")
    fig.tight_layout()

    ruta = OUTPUT_DIR / f"tendencia_sector_{ramo}.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def plot_tendencia_salud(df_agrupado: pd.DataFrame, ramo: str = "salud", entidades: list[str] | None = None) -> Path:
    """Serie de tiempo mensual de quejas en el ramo indicado, por entidad.

    Pensada para "zoom in" en un grupo pequeño de entidades (pasar
    `entidades`); con las ~38 del sector completo el gráfico de líneas
    deja de ser legible (usar plot_ranking_desproporcion o
    plot_tendencia_sector en su lugar para la vista de sector completo)."""
    tabla = volumen_por_entidad_mes(df_agrupado, ramo=ramo)
    if entidades is not None:
        tabla = tabla[[c for c in entidades if c in tabla.columns]]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    tabla.plot(ax=ax, marker="o")
    ax.set_title(f"Quejas mensuales - ramo {ramo}")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Cantidad de quejas")
    ax.legend(title="Entidad")
    fig.tight_layout()

    ruta = OUTPUT_DIR / f"tendencia_{ramo}.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def plot_motivos_top(df_motivo: pd.DataFrame, ramo: str = "salud", entidad: str | None = None, top_n: int = 10) -> Path:
    """Barras horizontales con los motivos de queja más frecuentes en el
    ramo indicado, con el valor anotado al final de cada barra (en vez de
    un eje x con ticks) y color según el ramo (ver config.COLOR_POR_RAMO).

    Sin `entidad`, agrega el sector completo en una sola barra por motivo
    (vista por defecto: qué está reclamando la gente en este ramo, sin
    importar la entidad). Pasar `entidad` para el desglose por entidad de
    una marca puntual (zoom-in), útil solo con pocas entidades a la vez."""
    tabla = distribucion_motivo(df_motivo, ramo=ramo, entidad=entidad, top_n=top_n)
    tabla = tabla[["total"]] if entidad is None else tabla.drop(columns="total")
    columna_valor = tabla.columns[0]
    df_plot = tabla.reset_index().rename(columns={columna_valor: "cantidad"})
    color = _color_ramo(ramo)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8 * 1.6, 8))
    sns.barplot(data=df_plot, x="cantidad", y="motivo", color=color, ax=ax)

    for bar in ax.patches:
        ancho = bar.get_width()
        y = bar.get_y() + bar.get_height() / 2
        ax.annotate(
            f"{ancho:,.0f}",
            xy=(ancho, y),
            xytext=(12, 0),
            textcoords="offset points",
            va="center", ha="left",
            fontsize=12,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor=color, linewidth=0.8, alpha=0.9),
        )

    ax.set_yticks(range(len(df_plot)))
    ax.set_yticklabels(_wrap_labels(df_plot["motivo"], width=28))

    titulo_entidad = f" - {entidad}" if entidad else " - sector completo"
    ax.set_title(f"Motivos de queja más frecuentes - ramo {ramo}{titulo_entidad}", fontsize=18, loc="left", pad=10)
    ax.set_xlabel("Cantidad de quejas", fontsize=12)
    ax.set_ylabel("")
    ax.set_xticks([])
    ax.set_xlim(0, df_plot["cantidad"].max() * 1.15)  # espacio a la derecha para las anotaciones
    sns.despine(ax=ax, left=True, bottom=True)
    fig.tight_layout()

    sufijo = f"_{entidad}" if entidad else ""
    ruta = OUTPUT_DIR / f"motivos_top_{ramo}{sufijo}.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def plot_quejas_por_poliza(df_joined: pd.DataFrame, ramo: str = "salud", entidades: list[str] | None = None) -> Path | None:
    """Quejas por cada 1000 pólizas vigentes, por entidad, para los meses en
    que el dato de pólizas totales está disponible en el F290 (no todos los
    meses lo reportan).

    Pensada para "zoom in" en un grupo pequeño (pasar `entidades`); con las
    ~38 del sector completo, usar plot_ranking_desproporcion en su lugar."""
    df = df_joined[(df_joined["ramo"] == ramo) & (df_joined["quejas_por_1000_polizas"].notna())]
    if entidades is not None:
        df = df[df["entidad"].isin(entidades)]
    if df.empty:
        print(f"Sin datos de pólizas totales disponibles para el ramo {ramo}; se omite el gráfico.")
        return None

    tabla = df.pivot_table(index="fecha", columns="entidad", values="quejas_por_1000_polizas")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    tabla.plot(ax=ax, marker="o")
    ax.set_title(f"Quejas por cada 1000 pólizas vigentes - ramo {ramo}")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Quejas / 1000 pólizas")
    ax.legend(title="Entidad")
    fig.tight_layout()

    ruta = OUTPUT_DIR / f"quejas_por_poliza_{ramo}.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def plot_ranking_desproporcion(df_joined: pd.DataFrame, ramo: str, top_n: int = 15, min_polizas: int = 0) -> Path | None:
    """Barras horizontales con las entidades que más concentran quejas
    respecto a su tamaño (índice de desproporción, ver
    analysis/concentracion.py), para un ramo. Esta es la visualización
    principal del proyecto: reemplaza comparar 2-3 marcas por un
    ranking del sector completo."""
    tabla = ranking_peores(df_joined, ramo=ramo, top_n=top_n, min_polizas=min_polizas)
    if tabla.empty:
        print(f"Sin datos suficientes de pólizas totales para el ramo {ramo}; se omite el gráfico.")
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, max(4, 0.4 * len(tabla))))
    ax.barh(tabla["entidad"], tabla["indice_desproporcion"], color=_color_ramo(ramo))
    ax.axvline(1.0, color="black", linestyle="--", linewidth=1, label="Proporcional al tamaño (índice = 1)")
    ax.set_title(f"Índice de desproporción de quejas - ramo {ramo}\n(top {top_n} más desproporcionadas)")
    ax.set_xlabel("Índice de desproporción (participación en quejas / participación en pólizas)")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()

    ruta = OUTPUT_DIR / f"ranking_desproporcion_{ramo}.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    return ruta


def generar_reporte_comparativo(tablas: dict[str, pd.DataFrame], ramo: str = "salud", entidades_zoom: list[str] | None = None) -> list[Path]:
    """Corre las visualizaciones principales del análisis sectorial (tendencia
    agregada + motivos agregados + ranking de desproporción) y devuelve las
    rutas generadas. Si se pasa `entidades_zoom` (2-5 nombres de config.ENTIDADES),
    añade también el desglose por esas entidades puntuales."""
    rutas = [
        plot_tendencia_sector(tablas["quejas_agrupado"], ramo=ramo),
        plot_motivos_top(tablas["quejas_motivo"], ramo=ramo),
    ]
    ruta_ranking = plot_ranking_desproporcion(tablas["joined"], ramo=ramo)
    if ruta_ranking:
        rutas.append(ruta_ranking)

    if entidades_zoom:
        rutas.append(plot_tendencia_salud(tablas["quejas_agrupado"], ramo=ramo, entidades=entidades_zoom))
        ruta_poliza = plot_quejas_por_poliza(tablas["joined"], ramo=ramo, entidades=entidades_zoom)
        if ruta_poliza:
            rutas.append(ruta_poliza)

    for ruta in rutas:
        print(f"Gráfico guardado: {ruta}")
    return rutas

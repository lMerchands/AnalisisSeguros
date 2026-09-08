from __future__ import annotations

"""----------------------------------------------------"""
"""   Reporte HTML estático (publicable en GitHub)     """
"""----------------------------------------------------"""
"""

Genera un único archivo HTML autocontenido (gráficos embebidos como
base64, sin dependencias externas) con la "Radiografía del sector
asegurador colombiano": tendencia sectorial, motivos de queja y el
índice de desproporción quejas/pólizas, para cada ramo con datos
comparables en el F290.

Pensado para publicarse con GitHub Pages: escribe el resultado en
docs/index.html. Para activarlo: Settings > Pages > Deploy from a
branch > main > /docs.

Requiere que ya se haya corrido `python run_pipeline.py --stage store`
al menos una vez (lee de data/pqrs_seguros.db).

Uso:
    python build_report.py
    python build_report.py --anio-desde 2023
"""

import argparse
import base64
from datetime import date
from pathlib import Path

import pandas as pd

from analysis.comparativo import plot_motivos_top, plot_ranking_desproporcion, plot_tendencia_sector
from analysis.concentracion import indice_desproporcion, ranking_mejores, ranking_peores, tendencia_sector
from analysis.descriptive import resumen_ejecutivo
from config import ENTIDADES, RAMOS_DISPONIBLES
from preprocessing.normalize import RAMO_RENAME
from storage.db import load_table

DOCS_DIR = Path(__file__).resolve().parent / "docs"

# Ramos con dato de pólizas comparable en el F290 (ver preprocessing/build_dataset.py:
# RAMOS_F290_COMPARABLES), en el orden en que se muestran en el reporte.
RAMOS_REPORTE = ["salud", "automoviles", "hogar", "vida_individual", "vida_grupo", "arl"]

NOMBRE_RAMO_LEGIBLE = {v: k for k, v in RAMO_RENAME.items() if v in RAMOS_REPORTE}
NOMBRE_RAMO_LEGIBLE.setdefault("arl", "Seguro de riesgos laborales")


def _img_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _tabla_html(df: pd.DataFrame, columnas: dict[str, str], index: bool = False) -> str:
    """Renderiza un DataFrame a una tabla HTML simple, renombrando y
    seleccionando solo las columnas indicadas (en orden). Las columnas
    numéricas de tipo float se formatean siempre a 2 decimales (pandas
    recorta ceros de cola por defecto, ej. 32.0 en vez de 32.00)."""
    df = df[list(columnas.keys())].rename(columns=columnas)
    formatters = {
        col: (lambda v: f"{v:.2f}") for col, dtype in df.dtypes.items() if pd.api.types.is_float_dtype(dtype)
    }
    return df.to_html(index=index, border=0, classes="tabla", justify="left", formatters=formatters)


def _seccion_ramo(tablas: dict[str, pd.DataFrame], ramo: str) -> str:
    df_agrupado, df_motivo, df_joined = tablas["quejas_agrupado"], tablas["quejas_motivo"], tablas["joined"]
    nombre_legible = NOMBRE_RAMO_LEGIBLE.get(ramo, ramo)

    resumen = resumen_ejecutivo(df_agrupado, ramo=ramo)
    tendencia = tendencia_sector(df_agrupado, ramo=ramo)
    desprop = indice_desproporcion(df_joined, ramo=ramo, min_polizas=1000)
    peores = ranking_peores(df_joined, ramo=ramo, top_n=5, min_polizas=1000)
    mejores = ranking_mejores(df_joined, ramo=ramo, top_n=5, min_polizas=1000)

    if resumen.empty or tendencia.empty:
        return f'<section class="ramo"><h2 id="{ramo}">{nombre_legible}</h2><p>Sin datos suficientes para este ramo en el periodo extraído.</p></section>'

    total_quejas = int(resumen["total_quejas"].sum())
    n_entidades_con_quejas = resumen["entidad"].nunique()
    top_motivo = (
        df_motivo[df_motivo["ramo"] == ramo]
        .groupby("motivo")["cantidad_quejas_recibidas"].sum()
        .sort_values(ascending=False)
        .head(1)
    )
    top_motivo_txt = top_motivo.index[0] if not top_motivo.empty else "sin dato"

    tendencia_ini, tendencia_fin = tendencia["total_quejas_sector"].iloc[0], tendencia["total_quejas_sector"].iloc[-1]
    direccion = "subió" if tendencia_fin > tendencia_ini else "bajó" if tendencia_fin < tendencia_ini else "se mantuvo estable"

    ruta_tendencia = plot_tendencia_sector(df_agrupado, ramo=ramo)
    ruta_motivos = plot_motivos_top(df_motivo, ramo=ramo)
    ruta_ranking = plot_ranking_desproporcion(df_joined, ramo=ramo, top_n=15, min_polizas=1000)

    imgs_html = f'<img src="data:image/png;base64,{_img_b64(ruta_tendencia)}" alt="Tendencia sectorial {nombre_legible}">'
    imgs_html += f'<img src="data:image/png;base64,{_img_b64(ruta_motivos)}" alt="Motivos de queja {nombre_legible}">'
    if ruta_ranking:
        imgs_html += f'<img src="data:image/png;base64,{_img_b64(ruta_ranking)}" alt="Índice de desproporción {nombre_legible}">'

    peor_txt = mejor_txt = "sin datos suficientes de pólizas para este ramo"
    if not peores.empty:
        fila = peores.iloc[0]
        peor_txt = f'<strong>{fila["entidad"]}</strong> (índice {fila["indice_desproporcion"]:.2f}×: concentra {fila["participacion_quejas_pct"]:.2f}% de las quejas con solo {fila["participacion_polizas_pct"]:.2f}% de las pólizas)'
    if not mejores.empty:
        fila = mejores.iloc[0]
        mejor_txt = f'<strong>{fila["entidad"]}</strong> (índice {fila["indice_desproporcion"]:.2f}×)'

    tabla_peores = _tabla_html(
        peores,
        {"entidad": "Entidad", "participacion_quejas_pct": "% quejas", "participacion_polizas_pct": "% pólizas", "indice_desproporcion": "Índice"},
    ) if not peores.empty else "<p>Sin datos suficientes.</p>"

    return f"""
    <section class="ramo">
      <h2 id="{ramo}">{nombre_legible}</h2>
      <p class="narrativa">
        En el periodo analizado, el sector registró <strong>{total_quejas:,}</strong> quejas en este ramo
        entre <strong>{n_entidades_con_quejas}</strong> entidades, y el volumen mensual del sector
        {direccion} respecto al inicio del periodo. El motivo más frecuente fue
        <em>&ldquo;{top_motivo_txt}&rdquo;</em>. La entidad con mayor índice de desproporción
        (más quejas de las que le corresponden por su tamaño) fue {peor_txt}; la de menor
        desproporción fue {mejor_txt}.
      </p>
      <div class="graficos">{imgs_html}</div>
      <h3>Top 5 entidades con mayor desproporción quejas/pólizas</h3>
      {tabla_peores}
    </section>
    """


CSS = """
:root {
  --bg: #f7f7f5; --panel: #ffffff; --text: #1f2328; --muted: #57606a;
  --accent: #7a3b3b; --border: #e3e1dc; --warn-bg: #fff3e0; --warn-border: #f0b429;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.55; }
header.hero { padding: 3rem 1.5rem 2rem; text-align: center; background: var(--panel); border-bottom: 1px solid var(--border); }
header.hero h1 { margin: 0 0 .5rem; font-size: 1.9rem; }
header.hero p.subtitulo { color: var(--muted); max-width: 46rem; margin: 0 auto; }
main { max-width: 56rem; margin: 0 auto; padding: 1.5rem; }
.disclaimer { background: var(--warn-bg); border: 1px solid var(--warn-border); border-radius: 8px;
  padding: 1rem 1.25rem; margin: 1.5rem 0; font-size: .95rem; }
.metodologia { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem 1.5rem; margin: 1.5rem 0; }
.metodologia summary { cursor: pointer; font-weight: 600; }
nav.indice { display: flex; flex-wrap: wrap; gap: .5rem; margin: 1.5rem 0; }
nav.indice a { padding: .35rem .8rem; border: 1px solid var(--border); border-radius: 999px;
  text-decoration: none; color: var(--text); background: var(--panel); font-size: .9rem; }
nav.indice a:hover { border-color: var(--accent); color: var(--accent); }
section.ramo { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.5rem; margin: 1.5rem 0; }
section.ramo h2 { margin-top: 0; }
.narrativa { color: var(--text); }
.graficos { display: flex; flex-direction: column; gap: 1rem; margin: 1rem 0; }
.graficos img { max-width: 100%; border: 1px solid var(--border); border-radius: 6px; }
table.tabla { border-collapse: collapse; width: 100%; font-size: .9rem; margin-top: .5rem; }
table.tabla th, table.tabla td { border-bottom: 1px solid var(--border); padding: .4rem .6rem; text-align: left; }
table.tabla th { color: var(--muted); font-weight: 600; }
footer { text-align: center; color: var(--muted); font-size: .85rem; padding: 2rem 1rem 3rem; }
footer a { color: var(--accent); }
"""


def build(anio_desde: int | None) -> Path:
    tablas = {
        "quejas_agrupado": load_table("quejas_agrupado"),
        "quejas_motivo": load_table("quejas_motivo"),
        "joined": load_table("joined"),
    }

    secciones = "".join(_seccion_ramo(tablas, ramo) for ramo in RAMOS_REPORTE)
    indice_nav = "".join(
        f'<a href="#{ramo}">{NOMBRE_RAMO_LEGIBLE.get(ramo, ramo)}</a>' for ramo in RAMOS_REPORTE
    )

    fecha_min = pd.to_datetime(tablas["quejas_agrupado"]["fecha"]).min().strftime("%b %Y")
    fecha_max = pd.to_datetime(tablas["quejas_agrupado"]["fecha"]).max().strftime("%b %Y")

    html = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radiografía del sector asegurador colombiano</title>
<style>{CSS}</style>
</head>
<body>
<header class="hero">
  <h1>Radiografía del sector asegurador colombiano</h1>
  <p class="subtitulo">
    ¿Qué aseguradoras concentran más quejas de las que les corresponderían por su tamaño?
    Análisis de las {len(ENTIDADES)} aseguradoras generales y de vida vigiladas por la
    Superintendencia Financiera de Colombia ({fecha_min} – {fecha_max}), con datos abiertos
    de <a href="https://www.datos.gov.co">datos.gov.co</a>.
  </p>
</header>
<main>
  <div class="disclaimer">
    <strong>Nota de independencia:</strong> este es un proyecto personal de análisis de datos,
    construido íntegramente sobre datos públicos oficiales. No usa, reproduce ni se basa en
    información, metodología o análisis interno de ningún empleador o cliente. Las cifras y
    conclusiones son responsabilidad exclusiva del autor.
  </div>

  <details class="metodologia">
    <summary>Metodología y limitaciones (clic para expandir)</summary>
    <p>
      Datos: quejas mensuales por entidad/ramo/motivo (dataset <code>xyy7-rn7p</code>) y
      primas/pólizas por entidad/ramo (Formato 290, dataset <code>e967-4a8r</code>), ambos de la
      Superintendencia Financiera vía Socrata. Alcance: 38 entidades (25 generales, tipo 13; 22 de
      vida, tipo 14; algunas presentes en ambos), verificadas contra el listado oficial de
      entidades vigiladas (<code>sr9n-792w</code>).
    </p>
    <p>
      <strong>Índice de desproporción</strong> = participación de la entidad en las quejas del
      sector ÷ participación de la entidad en las pólizas vigentes del sector, para el mismo ramo
      y periodo. Un índice de 2 significa que la entidad concentra el doble de quejas de las que
      le tocarían según su tamaño; 0.5, la mitad. Se excluyen combinaciones entidad/ramo/mes sin
      dato de pólizas totales reportado, y entidades con menos de 1.000 pólizas acumuladas en el
      periodo (para no sobrerreaccionar a aseguradoras casi sin operación en ese ramo).
    </p>
    <p>
      <strong>Limitaciones conocidas:</strong> el dataset trae conteos agregados mensuales, no
      casos individuales, por lo que no hay tiempos de respuesta ni tasa de resolución por caso.
      No todas las entidades reportan pólizas totales todos los meses. Compensar y Colmédica (EPS)
      no están vigiladas por la Superfinanciera y no aparecen aquí; &ldquo;Colsanitas&rdquo; es
      únicamente el brazo asegurador del grupo, no la EPS.
    </p>
  </details>

  <nav class="indice">{indice_nav}</nav>

  {secciones}
</main>
<footer>
  Generado el {date.today().isoformat()} a partir de datos abiertos de la Superintendencia
  Financiera de Colombia (<a href="https://www.datos.gov.co">datos.gov.co</a>).
  Código y metodología completa en el repositorio de este proyecto.
</footer>
</body>
</html>"""

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ruta = DOCS_DIR / "index.html"
    ruta.write_text(html, encoding="utf-8")
    print(f"Reporte generado: {ruta} ({ruta.stat().st_size / 1024:.0f} KB)")
    return ruta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera docs/index.html a partir de lo guardado en SQLite.")
    parser.add_argument("--anio-desde", type=int, default=None, help="No filtra datos; informativo para el nombre del reporte.")
    args = parser.parse_args()
    build(anio_desde=args.anio_desde)

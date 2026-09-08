# Radiografía del Sector Asegurador Colombiano

> **Proyecto personal e independiente.** Construido íntegramente sobre
> datos públicos oficiales de datos.gov.co. No usa, reproduce ni se
> basa en información, metodología o análisis interno de ningún
> empleador o cliente.

Pipeline reproducible y parametrizable que extrae, limpia, almacena y
analiza las quejas (PQRS) reportadas ante la Superintendencia
Financiera de Colombia para **las 38 aseguradoras generales y de vida
vigiladas** (no solo 2-3 marcas puntuales), para responder una
pregunta de transparencia regulatoria más que de benchmark
competitivo:

**¿Qué aseguradoras concentran más quejas de las que les
corresponderían por su tamaño?**

Para eso se calcula un **índice de desproporción** por entidad y ramo:
participación en las quejas del sector ÷ participación en las pólizas
vigentes del sector. Un índice de 2× significa que la entidad
concentra el doble de quejas de las que le tocarían según su tamaño.
Ver `analysis/concentracion.py` para la implementación y
`docs/index.html` para el reporte con resultados.

> Una primera versión de este proyecto comparaba solo Bolívar, SURA y
> Colsanitas en el ramo salud. Se amplió deliberadamente a todo el
> sector (generales + vida) para que el análisis tenga valor por sí
> mismo, sin depender del alcance elegido en un contexto laboral
> puntual — ver nota de independencia arriba.

## ⚠️ Limitaciones de datos (leer antes de usar)

Este proyecto partió de un alcance más amplio (Bolívar, SURA vs.
Compensar, Colsanitas y Colmédica). Durante la construcción se
verificó, contra los datasets reales de datos.gov.co, que ese alcance
no es viable tal cual se planteó:

1. **Compensar y Colmédica no están vigiladas por la Superintendencia
   Financiera** (son EPS / medicina prepagada, vigiladas por la
   Superintendencia Nacional de Salud - Supersalud). No existen en el
   dataset de quejas usado aquí (`xyy7-rn7p`), y no se encontró un
   dataset abierto en formato Socrata publicado por Supersalud con
   PQRS discriminadas por EPS. Por lo tanto **no están incluidas** en
   este análisis.
2. **"Colsanitas" sí aparece**, pero únicamente como *Compañía de
   Seguros Colsanitas S.A.* (tipo_entidad `14`, código `33`) — el brazo
   **asegurador**, no la EPS/medicina prepagada. Su volumen de quejas
   en este dataset es muy pequeño comparado con Bolívar y SURA (ver
   sección de resultados), por lo que las comparaciones directas con
   Colsanitas deben leerse con cautela: no es un competidor de tamaño
   similar dentro de este universo de datos.
3. **No hay tiempos de respuesta ni tasa de resolución a nivel de
   caso**: el dataset de quejas trae **conteos agregados mensuales**
   por entidad/producto/motivo/ubicación, no registros individuales de
   PQRS con fecha de radicación/respuesta. Ese objetivo se eliminó del
   alcance por decisión explícita del usuario.
4. **`polizas_total` (Formato 290) no se reporta todos los meses** para
   todas las entidades/ramos, por lo que la métrica "quejas por cada
   1000 pólizas" solo tiene valor en los meses en que ese dato existe.
   Cuando el número de pólizas base es muy pequeño (como en Colsanitas),
   la tasa puede dispararse de forma no representativa; no se filtró ni
   se suavizó ese efecto para no enmascarar el dato real.

Si en el futuro aparece un dataset Socrata de Supersalud con PQRS por
EPS, se puede añadir como una tercera fuente sin tocar el resto del
pipeline (ver `extraction/`).

## Alcance de datos confirmado

**38 entidades**: las 25 aseguradoras generales (`tipo_entidad = 13`) y
22 aseguradoras de vida (`tipo_entidad = 14`) vigiladas por la
Superintendencia Financiera al 2026-09-08, agrupadas por marca
comercial cuando la misma aseguradora opera con razón social separada
para generales y vida (ej. Seguros Bolívar, SURA, Mapfre — ver el
listado completo y los códigos exactos en `config.ENTIDADES`).

Fuente: dataset `xyy7-rn7p` (Quejas) y `e967-4a8r` (Formato 290),
verificados contra el listado oficial de entidades vigiladas
(`sr9n-792w`) de la Superintendencia Financiera en datos.gov.co.

## Estructura del proyecto

```
├── config.py                  # Datasets y las 38 entidades del sector en alcance
├── load_dataset.py             # Cliente base de Socrata (extendido: retries + app_token por .env)
├── pipeline_agrupado.py        # Pipeline original (primera versión, se conserva sin cambios)
├── pipeline_motivo.py          # Pipeline original con detalle de motivo (se conserva sin cambios)
├── extraction/
│   └── extract_pqrs.py         # Extracción parametrizable (quejas + F290) para todo el sector
├── preprocessing/
│   ├── normalize.py            # Normalización de entidad, ramo, motivo, fechas, duplicados
│   └── build_dataset.py        # Orquesta extracción + limpieza en tablas tidy
├── storage/
│   └── db.py                   # SQLite + export Parquet/CSV
├── analysis/
│   ├── descriptive.py          # Agregaciones (volumen, distribución, resumen ejecutivo)
│   ├── concentracion.py        # Índice de desproporción quejas/pólizas, rankings sectoriales
│   ├── comparativo.py          # Gráficos (tendencia sectorial, motivos, ranking de desproporción)
│   └── output/                 # Gráficos generados (PNG, no versionado)
├── data/                        # SQLite + Parquet/CSV generados (no versionado)
├── docs/
│   └── index.html              # Reporte HTML autocontenido (gráficos embebidos), publicable con GitHub Pages
├── build_report.py             # Genera docs/index.html a partir de lo guardado en SQLite
└── run_pipeline.py             # Orquestador CLI
```

## Instalación

Requiere **Python 3.12** (probado con 3.12.5).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # opcional: agrega tu SOCRATA_APP_TOKEN
```

El `app_token` de Socrata es opcional (sin él, la API funciona con
límites de tasa más estrictos). Nunca se hardcodea: se lee desde `.env`
vía `python-dotenv` en `load_dataset.py`.

## Cómo correr el pipeline

Todo el flujo, de extremo a extremo:

```bash
python run_pipeline.py --stage all --anio-desde 2023
```

- `--anio-desde` es opcional; si se omite trae todo el histórico
  disponible en el dataset.
- `--ramo` filtra el análisis final impreso en consola (por defecto
  `salud`; ver `config.RAMOS_DISPONIBLES`). La extracción siempre trae
  todos los ramos y las 38 entidades; el filtro es solo para el
  reporte de consola.
- Esto deja `data/pqrs_seguros.db` (SQLite), `data/*.parquet`,
  `data/*.csv`, y los gráficos en `analysis/output/`.

## Reporte HTML (publicable con GitHub Pages)

Una vez corrido el pipeline al menos una vez con `--stage store` (o
`all`), se puede generar un reporte HTML autocontenido — sin
dependencias externas, gráficos embebidos como base64 — con la
radiografía completa del sector (tendencia, motivos e índice de
desproporción) para cada ramo comparable:

```bash
python build_report.py
```

Esto escribe `docs/index.html`. Para publicarlo gratis con GitHub
Pages: `Settings → Pages → Deploy from a branch → main → /docs`. El
reporte queda disponible en `https://<usuario>.github.io/<repo>/`.

### Por etapas independientes

```bash
python run_pipeline.py --stage extract-clean --anio-desde 2024   # solo extrae + limpia, imprime shapes
python run_pipeline.py --stage store --anio-desde 2024            # extrae + limpia + guarda en SQLite/Parquet/CSV
python run_pipeline.py --stage analyze                            # reutiliza lo ya guardado en SQLite y genera gráficos
```

También se puede usar cada módulo directamente en Python/notebook:

```python
from preprocessing.build_dataset import build_full_dataset
from analysis.descriptive import resumen_ejecutivo, distribucion_motivo

tablas = build_full_dataset(anio_desde=2023)
resumen_ejecutivo(tablas["quejas_agrupado"], ramo="salud")
distribucion_motivo(tablas["quejas_motivo"], ramo="salud", entidad="SURA")
```

## Tablas generadas

| Tabla | Granularidad | Uso |
|---|---|---|
| `quejas_agrupado` | fecha, entidad, ramo | Series de tiempo de volumen, y base para unir con F290 |
| `quejas_motivo` | fecha, entidad, ramo, motivo | Distribución de motivos de queja |
| `quejas_geografico` | fecha, entidad, ramo, departamento, municipio | Detalle geográfico (no explotado en los gráficos por defecto) |
| `f290` | fecha, entidad, ramo | Primas emitidas/coaseguro/canceladas y pólizas emitidas/rehabilitadas/canceladas/vigentes |
| `joined` | fecha, entidad, ramo | `quejas_agrupado` + `f290`, con `quejas_por_1000_polizas` |

## Actualizar periódicamente

El pipeline es idempotente: cada corrida reemplaza el contenido de las
tablas en SQLite (`if_exists="replace"`) y sobrescribe los archivos
Parquet/CSV, así que basta con volver a correr
`python run_pipeline.py --stage all` (con o sin `--anio-desde`) para
refrescar los datos. Dado que el dataset es de conteos agregados
mensuales y de tamaño moderado, no se implementó una extracción
incremental por filas — se recarga el histórico completo cada vez, lo
cual es rápido y evita inconsistencias de merge.

## Qué reutiliza y qué extiende de tu código base

- `load_dataset.py`: se mantiene `load_full_socrata_dataset` y
  `soql_in_str` tal cual, y se les añade (sin romper compatibilidad):
  soporte de `app_token`/credenciales vía `.env`, y reintentos con
  backoff ante fallos transitorios de red/API.
- `pipeline_agrupado.py` y `pipeline_motivo.py`: se dejan intactos como
  referencia (la primera versión del proyecto, con 2-3 aseguradoras
  elegidas a mano); la lógica de limpieza de fecha, ramo y duplicados
  que usan se reutilizó y generalizó en `preprocessing/normalize.py` y
  `preprocessing/build_dataset.py` para el nuevo alcance (las 38
  entidades del sector), agregando el nivel geográfico, el cálculo de
  quejas por póliza y el índice de desproporción sectorial
  (`analysis/concentracion.py`) que no existían antes.

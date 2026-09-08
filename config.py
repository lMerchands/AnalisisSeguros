"""---------------------------------------------------"""
"""        Configuración de Alcance del Proyecto       """
"""---------------------------------------------------"""
"""

Identificadores de datasets y entidades vigiladas usados por el
pipeline de extracción/limpieza de PQRS del sector asegurador.

Alcance: TODAS las compañías de seguros generales (tipo_entidad "13")
y de seguros de vida (tipo_entidad "14") vigiladas por la
Superintendencia Financiera, agrupadas por marca/grupo económico
cuando una misma aseguradora opera con una razón social separada para
generales y para vida (ej. "Seguros Bolívar" = Seguros Comerciales
Bolívar S.A. [13-27] + Compañía de Seguros Bolívar S.A. [14-07]).

Este es un cambio deliberado de alcance frente a una primera versión
de este proyecto que comparaba solo 2-3 aseguradoras elegidas a mano
(Bolívar, SURA, Colsanitas). Analizar el sector completo, en vez de
un grupo pequeño de competidores, es lo que permite calcular un
índice de concentración/desproporción de quejas (ver
analysis/concentracion.py) que tiene sentido como pregunta de
transparencia regulatoria y no como benchmark competitivo de una
aseguradora puntual.

ENTIDADES fue construido a mano a partir del listado oficial
"Entidades vigiladas por la Superfinanciera" (dataset sr9n-792w,
consultado en datos.gov.co, tipo_entidad in ('13','14'), 47 registros
en total), agrupando razón social generales + razón social vida bajo
el nombre comercial cuando corresponde a la misma marca. No se agrupó
por matriz corporativa más allá de eso (ej. Colmena Seguros Generales/
Vida se agrupa, pero Colmena Seguros Riesgos Laborales, con licencia y
ramo distintos, se deja como entidad aparte).

IMPORTANTE - Limitaciones conocidas del alcance:
- Compensar (EPS/Caja de Compensación) y Colmédica (medicina
  prepagada) NO están vigiladas por la Superintendencia Financiera y
  por lo tanto NO existen en estos datasets. Tampoco se encontró un
  dataset abierto en formato Socrata publicado por la Superintendencia
  Nacional de Salud (Supersalud) con PQRS discriminadas por EPS. Ver
  README.md, sección "Limitaciones de datos" para más detalle.
- "Colsanitas" aquí es únicamente el brazo asegurador (Compañía de
  Seguros Colsanitas S.A., tipo 14 código 33), no la EPS/medicina
  prepagada del mismo grupo.
- No todas las 38 entidades reportan en todos los meses ni en todos
  los ramos; los rankings y el índice de desproporción (ver
  analysis/concentracion.py) se calculan solo sobre combinaciones
  entidad/ramo/mes con dato de pólizas disponible.
"""

# --- Datasets fuente en datos.gov.co (Superintendencia Financiera) --- #
DATASET_QUEJAS = "xyy7-rn7p"       # Quejas recibidas por entidad/producto/motivo/mes
DATASET_F290 = "e967-4a8r"         # Formato 290: primas y pólizas por entidad/ramo/mes
DATASET_ENTIDADES_VIGILADAS = "sr9n-792w"  # Listado oficial de entidades vigiladas (referencia/auditoría)

# --- tipo_entidad en alcance: 13 = seguros generales, 14 = seguros de vida --- #
TIPOS_ENTIDAD = ["13", "14"]

# --- Entidades en alcance: nombre comercial -> [(tipo_entidad, codigo_entidad), ...] --- #
# Verificado contra sr9n-792w el 2026-09-08. Cada entidad puede tener un solo
# par (solo generales o solo vida) o dos pares (mismo grupo en ambos ramos).
ENTIDADES = {
    # --- Grupos presentes en generales (13) y vida (14) ---
    "Allianz": [("13", "1"), ("14", "1")],
    "AXA Colpatria": [("13", "6"), ("14", "4")],
    "SURA": [("13", "18"), ("14", "11")],
    "Alfa": [("13", "25"), ("14", "17")],
    "Mapfre": [("13", "26"), ("14", "30")],
    "Seguros Bolívar": [("13", "27"), ("14", "7")],
    "Seguros del Estado": [("13", "29"), ("14", "19")],
    "BBVA Seguros": [("13", "41"), ("14", "26")],
    "Colmena Seguros": [("13", "50"), ("14", "32")],
    # --- Solo generales (13) ---
    "Chubb": [("13", "5")],
    "Nacional de Seguros": [("13", "7")],
    "Confianza": [("13", "8")],
    "Zurich": [("13", "9")],
    "Seguros Mundial": [("13", "17")],
    "SBS Seguros": [("13", "22")],
    "La Previsora": [("13", "24")],
    "Solunion": [("13", "42")],
    "Cardif": [("13", "44")],
    "Liberty Seguros": [("13", "45")],
    "Coface": [("13", "46")],
    "Berkley": [("13", "47")],
    "CESCE Colombia": [("13", "30")],
    "HDI Seguros": [("13", "33")],
    "Everest": [("13", "51")],
    "Quálitas": [("13", "52")],
    # --- Solo vida (14) ---
    "Aurora": [("14", "8")],
    "Skandia": [("14", "9")],
    "MetLife": [("14", "13")],
    "Pan-American Life": [("14", "16")],
    "Global Seguros": [("14", "20")],
    "Positiva Vida": [("14", "23")],
    "Colmena ARL": [("14", "25")],
    "La Equidad Seguros de Vida": [("14", "29")],
    "BMI Colombia": [("14", "31")],
    "Colsanitas": [("14", "33")],
    "Asulado": [("14", "34")],
    "EKG Aseguradora": [("14", "35")],
    "Andina Seguros": [("14", "36")],
}

# Pares completos (tipo, codigo) usados para construir los filtros $where
PARES_TIPO_CODIGO = [par for pares in ENTIDADES.values() for par in pares]

CODIGOS_ENTIDAD = sorted({codigo for _, codigo in PARES_TIPO_CODIGO})

# --- Ramos que existen en el dataset de quejas --- #
RAMOS_DISPONIBLES = [
    "Seguro de hogar",
    "Seguro de salud",
    "Seguro de vida individual",
    "Seguro de vida grupo",
    "Seguro colectivo de vida",
    "Seguro de riesgos laborales",
    "Seguro de automóviles",
]

# Ramo usado como ejemplo por defecto en el README y en algunos scripts,
# pero el pipeline y el análisis funcionan sobre cualquier ramo de la lista
# de arriba (o sobre el sector completo si no se filtra por ramo).
RAMO_EJEMPLO = "salud"

# --- Color por ramo (para los gráficos de analysis/comparativo.py) --- #
# Claves en el formato normalizado corto que produce preprocessing/normalize.py
# (RAMO_RENAME), no el nombre largo de RAMOS_DISPONIBLES.
#
# OJO: RAMO_RENAME fusiona "Seguro de vida grupo" y "Seguro colectivo de
# vida" en el mismo valor normalizado "vida_grupo" (se agregan juntos desde
# clean_quejas/clean_f290, antes de llegar a cualquier gráfico). Por eso acá
# solo hay un color para "vida_grupo": no hay forma de pintar "colectivo de
# vida" distinto mientras el pipeline los siga tratando como una sola
# categoría. Si en el futuro se separan en normalize.py, agregar aquí la
# entrada "colectivo_vida" con su propio color.
COLOR_POR_RAMO = {
    "hogar": "#D97706",           # Ámbar cálido
    "salud": "#0D9488",           # Verde azulado / Teal
    "vida_individual": "#2563EB",  # Azul zafiro
    "vida_grupo": "#4F46E5",       # Índigo (incluye "Seguro colectivo de vida", ver nota arriba)
    "arl": "#EA580C",             # Naranja seguridad
    "automoviles": "#DC2626",     # Rojo vial
}
COLOR_RAMO_DEFAULT = "royalblue"  # fallback para un ramo sin color asignado

# --- Mapeo (tipo_entidad, codigo_entidad) -> nombre canónico de entidad --- #
CODIGO_A_ENTIDAD = {
    f"{tipo}-{codigo}": nombre
    for nombre, pares in ENTIDADES.items()
    for tipo, codigo in pares
}

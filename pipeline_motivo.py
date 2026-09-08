"""--------------------------------------------------"""
"""        Extracción y Limpieza de Datos API        """
"""--------------------------------------------------"""
"""

Este archivo busca realizar la extracción y preprocesamiento de los datos 
para más adelante usar para alimentar los tableros dinámicos.

Creado por: Juan Merchán
"""

# Librerias
import pandas as pd
from load_dataset import load_full_socrata_dataset, soql_in_str
import logging; logging.getLogger().setLevel(logging.ERROR)  # hides WARNING:root:...

"""--------------------------------------------------"""
"""               Datos de Formato 290               """
"""--------------------------------------------------"""

def execute_pipeline():
    print('Trayendo Datasets...')

    """ Extracción Formato 290 """
    query_f290 = dict(
        entidades = ("13-27", "13-18", "13-06", "13-26", "13-01", "13-25", "14-07", "14-11", "14-04", "14-30", "14-01", "14-17"),
        unidad_captura = ("1", "20"),
        subcuentas = ("5", "10", "15", "20", "999"),
    )

    # Datos Formato 290 (Generales de Empresas en la Superfinanciera)
    df_f290 = load_full_socrata_dataset(
            dataset_id="e967-4a8r",
            where=f'''codigo_entidad IN {soql_in_str(query_f290["entidades"])} 
                    AND unidad_de_captura IN {soql_in_str(query_f290["unidad_captura"])} 
                    AND subcuenta IN {soql_in_str(query_f290["subcuentas"])}''', # Selecciona solo aseguradoras que sean competencia (Bolivar, SURA, Axa, Allianz, Alfa y Mapfre).
            app_token=None,
            chunk_size=50_000
        )
    print('Dataset F290 traído')

    """------------------------"""
    """ Limpieza de Datos F290 """
    """------------------------"""

    # --- Convierte Fecha en tipo Datetime --- #
    df_f290["fecha"] = pd.to_datetime(
        df_f290["a_o"].astype(str) + "-" + df_f290["mes"].astype(str) + "-01",
        format="%Y-%m-%d",
        errors="coerce"
    ).dt.date

    # --- Convierte filtra subcuentas --- #
    df_f290 = df_f290[(
        ((df_f290['subcuenta'].isin(['5', '10', '15'])) & (df_f290['unidad_de_captura'] == '1')) | # Selecciona Primas Emitidas, Coaseguro y Canceladas o Anuladas
        ((df_f290['subcuenta'].isin(['10', '15', '20', '999'])) & (df_f290['unidad_de_captura'] == '20')) # Selecciona Polizas Emitidas, Rehabilitadas y Canceladas o Vencidas
    )]

    # --- Transpone la tabla --- #
    df_f290 = df_f290[['fecha', 'codigo_entidad', 'nombre_entidad',        # Selecciona columnas
                       'nombre_subcuenta', 'automoviles', 'hogar_mes',     # para trabajar con un
                       'vida_indivudual_mes', 'vida_grupo_mes',            # filtro inicial
                       'riesgos_profesionales_mes', 'salud_mes']]\
        .melt(
            # --- Convierte las columnas de los ramos en valores en la columna "ramo" --- #
            id_vars=['fecha', 'codigo_entidad', 'nombre_entidad', 'nombre_subcuenta'], 
            value_vars=['automoviles', 'hogar_mes', 'vida_indivudual_mes', 
                        'vida_grupo_mes', 'riesgos_profesionales_mes', 'salud_mes'],
            var_name='ramo',
            value_name='valor'
    )\
        .pivot_table(
            # --- Convierte las subcuentas (polizas y primas) en columnas --- #
            index=['fecha', 'codigo_entidad', 'nombre_entidad', 'ramo'],
            columns=["nombre_subcuenta"],
            values="valor",
            aggfunc="first")\
                .reset_index()\
                .rename(
                    # --- Renombra las columnas --- #
                    columns={
                    'CANC Y-O ANULAC PRIMAS EMIT DIR Y COA': 'primas_canceladas',
                    'POLIZAS CANCELADAS Y-O VENCIDAS': 'polizas_canceladas',
                    'POLIZAS EMITIDAS NUEVAS': 'polizas_emitidas',
                    'POLIZAS REHABILITADAS': 'polizas_rehabilitadas',
                    'PRIMAS ACEPTADAS EN COASEGURO': 'primas_coaseguro',
                    'PRIMAS EMITIDAS DIRECTAS': 'primas_emitidas',
                    'TOTAL POLIZAS VIGENTES FINAL EJERCIC': 'polizas_total'
                })\
                    [   # --- Ordena las nuevas columnas --- #
                        ['fecha', 'codigo_entidad', 'nombre_entidad', 
                        'ramo','primas_emitidas', 'primas_coaseguro', 
                        'primas_canceladas', 'polizas_emitidas', 
                        'polizas_rehabilitadas', 'polizas_canceladas', 
                        'polizas_total']
                    ] 
    
    # --- Limpia el texto (elimina tildes, remueve "_mes", renombra arl) --- #
    df_f290['ramo'] = df_f290['ramo'].replace({
        # Remueve "_mes" #
        "hogar_mes": "hogar",
        "vida_indivudual_mes": "vida_individual",
        "vida_grupo_mes": "vida_grupo",
        "salud_mes": "salud",
        # Renombra ARL #
        "riesgos_profesionales_mes": "arl",
        # Remueve tilde #
        "automoviles": "automoviles",
    })

    # print(df_f290.head(20))
    # --- Dataset Formato 290 Listo --- #

    print('Dataset Formato 290 listo')

    """-------------------------------------------------"""
    """                 Datos de Quejas                 """
    """-------------------------------------------------"""

    """ Extracción Quejas """
    query_quejas = dict(
        tipo = ("13","14"),
        codigo = ("27", "18", "6", "1", "26", "25", "7", "11", "4", "30", "17")
    )

    # Datos Quejas
    df_quejas = load_full_socrata_dataset(
            dataset_id="xyy7-rn7p",
            where=f'''tipo_entidad IN {soql_in_str(query_quejas["tipo"])} 
                    AND codigo_entidad IN {soql_in_str(query_quejas["codigo"])}''', # Selecciona solo aseguradoras que sean competencia (Bolivar, SURA, Axa, Allianz, Alfa y Mapfre).
            app_token=None,
            chunk_size=50_000
        )
    print('Dataset Quejas traído')

    """--------------------------"""
    """ Limpieza de Datos Quejas """
    """--------------------------"""

    # --- Convierte Fecha en tipo Datetime --- #
    df_quejas["fecha"] = pd.to_datetime(
        df_quejas["a_o_creacion"].astype(str) + "-" + df_quejas["mes_creacion"].astype(str) + "-01",
        format="%Y-%m-%d",
        errors="coerce"
    ).dt.date

    # --- Fusiona tipo y código de entidad --- #
    df_quejas["codigo_entidad"] = df_quejas["tipo_entidad"].astype(str) + '-' + df_quejas['codigo_entidad'].astype('str').str.zfill(2)

    # --- Filtra y remueve --- #
    df_quejas = (
        df_quejas[
            # --- Filtra competencia --- #
            (df_quejas["codigo_entidad"].astype(str).isin([
                "13-27", "13-18", "13-06", "13-01", "13-26", "13-25", # Selecciona competencia
                "14-07", "14-11", "14-04", "14-01", "14-30", "14-17"  # Bolivar, SURA, AXA, Allianz, Mapfre, Alfa
            ])) & 
            # --- Elimina las quejas por SOAT (no ofertado por Bolivar) --- #
            (df_quejas['producto'] != "Seguro Obligatorio de Accidentes de Tránsito (SOAT)") # Quita SOAT
        ]
    )

    # --- Filtra, ordena y renombra variables --- #
    df_quejas = df_quejas.rename(
        # --- Renombra "producto" como "ramo" --- #
        columns={'producto': 'ramo'}
    )
    
    df_quejas = df_quejas[ 
            # --- Filtra variables --- #
            ['fecha', 'codigo_entidad', 'ramo', 'motivo', 'cantidad_quejas_recibidas']
        ]\
        [ # --- Selecciona solo los ramos necesarios --- #
            df_quejas['ramo'].isin(
                ['Seguro de hogar', 'Seguro de salud', 'Seguro de vida individual', 
                 'Seguro de vida grupo', 'Seguro colectivo de vida', 
                 'Seguro de riesgos laborales', 'Seguro de automóviles']
            )
        ]\
        .replace( # --- Limpia los nombres de los ramos --- #
        {   
            # --- Quita "Seguro de " --- #
            "Seguro de hogar": "hogar",
            "Seguro de salud": "salud",
            # --- Quita "Seguro de " y agrupa "vida grupo" y "colectivo de vida" --- #
            "Seguro de vida individual": "vida_individual",
            "Seguro de vida grupo": "vida_grupo",
            "Seguro colectivo de vida": "vida_grupo",
            # --- Renombra ARL y quita la tilde de automoviles --- #
            "Seguro de riesgos laborales": "arl",
            "Seguro de automóviles": "automoviles",
    })

    # --- Convierte quejas en valores enteros --- #
    df_quejas['cantidad_quejas_recibidas'] = df_quejas['cantidad_quejas_recibidas'].astype('int')

    # --- Suma los registros repetidos (duplicados por "motivo") --- #
    # df_quejas = df_quejas.groupby(
    #     ['fecha', 'codigo_entidad', 'ramo'], as_index=False
    # ).sum()

    # print(df_quejas.head(20))
    # --- Dataset Quejas Listo --- #
    print('Dataset Quejas listo')

    """--------------------------------------------------"""
    """                 Une los datasets                 """
    """--------------------------------------------------"""
    
    # --- Hace Join a los datasets --- #
    df_joined = df_f290.merge(
        df_quejas[['fecha', 'codigo_entidad', 'ramo', 'motivo','cantidad_quejas_recibidas']],
        on=['fecha', 'codigo_entidad', 'ramo'],
        how='left'
    )

    # --- Rellena los NaNs de quejas recibidas con 0 (si hay un vacío es porque no hubo quejas) --- #
    df_joined['cantidad_quejas_recibidas'] = df_joined['cantidad_quejas_recibidas'].fillna(0)

    # --- Cambia los tipos de datos a float (números reales) e int (números enteros) --- #
    df_joined = df_joined.astype({
        "primas_emitidas": "float32",
        "primas_coaseguro": "float32",
        "primas_canceladas": "float32",
        "polizas_emitidas": "int32",
        "polizas_rehabilitadas": "int32",
        "polizas_canceladas": "int32",
        "polizas_total": "int32",
        "cantidad_quejas_recibidas": "int32"
    })

    # --- Mapea los grupos según los códigos de las entidades --- #
    grupo_map = { # Diccionario de mapeo
        '13-27': 'Grupo Bolivar' , '14-07': 'Grupo Bolivar',
        '13-18': 'Grupo SURA'    , '14-11': 'Grupo SURA',
        '13-06': 'Grupo AXA'     , '14-04': 'Grupo AXA',
        '13-01': 'Grupo Allianz' , '14-01': 'Grupo Allianz',
        '13-26': 'Grupo Mapfre'  , '14-30': 'Grupo Mapfre',
        '13-25': 'Grupo Alfa'    , '14-17': 'Grupo Alfa'
    }

    # Mapeo
    df_joined["grupo"] = df_joined["codigo_entidad"].astype(str).map(grupo_map)

    # --- Quita la información de las entidades y agrupa por grupo (valga la redundancia) --- #
    df_joined = df_joined.drop(
        columns=['codigo_entidad', 'nombre_entidad']
    )\
        .groupby(
        ['fecha', 'grupo', 'ramo'], as_index=False
    ).sum()

    # --- Dataset Final Listo --- #

    return df_joined

# Ejecuta
if __name__ == "__main__":
    dataframes = execute_pipeline()
    print(
        f'df_quejas {dataframes[0].shape}\ndf_f290 {dataframes[1].shape}'
    )


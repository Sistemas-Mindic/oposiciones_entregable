import pandas as pd
import os 
import sys

# 1. CONFIGURACIÓN DE RUTAS DINÁMICAS (Arreglado para cualquier usuario)
# Detectamos la carpeta donde está guardado este mismo script (step4_resultados)
current_dir = os.path.dirname(os.path.abspath(__file__))

INPUT_DIR = current_dir
OUTPUT_DIR = current_dir

# Nombres de los archivos esperados
FILE_1 = "convocatorias_filtradas_tipo_proceso_AGE.csv"
FILE_2 = "resultado_todas_comunidades.csv"
OUTPUT_FILE = "concat_resultado_final2.csv"

CSV_INPUT_PATH_1 = os.path.join(INPUT_DIR, FILE_1)
CSV_INPUT_PATH_2 = os.path.join(INPUT_DIR, FILE_2)
CSV_OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

dataframes = []

# 2. CARGA SEGURA DEL PRIMER ARCHIVO (AGE)
if os.path.exists(CSV_INPUT_PATH_1):
    try:
        df1 = pd.read_csv(CSV_INPUT_PATH_1)
        dataframes.append(df1)
        print(f"Cargado: {FILE_1} ({len(df1)} filas)")
    except Exception as e:
        print(f"Error leyendo {FILE_1}: {e}")
else:
    print(f"AVISO: No existe el archivo {FILE_1}. Se omitirá.")

# 3. CARGA SEGURA DEL SEGUNDO ARCHIVO (Comunidades)
if os.path.exists(CSV_INPUT_PATH_2):
    try:
        df2 = pd.read_csv(CSV_INPUT_PATH_2)
        dataframes.append(df2)
        print(f"Cargado: {FILE_2} ({len(df2)} filas)")
    except Exception as e:
        print(f"❌ Error leyendo {FILE_2}: {e}")
else:
    print(f"AVISO: No existe el archivo {FILE_2}. Se omitirá.")

# 4. CONSOLIDACIÓN
if dataframes:
    # Concatena las filas de los que se hayan encontrado
    df_concat = pd.concat(dataframes, ignore_index=True)
    if 'FECHA_CIERRE' in df_concat.columns:
        
        fechas = df_concat['FECHA_CIERRE']
        hoy = pd.Timestamp.now().isoformat()
        condicion = (fechas.isna()) | (fechas >= hoy)
        df_concat = df_concat[condicion]
    # Guarda el resultado
    df_concat.to_csv(CSV_OUTPUT_PATH, index=False)
    print(f"\nÉXITO: Archivo consolidado guardado en:\n{CSV_OUTPUT_PATH}")
    print(f"Total filas consolidadas: {len(df_concat)}")
else:
    print("\nERROR CRÍTICO: No se encontró ningún archivo de entrada. No se ha generado el consolidado.")
    # Salimos con error para detener el pipeline si es necesario
    sys.exit(1)
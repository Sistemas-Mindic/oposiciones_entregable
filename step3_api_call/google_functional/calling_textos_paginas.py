# 3_api_call/GOOGLE_FUNCTIONAL/google_calling_textos_paginas.py

import os
import csv
import time
import json
from dotenv import load_dotenv

from google import genai
from google.genai import types

from tool_fine import extraer_convocatorias_sanitarias
from tool_ejemplos import EJEMPLOS_CONVOCATORIAS


# ───────── CONFIG ENTRADA CSV ───────── #
CSV_INPUT_PATH = "convocatorias_detalle_age_v4.csv"


# ───────── LEER CSV Y CREAR ENTRADAS ───────── #

with open(CSV_INPUT_PATH, newline="", encoding="utf-8") as f:
    #reader = csv.DictReader(f, delimiter=';', quotechar='"') # Este para generalitat 
    reader = csv.DictReader(f, delimiter=',' ) #Este para nacional
    filas = list(reader)
    print("Cabeceras detectadas en el CSV (NUEVO):", reader.fieldnames)

if not filas:
    raise RuntimeError(f"El CSV de entrada '{CSV_INPUT_PATH}' está vacío.")

entradas = []
for fila in filas:
    contenido = fila.get("contenido_pagina") #contenido_pagina
    if not contenido:
        continue

    enlace = fila.get("Enlace") or fila.get("enlace") or fila.get("url") or ""

    entradas.append(
        {
            "contenido": contenido,
            "id": enlace,
            "origen": fila,
        }
    )

print(f"Textos a procesar con Gemini (NUEVO CSV): {len(entradas)}")


# ───────── CONFIGURACIÓN CLIENTE GEMINI ───────── #

load_dotenv("API_GOOGLE.env")

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY no está definida en API_GOOGLE.env ni en el entorno")

client = genai.Client(api_key=API_KEY)

tool = types.Tool(function_declarations=[extraer_convocatorias_sanitarias])

config = types.GenerateContentConfig(
    tools=[tool],
    temperature=0.0,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=["extraer_convocatorias_sanitarias_csv"],
        )
    ),
)


# ───────── RATE LIMITS / DELAY ───────── #

MODEL_NAME = "gemini-2.5-flash-lite"

RATE_LIMITS = {
    "gemini-2.5-flash-lite": {
        "RPM": 15,
        "TPM": 250_000,
        "RPD": 1000,
    },
}

limits = RATE_LIMITS[MODEL_NAME]
RPM = limits["RPM"]
TPM = limits["TPM"]
RPD = limits["RPD"]

BASE_DELAY_SECONDS = 60.0 / RPM
SAFETY_FACTOR = 1
DELAY_BETWEEN_REQUESTS = BASE_DELAY_SECONDS * SAFETY_FACTOR

print(f"\nUsando modelo: {MODEL_NAME}")
print(f"Límite: {RPM} requests/min, {TPM} tokens/min, {RPD} requests/día")
print(f"Delay entre peticiones: {DELAY_BETWEEN_REQUESTS:.2f} segundos\n")

requests_done = 0


# ───────── HEADER CSV A PARTIR DEL SCHEMA ───────── #

convocatoria_schema = (
    extraer_convocatorias_sanitarias["parameters"]["properties"]["convocatorias"]["items"]
)
header = list(convocatoria_schema.get("required", []))

if "_ORIGEN_ENLACE" not in header:
    header.append("_ORIGEN_ENLACE")


# ───────── BLOQUE DE EJEMPLOS PARA FEW-SHOT ───────── #

def _construir_bloque_ejemplos() -> str:
    ejemplos = EJEMPLOS_CONVOCATORIAS.get("ejemplos_errores", [])
    if not ejemplos:
        return ""

    bloques = []
    for ej in ejemplos:
        texto = ej.get("texto_entrada", "").strip()
        salida = ej.get("salida_esperada", {})

        estructura = {"convocatorias": [salida]}
        estructura_str = json.dumps(estructura, ensure_ascii=False, indent=2)

        bloques.append(
            "EJEMPLO DE EXTRACCIÓN CORRECTA:\n"
            "TEXTO DE ENTRADA (resumen de convocatoria):\n"
            f"{texto}\n\n"
            "LLAMADA CORRECTA A LA FUNCIÓN extraer_convocatorias_sanitarias_csv:\n"
            f"extraer_convocatorias_sanitarias_csv({estructura_str})\n"
        )

    return "\n\n".join(bloques)


EJEMPLOS_BLOCK = _construir_bloque_ejemplos()


# ───────── PROMPT ESTRUCTURADO ───────── #

def _construir_prompt(texto: str, usar_ejemplos: bool = False) -> str:
    base = (
        "<role>\n"
        "You are a specialized assistant for extracting structured public-employment\n"
        "calls (convocatorias de empleo público) for ENFERMERÍA and TCAE from noisy Spanish\n"
        "administrative texts (administracion.gob.es, boletines oficiales, resoluciones, etc.).\n"
        "You ALWAYS respond ONLY via a single call to the tool 'extraer_convocatorias_sanitarias_csv'.\n"
        "</role>\n\n"

        "<instructions>\n"
        "1. Plan:\n"
        "   - Lee TODO el texto completo.\n"
        "   - Identifica si describe convocatorias de EMPLEO PÚBLICO para ENFERMERÍA o TCAE\n"
        "     (personal estatutario, funcionario, laboral, interino, bolsas, oposiciones,\n"
        "     concursos, concurso-oposición).\n"
        "   - Distingue si es:\n"
        "       * Página de DETALLE de una sola convocatoria.\n"
        "       * Documento con ANEXO/listado de puestos de un mismo proceso.\n"
        "       * Bloque de resultados / 'otras convocatorias' sin bloque principal de detalle.\n"
        "\n"
        "2. Execute:\n"
        "   - Aplica TODAS las reglas y pasos definidos en la descripción de la tool\n"
        "     'extraer_convocatorias_sanitarias_csv'. Esa descripción es de CUMPLIMIENTO\n"
        "     OBLIGATORIO e incluye también la definición detallada de cada campo de salida.\n"
        "   - Usa exclusivamente la información literal del texto. Si un dato no aparece,\n"
        "     déjalo vacío o usa 'NONE' cuando corresponda según el schema.\n"
        "   - En páginas tipo administracion.gob.es, trata la frase\n"
        "       'quizá también te interesen otras convocatorias'\n"
        "     (en cualquier combinación de mayúsculas/minúsculas) como un CORTE DURO:\n"
        "       * Solo analizas el bloque anterior (Detalle de convocatoria).\n"
        "       * Ignoras COMPLETAMENTE todo lo que venga después (otras convocatorias sugeridas),\n"
        "         aunque haya muchas referencias a ENFERMERÍA/TCAE.\n"
        "   - Agrupa SIEMPRE:\n"
        "       * Todas las denominaciones de ENFERMERÍA (incluyendo especialidades) en UNA\n"
        "         única convocatoria con PERFIL='enfermeria'.\n"
        "       * Todas las denominaciones de TCAE/Auxiliar de Enfermería en UNA única\n"
        "         convocatoria con PERFIL='tcae'.\n"
        "\n"
        "3. Validate:\n"
        "   - Antes de devolver la función, revisa el array 'convocatorias' que has construido:\n"
        "       * Si no hay empleo público válido de ENFERMERÍA/TCAE con plazo abierto o bolsa\n"
        "         permanente → convocatorias=[].\n"
        "       * Máximo 2 elementos en 'convocatorias'.\n"
        "       * Como mucho UNA convocatoria con PERFIL='enfermeria'.\n"
        "       * Como mucho UNA convocatoria con PERFIL='tcae'.\n"
        "       * Si hubiera más de una por perfil, quédate solo con la más representativa y\n"
        "         DESCARTA las demás ANTES de devolver la llamada de función.\n"
        "\n"
        "4. Format:\n"
        "   - Tu respuesta DEBE consistir EXCLUSIVAMENTE en UNA ÚNICA llamada a la función\n"
        "     'extraer_convocatorias_sanitarias_csv', con el argumento 'convocatorias' rellenado\n"
        "     según el schema que te proporciona el sistema.\n"
        "   - No escribas código Python, ni explicaciones, ni ningún otro texto libre.\n"
        "   - Si no hay convocatorias válidas, debes devolver exactamente:\n"
        "     extraer_convocatorias_sanitarias_csv(convocatorias=[])\n"
        "</instructions>\n\n"

        "<constraints>\n"
        "- Verbosity: mínima en lenguaje natural (NO generes explicación; solo la tool call).\n"
        "- Tone: técnico y preciso, respetando estrictamente las definiciones del schema de la tool.\n"
        "</constraints>\n\n"

        "<output_format>\n"
        "Tu salida explícita debe ser únicamente una llamada de función válida para el sistema\n"
        "de herramientas, con esta forma general:\n"
        "  extraer_convocatorias_sanitarias_csv(\n"
        "      convocatorias=[ {...}, {...} ]\n"
        "  )\n"
        "Sin texto adicional antes ni después.\n"
        "</output_format>\n\n"
    )

    if usar_ejemplos and EJEMPLOS_BLOCK:
        base += (
            "<examples>\n"
            "A continuación tienes ejemplos reales de comportamiento correcto cuando una página\n"
            "de detalle incluye un bloque de 'otras convocatorias'. En todos los casos la tool\n"
            "solo devuelve la convocatoria principal de ENFERMERÍA/TCAE de la página e ignora\n"
            "por completo las demás:\n\n"
            f"{EJEMPLOS_BLOCK}\n"
            "</examples>\n\n"
        )

    base += (
        "<task>\n"
        "Lee el siguiente texto completo, aplica el plan (Plan → Execute → Validate → Format),\n"
        "junto con TODAS las reglas de la descripción de la tool\n"
        "'extraer_convocatorias_sanitarias_csv' y las descripciones de cada uno de sus campos\n"
        "de salida, y devuelve únicamente la llamada de función correcta.\n"
        "</task>\n\n"
        "<TEXTO_A_ANALIZAR>\n"
        f"{texto}\n"
        "</TEXTO_A_ANALIZAR>\n"
    )

    return base


# ───────── HELPERS: EXTRAER FUNCTION CALL ───────── #

def _extraer_function_call(response) -> dict | None:
    function_call = None

    if getattr(response, "function_calls", None):
        if response.function_calls:
            function_call = response.function_calls[0]

    if function_call is None:
        candidates = getattr(response, "candidates", []) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", None) or []
            for part in parts:
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    function_call = fc
                    break
            if function_call is not None:
                break

    if function_call is None:
        return None

    args = dict(function_call.args or {})
    return args


def _llamar_modelo_y_obtener_convocatorias(
    texto: str,
    usar_ejemplos: bool,
    origen: str = "",
) -> list[dict]:
    global requests_done

    if requests_done >= RPD:
        print("Se ha alcanzado el límite diario de peticiones (RPD). No se hacen más llamadas.")
        return []

    prompt = _construir_prompt(texto, usar_ejemplos=usar_ejemplos)

    print(f"  → Llamando al modelo (usar_ejemplos={usar_ejemplos})...")
    if origen:
        print(f"    Origen: {origen}")

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config,
        )
        requests_done += 1

        args = _extraer_function_call(response)
        if args is None:
            print("  ⚠️ No function call found en esta respuesta.")
            return []

        convocatorias = args.get("convocatorias", []) or []
        print(f"  → Convocatorias devueltas por el modelo: {len(convocatorias)}")
        return convocatorias

    except Exception as e:
        print(f"  ❌ Error en la llamada al modelo: {repr(e)}")
        return []

    finally:
        time.sleep(DELAY_BETWEEN_REQUESTS)


# ───────── BUCLE PRINCIPAL ───────── #

convocatorias_totales = []

for idx, entrada in enumerate(entradas, start=1):
    if requests_done >= RPD:
        print("Se ha alcanzado el límite diario de peticiones (RPD). Deteniendo el proceso.")
        break

    texto = entrada["contenido"]
    enlace = entrada["id"]

    print(f"\n=== PROCESANDO TEXTO {idx}/{len(entradas)} ===")
    if enlace:
        print(f"Origen: {enlace}")

    try:
        # Primer intento: sin ejemplos
        convocatorias = _llamar_modelo_y_obtener_convocatorias(
            texto=texto,
            usar_ejemplos=False,
            origen=enlace,
        )

        # Si devuelve más de 2, reintentamos con ejemplos
        if len(convocatorias) > 2:
            print(
                f"  ⚠️ El modelo devolvió {len(convocatorias)} convocatorias "
                f"(más de 2). Reintentando con ejemplos de tool_ejemplos.py..."
            )

            convocatorias = _llamar_modelo_y_obtener_convocatorias(
                texto=texto,
                usar_ejemplos=True,
                origen=enlace,
            )

        # Desde aquí NO saneamos nada: se guarda lo que devuelva el modelo
        print(f"  → Convocatorias finales que se guardarán: {len(convocatorias)}")

        for conv in convocatorias:
            conv["_ORIGEN_ENLACE"] = enlace

        convocatorias_totales.extend(convocatorias)

    except Exception as e:
        print(f"❌ Error procesando TEXTO {idx}/{len(entradas)} (Origen: {enlace}): {repr(e)}")


# ───────── GUARDAR CSV FINAL ───────── #

print(f"\nTotal convocatorias de todos los textos: {len(convocatorias_totales)}")

output_path = "convocatorias_filtro_nacional.csv"
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=",") # Delimitado por coma formato que recibe zoho
    writer.writerow(header)
    for conv in convocatorias_totales:
        row = [conv.get(col, "") or "" for col in header]
        writer.writerow(row)

print(f"CSV guardado en {output_path}")



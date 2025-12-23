# 3_api_call/GOOGLE_FUNCTIONAL/google_calling_textos_paginas.py

import os
import csv
from dotenv import load_dotenv

from google import genai
from google.genai import types

from tool_convocatorias import extraer_convocatorias_sanitarias
from step3_api_call.google_functional.texto_pruebas import texto

    # header = [
    #     "AMBITO_TERRITORIAL_RESUMIDO",
    #     "ORGANO_CONVOCANTE",
    #     "TITULO",
    #     "FECHA_APERTURA",
    #     "FECHA_CIERRE",
    #     "REQUISITOS",
    #     "CREDITOS",
    #     "TITULO_PROPIO",
    #     "LINK_REQUISITOS",
    #     "LINK_APLICACION",
    #     "PERFIL",
    #     "TITULACION_REQUERIDA",
    #     "TIPO_PROCESO",
    # ]
# ───────── CONFIGURACIÓN CLIENTE ───────── #

load_dotenv("API_GOOGLE.env")

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY no está definida en API_GOOGLE.env ni en el entorno")

client = genai.Client(api_key=API_KEY)


# ───────── TOOLS + CONFIG ───────── #

# Tu función declarada como JSON-schema ya la tienes en tool_convocatorias.py
tool = types.Tool(function_declarations=[extraer_convocatorias_sanitarias])

config = types.GenerateContentConfig(
    tools=[tool],
    temperature=0.0,
    # Desactivamos la ejecución automática para poder leer nosotros la function_call
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",  # fuerza a que el modelo devuelva llamadas a funciones
            allowed_function_names=["extraer_convocatorias_sanitarias_csv"],
        )
    ),
)
#TAMBIEN EXTRAIGO HEADER DE tool_convocatorias.py para evitar reescribir cod.

convocatoria_schema= (extraer_convocatorias_sanitarias["parameters"]["properties"]["convocatorias"]["items"])
header = list(convocatoria_schema.get("required",[]))
# ───────── TEXTO DE ENTRADA ───────── #

prompt = (
    "Eres un asistente que SOLO debe usar la función 'extraer_convocatorias_sanitarias_csv' "
    "definida en las tools para extraer convocatorias de ENFERMERÍA o TCAE a partir del texto "
    "que te paso.\n\n"

    "Debes seguir OBLIGATORIAMENTE todos los pasos y reglas definidos en la descripción de la "
    "función 'extraer_convocatorias_sanitarias_csv'. Si en algún momento no puedes cumplir "
    "alguna de esas reglas (por ejemplo, porque no hay perfiles de enfermería/TCAE, porque no "
    "es empleo público o porque el plazo no está abierto ni es bolsa permanente), debes devolver "
    "exactamente convocatorias=[].\n\n"

    "Recuerda especialmente que:\n"
    "- Solo son válidas las convocatorias de empleo público (personal estatutario, funcionario, "
    "  laboral, interino, bolsas de empleo, concursos, oposiciones, concurso-oposición).\n"
    "- Solo se consideran los perfiles de ENFERMERÍA o TCAE. Si no hay ninguno de esos perfiles "
    "  en el texto, debes devolver convocatorias=[].\n"
    "- En páginas tipo administracion.gob.es, TODO lo que aparezca después de la frase "
    "  'Quizá también te interesen otras convocatorias...' (o variantes en minúsculas) son "
    "  sugerencias externas que debes ignorar completamente. SOLO se analiza el bloque de "
    "  'Detalle de convocatoria' anterior a esa frase.\n"
    "- Todas las denominaciones de enfermería (incluyendo especialidades) deben agruparse en "
    "  UNA ÚNICA convocatoria con PERFIL='enfermeria'.\n"
    "- Todas las denominaciones de TCAE/Auxiliar de Enfermería deben agruparse en UNA ÚNICA "
    "  convocatoria con PERFIL='tcae'.\n"
    "- Por cada texto de entrada SOLO puedes devolver como máximo DOS convocatorias en el "
    "  array 'convocatorias': como mucho UNA de enfermería y UNA de TCAE.\n\n"

    "Antes de responder, debes hacer un CHEQUEO FINAL del array 'convocatorias' que vayas a "
    "devolver y asegurarte de que:\n"
    "- No tiene más de 2 elementos.\n"
    "- No hay más de una convocatoria con PERFIL='enfermeria'.\n"
    "- No hay más de una convocatoria con PERFIL='tcae'.\n"
    "Si hubiera más, debes eliminar las sobrantes y quedarte únicamente con una por perfil "
    "ANTES de devolver la llamada de función.\n\n"

    "Tu respuesta debe consistir EXCLUSIVAMENTE en UNA ÚNICA llamada a la función "
    "'extraer_convocatorias_sanitarias_csv', con el argumento 'convocatorias' rellenado "
    "según el esquema. No escribas código Python, ni texto explicativo, ni ningún otro "
    "contenido fuera de esa llamada de función.\n\n"

    "TEXTO A ANALIZAR:\n"

    f"{texto}"
)


# ───────── LLAMADA AL MODELO ───────── #

response = client.models.generate_content(
    model="gemini-2.0-flash",  # puedes usar también gemini-2.0-flash-lite si quieres
    contents=prompt,
    config=config,
)


# ───────── LOCALIZAR LA FUNCTION_CALL ───────── #

function_call = None

# 1) API nueva: response.function_calls (cuando automatic_function_calling está desactivado)
if getattr(response, "function_calls", None):
    if response.function_calls:
        function_call = response.function_calls[0]

# 2) Fallback: buscar en candidates/parts (por si acaso)
if function_call is None and response.candidates:
    for cand in response.candidates:
        for part in cand.content.parts:
            fc = getattr(part, "function_call", None)
            if fc is not None:
                function_call = fc
                break
        if function_call is not None:
            break


# ───────── PROCESAR RESULTADO ───────── #

if function_call is None:
    print("No function call found in the response.\n")
    print("Texto devuelto por el modelo (response.text):")
    print(response.text)
else:
    # Los argumentos ya vienen como dict (no hay que hacer json.loads ni nada)
    args = dict(function_call.args or {})
    convocatorias = args.get("convocatorias", []) or []

    print(f"Convocatorias devueltas: {len(convocatorias)}\n")
    print("CABECERA CSV:")
    print(",".join(header))
    print()

    for i, conv in enumerate(convocatorias, start=1):
        print(f"=== CONVOCATORIA {i} ===")
        for col in header:
            print(f"{col}: {conv.get(col, '')}")
        print()

    # ── Guardar CSV en disco ── #
    output_path = "convocatorias.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for conv in convocatorias:
            row = [conv.get(col, "") or "" for col in header]
            writer.writerow(row)

    print(f"CSV guardado en {output_path}")

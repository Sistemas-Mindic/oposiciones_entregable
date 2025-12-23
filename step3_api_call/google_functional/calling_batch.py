# 3_api_call/GOOGLE_FUNCTIONAL/google_calling_textos_paginas_batch.py

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
    reader = csv.DictReader(f)
    filas = list(reader)
    print("Cabeceras detectadas en el CSV (NUEVO):", reader.fieldnames)

if not filas:
    raise RuntimeError(f"El CSV de entrada '{CSV_INPUT_PATH}' está vacío.")

entradas = []
for fila in filas:
    contenido = fila.get("contenido_pagina")
    if not contenido:
        continue

    enlace = (
        fila.get("Enlace")
        or fila.get("enlace")
        or fila.get("url")
        or fila.get("URL")
        or ""
    )

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

# Configuración de la generación (tools + function calling) que se usará en CADA request del batch
gen_config = types.GenerateContentConfig(
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

# Nombre de modelo para Batch API (forma 'models/...'):
MODEL_NAME = "models/gemini-2.5-flash-lite"


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
"You are extremely strict with legal/administrative details and NEVER invent data.\n"
"You ALWAYS respond ONLY via a single call to the tool 'extraer_convocatorias_sanitarias_csv'.\n"
"</role>\n\n"
"<instructions>\n"
"1. Plan (comprensión del documento):\n"
"   - Lee TODO el texto completo, sin saltarte ninguna parte.\n"
"   - Identifica si describe convocatorias de EMPLEO PÚBLICO para ENFERMERÍA o TCAE\n"
"     (personal estatutario, funcionario, laboral, interino, bolsas, oposiciones,\n"
"     concursos, concurso-oposición).\n"
"   - Clasifica mentalmente el tipo de documento entre:\n"
"       * Página de DETALLE de una sola convocatoria.\n"
"       * Página de DETALLE + bloque posterior de 'otras convocatorias' / sugerencias.\n"
"       * Documento con ANEXO / tabla de múltiples puestos de un mismo proceso.\n"
"       * Listado de múltiples referencias (varias 'ref:', 'plazas:', 'fin de plazo:', etc.).\n"
"       * Documento extenso multi-proyecto o multi-puesto (varios bloques largos: 'Proyecto...',\n"
"         'PROYECTO 1', 'PUESTO 1', etc.).\n"
"\n"
"2. Execute (aplicación de reglas):\n"
"   - Aplica TODAS las reglas y pasos definidos en la descripción de la tool\n"
"     'extraer_convocatorias_sanitarias_csv' (incluido el bloque <domain_rules>). Esa\n"
"     descripción es de CUMPLIMIENTO OBLIGATORIO e incluye la definición detallada de\n"
"     cada campo (incluido 'EXTRAIDO_DE').\n"
"   - Usa exclusivamente la información literal del texto. Si un dato no aparece,\n"
"     deja el campo vacío o usa 'NONE' cuando corresponda según el schema.\n"
"\n"
"   - Páginas tipo DETALLE + 'otras convocatorias' (administracion.gob.es y similares):\n"
"       * Localiza el bloque principal de detalle de la convocatoria (descripción, ámbito,\n"
"         órgano convocante, titulación, plazo de presentación, bases, enlaces, etc.).\n"
"       * Trata cualquier texto posterior a frases como\n"
"           'quizá también te interesen otras convocatorias'\n"
"         (en cualquier combinación de mayúsculas/minúsculas) como un CORTE DURO:\n"
"           - Solo analizas el bloque anterior (Detalle de convocatoria principal).\n"
"           - Ignoras COMPLETAMENTE todo lo que venga después (otras convocatorias sugeridas),\n"
"             aunque haya muchas referencias a ENFERMERÍA/TCAE o varias 'ref: XXXXX'.\n"
"\n"
"   - ANEXOS / tablas de múltiples puestos (un mismo proceso con muchas categorías):\n"
"       * Considera que todo el documento describe UN único proceso selectivo.\n"
"       * Revisa todas las filas/categorías y detecta si hay al menos alguna de ENFERMERÍA\n"
"         y/o alguna de TCAE.\n"
"       * Agrupa toda la información relevante de ENFERMERÍA en UNA única convocatoria\n"
"         PERFIL='enfermeria', y toda la de TCAE/Auxiliar en UNA única convocatoria\n"
"         PERFIL='tcae'.\n"
"\n"
"   - Listados de múltiples referencias (muchas 'ref:', 'plazas:', 'fin de plazo:', etc.):\n"
"       * Considera cada bloque coherente de campos ('ref:', 'plazas:', 'fin de plazo:',\n"
"         'titulación:', 'ubicación:', 'órgano convocante:', etc.) como una posible\n"
"         convocatoria independiente.\n"
"       * Identifica qué referencias corresponden claramente a ENFERMERÍA y cuáles a TCAE.\n"
"       * De todas las referencias de ENFERMERÍA, selecciona SOLO la más representativa\n"
"         (normalmente la primera que aparece con información más completa) y construye\n"
"         una única convocatoria PERFIL='enfermeria'.\n"
"       * De todas las referencias de TCAE/Auxiliar, selecciona SOLO la más representativa\n"
"         y construye una única convocatoria PERFIL='tcae'.\n"
"       * Nunca superes el límite global de 2 convocatorias (1 ENFERMERÍA + 1 TCAE).\n"
"\n"
"   - Documentos extensos multi-proyecto / multi-puesto:\n"
"       * Si el texto contiene varios bloques largos (por ejemplo, proyectos distintos\n"
"         con códigos CPI-XX, 'PROYECTO 1', 'PUESTO 2', etc.), considera cada bloque como\n"
"         una posible unidad (proyecto/puesto).\n"
"       * Detecta qué bloques corresponden a ENFERMERÍA y qué bloques a TCAE.\n"
"       * Agrupa todos los bloques de ENFERMERÍA en UNA única convocatoria\n"
"         PERFIL='enfermeria' y todos los de TCAE en UNA única convocatoria PERFIL='tcae',\n"
"         eligiendo siempre el bloque más representativo de cada perfil (normalmente el primero\n"
"         o el que tiene descripción más completa) y descartando el resto.\n"
"\n"
"   - Agrupación por perfil (regla central):\n"
"       * Todas las denominaciones de ENFERMERÍA (incluidas especialidades) se agrupan en\n"
"         UNA sola convocatoria con PERFIL='enfermeria'.\n"
"       * Todas las denominaciones de TCAE/Auxiliar de Enfermería se agrupan en UNA sola\n"
"         convocatoria con PERFIL='tcae'.\n"
"\n"
"   - Campo EXTRAIDO_DE:\n"
"       * Para cada convocatoria, rellena el campo EXTRAIDO_DE con la URL principal desde\n"
"         la que se ha obtenido la información (por ejemplo, 'url_detalle' de\n"
"         administracion.gob.es o la URL del boletín/PDF donde están las bases).\n"
"       * Si no se puede identificar claramente una URL principal para esa convocatoria,\n"
"         deja EXTRAIDO_DE vacío.\n"
"\n"
"3. Validate (comprobaciones finales):\n"
"   - Antes de devolver la función, revisa el array 'convocatorias' que has construido:\n"
"       * Asegúrate de que SOLO incluye empleo público de ENFERMERÍA/TCAE con plazo abierto\n"
"         o bolsa permanente (no empleo privado, no noticias, no formación sin plaza).\n"
"       * Si no hay ninguna convocatoria válida → convocatorias=[].\n"
"       * El array 'convocatorias' debe tener 0, 1 o 2 elementos (NUNCA más).\n"
"       * Como mucho UNA convocatoria con PERFIL='enfermeria' y UNA con PERFIL='tcae'.\n"
"       * Si has identificado varias posibles convocatorias del mismo perfil, quédate solo\n"
"         con la más representativa y DESCARTA las demás ANTES de devolver la llamada.\n"
"       * Comprueba que cada objeto de 'convocatorias' incluye TODOS los campos requeridos\n"
"         por el schema de la tool (incluyendo EXTRAIDO_DE).\n"
"\n"
"4. Format (salida obligatoria):\n"
"   - Tu respuesta DEBE consistir EXCLUSIVAMENTE en UNA ÚNICA llamada a la función\n"
"     'extraer_convocatorias_sanitarias_csv', con el argumento 'convocatorias' relleno\n"
"     según el schema que te proporciona el sistema.\n"
"   - No escribas código Python, ni explicaciones, ni comentarios, ni ningún otro texto libre.\n"
"   - Ejemplo de caso sin convocatorias válidas (solo a modo ilustrativo):\n"
"       extraer_convocatorias_sanitarias_csv(convocatorias=[])\n"
"   - En cualquier caso real, devuelve SIEMPRE una única tool call con el array 'convocatorias'\n"
"     correctamente construido.\n"
"</instructions>\n\n"
"<constraints>\n"
"- Verbosity: mínima en lenguaje natural (NO generes explicación; solo la tool call).\n"
"- Tone: técnico, jurídico-administrativo y muy preciso, respetando estrictamente las\n"
"  definiciones del schema de la tool y las reglas de negocio.\n"
"</constraints>\n\n"
"<output_format>\n"
"Tu salida explícita debe ser únicamente una llamada de función válida para el sistema\n"
"de herramientas, con esta forma general:\n"
"  extraer_convocatorias_sanitarias_csv(\n"
"      convocatorias=[ {...}, {...} ]\n"
"  )\n"
"sin texto adicional antes ni después.\n"
"</output_format>\n"

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
    """
    Recibe un objeto GenerateContentResponse y devuelve los args
    de la primera function_call encontrada, o None.
    """
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


# ───────── CREACIÓN DE INLINE REQUESTS PARA BATCH ───────── #

def _crear_inline_requests(entradas_local, usar_ejemplos: bool) -> list[dict]:
    """
    Construye la lista de GenerateContentRequest que se pasará como src al Batch API.
    Cada item incluye: contents (prompt) + config (tools, function calling…).
    """
    inline_requests = []
    for entrada in entradas_local:
        texto = entrada["contenido"]
        prompt = _construir_prompt(texto, usar_ejemplos=usar_ejemplos)

        inline_requests.append(
            {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "config": gen_config,
            }
        )

    return inline_requests


# ───────── FUNCIONES PARA EJECUTAR UN BATCH Y LEER RESPUESTAS ───────── #

def _esperar_a_terminar_batch(job_name: str) -> object:
    """
    Hace polling hasta que el batch job termina (SUCCEEDED/FAILED/CANCELLED/EXPIRED)
    y devuelve el objeto batch_job final.
    """
    completed_states = {
        "JOB_STATE_SUCCEEDED",
        "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED",
        "JOB_STATE_EXPIRED",
    }

    print(f"\nPolling estado para batch job: {job_name}")
    batch_job = client.batches.get(name=job_name)
    while batch_job.state.name not in completed_states:
        print(f"  Estado actual: {batch_job.state.name}")
        time.sleep(30)
        batch_job = client.batches.get(name=job_name)

    print(f"Batch job terminado con estado: {batch_job.state.name}")
    if batch_job.state.name == "JOB_STATE_FAILED":
        print(f"Error del batch job: {batch_job.error}")
    return batch_job


def _procesar_batch_responses(batch_job, n_entradas: int) -> list[list[dict]]:
    """
    Dado un batch_job ya terminado (JOB_STATE_SUCCEEDED),
    devuelve una lista `convocatorias_por_idx` de longitud n_entradas,
    donde cada posición es la lista de convocatorias devueltas para ese índice.
    """
    convocatorias_por_idx: list[list[dict]] = [[] for _ in range(n_entradas)]

    if not batch_job.dest or not getattr(batch_job.dest, "inlined_responses", None):
        print("⚠️ Batch job no contiene inlined_responses.")
        return convocatorias_por_idx

    responses = batch_job.dest.inlined_responses
    if len(responses) != n_entradas:
        print(
            f"⚠️ Número de respuestas ({len(responses)}) "
            f"distinto del número de entradas ({n_entradas})."
        )

    for idx, inline_response in enumerate(responses):
        if idx >= n_entradas:
            break

        print(f"\n--- Procesando respuesta batch índice {idx} ---")

        if getattr(inline_response, "error", None):
            print(f"  ❌ Error en respuesta {idx}: {inline_response.error}")
            convocatorias_por_idx[idx] = []
            continue

        resp = getattr(inline_response, "response", None)
        if resp is None:
            print("  ⚠️ inline_response.response es None.")
            convocatorias_por_idx[idx] = []
            continue

        args = _extraer_function_call(resp)
        if args is None:
            print("  ⚠️ No se encontró function_call en esta respuesta.")
            convocatorias_por_idx[idx] = []
            continue

        convocatorias = args.get("convocatorias", []) or []
        print(f"  → Convocatorias devueltas: {len(convocatorias)}")
        convocatorias_por_idx[idx] = convocatorias

    return convocatorias_por_idx


# ───────── BATCH PRINCIPAL (SIN EJEMPLOS) ───────── #

if not entradas:
    print("No hay textos con contenido_pagina en el CSV. Nada que procesar.")
    exit(0)

print("\nCreando batch principal (sin ejemplos)...")
inline_requests_1 = _crear_inline_requests(entradas, usar_ejemplos=False)

batch_job_1 = client.batches.create(
    model=MODEL_NAME,
    src=inline_requests_1,
    config={"display_name": "convocatorias-step1-batch-sin-ejemplos"},
)

job_name_1 = batch_job_1.name
print(f"Batch job principal creado: {job_name_1}")

batch_job_1 = _esperar_a_terminar_batch(job_name_1)

if batch_job_1.state.name != "JOB_STATE_SUCCEEDED":
    print("El batch principal no ha terminado con éxito. No se generará CSV.")
    exit(1)

convocatorias_por_idx = _procesar_batch_responses(batch_job_1, len(entradas))

# Detectar índices problemáticos (más de 2 convocatorias) para reintentar con ejemplos
indices_problema = [
    idx for idx, convs in enumerate(convocatorias_por_idx) if len(convs) > 2
]

print(f"\nÍndices con más de 2 convocatorias (reintento con ejemplos): {indices_problema}")


# ───────── BATCH SECUNDARIO (CON EJEMPLOS) SOLO PARA PROBLEMÁTICOS ───────── #

if indices_problema:
    # Construimos una lista de "entradas" solo para esos índices
    entradas_problema = [entradas[idx] for idx in indices_problema]

    print("\nCreando batch de reintento (con ejemplos few-shot)...")
    inline_requests_2 = _crear_inline_requests(entradas_problema, usar_ejemplos=True)

    batch_job_2 = client.batches.create(
        model=MODEL_NAME,
        src=inline_requests_2,
        config={"display_name": "convocatorias-step1-batch-con-ejemplos"},
    )

    job_name_2 = batch_job_2.name
    print(f"Batch job de reintento creado: {job_name_2}")

    batch_job_2 = _esperar_a_terminar_batch(job_name_2)

    if batch_job_2.state.name == "JOB_STATE_SUCCEEDED":
        convs_reintento = _procesar_batch_responses(batch_job_2, len(entradas_problema))

        # Sobrescribimos las convocatorias de esos índices con las del reintento
        for local_idx, idx_global in enumerate(indices_problema):
            convocatorias_por_idx[idx_global] = convs_reintento[local_idx]
    else:
        print("El batch de reintento no ha terminado con éxito. Se mantienen las convocatorias originales.")


# ───────── CONSTRUIR LISTA FINAL DE CONVOCATORIAS ───────── #

convocatorias_totales: list[dict] = []

for idx, convs in enumerate(convocatorias_por_idx):
    enlace = entradas[idx]["id"]
    print(f"\nEntrada {idx}: enlace={enlace} | convocatorias={len(convs)}")

    # Igual que antes: no saneamos nada más; solo añadimos _ORIGEN_ENLACE
    for conv in convs:
        conv["_ORIGEN_ENLACE"] = enlace
        convocatorias_totales.append(conv)

print(f"\nTotal convocatorias de todos los textos: {len(convocatorias_totales)}")


# ───────── GUARDAR CSV FINAL ───────── #

output_path = "convocatorias_de_step1_nacional_v2_batch.csv"
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=";")
    writer.writerow(header)
    for conv in convocatorias_totales:
        row = [conv.get(col, "") or "" for col in header]
        writer.writerow(row)

print(f"CSV guardado en {output_path}")

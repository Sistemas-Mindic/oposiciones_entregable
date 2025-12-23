import os
import csv
import time
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Tool grande de extracción (prompt maestro con patrones dentro)
from step2_tool_fine import extraer_convocatorias_sanitarias

# Tool 1: analizador/filtro (tiene_perfil_sanitario, es_descartable)
from step1_analizar_doc import analizar_documento_sanitario


# ───────── CONFIG ENTRADA CSV ───────── #
#CSV_INPUT_PATH = "convocatorias_detalle_age_v4.csv" #este es el de convocatorias de nacional
CSV_INPUT_PATH = "extraccion_data_v3_2.csv" #generalitat todos


# ───────── LEER CSV Y CREAR ENTRADAS ───────── #

with open(CSV_INPUT_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=",")  # Nacional
    filas = list(reader)
    print("Cabeceras detectadas en el CSV (NUEVO):", reader.fieldnames)

if not filas:
    raise RuntimeError(f"El CSV de entrada '{CSV_INPUT_PATH}' está vacío.")

entradas = []
for fila in filas:
    contenido = fila.get("contenido_pagina")
    if not contenido:
        continue

    # Campo URL de origen (del CSV) si existiera
    enlace = fila.get("Enlace") or fila.get("enlace") or fila.get("url") or ""
    url_detalle = fila.get("url_detalle") or enlace or ""

    # Leer es_pdf y derivar tipo_fuente
    raw_es_pdf = (
        fila.get("es_pdf")
        or fila.get("ES_PDF")
        or fila.get("esPdf")
        or fila.get("ESPDF")
        or ""
    )
    es_pdf_flag = str(raw_es_pdf).strip().lower()
    if es_pdf_flag in ("true", "1", "sí", "si", "y", "yes"):
        tipo_fuente = "pdf"
    else:
        tipo_fuente = "html"

    entradas.append(
        {
            "contenido": contenido,
            "id": enlace,          # enlace "visible" si lo hubiera
            "origen": fila,        # fila completa original
            "tipo_fuente": tipo_fuente,
            "url_detalle": url_detalle,  # URL que queremos conservar y usar en prompts
        }
    )

print(f"Textos a procesar con Gemini (NUEVO CSV): {len(entradas)}")


# ───────── CONFIGURACIÓN CLIENTE GEMINI ───────── #

load_dotenv("API_GOOGLE.env")

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY no está definida en API_GOOGLE.env ni en el entorno")

client = genai.Client(api_key=API_KEY)

# ───────── TOOLS GEMINI ───────── #

# Obtenemos los nombres de función directamente del schema para evitar errores
ANALIZADOR_FUNC_NAME = analizar_documento_sanitario["name"]
EXTRACCION_FUNC_NAME = extraer_convocatorias_sanitarias["name"]

# Tool de extracción
tool_extraccion = types.Tool(function_declarations=[extraer_convocatorias_sanitarias])
config_extraccion = types.GenerateContentConfig(
    tools=[tool_extraccion],
    temperature=0.0,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[EXTRACCION_FUNC_NAME],
        )
    ),
)

# Tool de análisis/filtro
tool_analizador = types.Tool(function_declarations=[analizar_documento_sanitario])
config_analizador = types.GenerateContentConfig(
    tools=[tool_analizador],
    temperature=0.0,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[ANALIZADOR_FUNC_NAME],
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

# Añadimos columna para conservar la URL original del detalle
if "_ORIGEN_ENLACE" not in header:
    header.append("_ORIGEN_ENLACE")


# ───────── PROMPT PARA LA TOOL DE ANÁLISIS ───────── #

def _construir_prompt_analizador(
    texto: str,
    tipo_fuente: str,
    origen_url: str = "",
) -> str:
    """
    Prompt estructurado para la tool analizar_documento_sanitario.

    Objetivo:
      - tiene_perfil_sanitario: True si el texto es de empleo público para
        ENFERMERÍA o TCAE/Auxiliar de Enfermería (incluyendo especialidades
        y perfiles sociosanitarios muy próximos).
      - es_descartable: True solo si NO hay contenido relevante sanitario
        (ni enfermería ni TCAE) o el texto es puro ruido.
    """
    return (
        "<role>\n"
        "Eres un analizador especializado de textos de empleo público.\n"
        "Tu única tarea es decidir si el documento tiene perfil sanitario\n"
        "relevante para ENFERMERÍA y/o TCAE/Auxiliares de Enfermería.\n"
        "SIEMPRE respondes SOLO llamando a la función\n"
        "'analizar_documento_sanitario'.\n"
        "</role>\n\n"

        "<tool_schema>\n"
        "La función analizar_documento_sanitario tiene estos campos:\n"
        "- tiene_perfil_sanitario (bool):\n"
        "    * True → el texto describe o afecta a empleo público\n"
        "      de ENFERMERÍA o TCAE/Auxiliar de Enfermería (incluyendo\n"
        "      especialidades de enfermería y perfiles sociosanitarios\n"
        "      muy próximos, como atención sociosanitaria y dependencia).\n"
        "    * False → no hay contenido laboral relevante para estos\n"
        "      perfiles.\n"
        "- es_descartable (bool):\n"
        "    * True → el documento puede ignorarse en el pipeline\n"
        "      (no sanitario, o solo ruido legal/cookies, etc.).\n"
        "    * False → el documento debe pasar a la siguiente fase\n"
        "      de extracción detallada.\n"
        "</tool_schema>\n\n"

        "<patterns>\n"
        "Utiliza estos PATRONES como guía POSITIVA. Si aparecen en el\n"
        "título, cuerpo, descripción, titulación, requisitos o texto,\n"
        "el documento tiene perfil sanitario:\n"
        "\n"
        "ENFERMERÍA (PATRONES_ENFERMERO):\n"
        "- 'ENFERMERO', 'ENFERMERA', 'ENFERMERÍA'.\n"
        "- 'GRADO EN ENFERMERIA', 'GRADO UNIVERSITARIO EN ENFERMERIA'.\n"
        "- 'DIPLOMADO EN ENFERMERIA', 'DIPLOMADO UNIVERSITARIO EN ENFERMERIA'.\n"
        "- 'DIPLOMADO-GRADO EN ENFERMERIA'.\n"
        "- Abreviaturas históricas: 'ATS', 'ATS/DUE', 'ATS DUE', 'ATS-DE',\n"
        "  'AYUDANTE TECNICO SANITARIO', 'DUE'.\n"
        "- Categorías como 'DIPLOMADOS Y TECNICOS MEDIOS, ESPECIALIDAD ATS/DE'.\n"
        "- Especialistas: 'ENFERMERO ESPECIALISTA', 'ENFERMERIA FAMILIAR Y\n"
        "  COMUNITARIA', 'ENFERMERIA DE SALUD MENTAL', 'ENFERMERIA GERIATRICA',\n"
        "  'MATRONA', etc.\n"
        "\n"
        "TCAE / AUXILIAR (PATRONES_TCAE_AUX_ENFERMERIA):\n"
        "- 'AUXILIAR DE ENFERMERIA', 'AUXILIAR ENFERMERIA',\n"
        "  'AUXILIARES DE ENFERMERIA'.\n"
        "- 'TECNICO EN CUIDADOS AUXILIARES DE ENFERMERIA', 'TCAE',\n"
        "  'TECNICO AUXILIAR DE ENFERMERIA', 'TECNICO AUXILIAR DE CLINICA',\n"
        "  'TECNICO AUXILIAR DE PSIQUIATRIA'.\n"
        "- Perfiles sociosanitarios muy próximos:\n"
        "  'TECNICO EN ATENCION A PERSONAS EN SITUACION DE DEPENDENCIA',\n"
        "  'TECNICO EN ATENCION SOCIOSANITARIA', y los diferentes\n"
        "  certificados de profesionalidad en atención sociosanitaria.\n"
        "\n"
        "Regla general TCAE/Auxiliar:\n"
        "- Si aparece ENFERMERIA + (TECNICO/TECNICA/TECNICOS o\n"
        "  AUXILIAR/AUXILIARES), lo consideras perfil TCAE/Auxiliar.\n"
        "\n"
        "Ten en cuenta variaciones de acentos, género y número.\n"
        "</patterns>\n\n"

        "<plazas_y_bolsas>\n"
        "En este paso PREVIO debes IGNORAR por completo los campos de plazas\n"
        "que aparezcan en el texto (por ejemplo: 'Convocadas:0 Libres:0\n"
        "Internas:0 Discapacidad General:0 Discapacidad Intelectual:0').\n"
        "- Esos valores a menudo están mal rellenados en bolsas sanitarias.\n"
        "- Nunca uses que sean 0 para marcar el documento como descartable.\n"
        "- Si el documento habla de una bolsa de empleo sanitaria o de una\n"
        "  convocatoria de enfermería/TCAE, márcalo como NO descartable\n"
        "  aunque todas las plazas numéricas sean 0.\n"
        "</plazas_y_bolsas>\n\n"

        "<rules>\n"
        "- Si el texto describe una convocatoria, bolsa, oposición,\n"
        "  concurso o concurso-oposición para alguno de estos patrones,\n"
        "  devuelve:\n"
        "    analizar_documento_sanitario(\n"
        "        tiene_perfil_sanitario=True,\n"
        "        es_descartable=False\n"
        "    )\n"
        "- Si el texto trata claramente de otros cuerpos sin relación\n"
        "  (administrativos, arquitectos, profesores, policía, etc.) y no\n"
        "  aparece ningún término de los patrones anteriores, devuelve:\n"
        "    analizar_documento_sanitario(\n"
        "        tiene_perfil_sanitario=False,\n"
        "        es_descartable=True\n"
        "    )\n"
        "- Si hay mezcla de varias categorías y ALGUNA es de\n"
        "  ENFERMERÍA/TCAE, sé INCLUSIVO:\n"
        "    tiene_perfil_sanitario=True, es_descartable=False.\n"
        "- Nunca escribas texto libre. Tu respuesta debe ser SOLO una\n"
        "  llamada a la función 'analizar_documento_sanitario'.\n"
        "</rules>\n\n"

        "<task>\n"
        "Analiza el siguiente documento y devuelve únicamente la llamada\n"
        "a analizar_documento_sanitario con los dos flags correctos.\n"
        "</task>\n\n"
        "<ENTRADA_DOCUMENTO>\n"
        f"TIPO_FUENTE: {tipo_fuente}\n"
        f"URL_ORIGEN: {origen_url}\n\n"
        f"{texto}\n"
        "</ENTRADA_DOCUMENTO>\n"
    )


# ───────── PROMPT PARA LA TOOL DE EXTRACCIÓN ───────── #

def _construir_prompt(
    texto: str,
    tipo_fuente: str,
    origen_url: str,
) -> str:
    base = (
        "<role>\n"
        "You are a specialized assistant for extracting structured public-employment\n"
        "calls (convocatorias de empleo público) for ENFERMERÍA and TCAE from noisy Spanish\n"
        "administrative texts (administracion.gob.es, boletines oficiales, resoluciones, etc.).\n"
        "You ALWAYS respond ONLY via a single call to the tool 'extraer_convocatorias_sanitarias_csv'.\n"
        "You are precise, analytical and persistent.\n"
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
        "     'extraer_convocatorias_sanitarias_csv'.\n"
        "   - Usa exclusivamente la información literal del texto. Si un dato no aparece,\n"
        "     déjalo vacío o usa 'NONE' cuando corresponda según el schema.\n"
        "   - En páginas tipo administracion.gob.es, trata la frase\n"
        "       'quizá también te interesen otras convocatorias' (y variantes)\n"
        "     como un CORTE DURO: sólo analizas el bloque anterior.\n"
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
        "       * Si URL_ORIGEN contiene 'ofertasempleopublico/detalleEmpleo.htm', se trata de\n"
        "         una ficha de detalle de administracion.gob.es: en ese caso el número final de\n"
        "         elementos en 'convocatorias' DEBE ser 0 (si no es empleo válido) o EXACTAMENTE 1.\n"
        "         Nunca 2, 3, 4, etc.\n"
        "       * Si mentalmente has construido más de una convocatoria en ese caso, DEBES\n"
        "         eliminar todas las que sobren y quedarte sólo con la convocatoria principal\n"
        "         de esa ficha (la categoría que aparece en título/descripcion de la página).\n"
        "\n"
        "4. Format:\n"
        "   - Tu respuesta DEBE consistir EXCLUSIVAMENTE en UNA ÚNICA llamada a la función\n"
        "     'extraer_convocatorias_sanitarias_csv', con el argumento 'convocatorias' rellenado\n"
        "     según el schema que te proporciona el sistema.\n"
        "   - No escribas código Python, ni explicaciones, ni ningún otro texto libre.\n"
        "   - Si no hay convocatorias válidas, debes devolver exactamente:\n"
        "     extraer_convocatorias_sanitarias_csv({\"convocatorias\": []})\n"
        "</instructions>\n\n"

        "<patterns>\n"
        "POSITIVE PATTERN 1 (detalle administracion.gob.es, una sola ficha):\n"
        "- Input prefix: TEXTO_DETALLE:\n"
        "- Output prefix: CALL:\n"
        "Ejemplo resumido:\n"
        "  TEXTO_DETALLE: ficha de detalle 'ENFERMERO ESPECIALISTA: TRABAJO'. El texto dice\n"
        "  que se convoca bolsa de empleo de 'enfermero/a especialista del trabajo' y en las\n"
        "  disposiciones aparece una resolución que menciona varias categorías:\n"
        "  'enfermero/a especialista de salud mental, del trabajo, geriátrica, familiar y\n"
        "  comunitaria y pediátrica'.\n"
        "  CALL: extraer_convocatorias_sanitarias_csv({\"convocatorias\": [ UNA sola entrada\n"
        "  para ENFERMERÍA ESPECIALISTA DEL TRABAJO, PERFIL='enfermeria' ]})\n"
        "Regla asociada:\n"
        "- Aunque la resolución cite varias categorías de enfermería especialista, la ficha de\n"
        "  detalle sólo corresponde a UNA de ellas (la que aparece en la cabecera: título,\n"
        "  descripción, cuerpo). Solo se devuelve UNA convocatoria, la de esa categoría.\n"
        "\n"
        "NEGATIVE PATTERN 1 (anti-ejemplo):\n"
        "- No generes una convocatoria separada por cada categoría mencionada en un listado\n"
        "  general dentro de la misma resolución o de los apartados de 'seguimiento'. Eso\n"
        "  produciría 5–8 convocatorias diferentes para una sola ficha de detalle, lo cual es\n"
        "  incorrecto.\n"
        "\n"
        "Regla fuerte de control:\n"
        "- Si URL_ORIGEN contiene 'ofertasempleopublico/detalleEmpleo.htm' y has construido\n"
        "  mentalmente más de una convocatoria, debes fusionarlas y quedarte sólo con la que\n"
        "  representa la categoría principal de la ficha. El tamaño final de 'convocatorias'\n"
        "  en estos casos es 1 o 0, nunca mayor que 1.\n"
        "</patterns>\n\n"

        "<constraints>\n"
        "- Verbosity: mínima en lenguaje natural (NO generes explicación; solo la tool call).\n"
        "- Tone: técnico y preciso.\n"
        "</constraints>\n\n"

        "<output_format>\n"
        "Tu salida explícita debe ser únicamente una llamada de función válida para el sistema\n"
        "de herramientas, con esta forma general:\n"
        "  extraer_convocatorias_sanitarias_csv(\n"
        "      {\"convocatorias\": [ {...}, {...} ]}\n"
        "  )\n"
        "Sin texto adicional antes ni después.\n"
        "</output_format>\n\n"
        "<task>\n"
        "Lee el siguiente TEXTO_DETALLE completo, aplica el plan (Plan → Execute → Validate → Format),\n"
        "junto con TODAS las reglas de la descripción de la tool y del bloque <patterns>, y\n"
        "devuelve únicamente la llamada de función correcta.\n"
        "</task>\n\n"
        "<TEXTO_DETALLE>\n"
        f"TIPO_FUENTE: {tipo_fuente}\n"
        f"URL_ORIGEN: {origen_url}\n\n"
        f"{texto}\n"
        "</TEXTO_DETALLE>\n"
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


# ───────── LLAMADA AL ANALIZADOR (CON REINTENTOS) ───────── #

def _llamar_analizador(
    texto: str,
    tipo_fuente: str,
    origen: str = "",
    max_reintentos: int = 3,
) -> tuple[bool, bool]:
    """
    Devuelve (tiene_perfil_sanitario, es_descartable).

    Estrategia ante errores:
    - Reintenta en errores 503/UNAVAILABLE/overloaded.
    - Si, tras todos los reintentos, sigue fallando, se adopta una postura
      CONSERVADORA: se considera que puede ser relevante y NO se filtra:
        (tiene_perfil_sanitario=True, es_descartable=False)
    """
    global requests_done

    if requests_done >= RPD:
        print("Se ha alcanzado el límite diario de peticiones (RPD) en analizador.")
        # Por seguridad: no filtramos.
        return True, False

    prompt = _construir_prompt_analizador(
        texto=texto,
        tipo_fuente=tipo_fuente,
        origen_url=origen,
    )

    print("  → Llamando al ANALIZADOR (analizar_documento_sanitario)...")
    if origen:
        print(f"    URL_ORIGEN: {origen}")
    print(f"    Tipo de fuente: {tipo_fuente}")

    for intento in range(1, max_reintentos + 1):
        if requests_done >= RPD:
            print("  ⛔ RPD alcanzado dentro del analizador. Detenemos reintentos.")
            # De nuevo, postura conservadora: no filtramos.
            return True, False

        try:
            print(f"    Intento {intento}/{max_reintentos}...")
            requests_done += 1

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config_analizador,
            )

            args = _extraer_function_call(response)
            if args is None:
                print("  ⚠️ Analizador: no function call encontrada. Por seguridad NO filtramos.")
                time.sleep(DELAY_BETWEEN_REQUESTS)
                return True, False

            tiene = bool(args.get("tiene_perfil_sanitario", False))
            descartable = bool(args.get("es_descartable", False))

            print(f"  → Analizador: tiene_perfil_sanitario={tiene}, es_descartable={descartable}")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            return tiene, descartable

        except Exception as e:
            msg = repr(e)
            print(f"  ❌ Error en la llamada al analizador: {msg}")

            # Errores típicamente recuperables (503, modelo sobrecargado, etc.)
            if ("503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg) and intento < max_reintentos:
                backoff = DELAY_BETWEEN_REQUESTS * (2 ** (intento - 1))
                print(f"  ↪️  Error recuperable (503/UNAVAILABLE). Reintentando tras {backoff:.2f} segundos...")
                time.sleep(backoff)
                continue

            # Otros errores o ya sin más reintentos:
            print("  ⛔ Error no recuperable o alcanzado número máximo de reintentos en ANALIZADOR.")
            print("     Por seguridad, NO filtramos este documento (lo marcamos como relevante).")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            return True, False

    # Si no se devuelve antes (caso muy raro), también postura conservadora:
    return True, False


# ───────── LLAMADA A EXTRACCIÓN (CON REINTENTOS) ───────── #

def _llamar_modelo_y_obtener_convocatorias(
    texto: str,
    tipo_fuente: str,
    origen: str = "",
    max_reintentos: int = 3,
) -> list[dict]:
    """
    Llama a la tool de extracción y devuelve la lista de convocatorias.
    En caso de errores 503/UNAVAILABLE/overloaded, reintenta hasta
    max_reintentos veces con backoff exponencial.
    Si tras los reintentos sigue fallando, devuelve [].
    """
    global requests_done

    if requests_done >= RPD:
        print("Se ha alcanzado el límite diario de peticiones (RPD). No se hacen más llamadas (EXTRACCIÓN).")
        return []

    prompt = _construir_prompt(
        texto=texto,
        tipo_fuente=tipo_fuente,
        origen_url=origen,
    )

    print("  → Llamando al modelo (EXTRACCIÓN)...")
    if origen:
        print(f"    URL_ORIGEN: {origen}")
    print(f"    Tipo de fuente: {tipo_fuente}")

    for intento in range(1, max_reintentos + 1):
        if requests_done >= RPD:
            print("  ⛔ RPD alcanzado dentro de la EXTRACCIÓN. Detenemos reintentos.")
            return []

        try:
            print(f"    Intento {intento}/{max_reintentos}...")
            requests_done += 1

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config_extraccion,
            )

            args = _extraer_function_call(response)
            if args is None:
                print("  ⚠️ No function call found en esta respuesta. Devolvemos lista vacía.")
                time.sleep(DELAY_BETWEEN_REQUESTS)
                return []

            convocatorias = args.get("convocatorias", []) or []
            print(f"  → Convocatorias devueltas por el modelo: {len(convocatorias)}")

            # Pausa estándar antes de otra petición
            time.sleep(DELAY_BETWEEN_REQUESTS)
            return convocatorias

        except Exception as e:
            msg = repr(e)
            print(f"  ❌ Error en la llamada al modelo (extracción): {msg}")

            # Errores típicamente recuperables (503, modelo sobrecargado, etc.)
            if ("503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg) and intento < max_reintentos:
                backoff = DELAY_BETWEEN_REQUESTS * (2 ** (intento - 1))
                print(f"  ↪️  Error recuperable (503/UNAVAILABLE). Reintentando tras {backoff:.2f} segundos...")
                time.sleep(backoff)
                continue

            # Otros errores o ya sin más reintentos
            print("  ⛔ Error no recuperable o alcanzado número máximo de reintentos en EXTRACCIÓN. Devolvemos [].")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            return []

    # Si no ha devuelto antes, por seguridad:
    return []


# ───────── BUCLE PRINCIPAL ───────── #

convocatorias_totales = []
resumen_filas = []  # TEXTO / ANALIZADOR / EXTRACTOR

for idx, entrada in enumerate(entradas, start=1):
    if requests_done >= RPD:
        print("Se ha alcanzado el límite diario de peticiones (RPD). Deteniendo el proceso.")
        break

    texto = entrada["contenido"]
    enlace = entrada["id"]
    tipo_fuente = entrada.get("tipo_fuente", "html")
    url_detalle = entrada.get("url_detalle") or enlace

    print(f"\n=== PROCESANDO TEXTO {idx}/{len(entradas)} ===")
    if enlace:
        print(f"Enlace (CSV): {enlace}")
    if url_detalle:
        print(f"URL_DETALLE usada en prompts: {url_detalle}")
    print(f"Tipo de fuente (desde es_pdf): {tipo_fuente}")

    analizador_count = 0
    extractor_count = 0

    try:
        # 1) Filtro previo: usar URL_DETALLE como URL_ORIGEN
        tiene_perfil, es_descartable = _llamar_analizador(
            texto=texto,
            tipo_fuente=tipo_fuente,
            origen=url_detalle,
        )

        if es_descartable or not tiene_perfil:
            print("  → Documento descartado por el analizador. No se extraen convocatorias.")
            analizador_count = 0
            extractor_count = 0
        else:
            analizador_count = 1

            # 2) Extracción detallada solo si pasa el filtro
            convocatorias = _llamar_modelo_y_obtener_convocatorias(
                texto=texto,
                tipo_fuente=tipo_fuente,
                origen=url_detalle,
            )

            extractor_count = len(convocatorias)
            print(f"  → Convocatorias finales que se guardarán: {len(convocatorias)}")

            for conv in convocatorias:
                conv["_ORIGEN_ENLACE"] = url_detalle

            convocatorias_totales.extend(convocatorias)

    except Exception as e:
        print(f"❌ Error procesando TEXTO {idx}/{len(entradas)} (Origen: {enlace}): {repr(e)}")
        analizador_count = 0
        extractor_count = 0

    resumen_filas.append(
        {
            "texto": idx,
            "analizador": analizador_count,
            "extractor": extractor_count,
        }
    )


# ───────── GUARDAR CSV FINAL ───────── #

print(f"\nTotal convocatorias de todos los textos: {len(convocatorias_totales)}")

output_path = "convocatorias_filtro_nacional_v2_nueva_funcion_TODOS.csv"
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f, delimiter=",")
    writer.writerow(header)
    for conv in convocatorias_totales:
        row = [conv.get(col, "") or "" for col in header]
        writer.writerow(row)

print(f"CSV guardado en {output_path}")

# ───────── TABLA RESUMEN ANALIZADOR / EXTRACTOR ───────── #

print("\nRESUMEN POR TEXTO:")
print("{:<18} {:<15} {:<15}".format("TEXTO_PROCESADO", "ANALIZADOR", "EXTRACTOR"))
for fila in resumen_filas:
    print(
        "{:<18} {:<15} {:<15}".format(
            fila["texto"],
            fila["analizador"],
            fila["extractor"],
        )
    )

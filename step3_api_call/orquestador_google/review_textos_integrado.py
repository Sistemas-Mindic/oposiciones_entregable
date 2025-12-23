# review_textos_integrado.py
# Orquestador completo STEP 0 → STEP 1 → STEP 2 → STEP 3 para convocatorias sanitarias

import os
import csv
import time
import sys


from dotenv import load_dotenv

from google import genai
from google.genai import types

from collections import deque  # ### CAMBIO: para el estimador dinámico de RPM

# ─────────────────────────────────────────────────────────────
# IMPORT DE TOOLS (SOLO SCHEMAS DE FUNCTION CALLING)
# ─────────────────────────────────────────────────────────────

# STEP 0 – Prefiltrado HTML (cortar "otras convocatorias", listados, buscadores…)
from step0_prefiltrado_html import refinar_contenido_principal

# STEP 1 – Triage documental (empleo público + Enfermería/TCAE + trámite descartable)
from step1_analizar_doc import analizar_documento_sanitario

# STEP 2 – Clasificación tipo de proceso
from step2_clasificacion_tipo_convocatoria import clasificar_tipo_proceso_convocatoria

# STEP 3 – Extractores especializados por tipo de proceso
from step3_bolsa_extractor import extraer_convocatorias_bolsa
from step3_oposicion_extractor import extraer_convocatorias_oposicion
from step3_concurso_extractor import extraer_convocatorias_concurso
from step3_concurso_oposicion_extractor import extraer_convocatorias_concurso_oposicion
from step3_otro_extractor import extraer_convocatorias_otro


csv.field_size_limit(sys.maxsize)   # permite celdas enormes
# ─────────────────────────────────────────────────────────────
# CONFIG ENTRADA / SALIDA CSV
# ─────────────────────────────────────────────────────────────

INPUT_DIR = "/Users/AndresFelipe/Desktop/Codigo/PROYECTO_OPOSICIONES/step1_scraping/resultados_scraping"
OUTPUT_DIR = "/Users/AndresFelipe/Desktop/Codigo/PROYECTO_OPOSICIONES/step4_resultados"

CSV_INPUT_PATH = os.path.join(INPUT_DIR, "extraccion_data_todas_comunidades.csv")
CSV_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "resultado_todas_comunidades.csv")


# Cabecera fija (schema de salida + contexto pedido)
BASE_FIELDS = [
    "AMBITO_TERRITORIAL_RESUMIDO",
    "ORGANO_CONVOCANTE",
    "TITULO",
    "FECHA_APERTURA",
    "FECHA_CIERRE",
    "REQUISITOS",
    "CREDITOS",
    "TITULO_PROPIO",
    "LINK_REQUISITOS",
    "LINK_APLICACION",
    "PERFIL",
    "TITULACION_REQUERIDA",
    # Tipo de proceso de la propia convocatoria:
    # BOLSA / OPOSICION / CONCURSO-OPOSICION / CONCURSO / OTRO
    "TIPO_PROCESO",
    # Siempre la url_detalle del CSV de entrada
    "EXTRAIDO_DE",
]

# Campos adicionales de contexto (sin nada sobre PDF/HTML)
EXTRA_FIELDS = [
    "TIPO_PROCESO_CLASIFICADOR",  # bolsa / oposicion / concurso / concurso-oposicion / otro
    "CLASIFICADOR_CONFIANZA",     # alta / media / baja / error_modelo / …
]

CSV_HEADER = BASE_FIELDS + EXTRA_FIELDS


# ─────────────────────────────────────────────────────────────
# CONFIG CLIENTE GEMINI
# ─────────────────────────────────────────────────────────────

load_dotenv("API_GOOGLE.env")
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY no está definida en API_GOOGLE.env ni en el entorno")

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-2.5-flash-lite"

# ─────────────────────────────────────────────────────────────
# LIMITES / RATE LIMIT
# ─────────────────────────────────────────────────────────────
#
# Valores anteriores (free tier clásico):
#   - MAX_REQUESTS_PER_MINUTE = 15
#   - TPM ≈ 250.000
#   - RPD ≈ 1.000
#
# Nuevos límites teóricos para Gemini 2.5 Flash-Lite:
#   - RPM: 4.000
#   - TPM: 4.000.000
#   - RPD: sin límite relevante para este script
#   - Batch Enqueued Tokens: 10.000.000
#
# Usamos un valor "seguro" por debajo del máximo teórico,
# y además un estimador dinámico para adaptarnos a la carga real.

MAX_RPM_CAP = 4000                        # límite teórico del modelo
MAX_REQUESTS_PER_MINUTE = 1200            # ### CAMBIO: modo seguro (~20 req/seg)
DELAY_BETWEEN_CALLS = 60.0 / MAX_REQUESTS_PER_MINUTE  # ~0.05 segundos por llamada

# ─────────────────────────────────────────────────────────────
# ESTIMADOR DINÁMICO DE RPM (añadido)
# ─────────────────────────────────────────────────────────────

_historial_llamadas = deque()

def registrar_llamada():
    """
    Registra una llamada al modelo en una ventana deslizante de 60 segundos.
    """
    ahora = time.time()
    _historial_llamadas.append(ahora)
    # Limpiar registros más antiguos de 60 segundos
    while _historial_llamadas and _historial_llamadas[0] < ahora - 60:
        _historial_llamadas.popleft()

def rpm_actual():
    """
    Calcula el RPM efectivo en los últimos 60 segundos.
    """
    ahora = time.time()
    while _historial_llamadas and _historial_llamadas[0] < ahora - 60:
        _historial_llamadas.popleft()
    return len(_historial_llamadas)

def calcular_delay_dinamico() -> float:
    """
    Ajusta un delay adicional según la carga real (RPM observado) respecto al
    límite seguro configurado en MAX_REQUESTS_PER_MINUTE.
    """
    rpm = rpm_actual()

    # Por debajo del 60% → sin delay extra
    if rpm < MAX_REQUESTS_PER_MINUTE * 0.60:
        return 0.0

    # Entre 60% y 85% → ligero frenado
    if rpm < MAX_REQUESTS_PER_MINUTE * 0.85:
        return 0.02  # 20 ms

    # Entre 85% y 100% → frenar más
    if rpm < MAX_REQUESTS_PER_MINUTE:
        return 0.10  # 100 ms

    # Por encima del límite → pausa clara
    return 0.25  # 250 ms


# ─────────────────────────────────────────────────────────────
# HELPERS COMUNES
# ─────────────────────────────────────────────────────────────

def _parse_bool_es_pdf(raw) -> bool:
    """
    Convierte el valor de es_pdf del CSV a booleano.
    Admite: true/false, verdadero/falso, 1/0, sí/no, etc.
    Si viene vacío o None, se interpreta como False (HTML).
    """
    if raw is None:
        return False
    s = str(raw).strip().lower()
    return s in ("true", "1", "sí", "si", "y", "yes", "verdadero")


def _extraer_function_call(response) -> dict | None:
    """
    Extrae el primer function_call.args de una respuesta de Gemini
    (independientemente de si viene en response.function_calls o en candidates/parts).
    Devuelve un dict con los argumentos o None si no hay function_call.
    """
    function_call = None

    # Caso 1: API nueva (response.function_calls)
    if getattr(response, "function_calls", None):
        if response.function_calls:
            function_call = response.function_calls[0]

    # Caso 2: API "clásica" con candidates -> content -> parts
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

    return dict(function_call.args or {})


def _call_with_retries(prompt: str, config: types.GenerateContentConfig,
                       step_label: str, max_retries: int = 3):
    """
    Envuelve client.models.generate_content con reintentos (máximo 3).

    - 503 / UNAVAILABLE / overloaded  → backoff exponencial corto y reintenta.
    - 429 / RESOURCE_EXHAUSTED       → cuota por minuto agotada; backoff moderado.
    - Tras cada llamada EXITOSA se respeta DELAY_BETWEEN_CALLS (≈4 s para 15 RPM,
      ahora adaptado a 1200 RPM con delay dinámico).
    - Si tras los reintentos sigue fallando, devuelve None.
    """
    for intento in range(1, max_retries + 1):
        try:
            print(f"    [{step_label}] Llamada a modelo (intento {intento}/{max_retries})...")
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config,
            )

            # Respetar rate limit local:
            # 1) registramos la llamada
            # 2) aplicamos delay fijo + delay dinámico según carga observada
            registrar_llamada()  # ### CAMBIO
            delay_auto = calcular_delay_dinamico()  # ### CAMBIO
            time.sleep(DELAY_BETWEEN_CALLS + delay_auto)  # ### CAMBIO

            return response

        except Exception as e:
            msg = repr(e)
            print(f"    ❌ Error en {step_label} intento {intento}: {msg}")

            # --- Caso 429 / RESOURCE_EXHAUSTED (cuota por minuto agotada) ---
            if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
                if intento < max_retries:
                    backoff = 5  # ### CAMBIO: antes 65s, ahora más razonable
                    print(f"    ↪️ Cuota agotada en {step_label}. Reintento tras {backoff} s...")
                    time.sleep(backoff)
                    continue

                print(f"    ⛔ Cuota agotada en {step_label} tras varios intentos. Se omite esta llamada.")
                return None

            # --- Caso 503 / modelo sobrecargado (recuperable) ---
            if ("503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg) and intento < max_retries:
                backoff = 2 ** (intento - 1)  # 1s, 2s, 4s...
                print(f"    ↪️ Modelo sobrecargado en {step_label}. Reintento tras {backoff} s...")
                time.sleep(backoff)
                continue

            # --- Otros errores o último intento ---
            print(f"    ⛔ Error no recuperable en {step_label}. No se reintenta más.")
            return None

    return None


# ─────────────────────────────────────────────────────────────
# CONFIG TOOLS Y PROMPTS POR STEP
# ─────────────────────────────────────────────────────────────

# STEP 0 – Prefiltrado HTML
STEP0_FUNC_NAME = refinar_contenido_principal["name"]
tool_step0 = types.Tool(function_declarations=[refinar_contenido_principal])
config_step0 = types.GenerateContentConfig(
    tools=[tool_step0],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP0_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

def _prompt_step0(texto_html_markdown: str, url_detalle: str) -> str:
    """
    Prompt de STEP 0 – Prefiltrado HTML.
    Aísla la convocatoria principal y corta listados de otras convocatorias / buscadores.
    """
    return (
        "STEP 0 – PREFILTRADO HTML\n"
        "Tarea: usar la función 'refinar_contenido_principal' para aislar SOLO la "
        "convocatoria principal y eliminar listados de otras convocatorias, buscadores "
        "y ruido que haya quedado del scraping.\n\n"
        f"URL_ORIGEN: {url_detalle}\n\n"
        "TEXTO_HTML_MARKDOWN:\n"
        f"{texto_html_markdown}\n"
    )


# STEP 1 – Triage documental
STEP1_FUNC_NAME = analizar_documento_sanitario["name"]
tool_step1 = types.Tool(function_declarations=[analizar_documento_sanitario])
config_step1 = types.GenerateContentConfig(
    tools=[tool_step1],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP1_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

def _prompt_step1(texto: str, tipo_fuente: str, url_detalle: str) -> str:
    """
    Prompt de STEP 1 – Triage documental (primeros 3000 caracteres).
    Decide si es empleo público, si es sanitario (Enfermería/TCAE) y si es descartable.
    """
    return (
        "STEP 1 – TRIAGE DOCUMENTAL\n"
        "Usa la función 'analizar_documento_sanitario' para decidir:\n"
        "- si es empleo público,\n"
        "- si tiene perfil Enfermería/TCAE,\n"
        "- si debe ser descartado (trámite, lista de admitidos, modelo de solicitud, etc.).\n\n"
        f"TIPO_FUENTE: {tipo_fuente}\n"
        f"URL_ORIGEN: {url_detalle}\n\n"
        "ENTRADA_TEXTO:\n"
        f"{texto}\n"
    )


# STEP 2 – Clasificación tipo de proceso
STEP2_FUNC_NAME = clasificar_tipo_proceso_convocatoria["name"]
tool_step2 = types.Tool(function_declarations=[clasificar_tipo_proceso_convocatoria])
config_step2 = types.GenerateContentConfig(
    tools=[tool_step2],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP2_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

def _prompt_step2(texto_corto: str, tipo_fuente: str, url_detalle: str) -> str:
    """
    Prompt de STEP 2 – Clasificación del tipo de proceso (bolsa/oposición/concurso/…).
    Usa solo un fragmento inicial (3000 chars) porque es donde suelen aparecer
    'Bases', 'Proceso selectivo', 'Bolsa de trabajo', 'Pruebas selectivas', etc.
    """
    return (
        "STEP 2 – CLASIFICAR TIPO DE PROCESO\n"
        "El documento YA ha sido validado como convocatoria de empleo público sanitario "
        "(Enfermería/TCAE). Usa la función 'clasificar_tipo_proceso_convocatoria' para "
        "etiquetar el mecanismo de selección exacto (bolsa, oposición, concurso, "
        "concurso-oposición u otro), siguiendo la jerarquía de decisión definida en la tool.\n\n"
        f"TIPO_FUENTE: {tipo_fuente}\n"
        f"URL_ORIGEN: {url_detalle}\n\n"
        "TEXTO_INICIAL:\n"
        f"{texto_corto}\n"
    )


# STEP 3 – Extractores especializados

# Bolsa
STEP3_BOLSA_FUNC_NAME = extraer_convocatorias_bolsa["name"]
tool_step3_bolsa = types.Tool(function_declarations=[extraer_convocatorias_bolsa])
config_step3_bolsa = types.GenerateContentConfig(
    tools=[tool_step3_bolsa],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP3_BOLSA_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

# Oposición
STEP3_OPOS_FUNC_NAME = extraer_convocatorias_oposicion["name"]
tool_step3_opos = types.Tool(function_declarations=[extraer_convocatorias_oposicion])
config_step3_opos = types.GenerateContentConfig(
    tools=[tool_step3_opos],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP3_OPOS_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

# Concurso
STEP3_CONC_FUNC_NAME = extraer_convocatorias_concurso["name"]
tool_step3_conc = types.Tool(function_declarations=[extraer_convocatorias_concurso])
config_step3_conc = types.GenerateContentConfig(
    tools=[tool_step3_conc],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP3_CONC_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

# Concurso-oposición
STEP3_CO_FUNC_NAME = extraer_convocatorias_concurso_oposicion["name"]
tool_step3_co = types.Tool(function_declarations=[extraer_convocatorias_concurso_oposicion])
config_step3_co = types.GenerateContentConfig(
    tools=[tool_step3_co],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP3_CO_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

# OTRO
STEP3_OTRO_FUNC_NAME = extraer_convocatorias_otro["name"]
tool_step3_otro = types.Tool(function_declarations=[extraer_convocatorias_otro])
config_step3_otro = types.GenerateContentConfig(
    tools=[tool_step3_otro],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(
            mode="ANY",
            allowed_function_names=[STEP3_OTRO_FUNC_NAME],
        )
    ),
    temperature=0.0,
)

def _prompt_step3(texto: str, tipo_fuente: str, url_detalle: str,
                  tipo_proceso_clasificador: str) -> str:
    """
    Prompt de STEP 3 – Extracción estructurada según tipo de proceso.
    Máximo 2 convocatorias (1 enfermería + 1 TCAE) por documento.
    """
    return (
        "STEP 3 – EXTRACCIÓN ESTRUCTURADA SEGÚN TIPO DE PROCESO\n"
        "El documento ya ha sido clasificado como convocatoria sanitaria y se conoce el "
        "tipo de proceso principal. Usa la función de extracción correspondiente a ese tipo "
        "para rellenar el array 'convocatorias' con 0, 1 o 2 filas (como máximo una de "
        "enfermería y una de TCAE), siguiendo el schema JSON de salida.\n\n"
        f"TIPO_FUENTE: {tipo_fuente}\n"
        f"URL_ORIGEN: {url_detalle}\n"
        f"TIPO_PROCESO_CLASIFICADO: {tipo_proceso_clasificador}\n\n"
        "TEXTO_COMPLETO:\n"
        f"{texto}\n"
    )


# ─────────────────────────────────────────────────────────────
# BUCLE PRINCIPAL
# ─────────────────────────────────────────────────────────────

def main():
    # Leer CSV de entrada
    with open(CSV_INPUT_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=",")
        filas = list(reader)
        print("Cabeceras detectadas en el CSV:", reader.fieldnames)

    if not filas:
        raise RuntimeError(f"El CSV de entrada '{CSV_INPUT_PATH}' está vacío.")

    convocatorias_totales: list[dict] = []

    for idx, fila in enumerate(filas, start=1):
        print(f"\n=== PROCESANDO FILA {idx}/{len(filas)} ===")

        # 1) Texto de entrada (siempre contenido_pagina)
        texto_original = fila.get("contenido_pagina", "") or ""
        if not texto_original.strip():
            print("  → Fila sin contenido_pagina. Se salta.")
            continue

        # 2) Tipo de fuente según es_pdf
        es_pdf_raw = fila.get("es_pdf", "")
        es_pdf = _parse_bool_es_pdf(es_pdf_raw)
        tipo_fuente = "pdf" if es_pdf else "html"

        # 3) URL de detalle (se usará también para EXTRAIDO_DE)
        url_detalle = (
            fila.get("url_detalle")
            or fila.get("Enlace")
            or fila.get("enlace")
            or fila.get("url")
            or ""
        )

        print(f"  Tipo_fuente = {tipo_fuente}  |  URL_DETALLE = {url_detalle}")

        # Por defecto, el texto base es el original
        texto_base = texto_original

        # ───────── STEP 0 – PREFILTRADO HTML (solo si NO es PDF) ─────────
        if not es_pdf:
            prompt0 = _prompt_step0(texto_original, url_detalle)
            response0 = _call_with_retries(prompt0, config_step0, "STEP 0")

            if response0 is None:
                # Error total → mantenemos texto original
                print("  ⚠️ STEP 0: sin respuesta válida. Se usa texto original.")
            else:
                args0 = _extraer_function_call(response0)
                if args0 is None:
                    print("  ⚠️ STEP 0: sin function_call. Se usa texto original.")
                else:
                    texto_limpio = (args0.get("texto_final_limpio") or "").strip()
                    se_realizo_corte = bool(args0.get("se_realizo_corte", False))
                    titulo_detectado = (args0.get("titulo_detectado") or "").strip()
                    print(f"  STEP 0 → se_realizo_corte={se_realizo_corte}, titulo_detectado='{titulo_detectado}'")

                    if texto_limpio:
                        texto_base = texto_limpio

        # ───────── STEP 1 – TRIAGE DOCUMENTAL ─────────
        # Para el triage basta con el inicio del documento (primeras ~3k chars)
        texto_step1 = texto_base[:3000]

        prompt1 = _prompt_step1(texto_step1, tipo_fuente, url_detalle)
        response1 = _call_with_retries(prompt1, config_step1, "STEP 1")

        # Valores por defecto (postura conservadora: NO descartar por fallo de modelo)
        es_empleo_publico = True
        tiene_perfil_sanitario = True
        es_descartable = False

        if response1 is None:
            print("  ⚠️ STEP 1: sin respuesta válida. Postura conservadora: NO descartamos por error de modelo.")
        else:
            args1 = _extraer_function_call(response1)
            if args1 is None:
                print("  ⚠️ STEP 1: sin function_call. Postura conservadora.")
            else:
                es_empleo_publico = bool(args1.get("es_empleo_publico", False))
                tiene_perfil_sanitario = bool(args1.get("tiene_perfil_sanitario", False))
                es_descartable = bool(args1.get("es_descartable", False))
                motivo = (args1.get("motivo") or "").strip()
                print(
                    f"  STEP 1 → es_empleo_publico={es_empleo_publico}, "
                    f"tiene_perfil_sanitario={tiene_perfil_sanitario}, "
                    f"es_descartable={es_descartable}, motivo='{motivo}'"
                )

        if es_descartable or not es_empleo_publico or not tiene_perfil_sanitario:
            print("  → TRIAGE: Documento descartado (no seguimos con STEP 2/3).")
            continue

        # ───────── STEP 2 – CLASIFICAR TIPO DE PROCESO ─────────
        texto_step2 = texto_base[:3000]
        prompt2 = _prompt_step2(texto_step2, tipo_fuente, url_detalle)
        response2 = _call_with_retries(prompt2, config_step2, "STEP 2")

        tipo_proceso_clasificador = "otro"
        clasificador_confianza = "desconocida"

        if response2 is None:
            print("  ⚠️ STEP 2: sin respuesta válida. Se marca tipo_proceso_clasificador='otro'.")
            tipo_proceso_clasificador = "otro"
            clasificador_confianza = "error_modelo"
        else:
            args2 = _extraer_function_call(response2)
            if args2 is None:
                print("  ⚠️ STEP 2: sin function_call. tipo_proceso='otro'.")
                tipo_proceso_clasificador = "otro"
                clasificador_confianza = "sin_function_call"
            else:
                tipo_proceso_clasificador = str(args2.get("tipo_proceso", "otro") or "otro")
                clasificador_confianza = str(args2.get("confianza", "") or "")
                print(
                    f"  STEP 2 → tipo_proceso_clasificador={tipo_proceso_clasificador}, "
                    f"confianza={clasificador_confianza}"
                )

        # ───────── STEP 3 – SWITCH → EXTRACTOR POR TIPO ─────────
        prompt3 = _prompt_step3(texto_base, tipo_fuente, url_detalle, tipo_proceso_clasificador)

        # Elegimos tool/config según tipo
        if tipo_proceso_clasificador == "bolsa":
            print("  → STEP 3: usando extractor BOLSA.")
            config3 = config_step3_bolsa
        elif tipo_proceso_clasificador == "oposicion":
            print("  → STEP 3: usando extractor OPOSICIÓN.")
            config3 = config_step3_opos
        elif tipo_proceso_clasificador == "concurso":
            print("  → STEP 3: usando extractor CONCURSO.")
            config3 = config_step3_conc
        elif tipo_proceso_clasificador == "concurso-oposicion":
            print("  → STEP 3: usando extractor CONCURSO-OPOSICIÓN.")
            config3 = config_step3_co
        else:
            print("  → STEP 3: tipo_proceso='otro' → usando extractor OTRO (documento accesorio / anexo, etc.).")
            config3 = config_step3_otro

        response3 = _call_with_retries(prompt3, config3, "STEP 3")

        if response3 is None:
            print("  ⚠️ STEP 3: sin respuesta válida. No se extraen convocatorias.")
            continue

        args3 = _extraer_function_call(response3)
        if args3 is None:
            print("  ⚠️ STEP 3: sin function_call. No se extraen convocatorias.")
            continue

        convocatorias = args3.get("convocatorias", []) or []
        print(f"  STEP 3 → convocatorias devueltas: {len(convocatorias)}")

        # Post-procesado de cada convocatoria antes de añadirla al CSV
        for conv in convocatorias:
            # Asegurar todos los campos base existen en el dict
            for field in BASE_FIELDS:
                conv.setdefault(field, "")

            # EXTRAIDO_DE = url_detalle del CSV SIEMPRE
            conv["EXTRAIDO_DE"] = url_detalle

            # Normalizar TIPO_PROCESO (si el modelo no lo ha rellenado)
            if not conv.get("TIPO_PROCESO"):
                tipo_upper = tipo_proceso_clasificador.upper()
                if tipo_upper == "CONCURSO-OPOSICION":
                    conv["TIPO_PROCESO"] = "CONCURSO-OPOSICION"
                elif tipo_upper == "OPOSICION":
                    conv["TIPO_PROCESO"] = "OPOSICION"
                elif tipo_upper == "BOLSA":
                    conv["TIPO_PROCESO"] = "BOLSA"
                elif tipo_upper == "CONCURSO":
                    conv["TIPO_PROCESO"] = "CONCURSO"
                else:
                    conv["TIPO_PROCESO"] = "OTRO"

            # Campos extra de contexto (sin info de PDF/HTML)
            conv["TIPO_PROCESO_CLASIFICADOR"] = tipo_proceso_clasificador
            conv["CLASIFICADOR_CONFIANZA"] = clasificador_confianza

            convocatorias_totales.append(conv)

    # ───────── ESCRIBIR CSV DE SALIDA ─────────
    print(f"\nTotal convocatorias extraídas: {len(convocatorias_totales)}")

    with open(CSV_OUTPUT_PATH, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.writer(f_out, delimiter=",")
        writer.writerow(CSV_HEADER)
        for conv in convocatorias_totales:
            row = [conv.get(col, "") or "" for col in CSV_HEADER]
            writer.writerow(row)

    print(f"CSV de salida guardado en: {CSV_OUTPUT_PATH}")


if __name__ == "__main__":
    main()

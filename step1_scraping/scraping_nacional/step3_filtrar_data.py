# step1_scraping/scraping_nacional/step3_filtrar_data.py
"""
Carga de datos críticos desde el CSV crudo de convocatorias AGE
y filtrado general por perfil ENFERMERO, TCAES o ENFERMEROYTCAES
usando diccionarios de patrones.

Este script:

1) Lee el CSV generado por el scraper: convocatorias_age_crudo_v2.csv
2) Selecciona solo un subconjunto de columnas "críticas" para el proceso
3) Carga una lista de dicts en memoria (toda la data crítica)
4) Filtra las filas según el perfil:

   - "ENFERMERO"       → usa PATRONES_ENFERMERO,
                         excluyendo textos que sean claramente TCAE/Auxiliar.
   - "TCAES"           → usa PATRONES_TCAE_AUX_ENFERMERIA
                         y heurísticos de TCAE/Auxiliar.
   - "ENFERMEROYTCAES" → acepta tanto patrones de ENFERMERO como de TCAES
                         (perfil combinado).

5) Imprime solo algunos campos clave de ejemplo, pero mantiene todos en memoria.

Luego:
- Para cada convocatoria filtrada construye la URL de detalle
- Navega con Selenium a la página de detalle
- Extrae el contenido principal de la página con lxml (extract_main_text_from_html)
- Limpia el texto con mi_limpiador
- CORTA el texto antes de "quizá también te interesen otras convocatorias..."
- Guarda un CSV: convocatorias_detalle_age_v4.csv con:
    - TODAS las columnas originales
    - + url_detalle (construida aquí)
    - + es_pdf = "false"
    - + una columna contenido_pagina con:
        → todas las columnas de la fila concatenadas como "campo: valor"
        → + el texto detalle web como "texto_detalle: <contenido>"
"""

import html
import re
import csv
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

from patrones_enfermero_o_tcaes import (
    PATRONES_ENFERMERO,
    PATRONES_TCAE_AUX_ENFERMERIA,
    PATRONES_ENFERMEROYTCAES,  # diccionario combinado ENFERMERO + TCAES
)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Para extraer el contenido principal desde el HTML
from lxml import html as lxml_html, etree


# -------------------------------------------------------------------
#  CONFIGURACIÓN
# -------------------------------------------------------------------

# Nombre del CSV de entrada (el que genera tu scraper)
CSV_ENTRADA = Path(__file__).with_name("convocatorias_age_crudo_v2.csv")

# Perfil objetivo para filtrar:
#   - "ENFERMERO"       → solo enfermería (excluyendo TCAE/Auxiliar)
#   - "TCAES"           → solo TCAE / Auxiliar de Enfermería
#   - "ENFERMEROYTCAES" → ambos perfiles (combinado)
#PERFIL_OBJETIVO = "ENFERMERO"
#PERFIL_OBJETIVO = "TCAES"
PERFIL_OBJETIVO = "ENFERMEROYTCAES"

# Lista de columnas críticas a conservar (toda la data que quieres guardar)
# OJO: el CSV original no tiene url_detalle ni es_pdf; aquí no las pedimos.
COLUMNAS_CRITICAS = [
    "administracionconvocante",
    "administracionconvocanteid",
    "agid",
    "ambito",
    "comunidadautonoma",
    "comunidadid",
    "cuerpo",
    "cuerpoid",
    "descripcion",
    "diariopublicacion",
    "direccioninternet",
    "disposiciones",
    "fechapublicacion",
    "grupo",
    "idniveltitulacion",
    "organo",
    "plazas",
    "plazasconvocadas",
    "plazasinternas",
    "plazaslibres",
    "plazos",
    "provinciaId",
    "pruebasselectivas",
    "referencia",
    "requisitos",
    "seleccion",
    "suscripcionseguimiento",
    "tipoconvocatoria",
    "tipopersonalid",
    "tipoplazas",
    "titulacion",
    "titulo",
    "via",
    "viagrupo",
    "viagrupoid",
    "fechaweb",
    "observaciones",
    "plazasdiscapacidadgeneral",
    "plazasdiscapacidadintelectual",
    "provincia",
    "seguimientos",
    "unidad",
]

# Campos donde buscar variantes del perfil: será un OR de TODOS
CAMPOS_SECUNDARIOS_PERFIL = ["titulo", "cuerpo", "descripcion", "grupo"]

# Campos que QUIERES IMPRIMIR (aunque el registro tenga muchos más)
CAMPOS_A_IMPRIMIR = [
    "fechapublicacion",
    "ambito",
    "administracionconvocante",
    "comunidadautonoma",
    "titulacion",
    "titulo",
    "cuerpo",
    "descripcion",
    "grupo",
    "requisitos",
    "pruebasselectivas",
    "referencia",
]


# -------------------------------------------------------------------
#  NORMALIZACIÓN
# -------------------------------------------------------------------

def normalizar_texto(texto_original: str) -> str:
    """
    Normaliza texto para comparaciones robustas:
    - Si es None → ""
    - Quita espacios extremos
    - Pasa a mayúsculas
    - Elimina tildes (NFD + filtrado de 'Mn')
    """
    if texto_original is None:
        texto_original = ""

    texto_sin_espacios = texto_original.strip().upper()
    texto_descompuesto = unicodedata.normalize("NFD", texto_sin_espacios)

    texto_normalizado = ""
    for caracter in texto_descompuesto:
        if unicodedata.category(caracter) != "Mn":  # quita tildes
            texto_normalizado += caracter

    return texto_normalizado


# -------------------------------------------------------------------
#  DETECCIÓN POR PATRONES (ENFERMERO / TCAES / ENFERMEROYTCAES)
# -------------------------------------------------------------------

def es_texto_perfil(texto: str, tipo_perfil: str) -> bool:
    perfil_normalizado = (tipo_perfil or "").strip().upper()
    texto_normalizado = normalizar_texto(texto)

    if texto_normalizado == "":
        return False

    # 0) Perfil combinado: ENFERMERO + TCAES
    if perfil_normalizado == "ENFERMEROYTCAES":
        for patron in PATRONES_ENFERMEROYTCAES.keys():
            if patron in texto_normalizado:
                return True

        return (
            es_texto_perfil(texto, "ENFERMERO")
            or es_texto_perfil(texto, "TCAES")
        )

    # 1) Detectar si el texto corresponde a TCAE / Auxiliar (heurístico general)
    es_tcaes_eliminar = False

    if (
        "ENFERMERIA" in texto_normalizado
        and (
            "TECNICO" in texto_normalizado
            or "TECNICOS" in texto_normalizado
            or "AUXILIAR" in texto_normalizado
            or "AUXILIARES" in texto_normalizado
        )
    ):
        es_tcaes_eliminar = True

    if not es_tcaes_eliminar:
        for patron_tcae in PATRONES_TCAE_AUX_ENFERMERIA.keys():
            if patron_tcae in texto_normalizado:
                es_tcaes_eliminar = True
                break

    # 2) Perfil TCAES
    if perfil_normalizado in ("TCAES", "TCAE", "AUXILIAR"):
        return es_tcaes_eliminar

    # 3) Perfil ENFERMERO sin TCAES
    if perfil_normalizado == "ENFERMERO":
        for patron_enfermeria in PATRONES_ENFERMERO.keys():
            if patron_enfermeria in texto_normalizado and not es_tcaes_eliminar:
                return True
        return False

    # 4) Error
    raise ValueError("PERFIL_OBJETIVO debe ser 'ENFERMERO', 'TCAES' o 'ENFERMEROYTCAES'")


def es_convocatoria_perfil(registro: dict, tipo_perfil: str) -> bool:
    campos_a_revisar = ["titulacion"] + CAMPOS_SECUNDARIOS_PERFIL

    for nombre_campo in campos_a_revisar:
        valor_campo = registro.get(nombre_campo, "")
        if valor_campo and es_texto_perfil(valor_campo, tipo_perfil):
            return True

    return False


# -------------------------------------------------------------------
#  CARGA DE CSV → LISTA[DICT]
# -------------------------------------------------------------------

def cargar_convocatorias_campos_clave(
    ruta_entrada: Path = CSV_ENTRADA,
    columnas_deseadas: list[str] = COLUMNAS_CRITICAS,
) -> list[dict]:
    if not ruta_entrada.exists():
        raise FileNotFoundError(f"No se encontró el CSV de entrada: {ruta_entrada}")

    with ruta_entrada.open("r", encoding="utf-8-sig", newline="") as archivo_entrada:
        lector_csv = csv.DictReader(archivo_entrada)
        columnas_en_csv = lector_csv.fieldnames or []

        columnas_finales = []
        for nombre_columna in columnas_deseadas:
            if nombre_columna in columnas_en_csv:
                columnas_finales.append(nombre_columna)

        if not columnas_finales:
            mensaje_error = (
                "Ninguna de las columnas críticas se encontró en el CSV de entrada.\n"
                f"Columnas del CSV: {columnas_en_csv}"
            )
            raise ValueError(mensaje_error)

        print("Columnas encontradas en el CSV de entrada:")
        print(columnas_en_csv)
        print("\nColumnas que se usarán en los diccionarios:")
        print(columnas_finales)

        lista_registros: list[dict] = []

        for fila_original in lector_csv:
            registro_filtrado = {}
            for nombre_columna in columnas_finales:
                registro_filtrado[nombre_columna] = fila_original.get(nombre_columna, "")
            lista_registros.append(registro_filtrado)

    print(f"\nTotal de registros cargados en memoria: {len(lista_registros)}")
    return lista_registros


# -------------------------------------------------------------------
#  FUNCIONES PARA HTML: LIMPIEZA / CONTENIDO PRINCIPAL
# -------------------------------------------------------------------

def mi_limpiador(texto: str) -> str:
    texto = html.unescape(texto or "")
    texto = texto.replace("\u00A0", " ")  # NBSP -> espacio normal

    texto = re.sub(r'#\w+', ' ', texto)
    texto = texto.lower()
    texto = re.sub(r"[^\w\s/\-:\.,\+]", " ", texto, flags=re.UNICODE)
    texto = re.sub(r"_+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def _norm(s: str) -> str:
    s = (s or "").replace("\u00A0", " ")
    s = unicodedata.normalize("NFD", s)
    s = "".join(caracter for caracter in s if unicodedata.category(caracter) != "Mn")
    return s.lower()


def extract_main_text_from_html(html_str: str) -> str:
    if not html_str:
        return ""

    tree = lxml_html.fromstring(html_str)
    etree.strip_elements(tree, "script", "style", "noscript", with_tail=False)

    for tag in ["header", "footer", "nav", "aside"]:
        for el in tree.xpath(f"//{tag}"):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    for el in tree.xpath("//div[@id or @class]"):
        id_class = " ".join([el.get("id", ""), el.get("class", "")]).lower()

        if any(keyword in id_class for keyword in [
            "header", "footer", "nav", "menu", "sidebar", "lateral",
            "breadcrumbs", "migas", "cookies", "banner"
        ]):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    candidates = []
    candidates.extend(tree.xpath("//main"))
    candidates.extend(tree.xpath("//article"))
    candidates.extend(tree.xpath(
        "//div[not(ancestor::header) and not(ancestor::footer) "
        "and not(ancestor::nav) and not(ancestor::aside)]"
    ))

    if not candidates:
        body = tree.xpath("//body")
        container = body[0] if body else tree
    else:
        def text_len(el):
            text = el.text_content() or ""
            text = re.sub(r"\s+", " ", text)
            return len(text)

        candidates = sorted(candidates, key=text_len, reverse=True)
        container = candidates[0]

    raw_text = container.text_content() or ""
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    return "\n".join(lines)


# -------------------------------------------------------------------
#  SCRAPING DE DETALLE DE LAS CONVOCATORIAS FILTRADAS
# -------------------------------------------------------------------

URL_DETALLE_BASE = "https://administracion.gob.es/pagFront/ofertasempleopublico/detalleEmpleo.htm"


def construir_url_detalle_desde_referencia(referencia: str) -> str:
    referencia_limpia = (referencia or "").strip()
    if referencia_limpia == "":
        return ""

    parametros = {"idConvocatoria": referencia_limpia}
    cadena_parametros = urlencode(parametros)

    url_completa = f"{URL_DETALLE_BASE}?{cadena_parametros}"
    return url_completa


def crear_driver_chrome_detalle():
    opciones = Options()
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opciones)
    driver.set_page_load_timeout(20)
    return driver


def extraer_texto_detalle_con_selenium(url_detalle: str, driver) -> str:
    """
    Extrae el detalle:
      - HTML → bloque principal
      - Limpia con mi_limpiador
      - Corta antes de "quizá tambien te interesen otras convocatorias..."
    """
    if not url_detalle:
        return ""

    try:
        driver.get(url_detalle)
        html_pagina = driver.page_source

        texto_principal = extract_main_text_from_html(html_pagina)
        texto_limpio = mi_limpiador(texto_principal)

        marker_variants = [
            "quizá tambien te interesen otras convocatorias",
            "quiza tambien te interesen otras convocatorias",
            "quizá también te interesen otras convocatorias",
            "quiza también te interesen otras convocatorias",
        ]
        texto_lower = texto_limpio.lower()
        corte = -1
        for m in marker_variants:
            idx = texto_lower.find(m)
            if idx != -1 and (corte == -1 or idx < corte):
                corte = idx

        if corte != -1:
            texto_limpio = texto_limpio[:corte].strip()

        return texto_limpio
    except Exception as error:
        print(f"Error extrayendo texto de {url_detalle}: {error}")
        return ""


def guardar_detalle_convocatorias_en_csv(
    registros_filtrados: list[dict],
    nombre_archivo: str = "convocatorias_detalle_age_v4.csv",
):
    """
    Para cada registro filtrado:

      - Construye url_detalle a partir de referencia (CSV original no la trae).
      - Marca es_pdf = "false" (todas son páginas HTML).
      - Extrae el contenido principal de la página de detalle.
      - Exporta un CSV con:
          - TODAS las columnas originales
          - + url_detalle
          - + es_pdf
          - + contenido_pagina (fila etiquetada + texto_detalle recortado)
    """
    if not registros_filtrados:
        print("No hay registros filtrados para guardar en CSV.")
        return

    columnas_base = list(registros_filtrados[0].keys())

    if "url_detalle" not in columnas_base:
        columnas_base.append("url_detalle")
    if "es_pdf" not in columnas_base:
        columnas_base.append("es_pdf")

    nombre_columna_contenido = "contenido_pagina"
    columnas_csv = columnas_base + [nombre_columna_contenido]

    driver = None
    try:
        driver = crear_driver_chrome_detalle()

        with open(nombre_archivo, "w", newline="", encoding="utf-8") as archivo_salida:
            escritor = csv.writer(archivo_salida)
            escritor.writerow(columnas_csv)

            for registro in registros_filtrados:
                referencia_convocatoria = registro.get("referencia", "")

                # Siempre construimos la URL de detalle a partir de referencia
                url_detalle = construir_url_detalle_desde_referencia(referencia_convocatoria)
                registro["url_detalle"] = url_detalle

                # Para este script: siempre HTML → es_pdf = "false"
                registro["es_pdf"] = "false"

                texto_detalle = extraer_texto_detalle_con_selenium(url_detalle, driver)

                fila = []
                texto_campos = []

                for nombre_columna in columnas_base:
                    valor = registro.get(nombre_columna, "")
                    fila.append(valor)

                    if valor is None:
                        continue

                    v = str(valor).strip()
                    if v:
                        texto_campos.append(f"{nombre_columna}: {v}")

                if texto_detalle:
                    texto_campos.append(f"texto_detalle: {texto_detalle}")

                texto_concatenado = " | ".join(texto_campos)
                fila.append(texto_concatenado)

                escritor.writerow(fila)

        print(f"Se guardaron {len(registros_filtrados)} filas en {nombre_archivo}")
    except Exception as error:
        print(f"Error guardando el CSV de detalle: {error}")
    finally:
        if driver is not None:
            driver.quit()


# -------------------------------------------------------------------
#  EJEMPLO DE USO DIRECTO
# -------------------------------------------------------------------

if __name__ == "__main__":
    print("Cargando convocatorias desde CSV (campos clave)...\n")
    registros = cargar_convocatorias_campos_clave()

    print(f"\nConvocatorias en memoria (total): {len(registros)}")

    registros_filtrados = []
    for registro in registros:
        if es_convocatoria_perfil(registro, PERFIL_OBJETIVO):
            registros_filtrados.append(registro)

    print(
        f"Convocatorias de perfil {PERFIL_OBJETIVO} detectadas por patrones: "
        f"{len(registros_filtrados)}"
    )

    guardar_detalle_convocatorias_en_csv(registros_filtrados)

    if registros_filtrados:
        print(f"\nPrimer registro {PERFIL_OBJETIVO} (campos seleccionados):")
        primer_registro = registros_filtrados[0]
        for nombre_campo in CAMPOS_A_IMPRIMIR:
            print(f"  {nombre_campo}: {primer_registro.get(nombre_campo, '')}")
        print(f"  url_detalle (construida): {construir_url_detalle_desde_referencia(primer_registro.get('referencia', ''))}")
        print(f"  es_pdf: false")

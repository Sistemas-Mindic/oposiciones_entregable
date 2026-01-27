#!/usr/bin/env python3
# python step1_scraping/extraccion_data.py
import argparse
import sys
import re
import html
import requests
from bs4 import BeautifulSoup
import pdfplumber
import csv
import unicodedata
from io import BytesIO
from urllib.parse import urljoin
from requests.exceptions import SSLError, RequestException
from pathlib import Path
from lxml import html as lxml_html, etree
import html2text

from step1_scraping.extraccion_config import (
    DEFAULT_FUENTES,
    DEFAULT_FUENTES_RECURSIVAS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_FILENAME,
)

from step2_filtrado.palabras_oposiciones import palabras_oposiciones
from step2_filtrado.patrones_convocatoria import (
    _PAT_CONV, _PAT_EMP, _NEG_NO_EMPLEO,
    _RE_CONV, _RE_EMP, _RE_CANON, _RE_VENTANA, _RE_VENTANA_NEG,
    WINDOW_WORDS,
)

# ---------------------------------------------------------------
#          CONVERSIÓN HTML → MARKDOWN OPTIMIZADA PARA IA
# ---------------------------------------------------------------

def convertir_html_a_markdown_optimizado(html_content: str) -> str:
    """
    Convierte HTML a Markdown con configuración optimizada para LLM:
    - Mantiene enlaces
    - Ignora imágenes
    - Mantiene énfasis (negritas, cursivas)
    - No introduce saltos de línea arbitrarios (body_width=0)
    - Protege enlaces complejos
    - Estandariza listas con '-'
    - Compacta saltos de línea excesivos
    - HEURÍSTICA EXTRA: inserta saltos de línea antes de patrones de fecha tipo dd/mm/aaaa
      para no dejar calendarios en una sola línea.
    """
    h = html2text.HTML2Text()

    # CONFIGURACIÓN CLAVE PARA IA
    h.ignore_links = False      # Mantener enlaces (necesitas las URLs de los PDFs)
    h.ignore_images = True      # Imágenes = ruido (logos, banners)
    h.ignore_emphasis = False   # Mantener negritas/cursivas
    h.body_width = 0            # 0 evita cortes de línea arbitrarios
    h.protect_links = True      # Evita que rompa enlaces complejos
    h.ul_item_mark = '-'        # Estandariza listas

    try:
        markdown = h.handle(html_content or "")

        # ── Heurística para calendarios y listados con fechas ──
        # Inserta un salto de línea ANTES de cada fecha dd/mm/aaaa si no hay ya uno
        # Ejemplo: "... mayo 2025 05/05/2025 técnico..." -> "... mayo 2025\n05/05/2025 técnico..."
        markdown = re.sub(
            r'(?<!\n)(\d{2}/\d{2}/\d{4})',
            r'\n\1',
            markdown
        )

        # Limpieza extra: reducir bloques de saltos de línea muy largos
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)

        return markdown.strip()
    except Exception as e:
        print(f"Error en convertir_html_a_markdown_optimizado: {e}")
        # Fallback: devolvemos el HTML crudo
        return html_content or ""



# ---------------------------------------------------------------
#        HEURÍSTICA: DETECTAR ESTRUCTURA LISTADO / DETALLE
# ---------------------------------------------------------------

def detectar_estructura_html(soup_objeto: BeautifulSoup) -> str:
    """
    Analiza el DOM para dar una pista sobre la estructura:
    - 'posible_listado' : muchas filas / artículos + varios PDFs
    - 'posible_detalle' : ficha más unitaria
    """
    if soup_objeto is None:
        return "posible_detalle"

    # Contar enlaces a PDFs
    enlaces_pdf = len(soup_objeto.select('a[href$=".pdf"]'))

    # Contar elementos de lista (li) o artículos (article)
    items_lista = len(soup_objeto.find_all(['li', 'article']))

    # Heurística:
    if items_lista > 10 and enlaces_pdf > 3:
        return "posible_listado"

    return "posible_detalle"


# ---------------------------------------------------------------
#                   DETECCIÓN DE PDF
# ---------------------------------------------------------------

def es_pdf(url: str) -> bool:
    """
    Devuelve True si la URL parece apuntar a un PDF según la cabecera Content-Type.
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get("Content-Type", "") or ""
        return "application/pdf" in content_type.lower()
    except SSLError as e:
        print(f"Certificado no válido en {url}: {e}")
        return False
    except RequestException as e:
        print(f"Error comprobando PDF para {url}: {e}")
        return False


def extraer_texto_pdf(url: str) -> str:
    """
    Descarga un PDF y devuelve el texto bruto concatenado de todas las páginas.
    """
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)
        texto = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                texto += (page.extract_text() or "") + "\n"
        return texto
    except Exception as e:
        print(f"Error extrayendo PDF de {url}: {e}")
        return ""


# ---------------------------------------------------------------
#                   PROCESADO DE HTML
# ---------------------------------------------------------------

def extract_main_text_from_html(html_str: str) -> str:
    """
    Extrae el texto del contenedor principal (main/article/div más largo)
    eliminando cabeceras, menús, footers, scripts, etc.
    (Puede quedar como función auxiliar si la usas en otros módulos.)
    """
    if not html_str:
        return ""

    try:
        tree = lxml_html.fromstring(html_str)
    except Exception as e:
        print(f"Error parseando HTML (extract_main_text_from_html): {e}")
        soup = BeautifulSoup(html_str, "html.parser")
        return soup.get_text(separator="\n")

    # Eliminar scripts, estilos y noscript
    etree.strip_elements(tree, "script", "style", "noscript", with_tail=False)

    # Eliminar header/footer/nav/aside
    for tag in ["header", "footer", "nav", "aside"]:
        for el in tree.xpath(f"//{tag}"):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Divs típicos de navegación/footers
    for el in tree.xpath("//div[@id or @class]"):
        id_class = " ".join([
            el.get("id", "") or "",
            el.get("class", "") or "",
        ]).lower()

        if any(k in id_class for k in [
            "header", "footer", "nav", "menu", "sidebar", "lateral",
            "breadcrumbs", "migas", "cookies", "banner"
        ]):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Candidatos a contenedor principal
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
            return len(re.sub(r"\s+", " ", text))

        candidates = sorted(candidates, key=text_len, reverse=True)
        container = candidates[0]

    raw_text = container.text_content() or ""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return "\n".join(lines)


def _get_main_container(html_str: str):
    """
    Igual que extract_main_text_from_html, pero devuelve el ELEMENTO contenedor,
    para poder buscar <a> o convertir solo esa zona.
    """
    if not html_str:
        return None

    try:
        tree = lxml_html.fromstring(html_str)
    except Exception as e:
        print(f"Error parseando HTML (_get_main_container): {e}")
        return None

    # Eliminar scripts, estilos y noscript
    etree.strip_elements(tree, "script", "style", "noscript", with_tail=False)

    # Eliminar header/footer/nav/aside
    for tag in ["header", "footer", "nav", "aside"]:
        for el in tree.xpath(f"//{tag}"):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Divs típicos de navegación/footers
    for el in tree.xpath("//div[@id or @class]"):
        id_class = " ".join([
            el.get("id", "") or "",
            el.get("class", "") or "",
        ]).lower()
        if any(k in id_class for k in [
            "header", "footer", "nav", "menu", "sidebar", "lateral",
            "breadcrumbs", "migas", "cookies", "banner"
        ]):
            parent = el.getparent()
            if parent is not None:
                parent.remove(el)

    # Candidatos
    candidates = []
    candidates.extend(tree.xpath("//main"))
    candidates.extend(tree.xpath("//article"))
    candidates.extend(tree.xpath(
        "//div[not(ancestor::header) and not(ancestor::footer) "
        "and not(ancestor::nav) and not(ancestor::aside)]"
    ))

    if not candidates:
        body = tree.xpath("//body")
        return body[0] if body else tree

    def text_len(el):
        text = el.text_content() or ""
        return len(re.sub(r"\s+", " ", text))

    candidates = sorted(candidates, key=text_len, reverse=True)
    return candidates[0]


def html_principal_a_markdown(html_str: str) -> str:
    """
    Localiza el contenedor principal usando _get_main_container
    (main/article/div más largo tras limpiar header/footer/nav/etc.)
    y lo convierte a Markdown con convertir_html_a_markdown_optimizado.
    Si algo falla, convierte todo el HTML a Markdown con la misma función.
    """
    if not html_str:
        return ""

    # Reutilizamos la lógica ya probada de _get_main_container
    container = _get_main_container(html_str)

    # Fallback: si no se ha podido obtener un contenedor principal,
    # convertimos TODO el HTML a Markdown (optimizado).
    if container is None:
        return convertir_html_a_markdown_optimizado(html_str or "")

    # Serializamos SOLO el contenedor principal a HTML
    try:
        fragment_html = etree.tostring(container, encoding="unicode", method="html")
    except Exception as e:
        print(f"Error serializando contenedor principal a HTML: {e}")
        fragment_html = html_str or ""

    # Aplicamos la conversión optimizada
    return convertir_html_a_markdown_optimizado(fragment_html)


# ---------------------------------------------------------------
#                   LIMPIEZA DE TEXTO
# ---------------------------------------------------------------

def mi_limpiador(texto: str) -> str:
    """
    Limpieza genérica FUERTE para texto plano (no Markdown):
    - Desescapa entidades HTML
    - Quita NBSP
    - Elimina hashtags
    - Pasa a minúsculas
    - Mantiene letras/dígitos/espacios y algunos separadores
    - Compacta espacios

    IMPORTANTE: no usar sobre el contenido Markdown que genera html2text.
    """
    texto = html.unescape(texto or "")
    texto = texto.replace("\u00A0", " ")
    texto = re.sub(r'#\w+', ' ', texto)
    texto = texto.lower()
    texto = re.sub(r"[^\w\s/\-:\.,\+]", " ", texto)
    texto = re.sub(r"_+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def extraer_texto_html(url: str) -> str:
    """
    Descarga HTML, selecciona el contenedor principal y devuelve el contenido
    en formato Markdown usando la conversión optimizada.
    """
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        html_str = resp.text
        return html_principal_a_markdown(html_str)
    except SSLError as e:
        print(f"Certificado no válido en {url}: {e}")
        return ""
    except RequestException as e:
        print(f"Error descargando HTML de {url}: {e}")
        return ""
    except Exception as e:
        print(f"Error genérico extrayendo HTML de {url}: {e}")
        return ""


# ---------------------------------------------------------------
#        EXTRACCIÓN DE TEXTO SEGÚN TIPO (PDF / HTML)
# ---------------------------------------------------------------

def extraccion_texto(url: str) -> str:
    """
    API genérica: decide si la URL es PDF o HTML.
      - Si es PDF: devuelve texto YA LIMPIO con mi_limpiador (texto plano).
      - Si es HTML: devuelve el Markdown generado por html_principal_a_markdown,
        SIN pasar por mi_limpiador para no romper el formato Markdown.
    (Se mantiene por compatibilidad si se llama desde otro módulo).
    """
    try:
        if es_pdf(url):
            texto_bruto = extraer_texto_pdf(url)
            return mi_limpiador(texto_bruto)
        else:
            return extraer_texto_html(url)
    except Exception as e:
        print(f"Error genérico extrayendo texto de {url}: {e}")
        return ""


# ---------------------------------------------------------------
#                   OBTENCIÓN DE ENLACES
# ---------------------------------------------------------------

def obtener_enlaces(url_base: str):
    """
    Devuelve la lista de enlaces absolutos encontrados dentro del contenedor principal
    (o, si falla el main, de todo el HTML).
    IMPORTANTE: si falla la descarga (DNS, HTTP...), lanza excepción.
    """
    resp = requests.get(url_base, timeout=20)
    resp.raise_for_status()
    html_str = resp.text

    enlaces = []
    container = _get_main_container(html_str)

    if container is not None:
        try:
            for a in container.xpath(".//a[@href]"):
                href = (a.get("href") or "").strip()
                if not href or href.startswith("#"):
                    continue
                if href.lower().startswith(("javascript:", "mailto:", "tel:")):
                    continue

                enlace = urljoin(url_base, href)
                if enlace not in enlaces:
                    enlaces.append(enlace)
        except Exception as e:
            print(f"Error extrayendo enlaces del main con lxml en {url_base}: {e}")

    # Fallback si no hay enlaces desde el main
    if not enlaces:
        soup = BeautifulSoup(html_str, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#"):
                continue
            if href.lower().startswith(("javascript:", "mailto:", "tel:")):
                continue

            enlace = urljoin(url_base, href)
            if enlace not in enlaces:
                enlaces.append(enlace)

    print(f"Encontrados {len(enlaces)} enlaces en la página base {url_base}.")
    return enlaces


# ---------------------------------------------------------------
#                   NORMALIZACIÓN PARA FILTRO
# ---------------------------------------------------------------

def _norm(s: str) -> str:
    s = (s or "").replace("\u00A0", " ")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower()


# ---------------------------------------------------------------
#         DETECCIÓN DE CONVOCATORIA DE OPOSICIÓN
# ---------------------------------------------------------------

def es_convocatoria_oposicion(texto: str) -> bool:
    """
    True si el texto apunta a CONVOCATORIA de empleo/oposiciones:
      - Coincidencia canónica directa
      - Ventana de proximidad convocatoria <-> empleo
      - Descarta casos típicos de licitaciones
    """
    if not texto:
        return False

    norm = _norm(texto)

    # 1) Coincidencia directa canónica
    if _RE_CANON.search(norm):
        return True

    # 2) Proximidad convocatoria <-> empleo
    if _RE_VENTANA.search(norm):
        return True

    # 3) "Convocatoria" sin empleo + ventana negativa (licitación)
    if _RE_CONV.search(norm) and not _RE_EMP.search(norm) and _RE_VENTANA_NEG.search(norm):
        return False

    return False


# ---------------------------------------------------------------
#            PROCESAR UNA URL DE DETALLE (PDF / HTML)
# ---------------------------------------------------------------

def procesar_url_detalle(url: str) -> dict:
    """
    Procesa una URL de detalle (PDF o HTML) y devuelve un dict con:
      - url_detalle
      - texto            -> contenido principal:
                              * HTML: Markdown (contenedor principal)
                              * PDF:  texto plano limpio con mi_limpiador
      - es_pdf
      - posible_convocatoria (calculado sobre texto adecuado para el filtro)
      - estructura_html  -> 'posible_listado' / 'posible_detalle' (solo HTML)
    """
    print(f"      [DETALLE] Procesando URL detalle: {url}")

    espdf = es_pdf(url)

    if espdf:
        # PDF -> texto bruto + limpieza fuerte para guardar y para detección
        texto_pdf_bruto = extraer_texto_pdf(url)
        texto_para_guardar = mi_limpiador(texto_pdf_bruto)
        texto_para_deteccion = texto_para_guardar
        estructura = ""  # no aplica para PDF
    else:
        # HTML -> hacemos UNA sola petición aquí para texto + estructura
        html_str = ""
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            html_str = resp.text
        except SSLError as e:
            print(f"Certificado no válido en detalle {url}: {e}")
        except RequestException as e:
            print(f"Error descargando HTML de detalle {url}: {e}")
        except Exception as e:
            print(f"Error genérico descargando HTML de detalle {url}: {e}")

        if not html_str:
            texto_markdown = ""
            estructura = ""
        else:
            # Detectar estructura listado/detalle con BeautifulSoup
            soup = BeautifulSoup(html_str, "html.parser")
            estructura = detectar_estructura_html(soup)

            # Convertir solo el contenedor principal a Markdown optimizado
            texto_markdown = html_principal_a_markdown(html_str)

        texto_para_guardar = texto_markdown
        texto_para_deteccion = texto_markdown  # es_convocatoria_oposicion usa _norm

    possible = es_convocatoria_oposicion(texto_para_deteccion)

    return {
        "url_detalle": url,
        "texto": texto_para_guardar,   # <- lo que se exporta como 'contenido' en el CSV
        "es_pdf": espdf,
        "posible_convocatoria": possible,
        "estructura_html": estructura,
    }


# ---------------------------------------------------------------
#                 RECORRER ENLACES Y EXTRAER INFO
# ---------------------------------------------------------------

def recorrer_enlaces(FUENTE: str):
    """
    Recorre todos los enlaces encontrados en la página FUENTE y devuelve
    una lista de dicts con:
      - url_detalle
      - texto (ya limpio/markdown)
      - es_pdf (True/False)
      - posible_convocatoria (True/False)
      - estructura_html
    """
    resultados = []
    enlaces = obtener_enlaces(FUENTE)

    for link in enlaces:
        print(f"Procesando {link}")
        try:
            resultado_detalle = procesar_url_detalle(link)
            resultados.append(resultado_detalle)
        except Exception as e:
            print(f"    [ERROR] Fallo procesando detalle {link}: {e}")

    return resultados


# ---------------------------------------------------------------
#                   EXPORTAR A CSV
# ---------------------------------------------------------------

def guardar_en_csv(resultados, nombre_archivo: str = "extraccion_data_v3_2.csv"):
    """
    Escribe la lista de resultados en un CSV con columnas:
      - url_detalle
      - contenido
      - es_pdf
      - posible_convocatoria
      - estructura_html
      - contenido_pagina (resumen legible de la fila, SIN recortar)
    Usando:
      - delimitador ","
      - todas las celdas entre comillas (QUOTE_ALL)
    """
    try:
        with open(nombre_archivo, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(
                csvfile,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_ALL
            )

            writer.writerow([
                "url_detalle",
                "contenido",
                "es_pdf",
                "posible_convocatoria",
                "estructura_html",
                "contenido_pagina"
            ])

            for item in resultados:
                url = item.get("url_detalle", "")
                texto = item.get("texto", "")
                espdf = item.get("es_pdf", False)
                possible = item.get("posible_convocatoria", False)
                estructura = item.get("estructura_html", "")

                partes = [
                    f"url_detalle: {url}",
                    f"contenido: {texto}",
                    f"posible_convocatoria: {possible}",
                    f"estructura_html: {estructura}",
                ]
                contenido_pagina = " | ".join(partes)

                writer.writerow([
                    url,
                    texto,
                    espdf,
                    possible,
                    estructura,
                    contenido_pagina
                ])

        print(f"Se guardaron {len(resultados)} filas en {nombre_archivo}")

    except Exception as e:
        print(f"Error guardando el CSV: {e}")


# ---------------------------------------------------------------
#        PROCESAR VARIAS FUENTES (PLANAS + RECURSIVAS)
# ---------------------------------------------------------------

def procesar_fuentes(fuentes_planas, fuentes_recursivas, nombre_archivo_csv: str = "extraccion_data_v3_2.csv"):
    """
    Procesa:
      - fuentes_planas: se procesan directamente con recorrer_enlaces()
      - fuentes_recursivas: primero se obtienen sus subenlaces con obtener_enlaces(),
        y cada subenlace se procesa como URL de detalle (procesar_url_detalle).

    Al final genera:
      - Un único CSV con todos los resultados concatenados
      - Un informe con:
          * Fuentes procesadas correctamente
          * Fuentes NO procesadas por error
    """
    todos_resultados = []
    fuentes_ok = []
    fuentes_error = []

    # 1) Fuentes planas
    for fuente in fuentes_planas:
        print("\n" + "=" * 60)
        print(f"Procesando fuente PLANA: {fuente}")
        print("=" * 60)

        try:
            resultados_fuente = recorrer_enlaces(fuente)
            todos_resultados.extend(resultados_fuente)
            fuentes_ok.append(fuente)
        except Exception as e:
            print(f"[ERROR] No se ha podido procesar la fuente plana {fuente}: {e}")
            fuentes_error.append(fuente)

    # 2) Fuentes recursivas
    for fuente in fuentes_recursivas:
        print("\n" + "=" * 60)
        print(f"Procesando fuente RECURSIVA: {fuente}")
        print("=" * 60)

        try:
            subfuentes = obtener_enlaces(fuente)
        except Exception as e:
            print(f"[ERROR] No se ha podido obtener subenlaces de la fuente recursiva {fuente}: {e}")
            fuentes_error.append(fuente)
            continue

        print(f"  -> Encontradas {len(subfuentes)} subfuentes en {fuente}")

        # Cada subfuente se trata como URL de detalle (no como nueva fuente de listado)
        for sub in subfuentes:
            print(f"    Procesando subfuente DETALLE: {sub}")
            try:
                resultado_detalle = procesar_url_detalle(sub)
                todos_resultados.append(resultado_detalle)
            except Exception as e:
                print(f"    [ERROR] No se ha podido procesar la subfuente {sub} de {fuente}: {e}")

        # Si hemos llegado hasta aquí, consideramos la fuente recursiva como procesada
        fuentes_ok.append(fuente)

    # Guardamos TODO en un único CSV
    guardar_en_csv(todos_resultados, nombre_archivo_csv)

    # Informe final
    print("\n" + "#" * 60)
    print("RESUMEN FINAL")
    print("#" * 60)

    print("\nFuentes procesadas correctamente:")
    if fuentes_ok:
        for f in fuentes_ok:
            print(f"  - {f}")
    else:
        print("  (Ninguna)")

    print("\nFuentes NO procesadas por error:")
    if fuentes_error:
        for f in fuentes_error:
            print(f"  - {f}")
    else:
        print("  (Ninguna)")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ejecuta la extracción de convocatorias desde varias fuentes")
    parser.add_argument(
        "--fuente-plana",
        action="append",
        dest="fuente_plana",
        help="Añade una URL de listado plana a procesar (puede repetirse)",
    )
    parser.add_argument(
        "--fuente-recursiva",
        action="append",
        dest="fuente_recursiva",
        help="Añade una URL de listado recursivo a procesar (cada subenlace se trata como detalle)",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_path",
        help="Ruta completa del CSV resultante (por defecto se guarda en resultados_scraping)",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    fuentes_planas = args.fuente_plana or DEFAULT_FUENTES
    fuentes_recursivas = args.fuente_recursiva or DEFAULT_FUENTES_RECURSIVAS
    output_path = Path(args.output_path) if args.output_path else DEFAULT_OUTPUT_DIR / DEFAULT_OUTPUT_FILENAME
    output_path.parent.mkdir(parents=True, exist_ok=True)

    procesar_fuentes(
        fuentes_planas,
        fuentes_recursivas,
        nombre_archivo_csv=str(output_path),
    )


if __name__ == "__main__":
    raise SystemExit(main())

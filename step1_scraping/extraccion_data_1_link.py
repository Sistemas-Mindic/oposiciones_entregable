#!/Users/AndresFelipe/Desktop/Codigo/PROYECTO_OPOSICIONES/oposiciones_ia/bin/python
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

from lxml import html as lxml_html, etree

from step2_filtrado.palabras_oposiciones import palabras_oposiciones
from step2_filtrado.patrones_convocatoria import (
    _PAT_CONV, _PAT_EMP, _NEG_NO_EMPLEO,
    _RE_CONV, _RE_EMP, _RE_CANON, _RE_VENTANA, _RE_VENTANA_NEG,
    WINDOW_WORDS,
)

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
    para poder buscar <a> solo dentro de la zona principal.
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


def mi_limpiador(texto: str) -> str:
    """
    Limpieza genérica:
    - Desescapa entidades HTML
    - Quita NBSP
    - Pasa a minúsculas
    - Mantiene letras/dígitos/espacios y algunos separadores
    - Compacta espacios
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
    Descarga HTML, selecciona el main/article/div principal y devuelve el texto bruto.
    """
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        return extract_main_text_from_html(resp.text)
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
    API genérica: decide si la URL es PDF o HTML y devuelve el texto YA LIMPIO.
    (Se mantiene por compatibilidad si se llama desde otro módulo).
    """
    try:
        if es_pdf(url):
            texto_bruto = extraer_texto_pdf(url)
        else:
            texto_bruto = extraer_texto_html(url)
        return mi_limpiador(texto_bruto)
    except Exception as e:
        print(f"Error genérico extrayendo texto de {url}: {e}")
        return ""


# ---------------------------------------------------------------
#                   OBTENCIÓN DE ENLACES
# ---------------------------------------------------------------

def obtener_enlaces(url_base: str):
    """
    Devuelve la lista de enlaces absolutos encontrados dentro del contenedor principal
    (o, si falla, de todo el HTML).
    """
    try:
        resp = requests.get(url_base, timeout=20)
        resp.raise_for_status()
        html_str = resp.text
    except Exception as e:
        print(f"Error descargando {url_base}: {e}")
        return []

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

    print(f"Encontrados {len(enlaces)} enlaces en la página base.")
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
#                 RECORRER ENLACES Y EXTRAER INFO
# ---------------------------------------------------------------

def recorrer_enlaces(FUENTE: str):
    """
    Recorre todos los enlaces encontrados en la página FUENTE y devuelve
    una lista de dicts con:
      - url_detalle
      - texto (ya limpio)
      - es_pdf (True/False)
      - posible_convocatoria (True/False)
    """
    resultados = []
    for link in obtener_enlaces(FUENTE):
        print(f"Procesando {link}")

        # Calculamos una sola vez si es PDF para no hacer dos HEAD
        espdf = es_pdf(link)
        if espdf:
            texto_bruto = extraer_texto_pdf(link)
        else:
            texto_bruto = extraer_texto_html(link)

        texto_limpio = mi_limpiador(texto_bruto)
        possible = es_convocatoria_oposicion(texto_limpio)

        resultados.append({
            "url_detalle": link,
            "texto": texto_limpio,
            "es_pdf": espdf,
            "posible_convocatoria": possible
        })

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
      - contenido_pagina (resumen legible de la fila)
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
                "contenido_pagina"
            ])

            for item in resultados:
                url = item.get("url_detalle", "")
                texto = item.get("texto", "")
                espdf = item.get("es_pdf", False)
                possible = item.get("posible_convocatoria", False)

                partes = [
                    f"url_detalle: {url}",
                    f"contenido: {texto}",
                    f"posible_convocatoria: {possible}",
                ]
                contenido_pagina = " | ".join(partes)

                writer.writerow([
                    url,
                    texto,
                    espdf,
                    possible,
                    contenido_pagina
                ])

        print(f"Se guardaron {len(resultados)} filas en {nombre_archivo}")

    except Exception as e:
        print(f"Error guardando el CSV: {e}")


# ---------------------------------------------------------------
#                   EJECUCIÓN PRINCIPAL
# ---------------------------------------------------------------

FUENTE = "https://www.san.gva.es/es/web/recursos-humans/empleo-publico"

if __name__ == "__main__":
    resultados = recorrer_enlaces(FUENTE)
    guardar_en_csv(resultados)

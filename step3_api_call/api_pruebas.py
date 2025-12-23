#!/Users/AndresFelipe/Desktop/Codigo/PROYECTO_OPOSICIONES/oposiciones_ia/bin/python

# -----------------------------
# IMPORTS
# -----------------------------
import csv
import html
import re
import unicodedata
from io import BytesIO  # para convertir pdf
from urllib.parse import urljoin

import pdfplumber  # para pdf
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from requests.exceptions import SSLError, RequestException  # extraccion_data.py:5

# -----------------------------
# FASTAPI APP
# -----------------------------
app = FastAPI()

# -----------------------------
# EXTRACCIÓN DE DATA
# -----------------------------

def es_pdf(url):  # extraccion_data.py:11
    """Comprueba si una URL apunta a un PDF por el Content-Type."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        return "application/pdf" in content_type.lower()
    except SSLError as e:
        print(f"Certificado no válido en {url}: {e}")
        return False
    except RequestException as e:
        print(f"Error comprobando PDF para {url}: {e}")
        return False


def extraer_texto_pdf(url):
    """Descarga un PDF y extrae todo el texto con pdfplumber."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)
        texto = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                texto += page.extract_text() + "\n"
        return texto
    except Exception as e:
        print(f"Error extrayendo PDF de {url}: {e}")
        return ""


def extraccion_texto(url):
    """Devuelve texto de una URL, sea PDF o HTML."""
    try:
        if es_pdf(url):
            return extraer_texto_pdf(url)
        html_respuesta = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html_respuesta, "html.parser")
        return soup.get_text()
    except SSLError as e:
        print(f"Certificado no válido en {url}: {e}")
        return ""
    except RequestException as e:
        print(f"Error descargando {url}: {e}")
        return ""


# -----------------------------
# RECORRER ENLACES
# -----------------------------

def obtener_enlaces(url_base):
    """Devuelve todos los enlaces absolutos encontrados en la página base."""
    try:
        html_respuesta = requests.get(url_base, timeout=10).text
    except Exception as e:
        print(f"Error descargando {url_base}: {e}")
        return []

    soup = BeautifulSoup(html_respuesta, "html.parser")
    enlaces = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        enlace = urljoin(url_base, href)
        if enlace not in enlaces:
            enlaces.append(enlace)

    print(f"Encontrados {len(enlaces)} enlaces en la página base.")
    return enlaces


def recorrer_enlaces(FUENTE):
    """Descarga y procesa todas las URLs encontradas en la página base."""
    resultados = []
    for link in obtener_enlaces(FUENTE):
        print(f"Procesando {link}")
        texto = extraccion_texto(link)
        texto = mi_limpiador(texto)
        resultados.append(
            {
                "url": link,
                "texto": texto,
                "convocatoria": es_convocatoria_oposicion(texto),
            }
        )
    return resultados


# -----------------------------
# PROCESADO DE TEXTO
# -----------------------------

# Diccionario o glosario términos clave
from palabras_oposiciones import palabras_oposiciones  # noqa: F401 (si no lo usas aún)


def mi_limpiador(texto: str) -> str:
    # Normaliza entidades HTML y espacios "raros"
    texto = html.unescape(texto or "")
    texto = texto.replace("\u00A0", " ")  # NBSP -> espacio normal

    # Elimina hashtags y menciones "tipo social"
    texto = re.sub(r"#\w+", " ", texto)

    # Minúsculas
    texto = texto.lower()

    # 1) Permite letras/dígitos/espacio y algunos separadores útiles; el resto -> espacio
    #    Permitimos: / - : . , + (el + puede aparecer en teléfonos) y _
    texto = re.sub(r"[^\w\s/\-:\.,\+]", " ", texto, flags=re.UNICODE)

    # 2) Elimina guiones bajos
    texto = re.sub(r"_+", " ", texto)

    # 3) Compacta espacios
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


# Limpiador de acentos
def _norm(s: str) -> str:
    s = (s or "").replace("\u00A0", " ")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # quita acentos
    return s.lower()


# -----------------------------
# FILTRADO SI ES CONVOCATORIA
# -----------------------------

from patrones_convocatoria import (
    _PAT_CONV,
    _PAT_EMP,
    _NEG_NO_EMPLEO,
    _RE_CANON,
    _RE_CONV,
    _RE_EMP,
    _RE_VENTANA,
    _RE_VENTANA_NEG,
    WINDOW_WORDS,
)


def es_convocatoria_oposicion(texto: str) -> bool:
    """
    True si el texto apunta a CONVOCATORIA de empleo/oposiciones.
      - Frase canónica directa, o
      - Proximidad (≤ WINDOW_WORDS palabras) entre 'convocatoria' y léxico de empleo.
    Descarte:
      - Si solo hay 'convocatoria' y, cerca, hay léxico de licitación (sin empleo).
    """
    if not texto:
        return False

    norm = _norm(texto)

    # 1) Coincidencia directa (muy precisa)
    if _RE_CANON.search(norm):
        return True

    # 2) Proximidad convocatoria <-> empleo
    if _RE_VENTANA.search(norm):
        return True

    # 3) "Convocatoria" sin empleo + ventana negativa (licitación)
    if _RE_CONV.search(norm) and not _RE_EMP.search(norm) and _RE_VENTANA_NEG.search(norm):
        return False

    return False


# -----------------------------
# EXPORTAMOS DATA A CSV
# -----------------------------

def guardar_en_csv(resultados, nombre_archivo="resultados_enlaces_otro.csv"):
    """Escribe la lista de resultados en un CSV con columnas link y texto."""
    try:
        with open(nombre_archivo, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Enlace", "Contenido", "Convocatoria"])
            for item in resultados:
                writer.writerow(
                    [
                        item.get("url", ""),
                        item.get("texto", ""),
                        item.get("convocatoria", ""),
                    ]
                )
        print(f"Se guardaron {len(resultados)} filas en {nombre_archivo}")
    except Exception as e:
        print(f"Error guardando el CSV: {e}")


# -----------------------------
# ENDPOINT FASTAPI
# -----------------------------

@app.post("/procesar")
def procesar_fuente(
    fuente: str = "https://www.san.gva.es/es/web/recursos-humans/cobertura-temporal-procesos-abiertos",
    nombre_archivo: str = "resultados_enlaces_otro.csv",
):
    """
    Endpoint para lanzar el proceso de:
      - Recorrer enlaces de 'fuente'
      - Extraer texto y detectar si es convocatoria
      - Guardar en CSV 'nombre_archivo'
    """
    resultados = recorrer_enlaces(fuente)
    guardar_en_csv(resultados, nombre_archivo)
    return JSONResponse(
        {
            "status": "ok",
            "fuente": fuente,
            "nombre_archivo": nombre_archivo,
            "total_resultados": len(resultados),
        }
    )


# -----------------------------
# MODO SCRIPT (EJECUCIÓN DIRECTA)
# -----------------------------
if __name__ == "__main__":
    FUENTE = "https://www.san.gva.es/es/web/recursos-humans/cobertura-temporal-procesos-abiertos"
    resultados = recorrer_enlaces(FUENTE)
    guardar_en_csv(resultados)
    print("Ejecución directa finalizada.")

    # Si quieres levantar FastAPI desde aquí:
    # import uvicorn
    # uvicorn.run("NOMBRE_DEL_FICHERO_SIN_PY:app", host="0.0.0.0", port=8000, reload=True)

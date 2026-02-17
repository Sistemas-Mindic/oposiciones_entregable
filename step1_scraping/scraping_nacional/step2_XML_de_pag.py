"""
Scraping empleo público AGE:
- Usa filtros del JSON filtros_empleo_publico.json
- Construye la URL de resultados
- Abre la página con Selenium (Chrome headless, perfil limpio)
- Hace clic en "Descargar XML"
- Espera a que se descargue el .xml y lo lee desde disco
- Parsea el XML y devuelve una lista de dicts (XML crudo)
- Exporta opcionalmente a CSV

Requisitos (en tu .venv):
    pip install selenium webdriver-manager beautifulsoup4 requests lxml
"""

import argparse
import csv
import json
import sys
import time
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import re  # <-- CAMBIO 1: Importamos re para limpieza
from lxml import etree  # <-- CAMBIO 2: Importamos lxml para mayor tolerancia a errores
from datetime import datetime
from pathlib import Path
import tempfile

import requests  # Por si lo necesitas más adelante (aquí no es obligatorio)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# -------------------------------------------------------------------
#  CONFIGURACIÓN GENERAL
# -------------------------------------------------------------------

BASE_RESULTADOS_URL = (
    "https://administracion.gob.es/pagFront/ofertasempleopublico/resultadosEmpleo.htm"
)

# JSON generado con tu otro script
FILTROS_JSON = Path(__file__).with_name("filtros_empleo_publico.json")

# Carpeta base donde se guardarán los XML descargados (se crearán subcarpetas por ejecución)
DOWNLOAD_DIR = Path(__file__).with_name("descargas_xml")
DOWNLOAD_DIR.mkdir(exist_ok=True)

DEFAULT_OUTPUT_CSV = Path(__file__).with_name("convocatorias_age_crudo_v2.csv")


# -------------------------------------------------------------------
#  UTILIDADES BÁSICAS
# -------------------------------------------------------------------

def normalizar_texto(s: str) -> str:
    """
    Normaliza un texto:
    - Quita espacios extremos
    - Elimina tildes
    - Pasa a mayúsculas
    """
    s = s.strip()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper()


def cargar_catalogos_filtros(path: Path | str = FILTROS_JSON) -> dict:
    """
    Carga el JSON de filtros y devuelve solo el bloque 'filtros'.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "filtros" not in data:
        raise KeyError("El JSON de filtros no contiene 'filtros'.")
    return data["filtros"]


def obtener_codigo_filtro_texto(
    catalogos: dict, nombre_filtro: str, texto_usuario: str | None
):
    """
    Devuelve el código (value del <option>) asociado al texto del usuario,
    usando el JSON de filtros.

    Si no hay texto, devuelve None.
    Si el filtro no es de tipo 'select', devuelve None.
    Si el texto no existe, lanza ValueError.
    """
    if not texto_usuario:
        return None

    meta = catalogos.get(nombre_filtro)
    if not meta or meta.get("tipo") != "select":
        return None

    opciones = meta["opciones"]
    mapa = {normalizar_texto(k): v for k, v in opciones.items()}
    clave = normalizar_texto(texto_usuario)

    if clave not in mapa:
        raise ValueError(
            f"Valor '{texto_usuario}' no válido para el filtro '{nombre_filtro}'."
        )

    return mapa[clave]


# -------------------------------------------------------------------
#  CONSTRUCCIÓN DE PARÁMETROS (URL)
# -------------------------------------------------------------------

# Mapa: nombre lógico del filtro -> (nombre parametro, nombre flag)
MAPA_PARAMETROS_URL = {
    "ambito_geografico": ("ambitoGeografico", "_ambitoGeografico"),
    "comunidad_autonoma": ("comunidadAutonoma", "_comunidadAutonoma"),
    "provincia": ("provincia", "_provincia"),
    "administracion_convocante": (
        "administracionConvocante",
        "_administracionConvocante",
    ),
    "nivel_titulacion": ("nivelTitulacion", "_nivelTitulacion"),
    "via_acceso": ("viaAcceso", "_viaAcceso"),
    "tipo_personal": ("tipoPersonal", "_tipoPersonal"),
    "plazo": ("tipoPlazo", "_tipoPlazo"),
    "discapacidad": ("discapacidad", "_discapacidad"),
}


def construir_params_busqueda(criterios: dict, catalogos: dict) -> dict:
    """
    Construye el diccionario de parámetros GET para resultadosEmpleo.htm.
    Replica lo más posible el comportamiento del formulario oficial:
    - Parámetros base fijos (incluyendo tipoPlazo=1 para abiertas)
    - Aplica los filtros select informados por el usuario
    - Añade _provincia=1 si no hay provincia concreta pero sí ámbito/CCAA
    """

    criterios_efectivos = dict(criterios)

    # Inferir ámbito si no lo han puesto pero sí hay CCAA o provincia
    if not criterios_efectivos.get("ambito_geografico"):
        if criterios_efectivos.get("provincia"):
            criterios_efectivos["ambito_geografico"] = "LOCAL"
        elif criterios_efectivos.get("comunidad_autonoma"):
            criterios_efectivos["ambito_geografico"] = "AUTONOMICO"

    # Parámetros base fijos, vistos en la URL del formulario oficial
    params = {
        "referencia": "",
        "tipoConvocatoria": "2",

        # SOLO PARA MANTENER CONVOCATORIAS ABIERTAS
        "tipoPlazo": "1",
        "_tipoPlazo": "1",

        "_discapacidadGeneral": "on",
        "_discapacidadIntelectual": "on",
        "_tipoPersonal": "1",          # valor por defecto del formulario
        "_administracionConvocante": "1",
        "viaAcceso": "2",              # valor por defecto en el ejemplo

        "_tipoBusqueda": "on",
        "orders": "id",
        "sort": "desc",
        "desde": "1",
        "tam": "",
        "txtClaveE": "",
        "tipoPlazaPublicacion": "",

        "tipoFechas": "default",
        "fechaPublicacionDesde": "",
        "fechaPublicacionHasta": "",
        "buscar": "true",
    }

    # Aplicar filtros select según el JSON
    for nombre_filtro, (param, flag) in MAPA_PARAMETROS_URL.items():
        texto = criterios_efectivos.get(nombre_filtro)
        if not texto:
            continue

        codigo = obtener_codigo_filtro_texto(catalogos, nombre_filtro, texto)
        if codigo:
            params[param] = codigo
            params[flag] = "1"

    # Lógica especial para _provincia=1 sin provincia concreta
    if "provincia" not in criterios_efectivos and (
        "comunidadAutonoma" in params or params.get("ambitoGeografico") in ("3", "4")
    ):
        params["_provincia"] = "1"

    # Filtrado de vacíos, pero respetando los que el formulario manda vacíos
    params_filtrados = {}
    for k, v in params.items():
        if v == "" and k not in (
            "referencia",
            "tam",
            "tipoPlazaPublicacion",
            "fechaPublicacionDesde",
            "fechaPublicacionHasta",
            "txtClaveE",
        ):
            # Campos vacíos que el formulario no suele mandar → se eliminan
            continue
        params_filtrados[k] = v

    return params_filtrados


# -------------------------------------------------------------------
#  SELENIUM: DRIVER Y DESCARGA XML
# -------------------------------------------------------------------

def _crear_driver_con_descargas(download_dir: Path) -> webdriver.Chrome:
    """
    Crea una instancia de Chrome headless, configurada para descargar
    automáticamente los archivos en la carpeta indicada.
    Versión estable (sin incógnito ni perfiles temporales raros).
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    prefs = {
        "download.default_directory": str(download_dir.resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver



from datetime import datetime

def descargar_xml_con_selenium(
    full_url: str,
    base_download_dir: Path = DOWNLOAD_DIR
) -> bytes:
    """
    Abre la página de resultados, pulsa 'Descargar XML'
    y lee el fichero .xml descargado en un subdirectorio único.

    - Usa una subcarpeta nueva por ejecución (para no mezclar XML antiguos).
    - Configuración de Chrome sencilla y estable (sin borrar cookies ni recargar).
    """

    # 📂 Subcarpeta única por ejecución (evita mezclar descargas)
    run_dir_name = datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
    download_dir = base_download_dir / run_dir_name
    download_dir.mkdir(parents=True, exist_ok=True)

    print(f"Directorio de descargas de esta ejecución: {download_dir}")

    driver = _crear_driver_con_descargas(download_dir)

    try:
        print(f"Abrimos URL en Selenium:\n{full_url}\n")
        driver.get(full_url)

        # Pequeña espera general por si hay scripts/cookies iniciales
        time.sleep(2)

        # 1) Buscar botón
        wait = WebDriverWait(driver, 60)
        print("Buscando botón de 'Descargar XML'...")
        boton = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[onclick*='downloadXML']"))
        )
        print("Botón encontrado, haciendo clic...")
        boton.click()

        # 2) Esperar a que aparezca un archivo .xml en la carpeta de descargas
        timeout = time.time() + 60
        xml_path = None

        print("Esperando a que se descargue el XML...")
        while time.time() < timeout:
            # Ignoramos posibles .crdownload y solo miramos .xml finales
            xml_files = list(download_dir.glob("*.xml"))
            if xml_files:
                xml_path = xml_files[0]
                break
            time.sleep(0.5)

        if not xml_path:
            raise RuntimeError(
                f"No se encontró ningún archivo .xml descargado en {download_dir}"
            )

        print(f"XML descargado en: {xml_path}")
        xml_bytes = xml_path.read_bytes()
        return xml_bytes

    finally:
        driver.quit()



# -------------------------------------------------------------------
#  PARSEO XML
# -------------------------------------------------------------------

def parsear_xml_convocatorias_bytes(xml_bytes: bytes) -> list[dict]:
    """
    Parsea el XML de convocatorias y devuelve una lista de dicts.
    CAMBIO 3: Añadida limpieza de caracteres de control y parser tolerante (lxml).
    """
    try:
        # Limpieza de bytes correspondientes a caracteres de control (inválidos en XML)
        xml_limpio = re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]', b'', xml_bytes)
        
        # Usamos lxml con recover=True para saltar errores de tokens inválidos (como el de la línea 8905)
        parser = etree.XMLParser(recover=True, encoding='utf-8')
        root = etree.fromstring(xml_limpio, parser=parser)
    except Exception as e:
        print(f"Advertencia: El parser avanzado detectó problemas, intentando fallback: {e}")
        # Fallback al método original si lxml falla catastróficamente
        root = ET.fromstring(xml_bytes)

    registros = []

    for nodo in root.findall(".//convocatorias"):
        if nodo.find("id") is None:
            continue

        reg = {child.tag: (child.text or "").strip() for child in nodo}
        registros.append(reg)

    return registros


# -------------------------------------------------------------------
#  FUNCIÓN PRINCIPAL (XML CRUDO)
# -------------------------------------------------------------------

def buscar_y_descargar_xml_automatico(criterios: dict) -> list[dict]:
    """
    Flujo completo:
    - Carga filtros del JSON
    - Construye parámetros de búsqueda a partir de 'criterios'
    - Construye la URL final
    - Descarga el XML con Selenium
    - Parsea el XML en list[dict]
    - Devuelve directamente la lista cruda (sin filtros en memoria)
    """
    catalogos = cargar_catalogos_filtros()
    params = construir_params_busqueda(criterios, catalogos)

    # Construir URL final
    full_url = BASE_RESULTADOS_URL + "?" + urllib.parse.urlencode(params)
    print(f"URL final utilizada:\n{full_url}\n")

    # Scraping
    xml_bytes = descargar_xml_con_selenium(full_url)
    registros = parsear_xml_convocatorias_bytes(xml_bytes)
    print(f"Registros crudos del XML: {len(registros)}")

    if registros:
        print("Claves del primer registro:", list(registros[0].keys()))

    return registros


# -------------------------------------------------------------------
#  EXPORTAR CSV
# -------------------------------------------------------------------

def exportar_registros_a_csv(registros: list[dict], ruta_csv: Path):
    """
    Exporta la lista de registros (list[dict]) a un CSV.

    - Cada clave del diccionario será una columna.
    - Cada registro será una fila.
    - Si algún registro no tiene alguna clave, se deja la celda vacía.

    El CSV se guarda con codificación UTF-8 BOM para que se vea bien en Excel.
    """
    if not registros:
        print("No hay registros para exportar. No se crea el CSV.")
        return

    # Tomamos todas las posibles claves (por si alguna fila tuviera alguna extra)
    todas_las_claves = set()
    for r in registros:
        todas_las_claves.update(r.keys())

    # Mantener un orden estable:
    # primero las claves del primer registro, luego el resto ordenadas
    claves_primero = list(registros[0].keys())
    resto_claves = sorted(k for k in todas_las_claves if k not in claves_primero)
    columnas = claves_primero + resto_claves

    ruta_csv.parent.mkdir(parents=True, exist_ok=True)

    with ruta_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()

        for reg in registros:
            fila = {col: reg.get(col, "") for col in columnas}
            writer.writerow(fila)

    print(f"CSV creado en: {ruta_csv}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Descarga convocatorias AGE en CSV y exporta los registros."
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Ruta donde se guardará el CSV generado (por defecto convocatorias_age_crudo_v2.csv).",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    print("Iniciando scraping AGE...\n")

    criterios = {
       # "ambito_geografico": "LOCAL",
       # "comunidad_autonoma": "ANDALUCÍA",
        #"plazo": "ABIERTO",  # ya se aplica con tipoPlazo=1
       # "nivel_titulacion": "GRADO UNIVERSITARIO, LICENCIATURA, DOCTORADO O EQUIVALENTE",
       # "administracion_convocante": "ESTADO",
    }

    registros = buscar_y_descargar_xml_automatico(criterios)
    print("Convocatorias obtenidas (XML crudo):", len(registros))

    if registros:
        print("\nPrimer registro (XML crudo):")
        for k, v in registros[0].items():
            print(f"  {k}: {v}")

        ruta_csv = Path(args.output_csv)
        exportar_registros_a_csv(registros, ruta_csv)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

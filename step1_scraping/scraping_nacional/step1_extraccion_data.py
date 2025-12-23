import json
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup
## 
"""
Este codigo crea el diccionario de con los codigos de la pagina https://administracion.gob.es/pagFront/ofertasempleopublico/resultadosEmpleo.htm?referencia=&_ambitoGeografico=1&_comunidadAutonoma=1&_provincia=1&tipoPlazo=1&_tipoPlazo=1&_discapacidadGeneral=on&_discapacidadIntelectual=on&_tipoPersonal=1&tipoFechas=default&fechaPublicacionDesde=&fechaPublicacionHasta=&tipoPlazaPublicacion=&_tipoBusqueda=on&_administracionConvocante=1&_nivelTitulacion=1&orders=id&sort=desc&desde=1&tam=&txtClaveE=&viaAcceso=&buscar=true
para poder filtrar las busquedas

"""
# -------------------------------------------------------------------
#  CONFIGURACIÓN
# -------------------------------------------------------------------

# Archivo HTML que guardaste desde el navegador
HTML_LOCAL = Path(__file__).with_name("buscador_empleo.html")

# Mapa: nombre lógico del filtro -> atributo name="" del <select> en el HTML
# ✔ CORREGIDO: plazo ahora es "tipoPlazo"
SELECTS_DE_FILTROS = {
    "ambito_geografico":      "ambitoGeografico",
    "comunidad_autonoma":     "comunidadAutonoma",
    "provincia":              "provincia",

    "administracion_convocante": "administracionConvocante",
    "via_acceso":                "tipoAcceso",
    "tipo_personal":             "tipoPersonal",

    # ✔ NOMBRE REAL DEL SELECT DEL PLAZO
    "plazo":                     "tipoPlazo",

    "nivel_titulacion":          "nivelTitulacion",
    "discapacidad":              "discapacidad",
}


# -------------------------------------------------------------------
#  FUNCIONES AUXILIARES
# -------------------------------------------------------------------

def normalizar_texto(s: str) -> str:
    """
    Normaliza el texto para que 'València', 'VALENCIA' y 'valencia ' sean iguales.
    """
    if not s:
        return ""
    s = s.strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper()


def extraer_diccionario_select(soup: BeautifulSoup, nombre_campo: str) -> dict:
    """
    Convierte un <select name="nombre_campo"> en un dict con formato:
        TEXTO_NORMALIZADO -> value
    Omitiendo:
        - opciones sin value
        - opciones tipo "Todos..."
    """
    select = soup.find("select", {"name": nombre_campo})
    if not select:
        raise RuntimeError(f"No se encontró <select name='{nombre_campo}'> en el HTML.")

    opciones = {}

    for opt in select.find_all("option"):
        value = opt.get("value")
        etiqueta = opt.get_text(strip=True)

        if not value:
            continue

        texto_norm = normalizar_texto(etiqueta)

        # Omitir "TODOS / TODAS / TODA"
        if "TOD" in texto_norm:
            continue

        opciones[texto_norm] = value

    return opciones


# -------------------------------------------------------------------
#  GENERACIÓN DEL JSON
# -------------------------------------------------------------------

def construir_todos_los_catalogos():
    """
    - Carga el HTML local del buscador.
    - Extrae las opciones de todos los <select>.
    - Agrega los filtros no select.
    - Guarda 'filtros_empleo_publico.json'.
    """
    if not HTML_LOCAL.exists():
        raise FileNotFoundError(
            f"No se encuentra {HTML_LOCAL}.\n"
            "Guarda la página como 'buscador_empleo.html' en la misma carpeta."
        )

    html = HTML_LOCAL.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    filtros = {}

    # 1) Extraer <select> automáticamente
    for nombre_filtro, nombre_select in SELECTS_DE_FILTROS.items():
        try:
            opciones = extraer_diccionario_select(soup, nombre_select)
            filtros[nombre_filtro] = {
                "tipo": "select",
                "opciones": opciones,
            }
        except RuntimeError as e:
            print(f"[AVISO] {e}")

    # 2) Filtros no select
    filtros["referencia"] = {
        "tipo": "texto",
        "descripcion": "Número de referencia exacto de la convocatoria."
    }

    filtros["fecha_publicacion"] = {
        "tipo": "fecha_intervalo",
        "campos": ["desde", "hasta"]
    }

    filtros["plazas_convocadas"] = {
        "tipo": "numero_con_operador",
        "operadores": [
            "TODAS", "IGUAL A", "MENOR QUE", "MAYOR QUE",
            "MENOR O IGUAL QUE", "MAYOR O IGUAL QUE", "INTERVALO"
        ]
    }

    filtros["bolsa_empleo"] = {
        "tipo": "booleano",
        "descripcion": "Si está a true, mostrar solo bolsas de empleo."
    }

    filtros["denominacion_cuerpo_proceso"] = {
        "tipo": "texto",
        "descripcion": "Texto libre con la denominación del cuerpo/proceso."
    }

    # 3) Guardar JSON
    salida = HTML_LOCAL.with_name("filtros_empleo_publico.json")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump({"filtros": filtros}, f, ensure_ascii=False, indent=2)

    return filtros, salida


# -------------------------------------------------------------------
#  MAIN
# -------------------------------------------------------------------

if __name__ == "__main__":
    filtros, ruta = construir_todos_los_catalogos()
    print(f"\n✔ Catálogo de filtros generado en: {ruta}\n")

    if "plazo" in filtros:
        print("PLAZO (TEXTO_NORMALIZADO -> value HTML):")
        for t, v in filtros["plazo"]["opciones"].items():
            print(f"  {t} -> {v}")

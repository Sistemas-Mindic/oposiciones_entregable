#prompts_common.py
MULTILINGUAL_BLOCK = (
    "<multilingual_context>\n"
    "El documento puede estar en CASTELLANO, CATALÁN/VALENCIANO, GALLEGO o EUSKERA.\n"
    "Debes ENTENDER el idioma original, pero GENERAR TODA LA SALIDA en CASTELLANO estándar,\n"
    "salvo los nombres propios oficiales.\n"
    "\n"
    "1. CATEGORÍAS (PERFIL): Mapea siempre al estándar en castellano.\n"
    "   - Enfermería → 'enfermeria'.\n"
    "   - TCAE / Auxiliar de Enfermería → 'tcae'.\n"
    "\n"
    "2. TIPOS DE PROCESO: Usa siempre las etiquetas estándar en castellano.\n"
    "   - Bolsa de empleo → 'BOLSA'.\n"
    "   - Concurso → 'CONCURSO'.\n"
    "   - Oposición → 'OPOSICION'.\n"
    "   - Concurso-oposición → 'CONCURSO-OPOSICION'.\n"
    "   - Otros casos → 'OTRO'.\n"
    "\n"
    "3. CAMPOS DE TEXTO LIBRE (títulos, requisitos, etc.):\n"
    "   - Redáctalos siempre en castellano neutro, aunque el original esté en otra lengua.\n"
    "   - Resume y reformula si hace falta, pero mantén el significado.\n"
    "\n"
    "4. TÍTULOS Y ORGANISMOS: no traduzcas nombres propios oficiales.\n"
    "   - Mantén formas como 'Generalitat de Catalunya', 'Osakidetza',\n"
    "     'Servizo Galego de Saúde', etc., tal cual aparecen.\n"
    "</multilingual_context>\n\n"
)


AMBITO_TERRITORIAL_RESUMIDO_OPCIONES = [
    "NACIONAL",
    "INTERNACIONAL",
   
    "AUTONOMICO - ANDALUCIA",
    "AUTONOMICO - ARAGON",
    "AUTONOMICO - ASTURIAS, PRINCIPADO DE",
    "AUTONOMICO - BALEARS, ILLES",
    "AUTONOMICO - CANARIAS",
    "AUTONOMICO - CANTABRIA",
    "AUTONOMICO - CASTILLA Y LEON",
    "AUTONOMICO - CASTILLA-LA MANCHA",
    "AUTONOMICO - CATALUNA",
    "AUTONOMICO - COMUNITAT VALENCIANA",
    "AUTONOMICO - EXTREMADURA",
    "AUTONOMICO - GALICIA",
    "AUTONOMICO - MADRID, COMUNIDAD DE",
    "AUTONOMICO - MURCIA, REGION DE",
    "AUTONOMICO - NAVARRA, COMUNIDAD FORAL DE",
    "AUTONOMICO - PAIS VASCO",
    "AUTONOMICO - RIOJA, LA",
    "AUTONOMICO - CIUDAD DE CEUTA",
    "AUTONOMICO - CIUDAD DE MELILLA",

    "LOCAL - ANDALUCIA - ALMERIA",
    "LOCAL - ANDALUCIA - CADIZ",
    "LOCAL - ANDALUCIA - CORDOBA",
    "LOCAL - ANDALUCIA - GRANADA",
    "LOCAL - ANDALUCIA - HUELVA",
    "LOCAL - ANDALUCIA - JAEN",
    "LOCAL - ANDALUCIA - MALAGA",
    "LOCAL - ANDALUCIA - SEVILLA",

    "LOCAL - ARAGON - HUESCA",
    "LOCAL - ARAGON - TERUEL",
    "LOCAL - ARAGON - ZARAGOZA",

    "LOCAL - ASTURIAS, PRINCIPADO DE - ASTURIAS",

    "LOCAL - BALEARS, ILLES - BALEARS (ILLES)",

    "LOCAL - CANARIAS - LAS PALMAS",
    "LOCAL - CANARIAS - SANTA CRUZ DE TENERIFE",

    "LOCAL - CANTABRIA - CANTABRIA",

    "LOCAL - CASTILLA Y LEON - AVILA",
    "LOCAL - CASTILLA Y LEON - BURGOS",
    "LOCAL - CASTILLA Y LEON - LEON",
    "LOCAL - CASTILLA Y LEON - PALENCIA",
    "LOCAL - CASTILLA Y LEON - SALAMANCA",
    "LOCAL - CASTILLA Y LEON - SEGOVIA",
    "LOCAL - CASTILLA Y LEON - SORIA",
    "LOCAL - CASTILLA Y LEON - VALLADOLID",
    "LOCAL - CASTILLA Y LEON - ZAMORA",

    "LOCAL - CASTILLA-LA MANCHA - ALBACETE",
    "LOCAL - CASTILLA-LA MANCHA - CIUDAD REAL",
    "LOCAL - CASTILLA-LA MANCHA - CUENCA",
    "LOCAL - CASTILLA-LA MANCHA - GUADALAJARA",
    "LOCAL - CASTILLA-LA MANCHA - TOLEDO",

    "LOCAL - CATALUNA - BARCELONA",
    "LOCAL - CATALUNA - GIRONA",
    "LOCAL - CATALUNA - LLEIDA",
    "LOCAL - CATALUNA - TARRAGONA",

    "LOCAL - COMUNITAT VALENCIANA - ALICANTE",
    "LOCAL - COMUNITAT VALENCIANA - CASTELLON",
    "LOCAL - COMUNITAT VALENCIANA - VALENCIA",

    "LOCAL - EXTREMADURA - BADAJOZ",
    "LOCAL - EXTREMADURA - CACERES",

    "LOCAL - GALICIA - A CORUNA",
    "LOCAL - GALICIA - LUGO",
    "LOCAL - GALICIA - OURENSE",
    "LOCAL - GALICIA - PONTEVEDRA",

    "LOCAL - MADRID, COMUNIDAD DE - MADRID",

    "LOCAL - MURCIA, REGION DE - MURCIA",

    "LOCAL - NAVARRA, COMUNIDAD FORAL DE - NAVARRA",

    "LOCAL - PAIS VASCO - ARABA/ALAVA",
    "LOCAL - PAIS VASCO - BIZKAIA",
    "LOCAL - PAIS VASCO - GIPUZKOA",

    "LOCAL - RIOJA, LA - LA RIOJA",

    "LOCAL - CIUDAD DE CEUTA - CEUTA",
    "LOCAL - CIUDAD DE MELILLA - MELILLA",

     "OTRO"
]
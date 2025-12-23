analizar_tabla = {
    "name": "analizar_tabla",
    "description": (
        "Tool auxiliar para analizar bloques de texto que representan TABLAS, ANEXOS o "
        "listados internos de puestos/plazas dentro de un mismo proceso.\n\n"
        "NO forma parte de la fase 1 ni de la fase 2 principales, "
        "sino que puede llamarse de forma opcional cuando el modelo detecta que un "
        "fragmento de texto tiene estructura de tabla/anexo con múltiples filas de "
        "categorías o puestos y no tiene claro qué filas corresponden a ENFERMERÍA o TCAE.\n\n"
        "Objetivo:\n"
        "  - Recibir solo el texto de la tabla/anexo (no todo el documento).\n"
        "  - Identificar qué filas pertenecen a ENFERMERÍA y cuáles a TCAE/auxiliar.\n"
        "  - Señalar, para cada perfil, una FILA PRINCIPAL representativa que luego se "
        "    usará en la fase de extracción (extraer_convocatorias_sanitarias_csv) "
        "    para consolidar en, como máximo, una convocatoria de ENFERMERÍA y otra de TCAE.\n\n"
        "La salida esperada de esta tool (conceptualmente) incluye:\n"
        "  - hay_enfermeria: bool\n"
        "  - hay_tcae: bool\n"
        "  - fila_principal_enfermeria: string (vacío si no hay enfermería)\n"
        "  - fila_principal_tcae: string (vacío si no hay TCAE)\n"
        "  - filas_enfermeria: array de strings con todas las filas detectadas de enfermería\n"
        "  - filas_tcae: array de strings con todas las filas detectadas de TCAE/auxiliar\n"
        "  - filas_otras: array de strings con el resto de filas no sanitarias\n\n"
        "Notas importantes:\n"
        "  - Solo debe analizar el fragmento de texto que parece tabla/anexo, "
        "    no el documento completo, para ahorrar tokens y evitar ruido.\n"
        "  - No construye convocatorias completas ni rellena campos de CSV; simplemente "
        "    ayuda a decidir qué filas son relevantes y cuál es la fila más representativa "
        "    por perfil.\n"
        "  - La clasificación de filas en ENFERMERÍA/TCAE se basa en la misma lógica "
        "    que TITULACION_REQUERIDA → PERFIL, usando denominaciones de enfermería "
        "    (DUE, ATS, grado en enfermería, especialidades, etc.) y de TCAE/auxiliar.\n"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "texto_tabla": {
                "type": "string",
                "description": (
                    "Únicamente el bloque de texto que corresponde a la tabla/anexo/listado de puestos. "
                    "Por ejemplo, un ANEXO I de plazas con códigos 001, 002, 003... y descripciones de "
                    "categorías, destinos y plazas.\n"
                    "No enviar aquí todo el documento, solo el trozo tabular."
                )
            },
            "tipo_fuente": {
                "type": "string",
                "description": (
                    "Tipo técnico de origen de este bloque tabular, si se conoce:\n"
                    "  - 'pdf'  → tabla/anexo extraído de un PDF (decreto, resolución, boletín...).\n"
                    "  - 'html' → tabla/listado extraído de una página web.\n"
                    "Se usa solo como pista; la lógica principal se basa en el texto."
                ),
                "enum": ["pdf", "html"]
            }
        },
        "required": ["texto_tabla"]
    }
}

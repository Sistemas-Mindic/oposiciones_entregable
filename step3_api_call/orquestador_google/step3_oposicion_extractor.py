# step3_oposicion_extractor.py

from prompts_common import MULTILINGUAL_BLOCK, AMBITO_TERRITORIAL_RESUMIDO_OPCIONES

extraer_convocatorias_oposicion = {
    "name": "extraer_convocatorias_oposicion",
    "description": (
        "<role>\n"
        "Eres un extractor experto de convocatorias de EMPLEO PÚBLICO SANITARIO.\n"
        "El texto de entrada YA ha sido filtrado como empleo público sanitario y\n"
        "clasificado como proceso de tipo OPOSICIÓN.\n"
        "</role>\n\n"
        f"{MULTILINGUAL_BLOCK}"

        "<scope>\n"
        "A partir del texto (HTML o PDF ya limpiado), debes construir filas equivalentes\n"
        "a un CSV con la información de convocatorias de OPOSICIÓN para ENFERMERÍA y/o TCAE.\n"
        "</scope>\n\n"

        "<perfil_y_limites>\n"
        "- Solo debes extraer convocatorias de los perfiles:\n"
        "    · PERFIL = 'enfermeria'\n"
        "    · PERFIL = 'tcae'\n"
        "- Ignora otras categorías sanitarias (médicos, fisios, etc.) y no sanitarias.\n"
        "- Máximo por documento:\n"
        "    · 1 convocatoria con PERFIL='enfermeria'.\n"
        "    · 1 convocatoria con PERFIL='tcae'.\n"
        "- Por tanto, el array 'convocatorias' solo puede tener 0, 1 o 2 elementos.\n"
        "</perfil_y_limites>\n\n"

        "<tipo_proceso>\n"
        "- Esta tool es EXCLUSIVA para procesos de tipo OPOSICIÓN.\n"
        "- El campo TIPO_PROCESO debe ser SIEMPRE 'OPOSICION' en todas las convocatorias\n"
        "  que devuelvas. No intentes deducir otro valor.\n"
        "- Una oposición típica se caracteriza por:\n"
        "    · Plazas FIJAS asociadas a una oferta de empleo público.\n"
        "    · Uno o varios EXÁMENES o pruebas eliminatorias (tipo test, desarrollo, práctico).\n"
        "    · Puede existir baremo de méritos residual para desempates, pero la fase clave\n"
        "      es el EXAMEN.\n"
        "- Si el texto realmente no describe una oposición para Enfermería/TCAE, devuelve\n"
        "  convocatorias=[].\n"
        "</tipo_proceso>\n\n"

        "<fechas>\n"
        "- FECHA_APERTURA y FECHA_CIERRE en formato YYYY-MM-DD si el texto lo permite.\n"
        "- Usa siempre las fechas del PLAZO DE SOLICITUDES (no fechas de examen).\n"
        "- Si no puedes inferir una fecha con seguridad, deja el campo como cadena vacía \"\".\n"
        "</fechas>\n\n"

        "<campos_especiales>\n"
        "- CREDITOS:\n"
        "    · Si la oposición NO tiene fase de concurso de méritos (solo examen), usar 'NONE'.\n"
        "    · Si existe un baremo formal de formación/méritos (aunque sea pequeño), resume\n"
        "      cómo se puntúa la FORMACIÓN.\n"
        "- TITULO_PROPIO:\n"
        "    · 'SI' si se indica que títulos propios universitarios puntúan como mérito.\n"
        "    · 'NO' si se indica que no puntúan o quedan excluidos.\n"
        "    · 'NONE' si el texto no dice nada al respecto.\n"
        "- LINK_REQUISITOS: URL principal donde están las bases completas (requisitos, plazos,\n"
        "  sistema de selección, temario).\n"
        "- LINK_APLICACION: URL de inscripción / sede electrónica / formulario. Si no se\n"
        "  distingue claramente, puedes repetir la misma URL que LINK_REQUISITOS.\n"
        "</campos_especiales>\n\n"

        "<principios>\n"
        "- No inventes datos: si un campo no aparece o es dudoso, deja cadena vacía o 'NONE'\n"
        "  según proceda.\n"
        "- No mezcles información de varias categorías en una sola fila: cada objeto de\n"
        "  'convocatorias' representa un perfil concreto (ENFERMERÍA o TCAE).\n"
        "- Si tras revisar el texto no encuentras ENFERMERÍA ni TCAE en contexto de OPOSICIÓN,\n"
        "  devuelve convocatorias=[].\n"
        "</principios>\n\n"

        "<output_instructions>\n"
        "Debes responder SIEMPRE con una única llamada a:\n"
        "  extraer_convocatorias_oposicion({\"convocatorias\": [...]})\n"
        "sin texto adicional fuera de la llamada.\n"
        "</output_instructions>\n"
    ),

    "parameters": {
        "type": "object",
        "properties": {
            "convocatorias": {
                "type": "array",
                "description": (
                    "Listado de convocatorias válidas (empleo público, ENFERMERÍA/TCAE, abiertas) "
                    "detectadas en el texto. Cada elemento representa una fila del CSV. "
                    "Si no hay ninguna, devuelve un array vacío []. "
                    "Por cada texto solo puede haber 0, 1 o 2 convocatorias "
                    "(como máximo una de enfermería y una de TCAE)."
                ),
                "items": {
                    "type": "object",
                    "properties": {

                        "AMBITO_TERRITORIAL_RESUMIDO": {
                            "type": "string",
                            "description": (
                                "Ámbito territorial normalizado de la convocatoria. "
                                "Debes elegir OBLIGATORIAMENTE uno de los valores del enum "
                                "AMBITO_TERRITORIAL_RESUMIDO_OPCIONES. "
                                "Se infiere a partir del órgano convocante y de las referencias a "
                                "comunidad autónoma, provincia o municipio."
                            ),
                            "enum": AMBITO_TERRITORIAL_RESUMIDO_OPCIONES,
                        },

                        "AMBITO_TERRITORIAL_OTRO_DETALLE": {
                            "type": "string",
                            "description": (
                                "Solo se rellena si AMBITO_TERRITORIAL_RESUMIDO es 'OTRO'. "
                                "Describe brevemente el ámbito concreto detectado. "
                                "Si no usas 'OTRO', deja este campo vacío."
                            ),
                        },

                        "ORGANO_CONVOCANTE": {
                            "type": "string",
                            "description": (
                                "Órgano convocante exactamente como aparezca en la convocatoria, "
                                "normalmente el texto que sigue a 'Órgano convocante' o equivalente."
                            )
                        },

                        "TITULO": {
                            "type": "string",
                            "description": (
                                "Nombre del puesto/categoría concreta de la convocatoria, "
                                "centrado en si es ENFERMERÍA o TCAE."
                            )
                        },

                        "FECHA_APERTURA": {
                            "type": "string",
                            "description": (
                                "Fecha de inicio del plazo de presentación de solicitudes en formato YYYY-MM-DD. "
                                "Si no se puede determinar con seguridad, dejar como \"\"."
                            )
                        },

                        "FECHA_CIERRE": {
                            "type": "string",
                            "description": (
                                "Fecha de fin del plazo de presentación de solicitudes en formato YYYY-MM-DD. "
                                "Si no se puede determinar con seguridad, dejar como \"\"."
                            )
                        },

                        "REQUISITOS": {
                            "type": "string",
                            "description": (
                                "Resumen breve (1–3 líneas) de los requisitos específicos más relevantes "
                                "para participar (titulación, experiencia específica, otros requisitos clave)."
                            )
                        },

                        "CREDITOS": {
                            "type": "string",
                            "description": (
                                "Si la oposición incluye baremo de formación/méritos, resume cómo se puntúa "
                                "la FORMACIÓN. Si es solo examen sin méritos, usar 'NONE'."
                            )
                        },

                        "TITULO_PROPIO": {
                            "type": "string",
                            "description": (
                                "'SI' si se indica que los títulos propios universitarios puntúan como mérito; "
                                "'NO' si se indica que no puntúan o quedan excluidos; "
                                "'NONE' si el texto no menciona nada sobre títulos propios."
                            ),
                            "enum": ["SI", "NO", "NONE"]
                        },

                        "LINK_REQUISITOS": {
                            "type": "string",
                            "description": (
                                "URL principal de la fuente donde se han leído las bases, requisitos, plazos "
                                "y sistema de selección de la oposición."
                            )
                        },

                        "LINK_APLICACION": {
                            "type": "string",
                            "description": (
                                "URL del trámite de solicitud / inscripción / sede electrónica. "
                                "Si no se distingue claramente de LINK_REQUISITOS, se puede repetir la misma."
                            )
                        },

                        "PERFIL": {
                            "type": "string",
                            "description": (
                                "Perfil profesional según el texto: debe ser exactamente 'enfermeria' "
                                "o 'tcae', agrupando todas las especialidades de enfermería bajo 'enfermeria' "
                                "y todas las denominaciones de TCAE/auxiliar bajo 'tcae'."
                            ),
                            "enum": ["enfermeria", "tcae"]
                        },

                        "TITULACION_REQUERIDA": {
                            "type": "string",
                            "description": (
                                "Titulación mínima requerida para participar en la convocatoria "
                                "(grado/diplomatura en enfermería, TCAE, FP, etc.)."
                            )
                        },

                        "TIPO_PROCESO": {
                            "type": "string",
                            "description": (
                                "Tipo de proceso selectivo. En esta herramienta debe ser SIEMPRE 'OPOSICION'."
                            ),
                            "enum": ["BOLSA", "OPOSICION", "CONCURSO-OPOSICION", "CONCURSO", "OTRO"]
                        }
                    },
                    "required": [
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
                        "TIPO_PROCESO"
                    ]
                }
            }
        },
        "required": ["convocatorias"]
    }
}

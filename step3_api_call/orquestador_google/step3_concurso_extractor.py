# step3_concurso_extractor.py

from prompts_common import MULTILINGUAL_BLOCK, AMBITO_TERRITORIAL_RESUMIDO_OPCIONES

extraer_convocatorias_concurso = {
    "name": "extraer_convocatorias_concurso",
    "description": (
        "<role>\n"
        "Eres un extractor experto de convocatorias de EMPLEO PÚBLICO SANITARIO.\n"
        "El texto de entrada YA ha sido filtrado como empleo público sanitario y\n"
        "clasificado como proceso de tipo CONCURSO (solo méritos).\n"
        "</role>\n\n"
        f"{MULTILINGUAL_BLOCK}"

        "<scope>\n"
        "A partir del texto (HTML o PDF ya limpiado), debes construir filas equivalentes\n"
        "a un CSV con la información de convocatorias de CONCURSO para ENFERMERÍA y/o TCAE.\n"
        "</scope>\n\n"

        "<perfil_y_limites>\n"
        "- Solo debes extraer convocatorias de los perfiles:\n"
        "    · PERFIL = 'enfermeria'\n"
        "    · PERFIL = 'tcae'\n"
        "- Ignora otras categorías sanitarias (médicos, fisios, etc.) y todas las no sanitarias.\n"
        "- Máximo por documento:\n"
        "    · 1 convocatoria con PERFIL='enfermeria'.\n"
        "    · 1 convocatoria con PERFIL='tcae'.\n"
        "- Por tanto, el array 'convocatorias' solo puede tener 0, 1 o 2 elementos.\n"
        "- Si el documento incluye muchas categorías (ANEXO/tabla como en el ejemplo de Defensa),\n"
        "  agrupa toda la información de ENFERMERÍA en UNA única fila y toda la de TCAE en OTRA.\n"
        "</perfil_y_limites>\n\n"

        "<tipo_proceso>\n"
        "- Esta tool es EXCLUSIVA para procesos de tipo CONCURSO.\n"
        "- El campo TIPO_PROCESO debe ser SIEMPRE 'CONCURSO' en todas las convocatorias.\n"
        "- Rasgos típicos de CONCURSO (solo méritos, sin examen eliminatorio):\n"
        "    · Fórmulas del tipo: «el proceso selectivo constará de una única fase de concurso».\n"
        "    · Se habla de BAREMO DE MÉRITOS con puntuación máxima total (ej. 100 puntos).\n"
        "    · Desglose en bloques de méritos: experiencia profesional, formación, investigación,\n"
        "      publicaciones, idiomas, etc.\n"
        "    · Se valoran servicios prestados (puntos/mes), créditos/horas de formación, doctorado,\n"
        "      máster, etc., pero NO hay ejercicio de oposición (test, desarrollo) como fase obligatoria.\n"
        "    · Suelen ser procesos de estabilización (Ley 20/2021) o nombramientos temporales por méritos.\n"
        "</tipo_proceso>\n\n"

        "<fechas>\n"
        "- FECHA_APERTURA y FECHA_CIERRE en formato YYYY-MM-DD si el texto lo permite.\n"
        "- Usa siempre las fechas del PLAZO DE SOLICITUDES (no fechas internas del baremo).\n"
        "- Si no puedes inferir una fecha con seguridad, deja el campo como cadena vacía \"\".\n"
        "</fechas>\n\n"

        "<campos_especiales>\n"
        "- CREDITOS:\n"
        "    · Resume cómo se puntúa la FORMACIÓN en el baremo de méritos: número máximo de puntos,\n"
        "      equivalencia horas/créditos, tipos de cursos que cuentan (acreditados, oficiales),\n"
        "      doctorado/máster, etc.\n"
        "    · Si el texto no detalla la FORMACIÓN como mérito, usa 'NONE'.\n"
        "- TITULO_PROPIO:\n"
        "    · 'SI' si se indica que títulos propios universitarios puntúan como mérito.\n"
        "    · 'NO' si se indica que no puntúan o quedan excluidos.\n"
        "    · 'NONE' si el texto no menciona nada sobre títulos propios.\n"
        "- LINK_REQUISITOS: URL de las bases completas (requisitos, sistema de concurso, baremo).\n"
        "- LINK_APLICACION: URL de inscripción / sede electrónica. Si no se distingue claramente,\n"
        "  se puede repetir la misma que LINK_REQUISITOS.\n"
        "</campos_especiales>\n\n"

        "<principios>\n"
        "- No inventes datos: si un campo no aparece o es dudoso, deja cadena vacía o 'NONE'.\n"
        "- Cada objeto de 'convocatorias' representa un perfil concreto (ENFERMERÍA o TCAE).\n"
        "- Si tras revisar el texto no encuentras ENFERMERÍA ni TCAE en un proceso claro de concurso,\n"
        "  devuelve convocatorias=[].\n"
        "</principios>\n\n"

        "<output_instructions>\n"
        "Debes responder SIEMPRE con una única llamada a:\n"
        "  extraer_convocatorias_concurso({\"convocatorias\": [...]})\n"
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
                                "para participar (titulación, experiencia específica, requisitos adicionales, etc.)."
                            )
                        },

                        "CREDITOS": {
                            "type": "string",
                            "description": (
                                "Resumen de cómo se puntúa la FORMACIÓN en el baremo de méritos de la fase "
                                "de CONCURSO (créditos/horas, límites de puntos, tipo de cursos, máster, "
                                "doctorado, etc.). Si el texto no lo detalla, usar 'NONE'."
                            )
                        },

                        "TITULO_PROPIO": {
                            "type": "string",
                            "description": (
                                "'SI' si se indica explícitamente que los títulos propios universitarios\n"
                                "puntúan como mérito; 'NO' si se indica que no puntúan o quedan excluidos;\n"
                                "'NONE' si el texto no menciona nada sobre títulos propios."
                            ),
                            "enum": ["SI", "NO", "NONE"]
                        },

                        "LINK_REQUISITOS": {
                            "type": "string",
                            "description": (
                                "URL principal de la fuente donde se han leído las bases, requisitos, plazos "
                                "y sistema de selección (concurso de méritos)."
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
                                "Perfil profesional según el texto: 'enfermeria' o 'tcae' exclusivamente.\n"
                                "Todas las especialidades de enfermería se agrupan en 'enfermeria';\n"
                                "todas las denominaciones TCAE/Auxiliar se agrupan en 'tcae'."
                            ),
                            "enum": ["enfermeria", "tcae"]
                        },

                        "TITULACION_REQUERIDA": {
                            "type": "string",
                            "description": (
                                "Titulación mínima requerida para participar en la convocatoria "
                                "(por ejemplo: 'Grado/Diplomatura en Enfermería', "
                                "'Técnico en Cuidados Auxiliares de Enfermería', etc.)."
                            )
                        },

                        "TIPO_PROCESO": {
                            "type": "string",
                            "description": (
                                "Tipo de proceso selectivo. En esta tool debe ser siempre 'CONCURSO'."
                            ),
                            "enum": ["CONCURSO"]
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

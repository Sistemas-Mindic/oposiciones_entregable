# step3_concurso_oposicion_extractor.py

from prompts_common import MULTILINGUAL_BLOCK, AMBITO_TERRITORIAL_RESUMIDO_OPCIONES

extraer_convocatorias_concurso_oposicion = {
    "name": "extraer_convocatorias_concurso_oposicion",
    "description": (
        "<role>\n"
        "Eres un extractor experto de convocatorias de EMPLEO PÚBLICO SANITARIO.\n"
        "El texto de entrada YA ha sido filtrado como empleo público sanitario y\n"
        "clasificado como proceso de tipo CONCURSO-OPOSICIÓN.\n"
        "</role>\n\n"
        f"{MULTILINGUAL_BLOCK}"

        "<scope>\n"
        "A partir del texto (HTML o PDF ya limpiado), debes construir filas equivalentes\n"
        "a un CSV con la información de convocatorias de CONCURSO-OPOSICIÓN para\n"
        "ENFERMERÍA y/o TCAE.\n"
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
        "- Si el documento listara muchas categorías, agrupa toda la información de\n"
        "  ENFERMERÍA en UNA sola fila y toda la de TCAE en OTRA sola fila.\n"
        "</perfil_y_limites>\n\n"

        "<tipo_proceso>\n"
        "- Esta tool es EXCLUSIVA para procesos de tipo CONCURSO-OPOSICIÓN.\n"
        "- El campo TIPO_PROCESO debe ser SIEMPRE 'CONCURSO-OPOSICION' en todas las\n"
        "  convocatorias que devuelvas.\n"
        "- Rasgos típicos de concurso-oposición (usa el conjunto, no una sola palabra):\n"
        "    · Se habla de PRUEBA o FASE DE OPOSICIÓN (test, desarrollo, práctico).\n"
        "    · Se habla de FASE DE CONCURSO o BAREMO DE MÉRITOS.\n"
        "    · Se menciona «puntuación final (fases de oposición y concurso)» o similar.\n"
        "    · Suele haber listas de aprobados de oposición, luego listas de méritos,\n"
        "      y finalmente listas definitivas de aprobados.\n"
        "- Muchos procesos son de PROMOCIÓN INTERNA: exige ser funcionario de carrera,\n"
        "  pertenecer a un cuerpo/escala de origen y tener cierta antigüedad.\n"
        "</tipo_proceso>\n\n"

        "<fechas>\n"
        "- FECHA_APERTURA y FECHA_CIERRE en formato YYYY-MM-DD si el texto lo permite.\n"
        "- Usa siempre las fechas del PLAZO DE SOLICITUDES (no fechas de examen).\n"
        "- Si no puedes inferir una fecha con seguridad, deja el campo como cadena vacía \"\".\n"
        "</fechas>\n\n"

        "<campos_especiales>\n"
        "- CREDITOS:\n"
        "    · Resume cómo se puntúa la FORMACIÓN en el baremo de méritos: créditos,\n"
        "      horas, puntos máximos por formación, máster, doctorado, cursos, etc.\n"
        "    · Si el texto no detalla la formación como mérito, usa 'NONE'.\n"
        "- TITULO_PROPIO:\n"
        "    · 'SI' si se indica que títulos propios universitarios puntúan como mérito.\n"
        "    · 'NO' si se indica que no puntúan o se excluyen.\n"
        "    · 'NONE' si el texto no menciona nada al respecto.\n"
        "- LINK_REQUISITOS: URL de las bases completas (requisitos, plazos, sistema de\n"
        "  selección, baremo de méritos, etc.).\n"
        "- LINK_APLICACION: URL de inscripción / sede electrónica / formulario. Si no se\n"
        "  distingue claramente, puedes repetir la misma que LINK_REQUISITOS.\n"
        "</campos_especiales>\n\n"

        "<principios>\n"
        "- No inventes datos: si un campo no aparece o es dudoso, deja cadena vacía o 'NONE'.\n"
        "- Cada objeto de 'convocatorias' representa un perfil concreto (ENFERMERÍA o TCAE).\n"
        "- Si tras revisar el texto no encuentras ENFERMERÍA ni TCAE en un proceso claro\n"
        "  de concurso-oposición, devuelve convocatorias=[].\n"
        "</principios>\n\n"

        "<output_instructions>\n"
        "Debes responder SIEMPRE con una única llamada a:\n"
        "  extraer_convocatorias_concurso_oposicion({\"convocatorias\": [...]})\n"
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
                                "para participar (titulación, experiencia específica, requisitos de "
                                "promoción interna, etc.)."
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
                                "y sistema de selección (oposición + concurso)."
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
                                "Tipo de proceso selectivo. En esta tool debe ser siempre 'CONCURSO-OPOSICION'."
                            ),
                            "enum": ["CONCURSO-OPOSICION"]
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

# step3_otro_extractor.py

from prompts_common import MULTILINGUAL_BLOCK, AMBITO_TERRITORIAL_RESUMIDO_OPCIONES

extraer_convocatorias_otro = {
    "name": "extraer_convocatorias_otro",
    "description": (
        "<role>\n"
        "Eres un extractor experto de convocatorias de EMPLEO PÚBLICO SANITARIO "
        "para perfiles de ENFERMERÍA y TCAE.\n"
        "</role>\n\n"
        f"{MULTILINGUAL_BLOCK}"

        "<objective>\n"
        "A partir de un texto completo, decidir si existe una CONVOCATORIA REAL "
        "para ENFERMERÍA o TCAE y, en su caso, extraer como máximo una fila por "
        "perfil (enfermería / tcae).\n"
        "Cuando el documento sea solo un modelo/formulario o pieza auxiliar sin "
        "bases ni descripción del proceso, NO debes extraer nada (convocatorias=[]).\n"
        "</objective>\n\n"

        "<when_to_extract>\n"
        "SÍ debes extraer (convocatorias != []), solo cuando el documento:\n"
        "- Incluye fórmulas de convocatoria claras, por ejemplo:\n"
        "    · «Se convoca proceso selectivo…»\n"
        "    · «Bases de la convocatoria…»\n"
        "    · «Convocatoria para la provisión de plazas…»\n"
        "    · «Proceso selectivo para la cobertura de…»\n"
        "- Describe que se van a cubrir puestos de ENFERMERÍA o TCAE.\n"
        "- Permite identificar al menos: órgano convocante, ámbito geográfico, "
        "  categoría (enfermería/TCAE) y algún dato de plazo (o indicios razonables "
        "  de vigencia del proceso).\n"
        "\n"
        "NO debes extraer (convocatorias = []), cuando el documento es, por ejemplo:\n"
        "- UN MODELO / FORMULARIO DE SOLICITUD, como:\n"
        "    · «SOLICITUD PARTICIPACIÓN SELECCIÓN COBERTURA DE PUESTO…»\n"
        "    · «Modelo de solicitud…»\n"
        "    · Documentos donde predominan campos a rellenar: nombre, NIF, domicilio,\n"
        "      firma, fecha, nº de puesto, características del puesto, etc.\n"
        "- Un autobaremo suelto sin texto de convocatoria (solo tablas de méritos).\n"
        "- Un buscador de empleo o listado genérico de muchas referencias "
        "  (muchas líneas tipo «Organismo:… Proceso selectivo:… Plazas:…» sin bases "
        "  completas de una convocatoria concreta).\n"
        "- Una nota informativa, recordatorio, FAQ o anuncio interno sin descripción "
        "  clara de plazas, requisitos y plazo.\n"
        "En TODOS estos casos, el objeto 'convocatorias' debe ser exactamente [].\n"
        "</when_to_extract>\n\n"

        "<perfil_y_limites>\n"
        "- Solo debes extraer convocatorias de los perfiles:\n"
        "    · PERFIL = 'enfermeria'\n"
        "    · PERFIL = 'tcae'\n"
        "- Ignora otras categorías sanitarias (médicos, fisios, etc.) y las no sanitarias.\n"
        "- Máximo por documento:\n"
        "    · 1 convocatoria con PERFIL='enfermeria'.\n"
        "    · 1 convocatoria con PERFIL='tcae'.\n"
        "- Por tanto, el array 'convocatorias' solo puede tener 0, 1 o 2 elementos.\n"
        "</perfil_y_limites>\n\n"

        "<tipo_proceso_campo>\n"
        "- El campo TIPO_PROCESO no sirve para clasificar el texto, solo es una etiqueta "
        "de salida.\n"
        "- En esta herramienta TIPO_PROCESO debe ser SIEMPRE 'OTRO' en todas las "
        "convocatorias extraídas.\n"
        "</tipo_proceso_campo>\n\n"

        "<fechas>\n"
        "- FECHA_APERTURA y FECHA_CIERRE en formato YYYY-MM-DD si el texto lo permite.\n"
        "- Usa siempre las fechas del PLAZO DE SOLICITUDES.\n"
        "- Si no puedes inferir una fecha con seguridad, deja el campo como \"\".\n"
        "</fechas>\n\n"

        "<campos_especiales>\n"
        "- CREDITOS: resumen de cómo se valora la FORMACIÓN si se menciona baremo; "
        "  si no, usar 'NONE'.\n"
        "- TITULO_PROPIO:\n"
        "    · 'SI' si los títulos propios universitarios puntúan.\n"
        "    · 'NO' si se excluyen o no puntúan.\n"
        "    · 'NONE' si no se menciona nada.\n"
        "- LINK_REQUISITOS: URL donde están las bases/requisitos (si existe).\n"
        "- LINK_APLICACION: URL del trámite de solicitud; si no se distingue, se puede "
        "  repetir la misma que LINK_REQUISITOS.\n"
        "</campos_especiales>\n\n"

        "<principios>\n"
        "- No inventes datos: si un campo no aparece o es dudoso, deja cadena vacía o 'NONE'.\n"
        "- Sé muy conservador: si dudas entre extraer una convocatoria o no, NO la extraigas "
        "(devuelve convocatorias=[]).\n"
        "</principios>\n\n"

        "<output_instructions>\n"
        "Debes responder SIEMPRE con una única llamada a:\n"
        "  extraer_convocatorias_otro({\"convocatorias\": [...]})\n"
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
                                "Resumen de cómo se puntúa la FORMACIÓN si se menciona algún baremo de méritos. "
                                "Si el documento no entra en detalle sobre formación como mérito, usar 'NONE'."
                            )
                        },

                        "TITULO_PROPIO": {
                            "type": "string",
                            "description": (
                                "'SI' si se indica explícitamente que los títulos propios universitarios "
                                "puntúan como mérito; 'NO' si se indica que no puntúan o quedan excluidos; "
                                "'NONE' si el texto no menciona nada sobre títulos propios."
                            ),
                            "enum": ["SI", "NO", "NONE"]
                        },

                        "LINK_REQUISITOS": {
                            "type": "string",
                            "description": (
                                "URL principal de la fuente donde se han leído requisitos, plazos y sistema "
                                "de selección, si se indica alguna."
                            )
                        },

                        "LINK_APLICACION": {
                            "type": "string",
                            "description": (
                                "URL del trámite de solicitud / inscripción / sede electrónica, si existe. "
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
                                "Tipo de proceso selectivo. En esta herramienta debe ser siempre 'OTRO'."
                            ),
                            "enum": ["OTRO"]
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

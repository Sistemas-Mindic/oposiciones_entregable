# step1_analizar_doc.py

analizar_documento_sanitario = {
    "name": "analizar_documento_sanitario",
    "description": (
        "<role>\n"
        "Eres un analizador previo de textos de empleo público en España.\n"
        "Tu única misión es decidir si el documento describe EMPLEO PÚBLICO\n"
        "SANITARIO relevante para ENFERMERÍA o TCAE / Auxiliar de enfermería.\n"
        "Eres prudente: prefieres dejar pasar algo dudoso a la siguiente fase\n"
        "antes que descartar una convocatoria sanitaria válida.\n"
        "</role>\n\n"

        "<output>\n"
        "Debes devolver SIEMPRE una única llamada a la función\n"
        "  analizar_documento_sanitario({ ... })\n"
        "con estos campos JSON:\n"
        "  - tiene_perfil_sanitario (bool)\n"
        "  - es_descartable (bool)\n"
        "Opcionalmente puedes incluir un campo 'motivo' (string) para logging.\n"
        "</output>\n\n"

        "<semantica_campos>\n"
        "- tiene_perfil_sanitario = true cuando el documento contiene al menos\n"
        "  UNA convocatoria o bolsa de EMPLEO PÚBLICO cuyo perfil sea claramente\n"
        "  ENFERMERÍA o TCAE/Auxiliar de enfermería.\n"
        "- es_descartable = true SOLO cuando el documento se puede ignorar por\n"
        "  completo: no es empleo público o no hay perfiles sanitarios ENF/TCAE.\n"
        "- Si tiene_perfil_sanitario = true, entonces es_descartable = false.\n"
        "</semantica_campos>\n\n"

        "<que_es_empleo_publico>\n"
        "Considera empleo público:\n"
        "- Oposiciones, concursos, concursos-oposición.\n"
        "- Bolsas de empleo, bolsas de trabajo, listas de contratación temporal.\n"
        "- Convocatorias para personal estatutario, funcionario, laboral o interino.\n"
        "</que_es_empleo_publico>\n\n"

        "<perfiles_sanitarios_validos>\n"
        "Perfila como ENFERMERÍA (enfermeria):\n"
        "- 'enfermero', 'enfermera', 'enfermería'.\n"
        "- 'grado en enfermería', 'diplomado en enfermería', 'due', 'ats', 'ats/de'.\n"
        "- 'ayudante técnico sanitario'.\n"
        "- Especialistas RD 450/2005: matrona, salud mental, pediátrica,\n"
        "  geriátrica, familiar y comunitaria, enfermería del trabajo, etc.\n"
        "\n"
        "Perfila como TCAE/Auxiliar (tcae):\n"
        "- 'técnico en cuidados auxiliares de enfermería', 'tcae'.\n"
        "- 'auxiliar de enfermería', 'auxiliares de enfermería'.\n"
        "- 'técnico auxiliar de clínica', 'técnico auxiliar de psiquiatría'.\n"
        "- Perfiles sociosanitarios muy próximos cuando las titulaciones son\n"
        "  claramente de TCAE/auxiliar de enfermería.\n"
        "</perfiles_sanitarios_validos>\n\n"

        "<plazas_y_bolsas>\n"
        "Muy importante:\n"
        "- NUNCA uses los campos numéricos de plazas como criterio de descarte.\n"
        "- Cadenas del tipo:\n"
        "    'Convocadas:0 Libres:0 Internas:0 Discapacidad General:0\n"
        "     Discapacidad Intelectual:0'\n"
        "  NO significan que la convocatoria no sea relevante.\n"
        "- Muchos portales rellenan estos campos con 0 en bolsas de empleo.\n"
        "- Por tanto, DEBES IGNORAR estos valores (0, 1, 100...) para decidir\n"
        "  tiene_perfil_sanitario o es_descartable.\n"
        "- Si el texto indica que es 'bolsa de empleo', 'bolsa abierta y\n"
        "  permanente', 'lista de contratación' o similar, y el perfil es\n"
        "  ENFERMERÍA/TCAE, marca tiene_perfil_sanitario = true aunque todas\n"
        "  las plazas numéricas valgan 0.\n"
        "</plazas_y_bolsas>\n\n"

        "<plazos>\n"
        "Este analizador NO aplica reglas finas de plazos abiertos/cerrados.\n"
        "Tu foco es SÓLO decidir si el documento es empleo público sanitario\n"
        "ENFERMERÍA/TCAE. Aunque el plazo parezca cerrado, si el texto describe\n"
        "claramente una convocatoria o bolsa sanitaria, marca\n"
        "tiene_perfil_sanitario = true y deja que la siguiente tool se encargue\n"
        "de filtrar por plazos.\n"
        "</plazos>\n\n"

        "<cuandos_marcar_verdadero>\n"
        "Marca tiene_perfil_sanitario = true, es_descartable = false cuando:\n"
        "- Se trate de OPOSICIÓN / CONCURSO / CONCURSO-OPOSICIÓN de ENFERMERÍA\n"
        "  o TCAE.\n"
        "- O se trate de BOLSA DE EMPLEO, bolsa de trabajo, lista de contratación,\n"
        "  convocatoria abierta y permanente, bolsa permanente, etc., de\n"
        "  ENFERMERÍA o TCAE, aunque las plazas numéricas aparezcan como 0.\n"
        "</cuandos_marcar_verdadero>\n\n"

        "<cuandos_descartar>\n"
        "Marca tiene_perfil_sanitario = false, es_descartable = true cuando:\n"
        "- El cuerpo/categoría/titulación es claramente NO sanitario\n"
        "  (administrativos, policía, bomberos, cuerpos generales, docentes no\n"
        "  sanitarios, etc.).\n"
        "- O el documento es puramente de seguimiento (listas de admitidos,\n"
        "  excluidos, méritos, resultados) sin nueva ventana de inscripción y\n"
        "  sin describir la convocatoria sanitaria original.\n"
        "- O no hay ninguna referencia a ENFERMERÍA o TCAE/Auxiliar.\n"
        "</cuandos_descartar>\n\n"

        "<formato_salida>\n"
        "Devuelve SIEMPRE una única llamada con este formato exacto:\n"
        "  analizar_documento_sanitario({\n"
        "    \"tiene_perfil_sanitario\": true/false,\n"
        "    \"es_descartable\": true/false,\n"
        "    \"motivo\": \"explicación breve\" (opcional)\n"
        "  })\n"
        "No añadas texto antes ni después.\n"
        "</formato_salida>\n"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "tiene_perfil_sanitario": {
                "type": "boolean",
                "description": (
                    "True si el documento describe empleo público sanitario "
                    "(convocatoria, bolsa, lista de contratación, etc.) donde al "
                    "menos un perfil es ENFERMERÍA o TCAE/Auxiliar de enfermería. "
                    "False en caso contrario."
                )
            },
            "es_descartable": {
                "type": "boolean",
                "description": (
                    "True solo si el documento puede ignorarse por completo en el "
                    "pipeline (no es empleo público, o no hay perfiles de "
                    "ENFERMERÍA/TCAE, o es solo seguimiento sin nueva inscripción). "
                    "False si debe pasar a extracción detallada."
                )
            },
            "motivo": {
                "type": "string",
                "description": (
                    "Explicación breve de la decisión, útil para logs internos. "
                    "No se usa en la lógica del pipeline."
                )
            }
        },
        "required": ["tiene_perfil_sanitario", "es_descartable"]
    }
}

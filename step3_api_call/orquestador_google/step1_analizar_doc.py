# step1_analizar_doc.py
from prompts_common import MULTILINGUAL_BLOCK

analizar_documento_sanitario = {
    "name": "analizar_documento_sanitario",
    "description": (
        "<role>\n"
        "Eres un analista experto en triaje de documentación oficial sanitaria.\n"
        "</role>\n\n"
        f"{MULTILINGUAL_BLOCK}"

        "<objective>\n"
        "Tu única misión es determinar si el texto corresponde a una CONVOCATORIA ACTIVA "
        "de empleo público para ENFERMERÍA o TCAE.\n"
        "</objective>\n\n"

        "<classification_logic>\n"
        "Para rellenar los parámetros, sigue estrictamente este flujo de decisión:\n"
        "1. Analiza si es 'Empleo Público' (Bolsas, Oposiciones, Concursos, Contratación temporal).\n"
        "2. Analiza si es 'Perfil Sanitario' (Enfermería/TCAE).\n"
        "3. Determina 'es_descartable'.\n"
        "\n"
        "ATENCIÓN:\n"
        "- La regla MÁS IMPORTANTE es identificar documentos de TRÁMITE.\n"
        "- Un documento puede tener (es_empleo_publico=True) y (tiene_perfil_sanitario=True)\n"
        "  pero aun así ser descartable si NO es la convocatoria base.\n"
        "- Ejemplos descartables: listas de admitidos/excluidos, baremos, notas, resultados,\n"
        "  nombramientos, relaciones provisionales/definitivas.\n"
        "</classification_logic>\n\n"

        "<instructions>\n"
        "- Sé conservador: ante la duda de si es una convocatoria real, es_descartable=false.\n"
        "- Ignora completamente los valores numéricos de plazas (0/1/100...).\n"
        "- No evalúes si el plazo está abierto o cerrado.\n"
        "</instructions>"
    ),

    "parameters": {
        "type": "object",
        "properties": {

            "es_empleo_publico": {
                "type": "boolean",
                "description": (
                    "True si describe procesos selectivos: convocatoria, bases, oposición, concurso, "
                    "concurso-oposición, bolsa de empleo, lista de contratación, interinidad con inscripción, "
                    "requisitos, tribunales, temario, fases de selección.\n"
                    "False si es licitación, contrato de servicios, subvención, normativa, anuncio sin selección."
                )
            },

            "tiene_perfil_sanitario": {
                "type": "boolean",
                "description": (
                    "True si aparecen categorías de ENFERMERÍA (enfermero/a, enfermería, DUE, ATS, ATS/DE, "
                    "especialidades: matrona, salud mental, pediátrica, geriátrica, comunitaria, trabajo) "
                    "o TCAE/Auxiliar (TCAE, auxiliar de enfermería, técnico auxiliar).\n"
                    "\n"
                    "False si SOLO aparecen categorías NO válidas: médico, celador, fisioterapeuta, técnico de laboratorio, "
                    "terapeuta ocupacional, trabajador social.\n"
                    "\n"
                    "IMPORTANTE: No considerar 'administrativo' como exclusión automática.\n"
                    "Un ENFERMERO puede desempeñar funciones administrativas y sigue siendo perfil sanitario.\n"
                    "Solo se excluyen CUERPOS ADMINISTRATIVOS GENERALISTAS (Aux. Administrativo, Administrativo, Gestión, "
                    "Cuerpos Generales) cuando NO aparezca titulación sanitaria."
                )
            },

            "es_descartable": {
                "type": "boolean",
                "description": (
                    "CRÍTICO: True si el documento debe descartarse.\n"
                    "Criterios de descarte:\n"
                    "1. No es empleo público.\n"
                    "2. No contiene perfiles de Enfermería/TCAE.\n"
                    "3. Es un TRÁMITE de seguimiento sin nueva inscripción:\n"
                    "   - listas de admitidos/excluidos,\n"
                    "   - baremación provisional/definitiva,\n"
                    "   - calificaciones/notas,\n"
                    "   - resultados de examen,\n"
                    "   - plantilla de respuestas,\n"
                    "   - relaciones provisionales/definitivas,\n"
                    "   - nombramientos.\n"
                    "4. Es una licitación o anuncio no selectivo.\n"
                    "\n"
                    "Puede ser true incluso si tiene_perfil_sanitario=true cuando NO es la convocatoria base."
                )
            },

            "motivo": {
                "type": "string",
                "description": (
                    "Razón breve de la clasificación: 'lista de admitidos', 'no sanitario', "
                    "'licitación', 'convocatoria OK', etc."
                )
            }
        },

        "required": ["es_empleo_publico", "tiene_perfil_sanitario", "es_descartable"]
    }
}

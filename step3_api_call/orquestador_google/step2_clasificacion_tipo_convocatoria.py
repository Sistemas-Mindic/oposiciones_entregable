# step2_classificacion_tipo_convocatoria.py
# Herramienta: clasificar_tipo_proceso_convocatoria
# -----------------------------------------------------------
# El STEP1 ya validó que:
#   - es empleo público,
#   - es sanitario (ENF/TCAE),
#   - y NO es trámite.
# Este STEP2 SOLO clasifica el tipo de proceso.

from prompts_common import MULTILINGUAL_BLOCK

clasificar_tipo_proceso_convocatoria = {
    "name": "clasificar_tipo_proceso_convocatoria",
    "description": (
        "<role>\n"
        "Eres un clasificador experto en empleo público sanitario. "
        "El texto recibido es una convocatoria válida de ENFERMERÍA o TCAE.\n"
        "</role>\n\n"
        f"{MULTILINGUAL_BLOCK}"

        "<objective>\n"
        "Determinar el MECANISMO DE SELECCIÓN exacto de la convocatoria.\n"
        "</objective>\n\n"

        "<hierarchy>\n"
        "Prioridad estricta para resolver ambigüedades:\n"
        "1) Si implica CONTRATACIÓN TEMPORAL o LISTA DE ESPERA → 'bolsa'.\n"
        "2) Si hay EXAMEN + MÉRITOS → 'concurso-oposicion'.\n"
        "3) Si hay SOLO EXAMEN → 'oposicion'.\n"
        "4) Si hay SOLO MÉRITOS → 'concurso'.\n"
        "5) Si no puede deducirse → 'otro'.\n"
        "</hierarchy>\n"
    ),

    "parameters": {
        "type": "object",
        "properties": {

            "tipo_proceso": {
                "type": "string",
                "description": (
                    "Seleccionar según estos indicadores:\n\n"
                    "• 'bolsa': contratación temporal, lista de espera/reserva, "
                    "«bolsa de empleo», «bolsa abierta y permanente», «selección temporal», "
                    "«interinidad», «actualización de méritos», «autobaremo de bolsa».\n\n"
                    "• 'oposicion': plazas fijas; existe examen; aparecen «oposición», "
                    "«ejercicio/test», «plantilla de respuestas», «lista aprobados fase oposición».\n\n"
                    "• 'concurso-oposicion': plazas fijas; examen + méritos; aparecen "
                    "«concurso-oposición», «fase oposición» + «fase concurso», "
                    "«autobaremo de méritos tras examen».\n\n"
                    "• 'concurso': selección solo por méritos (p. ej. estabilización Ley 20/2021); "
                    "«sistema de concurso», «única fase concurso», SIN examen eliminatorio.\n\n"
                    "• 'otro': documentos sin información suficiente o anexos que no especifican sistema."
                ),
                "enum": [
                    "bolsa",
                    "oposicion",
                    "concurso",
                    "concurso-oposicion",
                    "otro"
                ]
            },

            "confianza": {
                "type": "string",
                "description": (
                    "'alta' → indicadores claros.\n"
                    "'media' → señales parciales o mezcladas.\n"
                    "'baja' → texto ambiguo o incompleto."
                ),
                "enum": ["alta", "media", "baja"]
            }
        },

        "required": ["tipo_proceso", "confianza"]
    }
}

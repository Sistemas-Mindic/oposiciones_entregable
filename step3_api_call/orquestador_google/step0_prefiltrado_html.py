# step21_refinar_html.py
from prompts_common import MULTILINGUAL_BLOCK

refinar_contenido_principal = {
    "name": "refinar_contenido_principal",
    "description": (
        "<role>\n"
        "Eres un editor experto en limpieza de textos de convocatorias públicas. "
        "Recibes un documento HTML ya preprocesado y debes aislar SOLO la "
        "CONVOCATORIA PRINCIPAL.\n"
        "</role>\n\n"
        f"{MULTILINGUAL_BLOCK}"

        "<objective>\n"
        "Eliminar cualquier bloque de 'otras convocatorias', listados, fichas breves, "
        "o resultados de buscadores que hayan quedado al final del texto. "
        "Nunca inventes contenido: solo recorta.\n"
        "</objective>\n\n"

        "<detection_logic>\n"
        "1. Si existe un BLOQUE NARRATIVO inicial (bases, requisitos, descripción, "
        "plazo, órgano convocante), ese es el contenido principal.\n"
        "2. Todo lo que venga DESPUÉS de un cambio brusco de formato se elimina: "
        "· listas con 'Ref:', 'Plazas:', 'Titulación:', 'Ubicación:', "
        "· encabezados como 'Quizá también te interesen otras convocatorias', "
        "· listados de múltiples categorías no sanitarias o no relacionadas.\n"
        "3. Si el texto está compuesto SOLO por listados repetitivos y NO existe "
        "bloque narrativo, devuelve texto vacío (no hay convocatoria principal).\n"
        "</detection_logic>\n\n"

        "<action>\n"
        "Devuelve SIEMPRE:\n"
        "· el título detectado de la convocatoria principal (si existe),\n"
        "· el texto limpio SOLO del bloque principal,\n"
        "· si se hizo corte,\n"
        "· un breve fragmento de lo eliminado.\n"
        "Si no existe contenido narrativo válido → devuelve todo vacío.\n"
        "</action>\n"
    ),

    "parameters": {
        "type": "object",
        "properties": {

            "titulo_detectado": {
                "type": "string",
                "description": (
                    "El título principal de la oferta si existe. "
                    "Si no hay bloque narrativo o solo hay listados, dejar vacío."
                )
            },

            "texto_final_limpio": {
                "type": "string",
                "description": (
                    "El texto íntegro SOLO de la convocatoria principal. "
                    "Sin listados, sin resultados de buscador, sin otras referencias."
                )
            },

            "se_realizo_corte": {
                "type": "boolean",
                "description": (
                    "True si se detectó y eliminó contenido secundario. "
                    "False si el texto ya estaba limpio o si no existía narrativa."
                )
            },

            "fragmento_eliminado": {
                "type": "string",
                "description": (
                    "Breve muestra (10–15 palabras) del bloque eliminado. "
                    "Vacío si no se eliminó nada o si no existía narrativa principal."
                )
            }
        },

        "required": ["titulo_detectado", "texto_final_limpio", "se_realizo_corte"]
    }
}

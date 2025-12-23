#
## pip install google-genai

## pip install google-genai

from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv("API_GOOGLE.env")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Define the function declaration for the model
buscar_oposiciones = {
    "name": "buscar_oposiciones",
    "description": "Clasifica si un texto es una convocatoria de empleo público y extrae campos clave.",
    "parameters": {
        "type": "object",
        "properties": {
            "es_convocatoria": {
                "type": "boolean",
                "description": "True si el texto corresponde a una convocatoria de empleo público."
            },
            "tipo": {
                "type": "string",
                "description": "Tipo de proceso identificado.",
                "enum": ["proceso_selectivo", "oposicion", "concurso", "concurso_oposicion", "bolsa", "interino", "estatutario", "otro"]
            },
            "organismo": {
                "type": "string",
                "description": "Órgano/administración convocante (p. ej., Conselleria de Sanidad, Ayuntamiento...)."
            },
            "ambito": {
                "type": "string",
                "description": "Ámbito administrativo de la convocatoria.",
                "enum": ["estatal", "autonomico", "local", "universidad", "otro", "no_determinado"]
            },
            "plazas": {
                "type": "integer",
                "minimum": 1,
                "description": "Número de plazas si consta."
            },
            "titulacion_requerida": {
                "type": "string",
                "description": "Titulación o nivel exigido (p. ej., Grado en Enfermería, ESO...)."
            },
            "requisitos_experiencia": {
                "type": "string",
                "description": "Experiencia mínima u otros requisitos destacados."
            },
            "jornada": {
                "type": "string",
                "description": "Tipo de jornada si aparece.",
                "enum": ["completa", "parcial", "turnos", "otro", "no_consta"]
            },
            "sistema_seleccion": {
                "type": "string",
                "description": "Sistema de selección si se explicita.",
                "enum": ["oposicion", "concurso", "concurso_oposicion", "meritos", "otro", "no_consta"]
            },
            "fecha_publicacion": {
                "type": "string",
                "description": "Fecha de publicación si consta (YYYY-MM-DD).",
                "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
            },
           
            "plazo": {
                "type": "object",
                "description": "Plazo relativo: si existe 'fecha_publicacion' (top-level), úsala como ancla; solo informa 'fecha_referencia_iso' cuando NO exista 'fecha_publicacion'.",
                "properties": {
                    "texto": {
                        "type": "string",
                        "description": "Literal del plazo (p. ej., '5 días hábiles desde la publicación')."
                    },
                    "regla": {
                        "type": "string",
                        "description": "Resumen estructurado (p. ej., '5 dias habiles desde publicacion')."
                    },
                    "evento_referencia": {
                        "type": "string",
                        "description": "Evento que inicia el cómputo.",
                        "enum": ["publicacion","publicacion_web_conselleria","BOE","DOGV","BOP","resolucion","tablon","diligencia","otro"]
                    },
                    "fecha_referencia_iso": {
                        "type": "string",
                        "description": "Fecha ancla (YYYY-MM-DD). Rellenar solo si NO hay 'fecha_publicacion'.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    },
                    "dias": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Número de días del plazo (p. ej., 5)."
                    },
                    "tipo_dias": {
                        "type": "string",
                        "description": "Tipo de días.",
                        "enum": ["habiles","naturales"]
                    },
                    "computo": {
                        "type": "string",
                        "description": "Desde el mismo día o el día siguiente.",
                        "enum": ["desde_mismo_dia","desde_dia_siguiente"]
                    },
                    "calendario": {
                        "type": "string",
                        "description": "Calendario aplicable a días hábiles.",
                        "enum": ["estatal","autonomico","local","no_especificado"]
                    },
                    "inicio_calculado": {
                        "type": "string",
                        "description": "Fecha de inicio calculada (YYYY-MM-DD), si procede.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    },
                    "fin_calculado": {
                        "type": "string",
                        "description": "Fecha de fin calculada (YYYY-MM-DD), si procede.",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
                    },
                    "fuente_fecha": {
                        "type": "string",
                        "description": "Fragmento donde aparece la fecha ancla (p. ej., DILIGENCIA)."
                    }
                },
                "required": ["texto","regla","evento_referencia","dias","tipo_dias","computo"]
            },
            "referencia_oficial": {
                "type": "string",
                "description": "Referencia a BOE/DOGV/BOP… si aparece."
            },
            "urls": {
                "type": "object",
                "description": "Enlaces relevantes si existen.",
                "properties": {
                    "bases": {"type": "string", "description": "URL de las bases o resolución."},
                    "solicitud": {"type": "string", "description": "URL del trámite de solicitud."}
                }
            },
            "fragmentos_clave": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Frases del texto usadas para decidir."
            }
        },
        "required": ["es_convocatoria","tipo","organismo","ambito","plazas","titulacion_requerida","requisitos_experiencia","jornada","sistema_seleccion","fecha_publicacion","plazo","referencia_oficial","urls","fragmentos_clave"], # print(f"es_convocatoria: {es_convocatoria}\n tipo: {tipo}\n organismo: {organismo}\n ambito: {ambito}\n plazas: {plazas}\n titulacion_requerida: {titulacion_requerida}\n requisitos_experiencia: {requisitos_experiencia}\n jornada: {jornada}\n sistema_seleccion: {sistema_seleccion}\n fecha_publicacion: {fecha_publicacion}\n plazo: {plazo}\n referencia_oficial: {referencia_oficial}\n urls: {urls}\n fragmentos_clave: {fragmentos_clave}")
    }
}


# Configure the client and tools
client = genai.Client()
tools = types.Tool(function_declarations=[buscar_oposiciones])
config = types.GenerateContentConfig(tools=[tools])

# Send request with function declarations
response = client.models.generate_content(
    model="gemini-2.0-flash-lite",
    contents="""
  DILIGENCIA por la que se hace constar que en 
la fecha de la firma, se publica en la página 
web de la Conselleria de Sanidad 
(www.san.gva.es) la convocatoria de 4 de 
noviembre de 2025 de cobertura temporal de 
un puesto de características específicas de 
facultativo o facultativa especialistas de 
anestesiología y reanimación, plaza nº 
27.594, en el Hospital Universitari i Politècnic 
La Fe - Conselleria de Sanidad. 
La jefa del servicio de Planificación, Selección 
y Provisión de Personal,
CONVOCATORIA DE COBERTURA TEMPORAL DE UN PUESTO DE FACULTATIVO O 
FACULTATIVA (PUESTO Nº 27594) EN ANESTESIOLOGÍA Y REANIMACIÓN EN EL 
HOSPITAL UNIVERSITARI I POLITÈCNIC LA FE- CONSELLERIA DE SANIDAD. 
1.- OBJETO: 
La presente convocatoria tiene como objeto la selección de un candidato o candidata para el 
nombramiento temporal de sustitución en el puesto nº 27594 como Facultativo o Facultativa en
Anestesiología y Reanimación en el Hospital Universitari i Politècnic La Fe-Conselleria de 
Sanidad y se regirá por las presentes bases y por lo dispuesto en el Capítulo III del Decreto 
76/2024 de 2 de julio, del Consell, de regulación del procedimiento de selección de personal 
temporal estatutario sanitario de los subgrupos de clasificación A1 y A2 dependiente de la 
Conselleria con competencias en materia de sanidad. 
La plaza que se oferta ha sido declarada de características específicas de conformidad con la 
normativa vigente, al igual que la sustitución de la persona titular que la ocupa. 
2.- CARACTERISTICAS DEL PUESTO: 
• Número de puesto: 27594
• Requisitos específicos para su desempeño 
Coordinación de trasplantes. Experiencia mínima de 1 año 
• Funciones a desarrollar: 
1. Funciones relacionadas con la donación de órganos. 
- La detección proactiva de posibles donantes. Las herramientas de detección 
recomendadas son: 
✓ Elaboración de protocolos hospitalarios de identificación y notificación de posibles 
donantes en colaboración con aquellas áreas del hospital que atiendan pacientes que 
podrían ser donantes. 
✓ Implementación de sistemas automáticos de aviso de posibles donantes. 
✓ Revisión de ingresos hospitalarios, idealmente con periodicidad diaria en áreas 
estratégicas. 
✓ Visitas a las unidades de críticos, idealmente con periodicidad diaria. 
✓ Visitas periódicas a áreas diferentes de las unidades de críticos donde puedan 
atenderse pacientes que pudieran ser donantes. 
✓ Información periódica a las unidades generadoras acerca de los resultados de las 
actividades de donación y trasplante (feed-back). 
✓ Elaboración de protocolos para detección y manejo de posibles donantes en el ámbito 
extrahospitalario (pacientes con enfermedades neurodegenerativas, pacientes que 
soliciten la Prestación de Ayuda para Morir-PAM…). 
− Realizar las entrevistas relacionadas con la donación de órganos y tejidos. 
CSV:2KD6P3SE:3723ICXY:74MNM784 URL de validació:https://www.tramita.gva.es/csv-front/index.faces?cadena=2KD6P3SE:3723ICXY:74MNM784
Departamento de Salud Valencia La Fe 
Hospital Universitari i Politècnic La Fe 
Avda. Fernando Abril Martorell, 106· 46026 Valencia 
961244000
www.hospital-lafe.com
− Entablar la relación de ayuda con las familias de los donantes durante todo el 
proceso. Se requiere una adecuada formación en habilidades de comunicación social y 
prestación de ayuda psicológica. 
− Realizar las solicitudes de autorización judicial en aquellos casos en los que se 
requiera. 
− Recabar información de la situación de ocupación de camas hospitalarias para el 
ingreso de posibles donantes para cuidados intensivos orientados a la donación. 
− Realizar la valoración del posible donante y la solicitud de pruebas. 
− Supervisar el proceso en el diagnóstico de muerte. 
− Colaborar con el equipo asistencial del paciente en el mantenimiento del donante. 
− Gestión de la logística del proceso de donación, esto incluye la comunicación 
constante con los responsables de la distribución de los órganos (ONT) y, la 
organización de los equipos para el procedimiento de la extracción (intra y 
extrahospitalario). 
− Organizar de la logística del proceso de trasplante. 
− Coordinación y comunicación directa con el Banco/Establecimiento de Tejidos para el 
empaquetado y envío del material al banco, así como adecuar la obtención con las 
necesidades de cada momento. 
− Colaboración con los equipos de trasplantes en el mantenimiento y actualización 
periódica de las listas de espera de trasplantes de córneas. 
2. Funciones relacionadas con el trasplante. 
− Colaboración con el equipo de trasplantes en el mantenimiento y actualización diaria de 
las listas de espera. 
− Participación en la organización de la logística del trasplante, en colaboración con los 
equipos de trasplante. 
− Formar parte de la Comisión de Trasplantes Intrahospitalaria de donación y deben 
participar en reuniones con los diferentes equipos de trasplante. 
3. Otras funciones. 
− Establecer relaciones con múltiples profesionales (equipos clínicos, Coordinación 
Autonómica, Organización Nacional de Trasplantes, dirección del centro, consejería de 
salud, profesionales de prensa, etc.). 
− Realización de tareas de formación y tutorización en otros centros. 
− Responsable de Biovigilancia, declarando los eventos/reacciones adversas, 
relacionados con la donación y el trasplante, y realizar un seguimiento periódico de los 
receptores, refrendado con informes a la ONT. 
− Revisión sistemática de los pacientes fallecidos en las unidades de Críticos, la 
introducción de los datos en el Programa de Garantía de Calidad (PGC) del Proceso 
de Donación y la revisión crítica de los resultados propios de manera anual. 
CSV:2KD6P3SE:3723ICXY:74MNM784 URL de validació:https://www.tramita.gva.es/csv-front/index.faces?cadena=2KD6P3SE:3723ICXY:74MNM784
Departamento de Salud Valencia La Fe 
Hospital Universitari i Politècnic La Fe 
Avda. Fernando Abril Martorell, 106· 46026 Valencia 
961244000
www.hospital-lafe.com
− Cumplimentar los registros autonómicos/nacionales asociados a las actividades de 
donación hasta el trasplante. 
− Investigación en el ámbito de la donación y el trasplante. 
− Docencia: a coordinadores de trasplantes y profesionales de cuidados intensivos, a todo 
tipo de colectivos sanitarios y no sanitarios. Promoción de la integración de la donación 
en la planificación anticipada de decisiones y en los cuidados al final de la vida. 
Promoción de una cultura institucional en materia de Donación y Trasplantes y 
aseguramiento del Cumplimiento Legal y Ético. 
− Relación con los medios de comunicación. 
− Mantenimiento del archivo de actividad. 
− Participación en la Comisión de Trasplantes del centro. 
− Elaboración de campañas de información a la población general. 
− Relación con las asociaciones de enfermos vinculadas al trasplante. 
• Categoría: Facultativo o Facultativa Especialista 
• Titulación: Especialidad en Anestesiología y Reanimación 
• Retribuciones: A1 (complemento específico C) 
• Naturaleza de la relación jurídica: Estatutaria Temporal. 
• Tipo de nombramiento: Sustitución 
• Centro de Trabajo: Hospital Universitari i Politècnic La Fe - Conselleria de Sanidad 
• Jornada: Completa 
3.- REQUISITOS GENERALES PARA PARTICIPAR: 
Quienes deseen participar en la presente convocatoria deberán cumplir los siguientes 
requisitos: 
a) Nacionalidad: poseer la nacionalidad española, o de cualquier otro Estado miembro de la 
Unión Europea, así como de aquellos Estados a los que, en virtud de Tratados Internacionales
celebrados por la Unión Europea y ratificados por España, sea de aplicación la libre circulación
de trabajadoras y trabajadores. 
Asimismo, podrán participar, independientemente de su nacionalidad, el cónyuge de las y los 
españoles y de las personas nacionales de otros estados miembros de la Unión Europea, y
cuando así lo prevea el correspondiente tratado, el cónyuge de los nacionales de algún estado 
en los que sea de aplicación la libertad de circulación de los trabajadores, siempre que no estén 
separados de derecho. Asimismo, y con las mismas condiciones que los cónyuges, podrán 
participar sus descendientes y los de su cónyuge, menores de veintiún años o mayores de dicha 
edad que vivan a sus expensas, siempre que cuenten con la tarjeta de residencia de familiar 
de ciudadano de la Unión. 
En el caso de aspirantes de nacionalidad y lengua distinta a la española, deberán acreditar 
conocimiento suficiente de castellano mediante diploma nivel B2 expedido por el organismo 
CSV:2KD6P3SE:3723ICXY:74MNM784 URL de validació:https://www.tramita.gva.es/csv-front/index.faces?cadena=2KD6P3SE:3723ICXY:74MNM784
Departamento de Salud Valencia La Fe 
Hospital Universitari i Politècnic La Fe 
Avda. Fernando Abril Martorell, 106· 46026 Valencia 
961244000
www.hospital-lafe.com
oficial competente. En el supuesto de que se hubiera cursado la enseñanza obligatoria, ciclo 
formativo o enseñanza universitaria en España, no tendrán que acreditar el nivel de lengua. 
b) Edad: haber cumplido los 18 años y no exceder de la edad de jubilación forzosa. El 
cumplimiento de la edad de jubilación forzosa supondrá la baja inmediata de la condición de 
aspirante en las listas de empleo. 
c) Capacidad funcional: Poseer la capacidad funcional necesaria para el desempeño de las 
tareas que se deriven del correspondiente nombramiento. 
En aras de la protección de la seguridad y salud del personal y de la calidad asistencial, la 
administración sanitaria podrá requerir, en cualquier momento, de la Unidad de Prevención de 
Riesgos Laborales u órgano competente, la verificación del mantenimiento de la capacidad 
funcional cuando, por razón de las ausencias de estas en el transcurso de vinculaciones 
precedentes o de cualquier otra circunstancia, resulte necesario determinar su aptitud para 
futuros nombramientos. 
d) No tener separación del servicio, mediante expediente disciplinario, de cualquier servicio 
de salud o Administración pública, ni hallarse inhabilitado o inhabilitada con carácter firme para 
el ejercicio de funciones públicas ni, en su caso, para la correspondiente profesión. En el caso 
de personas nacionales de otros estados mencionados en el apartado a), ni hallarse en
inhabilitación, por sanción o pena, para el ejercicio profesional o para el acceso a funciones o 
servicios públicos en un estado miembro, ni tener separación del servicio, por sanción 
disciplinaria, de alguna de sus administraciones o servicios públicos. 
Dicha situación se acreditará mediante una declaración responsable de la persona interesada 
y, en caso de detectarse falsedad, determinará la imposibilidad de continuar el procedimiento, 
sin perjuicio de las responsabilidades que de tal hecho puedan derivarse. 
Asimismo, y conforme a lo establecido en el artículo 13.5 de la ley Orgánica 1/1996, de 15 de 
enero, de Protección Jurídica del Menor, de modificación parcial del Código Civil y de la Ley de 
Enjuiciamiento Civil, introducido por la Ley 26/2015, de 28 de julio y en vigor desde el 18 de 
agosto de 2015, establece que: “5. Será requisito para el acceso y ejercicio a las profesiones, 
oficios y actividades que impliquen contacto habitual con menores, el no haber sido condenado 
por sentencia firme por algún delito contra la libertad e indemnidad sexual, que incluye la 
agresión y abuso sexual, acoso sexual, exhibicionismo y provocación sexual, prostitución y
explotación sexual y corrupción de menores, así como por trata de seres humanos. 
En el momento de la toma de posesión, se deberá acreditar esta circunstancia en el 
departamento de salud correspondiente mediante la aportación de una certificación negativa 
del Registro Central de delincuentes sexuales. 
e) Estar en posesión de la titulación exigida para cada categoría o en condiciones de 
obtenerla cuando se presenta la solicitud de inscripción. 
En el caso de que la titulación sea de formación sanitaria especializada en ciencias de la salud, 
se entenderá que está en condiciones de obtenerla quien acredite haber finalizado con 
evaluación positiva la formación exigida para su consecución dentro del plazo de presentación 
de solicitudes. La fecha de finalización del programa formativo con evaluación positiva será la 
fecha de efectos plenos del título de especialista a los solos efectos de la inscripción en las 
listas de empleo temporal. 
CSV:2KD6P3SE:3723ICXY:74MNM784 URL de validació:https://www.tramita.gva.es/csv-front/index.faces?cadena=2KD6P3SE:3723ICXY:74MNM784
Departamento de Salud Valencia La Fe 
Hospital Universitari i Politècnic La Fe 
Avda. Fernando Abril Martorell, 106· 46026 Valencia 
961244000
www.hospital-lafe.com
f) Estar inscrito o inscrita en las listas de empleo temporal de la Conselleria con 
competencias en materia de sanidad o en las listas de reserva, en cualquiera de los 
Departamentos de salud. 
Todos los requisitos, tanto generales como específicos, deberán cumplirse en el momento de 
la inscripción y deberán mantenerse durante todo el tiempo de permanencia en las listas de 
empleo temporal. 
4.- SOLICITUDES: 
4.1.- Las solicitudes se presentarán en el plazo de cinco días hábiles, contados desde el 
siguiente a la publicación de este anuncio en la página web de la Conselleria de Sanidad, 
http://www.san.gva.es/. 
4.2.- Las solicitudes se dirigirán a la Secretaría de la Comisión, Subdirección Económica de 
Personal y podrán presentarse en: 
• Registro General del Departamento València La Fe, sito en la Avenida Fernando Abril 
Martorell nº 106, 46026 VALÈNCIA.
• Cualquiera de las formas previstas en el art. 16 de la Ley 39/2015, de 1 de octubre, del 
Procedimiento Administrativo Común de las Administraciones Públicas. 
4.3.- A la solicitud acompañarán necesariamente: 
• Titulación académica.
"""
,
    config=config,
)

# Check for a function call
if response.candidates[0].content.parts[0].function_call:
    function_call = response.candidates[0].content.parts[0].function_call
    args = dict(function_call.args or {})
    #print(f"Function to call: {function_call.name}")
    print("Arguments:")
    print(
    f"es_convocatoria: {args.get('es_convocatoria')}\n"
    f"tipo: {args.get('tipo')}\n"
    f"organismo: {args.get('organismo')}\n"
    f"ambito: {args.get('ambito')}\n"
    f"plazas: {args.get('plazas')}\n"
    f"titulacion_requerida: {args.get('titulacion_requerida')}\n"
    f"requisitos_experiencia: {args.get('requisitos_experiencia')}\n"
    f"jornada: {args.get('jornada')}\n"
    f"sistema_seleccion: {args.get('sistema_seleccion')}\n"
    f"fecha_publicacion: {args.get('fecha_publicacion')}\n"
    f"plazo: {args.get('plazo')}\n"
    f"referencia_oficial: {args.get('referencia_oficial')}\n"
    f"urls: {args.get('urls')}\n"
    f"fragmentos_clave: {args.get('fragmentos_clave')}"
)


else:
    print("No function call found in the response.")
    print(response.text)




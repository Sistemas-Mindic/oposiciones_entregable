from pathlib import Path

# Fuentes RECURSIVAS (las que estaban “sueltas”)
DEFAULT_FUENTES_RECURSIVAS = [
    "https://www.sede.dival.es/tablonpersonal/Convocatorias.do?codtipo=OP&lang=es&",  # ESTE NO DESCARGA SUBENLACES
   # "https://divalsitae.sede.dival.es/sitae/",  # ESTE SI DESCARGA PDFS
]

# Fuentes normales (planas)
DEFAULT_FUENTES = [
    "https://www.san.gva.es/es/web/recursos-humans/empleo-publico",
    "https://www.san.gva.es/es/web/recursos-humans/cobertura-temporal-procesos-abiertos",
    "https://www.gva.es/es/inicio/atencion_ciudadano/buscadores/busc_empleo_publico?descripcion=enfer&plazoSolicitud=A&estadoConvocatoria=Proceso",
    # NIVEL ESTATAL
    "https://administracion.gob.es/pag_Home/empleoPublico/buscador.html",
    "https://www.boe.es",
    "https://www.sanidad.gob.es/servCiudadanos/oposicionesConcursos/ofertasEmpleo/home.htm",
    "https://ingesa.sanidad.gob.es/RRHH-y-Empleo-INGESA.html",
    # SERVICIOS DE SALUD AUTONÓMICOS
    "https://www.sspa.juntadeandalucia.es/servicioandaluzdesalud/profesionales/ofertas-de-empleo/oferta-de-empleo-publico-puestos-base",
    "https://www.aragon.es/-/oposiciones",
    "https://www.aragon.es/-/trabajar-en-el-salud-seleccion-y-provision-",
    "https://www.astursalud.es/categorias/-/categorias/profesionales/06000recursos-humanos/04000procesos-selectivos",
    "https://www.ibsalut.es/es/profesionales/recursos-humanos/trabaja-con-nosotros/oposiciones",
    "https://www3.gobiernodecanarias.org/sanidad/scs/organica.jsp?idCarpeta=b8cf85ba-fc1e-11dd-a72f-93771b0e33f6",
    "https://www.scsalud.es/concurso-oposicion",
    "https://sanidad.castillalamancha.es/profesionales/atencion-al-profesional/oferta-de-empleo-publico",
    "https://www.saludcastillayleon.es/profesionales/es/ofertasconcursos/ofertas-empleo-publico-procesos-selectivos-sacyl",
    "https://ics.gencat.cat/ca/lics/treballeu-a-lics/",
    "https://convocatories.ics.extranet.gencat.cat/arbre.html?arbre=oposiciotornlliure",
    "https://www.san.gva.es/es/web/recursos-humans/empleo-publico",
    "https://saludextremadura.ses.es/seleccionpersonal/",
    "https://www.sergas.es/Recursos-Humanos?idcatgrupo=11029&idioma=es",
    "https://www.sergas.es/Recursos-Humanos/OPE-Oferta-Pública-de-Emprego?idioma=es",
    "https://www.larioja.org/empleo-publico/es/oposiciones/personal-estatutario-seris",
    "https://www.comunidad.madrid/gobierno/espacios-profesionales/seleccion-personal-estatutario-servicio-madrileno-salud",
    "https://www.murciasalud.es/web/recursos-humanos-y-empleo/oposiciones",
    "https://empleosalud.navarra.es/es/",
    "https://www.osakidetza.euskadi.eus/oferta-de-empleo-publico/webosk00-procon/es/",
]

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "resultados_scraping"
DEFAULT_OUTPUT_FILENAME = "extraccion_data_todas_comunidades.csv"

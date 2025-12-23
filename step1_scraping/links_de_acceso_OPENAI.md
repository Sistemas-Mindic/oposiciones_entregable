import pandas as pd

# Datos de acceso: sitios que funcionan y de los que se pueden extraer datos
sitios_accesibles = [
    ("Buscador AGE/CCAA", "https://administracion.gob.es/pag_Home/empleoPublico/buscador.html"),
    ("BOE", "https://www.boe.es"),
    ("Ministerio de Sanidad", "https://www.sanidad.gob.es/servCiudadanos/oposicionesConcursos/ofertasEmpleo/home.htm"),
    ("INGESA", "https://ingesa.sanidad.gob.es/RRHH-y-Empleo-INGESA.html"),
    ("Andalucía – SAS", "https://www.sspa.juntadeandalucia.es/servicioandaluzdesalud/profesionales/ofertas-de-empleo"),
    ("Aragón – SALUD", "https://www.aragon.es/-/oposiciones"),
    ("Asturias – SESPA", "https://www.astursalud.es/categorias/-/categorias/profesionales/06000recursos-humanos/04000procesos-selectivos"),
    ("Baleares – IB-SALUT", "https://www.ibsalut.es/es/profesionales/recursos-humanos/trabaja-con-nosotros/oposiciones"),
    ("Canarias – SCS", "https://www3.gobiernodecanarias.org/sanidad/scs/organica.jsp?idCarpeta=b8cf85ba-fc1a-11dd-a72f-93771b0e33f6"),
    ("Cantabria – SCS", "https://www.scsalud.es/concurso-oposicion"),
    ("Castilla y León – Sacyl", "https://www.saludcastillayleon.es/profesionales/es/ofertasconcursos"),
    ("Cataluña – ICS", "https://ics.gencat.cat/ca/lics/treballeu-a-lics/"),
    ("ICS – Portal oposiciones", "https://convocatories.ics.extranet.gencat.cat/arbre.html?arbre=oposiciotornlliure"),
    ("Comunidad Valenciana – San GVA", "https://www.san.gva.es/es/web/recursos-humans/empleo-publico"),
    ("Extremadura – SES", "https://saludextremadura.ses.es/seleccionpersonal/"),
    ("Galicia – SERGAS", "https://www.sergas.es/Recursos-Humanos"),
    ("La Rioja – SERIS", "https://www.larioja.org/empleo-publico/es/oposiciones/personal-estatutario-seris"),
    ("Madrid – SERMAS", "https://www.comunidad.madrid/gobierno/espacios-profesionales/seleccion-personal-estatutario-servicio-madrileno-salud"),
    ("Murcia – SMS", "https://www.murciasalud.es/web/recursos-humanos-y-empleo/oposiciones"),
    ("SAE – Empleo", "https://sindicatosae.com/empleo"),
    ("CSIF – Oferta Empleo", "https://www.csif.es/es/portada/nacionalsanidad/categoria/ofertaempleopublico"),
    ("CSIF – Bolsas de trabajo", "https://www.csif.es/es/portada/nacionalsanidad/categoria/ofertasybolsasdetrabajo"),
    ("EmpleoPublico.net", "https://www.empleopublico.net"),
    ("Opostal – Sanidad", "https://www.opostal.com/ofertas/sanidad"),
]

# Datos de sitios que fallaron o no permiten acceso
sitios_no_accesibles = [
    ("Defensa – Portal Empleo", "https://www.defensa.gob.es/portaldelefensa/empleo/"),
    ("Defensa – Concursos y oposiciones", "https://www.defensa.gob.es/defensa_yo/concursos-oposiciones/"),
    ("Instituciones Penitenciarias", "https://www.institucionpenitenciaria.es/es/web/home/empleo-publico"),
    ("MUFACE – Empleo", "https://www.muface.es/muface_Home/empleo"),
    ("ISFAS – Defensa", "https://www.defensa.gob.es/isfas/informacion/empleo/"),
    ("Justicia – Empleo Público", "https://www.mjusticia.gob.es/es/servicios/empleo-publico"),
    ("SATSE – Empleo", "https://www.satse.es/empleo"),
    ("CCOO Sanidad", "https://sanidad.ccoo.es"),
    ("CCOO Sanidad Madrid", "https://sanidad.ccoo.es/sanidadmadrid/Empleo"),
    ("UGT Sanidad", "https://ugt-sp.es/servicios-publicos/sanidad"),
    ("Opositas – Empleo Público", "https://www.opositas.com/empleo-publico/"),
    ("Iberoposiciones – Sanidad", "https://www.iberoposiciones.es/empleo-publico-sanidad"),
    ("Empléate – Portal", "https://empleate.gob.es/empleo/#/busqueda"),
    ("Castilla-La Mancha – SESCAM", "https://sanidad.castillalamancha.es/profesionales/atencion-al-profesional/oferta-de-empleo-publico"),
    ("Navarra – Osasunbidea", "https://empleosalud.navarra.es/es/"),
    ("País Vasco – Osakidetza", "https://www.osakidetza.euskadi.eus/oferta-de-empleo-publico"),
]

# Crear DataFrames
df_si = pd.DataFrame(sitios_accesibles, columns=["Sitio", "URL"])
df_no = pd.DataFrame(sitios_no_accesibles, columns=["Sitio", "URL"])

import ace_tools as tools; tools.display_dataframe_to_user(name="Sitios Accesibles", dataframe=df_si)
tools.display_dataframe_to_user(name="Sitios No Accesibles", dataframe=df_no)

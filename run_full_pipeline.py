#!/usr/bin/env python3
from __future__ import annotations

"""Pipeline ejecutable: aplica los pasos completos de scraping, filtrado, revisión y consolidación."""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from step1_scraping.extraccion_config import (
    DEFAULT_FUENTES,
    DEFAULT_FUENTES_RECURSIVAS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_FILENAME,
)

ROOT = Path(__file__).resolve().parent

EXTRACCION_OUTPUT_PATH: Path = DEFAULT_OUTPUT_DIR / DEFAULT_OUTPUT_FILENAME

RUN_PIPELINE_FUENTES_PLANAS: list[str] = [
    "https://www.san.gva.es/es/web/recursos-humans/empleo-publico",
    # "https://www.san.gva.es/es/web/recursos-humans/cobertura-temporal-procesos-abiertos",
    # "https://www.gva.es/es/inicio/atencion_ciudadano/buscadores/busc_empleo_publico?descripcion=enfer&plazoSolicitud=A&estadoConvocatoria=Proceso",
    # "https://administracion.gob.es/pag_Home/empleoPublico/buscador.html",
    # "https://www.boe.es",
    # "https://www.sanidad.gob.es/servCiudadanos/oposicionesConcursos/ofertasEmpleo/home.htm",
    # "https://ingesa.sanidad.gob.es/RRHH-y-Empleo-INGESA.html",
    # "https://www.sspa.juntadeandalucia.es/servicioandaluzdesalud/profesionales/ofertas-de-empleo/oferta-de-empleo-publico-puestos-base",
    # "https://www.aragon.es/-/oposiciones",
    # "https://www.aragon.es/-/trabajar-en-el-salud-seleccion-y-provision-",
    # "https://www.astursalud.es/categorias/-/categorias/profesionales/06000recursos-humanos/04000procesos-selectivos",
    # "https://www.ibsalut.es/es/profesionales/recursos-humanos/trabaja-con-nosotros/oposiciones",
    # "https://www3.gobiernodecanarias.org/sanidad/scs/organica.jsp?idCarpeta=b8cf85ba-fc1e-11dd-a72f-93771b0e33f6",
    # "https://www.scsalud.es/concurso-oposicion",
    # "https://sanidad.castillalamancha.es/profesionales/atencion-al-profesional/oferta-de-empleo-publico",
    # "https://www.saludcastillayleon.es/profesionales/es/ofertasconcursos/ofertas-empleo-publico-procesos-selectivos-sacyl",
    # "https://ics.gencat.cat/ca/lics/treballeu-a-lics/",
    # "https://convocatories.ics.extranet.gencat.cat/arbre.html?arbre=oposiciotornlliure",
    # "https://www.san.gva.es/es/web/recursos-humans/empleo-publico",
    # "https://saludextremadura.ses.es/seleccionpersonal/",
    # "https://www.sergas.es/Recursos-Humanos?idcatgrupo=11029&idioma=es",
    # "https://www.sergas.es/Recursos-Humanos/OPE-Oferta-Pública-de-Emprego?idioma=es",
    # "https://www.larioja.org/empleo-publico/es/oposiciones/personal-estatutario-seris",
    # "https://www.comunidad.madrid/gobierno/espacios-profesionales/seleccion-personal-estatutario-servicio-madrileno-salud",
    # "https://www.murciasalud.es/web/recursos-humanos-y-empleo/oposiciones",
    # "https://empleosalud.navarra.es/es/",
#     "https://www.osakidetza.euskadi.eus/oferta-de-empleo-publico/webosk00-procon/es/",
 ]

RUN_PIPELINE_FUENTES_RECURSIVAS: list[str] = [
    "https://www.sede.dival.es/tablonpersonal/Convocatorias.do?codtipo=OP&lang=es&",
]

EXTRACCION_PLAIN_LINKS: list[str] = list(RUN_PIPELINE_FUENTES_PLANAS)
EXTRACCION_RECURSIVE_LINKS: list[str] = list(RUN_PIPELINE_FUENTES_RECURSIVAS)

RUN_PIPELINE_CSV_CRUDO: Path = Path("step1_scraping/scraping_nacional/convocatorias_age_crudo_run_total.csv")
RUN_PIPELINE_CSV_DETALLE: Path = Path("step1_scraping/scraping_nacional/convocatorias_detalle_age_run_total.csv")


def _build_extraccion_args() -> list[str]:
    args: list[str] = []
    for fuente in EXTRACCION_PLAIN_LINKS:
        args.extend(["--fuente-plana", fuente])
    for fuente in EXTRACCION_RECURSIVE_LINKS:
        args.extend(["--fuente-recursiva", fuente])
    args.extend(["--output", str(EXTRACCION_OUTPUT_PATH)])
    return args


EXTRACCION_ARGS = _build_extraccion_args()
STEP2_ARGS: list[str] = ["--output", str(RUN_PIPELINE_CSV_CRUDO)]
STEP3_ARGS: list[str] = [
    "--input",
    str(RUN_PIPELINE_CSV_CRUDO),
    "--output",
    str(RUN_PIPELINE_CSV_DETALLE),
]

SCRIPTS: list[tuple[str, Sequence[str] | None]] = [
    ("step1_scraping/extraccion_data.py", EXTRACCION_ARGS),
    ("step1_scraping/scraping_nacional/step2_XML_de_pag.py", STEP2_ARGS),
    ("step1_scraping/scraping_nacional/step3_filtrar_data.py", STEP3_ARGS),
    ("step3_api_call/orquestador_google/review_textos_integrado.py", None),
    ("step4_resultados/consolidador.py", None),
]


def run_script(relpath: str, script_args: Sequence[str] | None, *, dry_run: bool) -> int:
    path = ROOT / relpath
    if not path.exists():
        logging.error("No se encuentra el script: %s", path)
        return 2
    cmd = [sys.executable, str(path)]
    if script_args:
        cmd.extend(script_args)
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    roots = [str(ROOT)]
    if pythonpath:
        roots.append(pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(roots)
    logging.info("Ejecutando: %s", " ".join(cmd))
    if dry_run:
        print("DRY-RUN:", " ".join(cmd))
        return 0
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    if proc.stdout:
        print(proc.stdout)
    return proc.returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lanza la tubería completa de scraping -> filtrado -> revisión -> consolidación",
    )
    parser.add_argument("--dry-run", action="store_true", help="Mostrar los comandos sin ejecutarlos")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Si se produce un error en un paso, continuar con los siguientes en vez de abortar",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    result_rc = 0
    for rel, step_args in SCRIPTS:
        logging.info("Paso: %s", rel)
        rc = run_script(rel, step_args, dry_run=args.dry_run)
        if rc != 0:
            logging.error("El paso %s finalizó con código %s", rel, rc)
            if not args.continue_on_error:
                logging.error("Abortando pipeline por error en %s", rel)
                return rc
            logging.warning(
                "Continuando por --continue-on-error a pesar del error en %s", rel,
            )
            result_rc = rc
    logging.info("Pipeline completado")
    return result_rc


if __name__ == "__main__":
    raise SystemExit(main())

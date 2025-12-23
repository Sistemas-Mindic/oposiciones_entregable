# -*- coding: utf-8 -*-
import re

# ----- Configuración de proximidad (en palabras) -----
WINDOW_WORDS = 50

# 1) Patrones de "convocatoria" (castellano + cooficiales)
_PAT_CONV = (
    r"\bconvocatoria(?:s)?\b|"                     # convocatoria(s)
    r"\bse\s+convoca(?:n)?\b|"                     # se convoca(n)
    r"\bpor\s+la\s+que\s+se\s+convoca\b|"          # por la que se convoca
    r"\bconvocatorio\b|"                           # (por si aparece mal escrito)
    r"\bconvocatoria\s+(?:de|del|para)\s+(?:proceso\s+selectivo|pruebas?\s+selectivas?|"
    r"concurso[ -]?oposicion(?:es)?|provision|cobertura|plazas?|puestos?)\b|"
    # Catalán/valenciano
    r"\bconvocatoria\b|"                           # tras normalizar, 'convocatòria' -> 'convocatoria'
    r"\bes\s+convoca(?:n)?\b|"
    r"\bper\s+la\s+qual\s+es\s+convoca\b|"
    r"\bconvocatoria\s+(?:de|del|per\s+a)\s+(?:proces\s+selectiu|proves?\s+selectives?|places?)\b|"
    # Euskera (formas más habituales)
    r"\bdeialdi(?:a|ak|aren)?\b|"                  # deialdia, deialdiak, deialdiaren
    r"\bdeialdi\s+publiko(?:a|ak)?\b"
)

# 2) Léxico de EMPLEO (añadidos para contratación laboral/bolsas)
_PAT_EMP = (
    r"oposicion(?:es)?|proceso(?:s)?\s+selectivo(?:s)?|pruebas?\s+selectivas?|"
    r"concurso[ -]?oposicion(?:es)?|concurso\s+de\s+meritos|"
    r"plaza(?:s)?|puesto(?:s)?|provision|cobertura|"
    r"seleccion\s+de\s+personal|empleo\s+publico|"
    r"funcionari[oa]s?|personal\s+laboral|interin[oa]s?|"
    r"proces\s+selectiu(?:s)?|proves?\s+selectives?|places?|"
    # --- Añadidos clave ---
    r"contrataci[oó]n\s+(?:de\s+personal|laboral|temporal)|"
    r"contrato\s+de\s+trabajo|"
    r"bolsa\s+de\s+(?:trabajo|empleo)|"
    r"lista\s+de\s+espera|"
    r"nombramiento(?:s)?|estatutari[oa]s?"
)

# 3) Negativos típicos (NO empleo): licitaciones/contratación pública
_NEG_NO_EMPLEO = re.compile(
    r"\bsubvencion(?:es)?\b|\bayuda(?:s)?\b|\bbeca(?:s)?\b|\bpremio(?:s)?\b|"
    r"\blicitaci[oó]n(?:es)?\b|\badjudicaci[oó]n(?:es)?\b|"
    r"\bperfil\s+del\s+contratante\b|\bplataforma\s+de\s+contrataci[oó]n\s+del\s+sector\s+p[uú]blico\b|"
    r"\bmesa\s+de\s+contrataci[oó]n\b|\bapertura\s+de\s+proposiciones\b|\bapertura\s+de\s+sobres?\b|"
    r"\bexpedient(?:e|es)\b|\bexpte\b|\bn[úu]m(?:ero)?\s+de\s+expediente\b|"
    r"\bpliegos?\b|\bpliegos?\s+de\s+(?:cl[aá]usulas|prescripciones)\b|"
    r"\boferta\s+econ[oó]mica\b|\bimporte\s+de\s+licitaci[oó]n\b|"
    r"\bcontrato\s+(?:de\s+obras|de\s+suministros?|de\s+servicios|de\s+concesi[oó]n)\b|"
    r"\bempresa\s+adjudicataria\b|\bcriterios?\s+de\s+adjudicaci[oó]n\b|"
    r"\bprocedimiento\s+(?:abierto|restringido|negociado)\b|\bCPV\b|\bDOUE\b",
    re.IGNORECASE
)

# Compilados base
_RE_CONV = re.compile(_PAT_CONV, re.IGNORECASE | re.DOTALL)
_RE_EMP  = re.compile(_PAT_EMP,  re.IGNORECASE | re.DOTALL)

# Frase canónica de convocatoria "de empleo"
_RE_CANON = re.compile(
    r"convocatoria\s+(?:de|del|para)\s+(?:proceso\s+selectivo|pruebas?\s+selectivas?|"
    r"concurso[ -]?oposicion(?:es)?|provision|cobertura|plazas?|puestos?)",
    re.IGNORECASE
)

# Ventana de proximidad (convocatoria <-> empleo) en ambos sentidos, medida por PALABRAS
_RE_VENTANA = re.compile(
    rf"(?:{_PAT_CONV})(?:\W+\w+){{0,{WINDOW_WORDS}}}\W+(?:{_PAT_EMP})|"
    rf"(?:{_PAT_EMP})(?:\W+\w+){{0,{WINDOW_WORDS}}}\W+(?:{_PAT_CONV})",
    re.IGNORECASE | re.DOTALL
)

# Ventana negativa: "convocatoria" cerca de indicios de licitación (NO empleo)
_RE_VENTANA_NEG = re.compile(
    rf"(?:{_PAT_CONV})(?:\W+\w+){{0,{WINDOW_WORDS}}}\W+(?:{_NEG_NO_EMPLEO.pattern})|"
    rf"(?:{_NEG_NO_EMPLEO.pattern})(?:\W+\w+){{0,{WINDOW_WORDS}}}\W+(?:{_PAT_CONV})",
    re.IGNORECASE | re.DOTALL
)

# Exportar símbolos útiles
__all__ = [
    "WINDOW_WORDS",
    "_PAT_CONV", "_PAT_EMP", "_NEG_NO_EMPLEO",
    "_RE_CONV", "_RE_EMP", "_RE_CANON", "_RE_VENTANA", "_RE_VENTANA_NEG",
]

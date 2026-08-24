# -*- coding: utf-8 -*-
"""Codificación de las 32 objeciones de producción para el análisis del paper.
Codificación de un revisor (borrador para validación de los autores).

Categoría (category):
  paraphrase = el alumno defiende que su respuesta coincide en contenido con lo
               esperado / su documento, expresado con otras palabras.
  validity   = crítica a la validez o el formato de la pregunta generada
               (o a cómo el evaluador la trata: pide algo inexistente, formato
               inadecuado, debería admitir más opciones...).
  key        = disputa la clave/opciones de una pregunta de opción múltiple.
  other      = mera aserción sin argumento ("es lo que había que poner") o meta.

cites_document (yes/no): la justificación cita contenido o términos técnicos
  específicos del propio documento/proyecto del alumno (nombres de sección,
  herramientas, decisiones de diseño), frente a una apelación genérica.
"""
import csv
from collections import Counter
from pathlib import Path

# id -> (category, cites_document)
CODING = {
    1:  ("paraphrase", "no"),   # "similar en el contenido... explicada de forma mas natural"
    2:  ("validity",   "yes"),  # TEST: roles solo enumerados en el trabajo; pide desc. de la referencia
    3:  ("paraphrase", "no"),   # "correcta pero no escrito tal como en el documento"
    4:  ("paraphrase", "no"),   # idem
    5:  ("paraphrase", "yes"),  # "lo mismo que en el apartado 'Limpieza de datos' de mi documento"
    6:  ("paraphrase", "yes"),  # "mencionado al menos dos medidas de accesibilidad..."
    7:  ("paraphrase", "yes"),  # idem (mismo alumno)
    8:  ("paraphrase", "yes"),  # "se menciona el algoritmo de proximidad, redactado de otra manera"
    9:  ("paraphrase", "yes"),  # "algoritmo de proximidad para enlazar areas deportivas y estaciones"
    10: ("validity",   "yes"),  # "no tiene respuesta definida en el documento... apenas endpoints"
    11: ("paraphrase", "yes"),  # "3 situaciones de ingesta, 2 APIs, validacion de campos, XML"
    12: ("paraphrase", "yes"),  # "con otras palabras... en lugar de cruce, agrupacion"
    13: ("other",      "no"),   # "Esta explicado perfectamente. Es CRUCIAL" (asercion)
    14: ("validity",   "no"),   # "deberia coger mas opciones de respuesta"
    15: ("paraphrase", "yes"),  # "hago referencia a la estructuracion a partir de RDF y SHACL"
    16: ("paraphrase", "yes"),  # "he usado las LSTMs... para los datos bursatiles"
    17: ("other",      "no"),   # "es exactamente lo que habia que poner" (asercion)
    18: ("validity",   "yes"),  # TEST: "requiere saber el orden... en la memoria fue aleatorio"
    19: ("paraphrase", "no"),   # "quiza mas general o diferente explicado"
    20: ("other",      "no"),   # "si que es lo que habia que poner" (asercion)
    21: ("key",        "no"),   # TEST: "el scatter plot tambien dejaria..."
    22: ("validity",   "no"),   # "no parece que haya que nombrar las APIs"
    23: ("key",        "no"),   # TEST: "ambas serian correctas"
    24: ("paraphrase", "no"),   # "los puntos que se deben abordar estan explicados"
    25: ("key",        "yes"),  # TEST: "el objetivo... crear arboles genealogicos... la respuesta B..."
    26: ("validity",   "no"),   # "no puede ser respuesta breve si se espera describir y explicar"
    27: ("validity",   "no"),   # "deberia dar parte de puntuacion y analizar mejor el lenguaje natural"
    28: ("paraphrase", "yes"),  # "se mencionan las herramientas utilizadas (SHACL y ShEx)"
    29: ("paraphrase", "yes"),  # "se menciona la relacion entre patologias y contaminantes"
    30: ("paraphrase", "yes"),  # "he hablado sobre los aspectos del preprocesado de datos GBIF"
    31: ("paraphrase", "no"),   # "he hablado de los criterios de evaluacion" (generico)
    32: ("paraphrase", "yes"),  # "terminos... como Html, d3, el mapa interactivo o la visualizacion del grafo"
}

src = Path(__file__).parent / "incidencias_codificacion.csv"
with open(src, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
    fields = rows[0].keys()

for r in rows:
    cat, cites = CODING[int(r["id"])]
    r["COD_categoria"] = cat
    r["COD_cita_su_documento"] = cites
    r["COD_argumentada"] = "no" if cat == "other" else "yes"

with open(src, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(fields))
    w.writeheader(); w.writerows(rows)

cats = Counter(CODING[i][0] for i in CODING)
cites = sum(1 for i in CODING if CODING[i][1] == "yes")
argued = sum(1 for i in CODING if CODING[i][0] != "other")
n = len(CODING)
print(f"N objeciones = {n}")
print(f"Categorías: {dict(cats)}")
print(f"  paraphrase={cats['paraphrase']}, validity={cats['validity']}, key={cats['key']}, other={cats['other']}")
print(f"Citan contenido específico de su documento: {cites}/{n} = {round(100*cites/n)}%")
print(f"Argumentadas (no mera aserción): {argued}/{n} = {round(100*argued/n)}%")
print(f"[OK] codificación escrita en {src.name}")

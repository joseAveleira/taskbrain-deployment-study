# -*- coding: utf-8 -*-
"""Reproduce la Tabla 3 del manuscrito (constructos de las encuestas) y las
tablas B1-B2 del apendice (estadisticos por item).

Reglas de calculo, declaradas en la Seccion 4.3-4.4 del manuscrito:
  - un 0 en la exportacion significa "sin responder" y se trata como perdido;
  - la puntuacion de constructo es la media de los items que cada participante
    respondio, calculada para quienes respondieron al menos la mitad de los items
    del constructo (columna n);
  - alfa de Cronbach se calcula sobre casos completos (columna n_alpha);
  - las desviaciones tipicas son poblacionales.

Fuente: exportaciones anonimas de las encuestas, una carpeta por asignatura.
"""
import csv, glob, json, os, re, statistics as st, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(os.environ.get("TASKBRAIN_SURVEYS",
           r"C:\Users\josea\Documents\proyectos\TaskBrain\Resultados"))
OUT = Path(__file__).parent / "survey_results.json"

INITIAL = ["IA1", "IA2", "IA3", "IA4", "CR1", "CR2", "TB1", "TB2", "TB3", "ET1", "ET3"]
FINAL = ["US1", "US2", "CP1", "CP2", "CP3", "CP4", "CP5", "CP6_INV", "CP7_INV",
         "FB1", "FB2", "FB3", "CF1", "CF2", "CF3", "CF4"]
CONSTRUCTS = [
    ("initial", "Prior use of generative AI for coursework", ["IA1", "IA2", "IA3", "IA4"]),
    ("initial", "Critical reading of AI output", ["CR1", "CR2"]),
    ("initial", "Prior interest in a tool of this kind", ["TB1", "TB2", "TB3"]),
    ("initial", "Ethical and privacy concern, need for oversight", ["ET1", "ET3"]),
    ("final", "Usability", ["US1", "US2"]),
    ("final", "Quality and personalisation of the questions",
     ["CP1", "CP2", "CP3", "CP4", "CP5"]),
    ("final", "Usefulness of the feedback", ["FB1", "FB2", "FB3"]),
    ("final", "Overall appraisal and future use", ["CF1", "CF2", "CF3", "CF4"]),
]


def read(pattern):
    rows = []
    for path in sorted(glob.glob(str(SRC / pattern))):
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                rows.append({(re.match(r"\((\w+)\)", k).group(1)
                              if re.match(r"\((\w+)\)", k) else k): v
                             for k, v in r.items()})
    return rows


def val(row, code):
    """Valor Likert o None. Un 0 en la exportacion es 'sin responder'."""
    v = (row.get(code) or "").strip()
    try:
        x = float(v)
    except ValueError:
        return None
    return None if x == 0 else x


def item_stats(rows, code):
    xs = [x for x in (val(r, code) for r in rows) if x is not None]
    return round(st.mean(xs), 2), round(st.pstdev(xs), 2), len(xs)


def alpha(rows, codes):
    cc = [[val(r, c) for c in codes] for r in rows]
    cc = [r for r in cc if all(x is not None for x in r)]
    k = len(codes)
    iv = sum(st.variance([r[i] for r in cc]) for i in range(k))
    tv = st.variance([sum(r) for r in cc])
    return round(k / (k - 1) * (1 - iv / tv), 2), len(cc)


def construct(rows, codes):
    k = len(codes)
    threshold = -(-k // 2)          # al menos la mitad de los items
    means = []
    for r in rows:
        xs = [x for x in (val(r, c) for c in codes) if x is not None]
        if len(xs) >= threshold:
            means.append(sum(xs) / len(xs))
    a, n_a = alpha(rows, codes)
    return dict(items=k, n=len(means), M=round(st.mean(means), 2),
                SD=round(st.pstdev(means), 2), n_alpha=n_a, alpha=a)


ini = read("*/Encuesta Inicial*.csv")
fin = read("*/Encuesta Final*.csv")
data = {"initial": ini, "final": fin}
print(f"Respondents: initial N={len(ini)}, final N={len(fin)}")

print("\nTable 3 - survey constructs")
print(f"{'construct':48s} {'items':>5} {'n':>4} {'M (SD)':>13} {'n_a':>4} {'alpha':>6}")
out = {"N": {"initial": len(ini), "final": len(fin)}, "constructs": [], "items": {}}
for survey, name, codes in CONSTRUCTS:
    c = construct(data[survey], codes)
    print(f"{name:48s} {c['items']:>5} {c['n']:>4} {c['M']:>7.2f} ({c['SD']:.2f}) "
          f"{c['n_alpha']:>4} {c['alpha']:>6.2f}")
    out["constructs"].append({"survey": survey, "name": name, **c})

for survey, codes in (("initial", INITIAL), ("final", FINAL)):
    print(f"\nItem-level statistics, {survey} survey")
    out["items"][survey] = {}
    for code in codes:
        m, s, n = item_stats(data[survey], code)
        print(f"  {code:9s} {m:>5.2f} ({s:.2f})  n={n}")
        out["items"][survey][code] = {"M": m, "SD": s, "n": n}

# extras citados en el texto
top = {c: round(100 * sum(1 for r in fin if val(r, c) == 5)
                / sum(1 for r in fin if val(r, c) is not None), 1)
       for c in ("US1", "US2")}
print(f"\nShare choosing the top category: {top}")
by_course = {}
for path in sorted(glob.glob(str(SRC / "*/Encuesta Final*.csv"))):
    rows = [{(re.match(r"\((\w+)\)", k).group(1) if re.match(r"\((\w+)\)", k) else k): v
             for k, v in r.items()} for r in csv.DictReader(open(path, encoding="utf-8-sig"))]
    xs = [x for x in (val(r, "CP7_INV") for r in rows) if x is not None]
    if xs:
        by_course[os.path.basename(os.path.dirname(path))] = (round(st.mean(xs), 2), len(xs))
print("CP7 (reverse-worded, errors or debatable corrections) by course unit:")
for k, v in by_course.items():
    print(f"  {k[:44]:46s} {v[0]:.2f} (n={v[1]})")
out["top_category_share"] = top
out["CP7_by_course"] = by_course

json.dump(out, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n[OK] {OUT.name} written")

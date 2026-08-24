# -*- coding: utf-8 -*-
"""Reproduce el hallazgo central de la Seccion 5.5 y la Tabla 4 del manuscrito:
que puntuacion propuso el modelo frente a que puntuacion almaceno el sistema en
las 170 respuestas breves del despliegue.

Fuentes (volcado de produccion, 2026-07-07):
  datos_crudos/quizgenerations.json  una fila por llamada al modelo, con la
                                     respuesta cruda incluso cuando fue rechazada
  datos_crudos/files.json            entrega -> curso (para acotar la cohorte)
  csv/intentos.csv, csv/respuestas.csv   intentos y respuestas almacenadas

Salida: consola + grading_artifact_results.json (solo agregados).
"""
import csv, json, os, re, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(os.environ.get("TASKBRAIN_DATA",
            r"C:\Users\josea\Documents\proyectos\investigacion\taskbrain\taskbrain_Estudio"))
RAW, CSVD = BASE / "datos_crudos", BASE / "csv"
OUT = Path(__file__).parent / "grading_artifact_results.json"

# Cursos de la cohorte de despliegue (las 6 actividades del manuscrito)
COHORT_COURSES = {
    "Prueba Taskbrain",                              # sesion de familiarizacion
    "SERVICIOS DE DATOS EN INTERNET DE LAS COSAS",
    "Redes Moviles Inalambricas",
    "Internet de las Cosas y Cloud",
    "Tecnicas de Modelado Semantico en la Web",
    "Modelado Semantico En La Web y Linked Data",
}
# La BD lleva tildes; comparamos sin ellas para no depender de la codificacion
def fold(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")
COHORT_FOLDED = {fold(c) for c in COHORT_COURSES}

PROD_ACTS = {
    "Primera prueba aula 1002": "Familiarisation session",
    "Trabajo sobre Meshtastic": "Data Services in IoT",
    "Contenidos 5G": "Mobile and Wireless Netw.",
    "Meshtastic Tarea": "IoT and Cloud",
    "ENTREGA PRACTICA FINAL": "Semantic Web Modelling",
    "Nombre Tarea": "Semantic Mod. and Linked Data",
}
ACT_ORDER = list(PROD_ACTS.values())


def ndjson(p):
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)


def oid(v):
    return v.get("$oid") if isinstance(v, dict) else v


def load_csv(name):
    with open(CSVD / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def act_of(row):
    a = (row.get("actividad") or "").lower()
    for k, v in PROD_ACTS.items():
        if k.lower() in a:
            return v
    return None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ 1. llamadas
files = {oid(f["_id"]): f for f in ndjson(RAW / "files.json")}
calls = [g for g in ndjson(RAW / "quizgenerations.json")]


def course_of(call):
    f = files.get(oid(call.get("fileId")))
    return f.get("courseTitle") if f else None


grading = [g for g in calls if g["operationType"] == "brief_evaluation"
           and fold(course_of(g)) in COHORT_FOLDED]
gener = [g for g in calls if g["operationType"] == "quiz_generation"
         and fold(course_of(g)) in COHORT_FOLDED]
ok = [g for g in grading if g.get("parsedSuccess")]
bad = [g for g in grading if not g.get("parsedSuccess")]

print(f"Cohort model calls: {len(gener)} generation + {len(grading)} grading")
print(f"  generation parsed ok : {sum(1 for g in gener if g.get('parsedSuccess'))}/{len(gener)}")
print(f"  grading   parsed ok  : {len(ok)}/{len(grading)}  -> rejected {len(bad)} "
      f"({100*len(bad)/len(grading):.0f}%)")

# ------------------------------------------- 2. lo que el modelo PROPUSO (crudo)
BLOCK = re.compile(
    r'id_pregunta=\s*"?(\w+)"?\s*\n\s*resultado=\s*"?([^"\n]+?)"?\s*\n\s*puntos=\s*([0-9.]+)')


def short_answers(callset):
    out = []
    for g in callset:
        for qid, label, pts in BLOCK.findall(g.get("rawResponse") or ""):
            if qid.startswith("BREVE"):
                out.append((label.strip(), float(pts)))
    return out


prop_ok, prop_bad = short_answers(ok), short_answers(bad)
print(f"\nShort answers found in raw responses: {len(prop_ok)} accepted + "
      f"{len(prop_bad)} rejected = {len(prop_ok)+len(prop_bad)}")

rows = {}
for label, pts in prop_ok:
    rows.setdefault(pts, {"ok": Counter(), "bad": Counter()})["ok"][label] += 1
for label, pts in prop_bad:
    rows.setdefault(pts, {"ok": Counter(), "bad": Counter()})["bad"][label] += 1

print("\nTable 4 - score proposed by the model x outcome of the call")
print(f"{'score':>6} {'accepted':>9} {'rejected':>9}  categories returned")
for pts in sorted(rows, reverse=True):
    r = rows[pts]
    cats = ", ".join(f"{k}({v})" for k, v in (r["ok"] + r["bad"]).most_common())
    print(f"{pts:>6.2f} {sum(r['ok'].values()):>9} {sum(r['bad'].values()):>9}  {cats}")
m_ok = st.mean([p for _, p in prop_ok])
m_bad = st.mean([p for _, p in prop_bad])
print(f"{'mean':>6} {m_ok:>9.2f} {m_bad:>9.2f}")
print(f"  scores above 0.5 in accepted calls: {sum(1 for _, p in prop_ok if p > 0.5)}")
print(f"  scores above 0.5 in rejected calls: {sum(1 for _, p in prop_bad if p > 0.5)}")

# ------------------------------------------- 3. lo que el sistema ALMACENO
attempts = [r for r in load_csv("intentos.csv") if act_of(r)]
ids = {r["attemptId"] for r in attempts}
answers = [r for r in load_csv("respuestas.csv") if r["attemptId"] in ids]
breve = [r for r in answers if r["questionId"].startswith("BREVE_")]
stored = [r for r in breve if (r["resultado_auto"] or "").strip()]
unscored = [r for r in breve if not (r["resultado_auto"] or "").strip()]
print(f"\nStored short answers: {len(stored)} with an automatic score, "
      f"{len(unscored)} without")
print("  stored automatic scores:", dict(sorted(Counter(r["nota_auto"] for r in stored).items())))
print("  final score of the unscored ones:",
      dict(Counter(r["nota_final"] for r in unscored)))
print(f"  of the {len(unscored)} unscored, "
      f"{sum(1 for r in unscored if not (r['nota_manual'] or '').strip())} were counted as 0")

# ------------------------------------------- 4. medias por actividad, ambas versiones
def is_lost(r):
    return (r["questionId"].startswith("BREVE_")
            and not (r["resultado_auto"] or "").strip()
            and not (r["nota_manual"] or "").strip())


by_att = defaultdict(list)
for r in answers:
    by_att[r["attemptId"]].append(r)

per_act = defaultdict(lambda: {"M": [], "Mstar": [], "uns": 0, "n": 0})
for a in attempts:
    rs = by_att[a["attemptId"]]
    allv = [num(r["nota_final"]) for r in rs if num(r["nota_final"]) is not None]
    keep = [num(r["nota_final"]) for r in rs
            if not is_lost(r) and num(r["nota_final"]) is not None]
    d = per_act[act_of(a)]
    d["M"].append(10 * st.mean(allv))
    d["Mstar"].append(10 * st.mean(keep))
    d["uns"] += sum(1 for r in rs if is_lost(r))
    d["n"] += 1

print("\nTable 2 - mean attempt score as awarded (M) and with lost answers "
      "treated as missing (M*)")
print(f"{'activity':32s} {'n':>3} {'M (SD)':>14} {'M* (SD)':>14} {'unscored':>9}")
tot_M, tot_Ms, tot_u = [], [], 0
for a in ACT_ORDER:
    d = per_act[a]
    tot_M += d["M"]; tot_Ms += d["Mstar"]; tot_u += d["uns"]
    print(f"{a:32s} {d['n']:>3} {st.mean(d['M']):>7.2f} ({st.stdev(d['M']):.2f}) "
          f"{st.mean(d['Mstar']):>7.2f} ({st.stdev(d['Mstar']):.2f}) {d['uns']:>9}")
print(f"{'All activities':32s} {len(tot_M):>3} {st.mean(tot_M):>7.2f} ({st.stdev(tot_M):.2f}) "
      f"{st.mean(tot_Ms):>7.2f} ({st.stdev(tot_Ms):.2f}) {tot_u:>9}")

# ------------------------------------------- 5. objeciones contra respuestas sin nota
inc = [r for r in load_csv("incidencias.csv") if r["attemptId"] in ids]
against_unscored = [r for r in inc if not (r["resultado_auto"] or "").strip()]
print(f"\nObjections: {len(inc)} total, {len(against_unscored)} filed against answers "
      f"that carried no automatic score")

# ------------------------------------------- 6. coste
ti = sum(g.get("inputTokens") or 0 for g in grading)
to = sum(g.get("outputTokens") or 0 for g in grading)
gen_instrumented = [g for g in calls if g["operationType"] == "quiz_generation"
                    and (g.get("inputTokens") or 0) > 0]
gi = st.mean([g["inputTokens"] for g in gen_instrumented])
go = st.mean([g["outputTokens"] for g in gen_instrumented])
cost_grade = ti / 1e6 * 2.5 + to / 1e6 * 10
cost_gen = (len(gener) * gi) / 1e6 * 2.5 + (len(gener) * go) / 1e6 * 10
print(f"\nCost: grading {ti} in / {to} out = ${cost_grade:.2f}; "
      f"generation estimated from {len(gen_instrumented)} instrumented pilot calls "
      f"({gi:.0f} in / {go:.0f} out each) = ${cost_gen:.2f}; "
      f"total ${cost_grade+cost_gen:.2f} = {100*(cost_grade+cost_gen)/len(attempts):.1f} cents/attempt")

json.dump({
    "calls": {"generation": len(gener), "grading": len(grading),
              "grading_rejected": len(bad)},
    "proposed": {"accepted": Counter(f"{p}" for _, p in prop_ok),
                 "rejected": Counter(f"{p}" for _, p in prop_bad),
                 "mean_accepted": round(m_ok, 3), "mean_rejected": round(m_bad, 3)},
    "stored": {"with_score": len(stored), "without_score": len(unscored),
               "counted_as_zero": sum(1 for r in unscored
                                      if not (r["nota_manual"] or "").strip())},
    "per_activity": {a: {"n": per_act[a]["n"],
                         "M": round(st.mean(per_act[a]["M"]), 2),
                         "M_sd": round(st.stdev(per_act[a]["M"]), 2),
                         "Mstar": round(st.mean(per_act[a]["Mstar"]), 2),
                         "Mstar_sd": round(st.stdev(per_act[a]["Mstar"]), 2),
                         "unscored": per_act[a]["uns"]} for a in ACT_ORDER},
    "objections": {"total": len(inc), "against_unscored": len(against_unscored)},
    "cost_usd": {"grading": round(cost_grade, 2), "generation_est": round(cost_gen, 2)},
}, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"\n[OK] {OUT.name} written")

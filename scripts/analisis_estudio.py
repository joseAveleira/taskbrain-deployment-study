# -*- coding: utf-8 -*-
"""
Análisis reproducible del despliegue TaskBrain para el manuscrito EAIT.
Fuente: snapshot íntegro de la BD de producción (taskbrain_Estudio/csv, 2026-07-07).
Salida: analysis_results.json + resumen por consola. Solo agregados (sin datos personales).
"""
import csv, json, statistics as st
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(r"C:\Users\josea\Documents\proyectos\investigacion\taskbrain\taskbrain_Estudio\csv")
OUT = Path(__file__).parent / "analysis_results.json"

def load(name):
    with open(BASE / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

intentos = load("intentos.csv")
respuestas = load("respuestas.csv")
incidencias = load("incidencias.csv")
gen = load("generaciones_ia.csv")
consent = load("consentimientos.csv")
lanz = load("lanzamientos.csv")

# ---- Cohorte de producción: actividades reales con alumnos (abril-junio 2026) ----
PROD_ACTS = {
    "Primera prueba aula 1002": "A1-Trial",
    "Trabajo sobre Meshtastic": "A2-IoTData",
    "Contenidos 5G": "A3-5G",
    "Meshtastic Tarea": "A4-IoTCloud",
    "ENTREGA PRACTICA FINAL": "A5-SemWeb",  # sin tilde en la BD
    "Nombre Tarea": "A6-LinkedData",  # Modelado Semántico y Linked Data
}
def act_of(row):
    for k, v in PROD_ACTS.items():
        if k.lower() in (row.get("actividad") or "").lower():
            return v
    return None

prod_att = [r for r in intentos if act_of(r)]
prod_ids = {r["attemptId"] for r in prod_att}
prod_resp = [r for r in respuestas if r["attemptId"] in prod_ids]
prod_inc = [r for r in incidencias if r["attemptId"] in prod_ids]

res = {}

# ---- 1. Cohorte ----
res["cohorte"] = {
    "intentos_produccion": len(prod_att),
    "alumnos_distintos": len({r["userId"] for r in prod_att}),
    "cursos": len({r["courseId"] for r in prod_att}),
    "actividades": len({act_of(r) for r in prod_att}),
    "consentimientos_total": len(consent),
    "respuestas": len(prod_resp),
    "periodo": (min(r["enviado"] for r in prod_att if r["enviado"]),
                max(r["enviado"] for r in prod_att if r["enviado"])),
    "intentos_totales_bd_incl_piloto": len(intentos),
}

# ---- 2. Por actividad ----
per_act = {}
for r in prod_att:
    a = act_of(r)
    per_act.setdefault(a, []).append(r)
tabla_act = {}
for a, rows in sorted(per_act.items()):
    notas = [float(r["nota_total"]) for r in rows if r["nota_total"]]
    dur = [float(r["duracion_min"]) for r in rows if r["duracion_min"]]
    ninc = sum(int(r["n_incidencias"] or 0) for r in rows)
    tabla_act[a] = {
        "actividad_moodle": rows[0]["actividad"], "curso": rows[0]["curso"],
        "alumnos": len({r["userId"] for r in rows}), "intentos": len(rows),
        "nota_media": round(st.mean(notas), 2) if notas else None,
        "nota_sd": round(st.stdev(notas), 2) if len(notas) > 1 else None,
        "nota_min": round(min(notas), 2) if notas else None,
        "nota_max": round(max(notas), 2) if notas else None,
        "duracion_media_min": round(st.mean(dur), 1) if dur else None,
        "incidencias": ninc,
        "incidencias_por_intento_pct": round(100 * sum(1 for r in rows if int(r["n_incidencias"] or 0) > 0) / len(rows), 1),
    }
res["por_actividad"] = tabla_act

# ---- 3. Respuestas: distribución por tipo y resultado ----
def tipo(r): return "test" if r["questionId"].startswith("TEST_") else "breve"
dist = defaultdict(Counter)
for r in prod_resp:
    dist[tipo(r)][r["resultado_auto"] or "sin_evaluar"] += 1
res["respuestas_por_tipo"] = {t: dict(c) for t, c in dist.items()}

# notas medias por tipo (nota final 0-1)
notas_tipo = defaultdict(list)
for r in prod_resp:
    if r["nota_final"]:
        notas_tipo[tipo(r)].append(float(r["nota_final"]))
res["nota_media_por_tipo"] = {t: {"n": len(v), "media": round(st.mean(v), 3), "sd": round(st.stdev(v), 3)}
                              for t, v in notas_tipo.items() if len(v) > 1}

# ---- 4. Incidencias (producción) ----
inc_stats = {
    "total": len(prod_inc),
    "intentos_con_incidencia": len({r["attemptId"] for r in prod_inc}),
    "pct_intentos_con_incidencia": round(100 * len({r["attemptId"] for r in prod_inc}) / len(prod_att), 1),
    "pct_respuestas_contestadas": round(100 * len(prod_inc) / len(prod_resp), 2),
    "por_tipo_pregunta": dict(Counter(r["tipo_pregunta"] for r in prod_inc)),
    "por_resultado_al_reportar": dict(Counter(r["resultado_auto"] or "sin_evaluar(0_provisional)" for r in prod_inc)),
    "por_actividad": dict(Counter(act_of(r) for r in prod_inc)),
    "con_ajuste_posterior": sum(1 for r in prod_inc if r["ajuste_posterior_a_incidencia"] == "SI"),
    "longitud_texto_mediana": int(st.median([len(r["texto_incidencia"]) for r in prod_inc])),
}
# tasa de objeción sobre respuestas breves CON evaluación IA visible
breves_eval = [r for r in prod_resp if tipo(r) == "breve" and (r["resultado_auto"] or "") not in ("", "pending")]
inc_breve_eval = [r for r in prod_inc if r["tipo_pregunta"] == "respuesta_breve" and (r["resultado_auto"] or "") not in ("", "pending")]
inc_stats["tasa_objecion_breves_evaluadas_pct"] = round(100 * len(inc_breve_eval) / len(breves_eval), 2)
tests_eval = [r for r in prod_resp if tipo(r) == "test"]
inc_test = [r for r in prod_inc if r["tipo_pregunta"] == "test"]
inc_stats["tasa_objecion_test_pct"] = round(100 * len(inc_test) / len(tests_eval), 2)
res["incidencias"] = inc_stats

# ---- 5. Ciclo profesor ----
res["ciclo_profesor"] = {
    "intentos_reviewed": sum(1 for r in prod_att if r["estado"] == "reviewed"),
    "alumnos_cerraron_revision": sum(1 for r in prod_att if r["alumno_cerro_revision"]),
    "respuestas_con_ajuste_manual": sum(1 for r in prod_resp if r.get("nota_manual")),
    "estados_intentos": dict(Counter(r["estado"] for r in prod_att)),
}

# ---- 6. Pipeline IA (SOLO cohorte de producción) ----
# generaciones_ia.csv no tiene attemptId; se cruza por curso. Filtramos a los
# cursos de las 6 actividades de producción para ser coherentes con el resto.
prod_cursos = {r["curso"] for r in prod_att}
gen_prod = [g for g in gen if g["curso"] in prod_cursos]
ops = defaultdict(lambda: {"llamadas": 0, "parse_ok": 0, "errores": 0, "tok_in": 0, "tok_out": 0, "reintentos": 0})
for g in gen_prod:
    o = ops[g["operacion"]]
    o["llamadas"] += 1
    o["parse_ok"] += g["parseo_ok"].lower() == "true"
    o["errores"] += bool((g["error"] or "").strip())
    o["tok_in"] += int(g["tokens_entrada"] or 0)
    o["tok_out"] += int(g["tokens_salida"] or 0)
    o["reintentos"] += int(g["reintentos"] or 0)
for o in ops.values():
    o["tasa_error_pct"] = round(100 * o["errores"] / o["llamadas"], 1)
res["pipeline_ia"] = dict(ops)
res["pipeline_ia"]["_nota"] = (f"cohorte: {len(gen_prod)} de {len(gen)} llamadas del snapshot "
                               f"(excluidas {len(gen)-len(gen_prod)} de pruebas/piloto fuera de cohorte)")

# respuestas afectadas por fallos del evaluador
sin_eval = [r for r in prod_resp if tipo(r) == "breve" and (r["resultado_auto"] or "") in ("", "pending")]
res["pipeline_ia"]["breves_sin_evaluacion_visible"] = len(sin_eval)
res["pipeline_ia"]["breves_total"] = sum(1 for r in prod_resp if tipo(r) == "breve")
res["pipeline_ia"]["intentos_atascados_submitted"] = sum(1 for r in prod_att if r["estado"] == "submitted")

# ---- 6b. Notas AUTOMÁTICAS reales de las respuestas breves (no los veredictos) ----
breve = [r for r in prod_resp if tipo(r) == "breve"]
notas_auto_breve = Counter(r["nota_auto"] for r in breve if (r["nota_auto"] or "") != "")
res["breves_notas_auto"] = {
    "con_nota_automatica": sum(notas_auto_breve.values()),
    "sin_nota_visible": len(sin_eval),
    "por_nota": {k: notas_auto_breve[k] for k in sorted(notas_auto_breve)},
    "con_nota_maxima_auto": sum(v for k, v in notas_auto_breve.items() if k in ("1", "1.0")),
    "nota_final_max": sorted({r["nota_final"] for r in breve if r["nota_final"]}, key=lambda x: float(x))[-3:],
}

# ---- 6c. Cierre de revisión vs objeción (no son excluyentes) ----
att_con_inc = {r["attemptId"] for r in prod_inc}
cerrados = [r for r in prod_att if r.get("alumno_cerro_revision")]
res["cierre_vs_objecion"] = {
    "cerraron_revision": len(cerrados),
    "cerraron_con_objecion": sum(1 for r in cerrados if r["attemptId"] in att_con_inc),
    "cerraron_sin_objecion": sum(1 for r in cerrados if r["attemptId"] not in att_con_inc),
    "intentos_con_objecion": len(att_con_inc),
    "intentos_sin_objecion_alguna": len(prod_att) - len(att_con_inc),
}

# ---- 7. Coste (precios Azure OpenAI gpt-4o: $2.50/M entrada, $10/M salida) ----
P_IN, P_OUT = 2.50, 10.00
# En el despliegue solo se registraron tokens de las llamadas de EVALUACIÓN de
# breves; las de GENERACIÓN de la cohorte no tienen tokens (=0). Estimamos la
# generación con el consumo por llamada observado en las generaciones del piloto.
ev = ops["brief_evaluation"]
coste_eval = ev["tok_in"] / 1e6 * P_IN + ev["tok_out"] / 1e6 * P_OUT
gen_piloto = [g for g in gen if g["operacion"] == "quiz_generation" and int(g["tokens_entrada"] or 0) > 0]
gp_in = sum(int(g["tokens_entrada"]) for g in gen_piloto) / len(gen_piloto)
gp_out = sum(int(g["tokens_salida"]) for g in gen_piloto) / len(gen_piloto)
n_gen = ops["quiz_generation"]["llamadas"]
coste_gen_est = n_gen * (gp_in / 1e6 * P_IN + gp_out / 1e6 * P_OUT)
coste_total_est = coste_eval + coste_gen_est
res["coste"] = {
    "eval_breves_medido_usd": round(coste_eval, 2),
    "eval_tokens": {"in": ev["tok_in"], "out": ev["tok_out"]},
    "generacion_tokens_registrados_cohorte": ops["quiz_generation"]["tok_in"] > 0,
    "generacion_por_llamada_piloto": {"in": round(gp_in), "out": round(gp_out), "n_piloto": len(gen_piloto)},
    "generacion_estimada_usd": round(coste_gen_est, 2),
    "coste_total_estimado_usd": round(coste_total_est, 2),
    "coste_por_intento_usd": round(coste_total_est / len(prod_att), 4),
    "precios_usd_por_M": {"entrada": P_IN, "salida": P_OUT},
    "nota": ("evaluación de breves MEDIDA (85 llamadas con tokens); generación de "
             "cohorte SIN tokens registrados, estimada desde generaciones del piloto"),
}

# ---- 8. Textos de incidencias para codificación cualitativa (solo id + tipo + texto) ----
res["incidencias_textos"] = [
    {"id": i + 1, "actividad": act_of(r), "tipo": r["tipo_pregunta"],
     "resultado_al_reportar": r["resultado_auto"] or "SIN_EVALUAR",
     "nota_auto": r["nota_auto"], "ajustada": r["ajuste_posterior_a_incidencia"],
     "texto": r["texto_incidencia"]}
    for i, r in enumerate(sorted(prod_inc, key=lambda x: x["fecha_incidencia"]))
]

OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "incidencias_textos"}, indent=2, ensure_ascii=False))
print(f"\n[OK] Guardado en {OUT} (incluye los {len(res['incidencias_textos'])} textos de incidencias para codificar)")

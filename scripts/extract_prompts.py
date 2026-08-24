# -*- coding: utf-8 -*-
"""Genera supplementary_prompts.md: plantillas de prompt tal y como estaban
configuradas en la plataforma durante el despliegue, mas el contrato de salida.

Fuente: taskbrain_Estudio/datos_crudos/systemconfigs.json (coleccion systemconfigs
del volcado de produccion). Contiene las plantillas COMPLETAS. El campo promptText
de quizgenerations.json esta truncado a 5.000 caracteres por el logger, asi que no
sirve para publicar los prompts (era la fuente de la version anterior de este script).
"""
import json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(os.environ.get("TASKBRAIN_DATA",
           r"C:\Users\josea\Documents\proyectos\investigacion\taskbrain\taskbrain_Estudio")) / "datos_crudos" / "systemconfigs.json"
LOG = SRC.parent / "quizgenerations.json"
OUT = Path(__file__).parent.parent / "supplementary_prompts.md"

cfg = {}
for line in SRC.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    d = json.loads(line)
    cfg[d["key"]] = d

order = [
    ("quiz_generation_prompt", "1. Quiz generation prompt (system message)"),
    ("report_generation_prompt", "2. Short-answer grading prompt (system message)"),
    ("loop_quiz_prompt", "3. Quiz extension prompt (used when more items are requested)"),
]

HEAD = """# Supplementary material: TaskBrain prompt templates and output contract

The three prompt templates below are reproduced verbatim from the platform
configuration in force during the deployment reported in the manuscript
(collection `systemconfigs` of the production database snapshot of 7 July 2026).
They are in Spanish, the language of instruction. Placeholders in double braces
are filled in per activity: `{{numTest}}` and `{{numShort}}` are the numbers of
multiple-choice and short-answer items configured by the teacher, `{{quizFocus}}`
is the optional topic focus, and `{{evaluatorPayload}}` is the block containing
the questions, the marking criteria extracted from the student's document and the
student's answers.

The model was GPT-4o on an institutional Azure OpenAI deployment, with sampling
temperature 0.7 for generation and 0.3 for grading.

## 0. Output contract for a graded answer

Each graded answer is stored with a numeric score and a categorical outcome. The
category is validated against a closed set:

| Stored category | Meaning | Numeric score it accompanied in the deployment |
|---|---|---|
| `correcta` | correct | 1.0 |
| `parcial` | partial | 0.5, 0.25 |
| `incorrecta` | incorrect | 0.0, 0.25 |
| `no_respondida` | the student left the item blank | 0.0 |
| `pending` | grading call in flight; never shown to the student | n/a |

Validation is applied to the whole attempt document, so a single category outside
this set rejects the entire grading call, including the answers in it whose
categories are valid.

The scale in the grading prompt of Section 2 below defines five bands
(1.0 *Correcta*, 0.75 *Muy bien*, 0.5 *Parcial*, 0.25 *Minima*, 0.0 *Incorrecta*),
while the output format of that same prompt enumerates only three categories
(`correcta|parcial|incorrecta`). The 0.75 and 0.25 bands therefore have no category
of their own. This is the mismatch analysed in Section 5.5 and Appendix A of the
manuscript: in the deployment the model returned the band descriptor itself
(`muy bien`, `minima`) or the numeric value (`0.75`) as the category, and 18 of the
85 grading calls were rejected on validation as a result.

"""

parts = [HEAD]
for key, title in order:
    if key not in cfg:
        print(f"[WARN] missing {key}")
        continue
    d = cfg[key]
    parts.append(f"## {title}\n")
    if d.get("description"):
        parts.append(f"*Configuration description (verbatim): {d['description']}*\n")
    parts.append("```\n" + d["value"].strip() + "\n```\n")

# Anexo: mensajes de error reales de las llamadas rechazadas
errs = {}
for line in LOG.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    g = json.loads(line)
    if g.get("operationType") == "brief_evaluation" and not g.get("parsedSuccess"):
        m = (g.get("errorMessage") or "").strip()
        errs[m] = errs.get(m, 0) + 1
parts.append("## 4. Validation errors of the rejected grading calls\n")
parts.append("Distinct error messages recorded for the rejected short-answer grading "
             "calls, with the number of calls affected (whole snapshot, deployment "
             "cohort and pilot).\n")
parts.append("```\n" + "\n".join(f"{n:>2}  {m}" for m, n in
                                 sorted(errs.items(), key=lambda x: -x[1])) + "\n```\n")

OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"[OK] {OUT.name} written ({OUT.stat().st_size} bytes); prompts: {list(cfg)}")

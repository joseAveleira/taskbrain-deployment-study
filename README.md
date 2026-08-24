# TaskBrain deployment study: analysis code, prompts and derived data

Supporting material for:

> Aveleira-Mata, J., Narciandi-Rodríguez, D., Rubio-Martín, S., Bayón-Gutiérrez, M.,
> & Benítez-Andrades, J.A. *Beyond AI detection in engineering education: a
> multi-course classroom deployment of LLM-generated quizzes on students' own work.*

TaskBrain generates a personalised quiz from each student's own submitted document,
delivers it in a supervised session inside the virtual campus through LTI 1.3, grades
it provisionally with an LLM, and lets the student raise a single justified objection
per question that the teacher reviews. This repository holds everything needed to
check the numbers reported in the paper.

## Contents

```
prompts/
  supplementary_prompts.md      The three prompt templates in force during the
                                deployment, verbatim, plus the output contract for a
                                graded answer and the validation errors of the
                                rejected grading calls.
coding/
  incidencias_codificacion.csv  The 32 student objections: question, student answer,
                                automatic feedback, the objection text, and its
                                coding (category, whether it cites the student's own
                                document, whether it is argued).
  code_objections.py            The coding, one entry per objection with its rationale.
scripts/
  grading_artifact.py           Reproduces Table 4 (score the model proposed against
                                score the system stored), the M* column of Table 2,
                                the split of objections and the cost figures.
  survey_constructs.py          Reproduces Table 3 and the item-level tables B1-B2.
  extract_prompts.py            Regenerates prompts/supplementary_prompts.md.
  analisis_estudio.py           General descriptive analysis of the deployment.
results/
  grading_artifact_results.json Aggregated output of grading_artifact.py.
  survey_results.json           Aggregated output of survey_constructs.py.
  analysis_results.json         Aggregated output of analisis_estudio.py.
```

## What is not here, and why

The scripts read a snapshot of the production database and the raw survey exports.
Those files contain personal data (student names, e-mail addresses, submitted
documents) and are **not** distributed. Only aggregated and derived outputs are, in
`results/`, together with the objection texts, which carry no identifiers. In those
texts the names of individual student projects are replaced by `[project name]`.

Authorised readers can run the scripts against the private snapshot by pointing two
environment variables at it:

```bash
export TASKBRAIN_DATA=/path/to/taskbrain_Estudio       # csv/ and datos_crudos/
export TASKBRAIN_SURVEYS=/path/to/survey_exports       # one folder per course unit
python scripts/grading_artifact.py
python scripts/survey_constructs.py
```

Python 3.11, standard library only. No third-party dependencies.

## The finding these scripts exist to support

The grading prompt defines a five-band scale for short answers (1.00, 0.75, 0.50,
0.25, 0.00) while the output contract enumerates only three categories, so the 0.75
and 0.25 bands have no category of their own. Validation ran once per call, so a
single unaccepted category discarded a whole grading call. `grading_artifact.py`
recovers, from the raw text of the 18 rejected calls, the scores the model had
proposed for the 36 discarded answers, and shows that every score above 0.50 the
grader produced in the deployment was inside a rejected call. See Section 5.5 and
Appendix A of the paper.

## Licence

Code: MIT. Data and documentation: CC BY 4.0.

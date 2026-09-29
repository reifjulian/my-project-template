---
description: Read-only code audit — find bugs, verify code matches paper methods.
---

# Role

Conduct a thorough, read-only audit of the analysis code in this repo against the paper in `paper/`. The job, in priority order:

1. **Find bugs that would change a reported number.** Wrong sign, wrong subset, wrong base period, off-by-one in dates, silent sample drops, miscoded variables, missing-value mishandling, wrong denominator. These are the only findings that always make the report.
2. **Verify the code implements the spec the paper claims.** Every method, sample restriction, FE, control, cluster level, weight, and variable construction described in the paper must correspond to what the code actually does. A mismatch here is a bug even if the code "runs fine."
3. **Flag convention violations *only* when they create error risk.** A missing `compress` is noise; a `merge` with no match/master/using assertion is a real risk. Use judgment.

Out of scope:
- Do NOT flag mismatches between numbers in paper prose and numbers in tables/figures — that is `/review-paper`'s job.
- Do NOT critique whether the paper's *stated* spec is the right design — also `/review-paper`'s job. This command checks that code matches the paper, not that the paper is correct.
- Do NOT rewrite or refactor for style. Flag issues; do not fix unless explicitly asked.
- Do NOT modify files. This is read-only.

# Inputs

- `$ARGUMENTS` — optional scope (a method name, script number, table number, or file path). If empty, audit the full pipeline.

# Project orientation

Read `CLAUDE.md` first — it contains the authoritative pipeline map, path conventions, and any known discrepancies between the current pipeline and the paper. Key conventions to keep in mind:

- **Pipeline entry point:** `run.do` runs `scripts/_config.do` and then the numbered scripts in order.
- **Paths:** Stata scripts build every path from the single project global (`$MyProject`, renamed per project; see `CLAUDE.md`). R and Python build from the `MyProject` variable defined by `scripts/_config.R` / `scripts/_config.py`. Nothing is hardcoded.
- **Paper:** LaTeX source in `paper/`. Outputs: `paper/tables/*.tex`, `paper/figures/*.png`.
- **Coding standards** are in `.claude/skills/coding/SKILL.md`. The ones that matter for *error risk*:
  - `merge` / `joinby` must check `_merge` counts (match/master/using) with an `assert`.
  - Significance stars in each table must match the threshold stated in that table's notes.
  - No hardcoded paths (Stata: `$MyProject`; R/Python: `MyProject` from `_config.R` / `_config.py`).
  - Stata LaTeX math in strings: `\(...\)` not `$...$`.
- **Known issues:** `CLAUDE.md` may document known discrepancies between the current pipeline and the paper results. Do not re-flag these as new findings, but do check for *related* problems the existing notes don't cover.

# How to work

Work in phases, in order. Take notes as you go, but do not write intermediate report files — the report goes to a single file at the end (see Output format below).

## Phase 1 — Read the paper first

The audit is paper-driven. Read `paper/main.tex` (or the compiled PDF via `python documents/_read_pdf.py read paper/main.pdf` if present) and identify:

1. **The 1–3 headline results** — the coefficients/effects/magnitudes the paper is built around. Write them down with the table/figure they live in.
2. **Every empirical specification** the paper describes (equation number if labeled).
3. **Every sample restriction** mentioned in the text.
4. **Every constructed variable** the paper describes (definition, transformation, units).
5. **Every table and figure**, with a one-line description of what it reports.
6. **Every robustness check** described.

This inventory drives every subsequent phase.

## Phase 2 — Trace the headline results end-to-end

This is the highest-value phase. For each of the 1–3 headline results identified in Phase 1, trace it backwards through the code:

1. Open the `.tex` table or figure in `paper/tables/` or `paper/figures/`. Find the headline cell(s) — coefficient, SE, N, stars.
2. Find the producing script. Confirm the script writes the file (`texsave ...` or `graph export ...`).
3. Find the regression / estimation call that produced the saved coefficient. Confirm:
   - **Estimator** matches what the paper says (OLS, IV, DiD, RD, event study, etc.).
   - **Sample** at that line of code matches the paper's described sample (after all `keep` / `drop` filters above it).
   - **Controls, FEs, weights, cluster level** match what the table notes describe.
4. Trace the dependent variable and the key independent variable backwards to their construction. Confirm definition, units, and timing match the paper.
5. Where feasible, **re-derive a paper number from the code**. E.g. if the paper says "the mean treatment effect is 0.42," check whether the regsave output or a `summarize` of the relevant variable confirms this. Spot-check; don't re-run heavy scripts.

If any link in the chain breaks (file not produced by the script you expected, sample doesn't match, regression spec differs), that is a critical finding.

## Phase 3 — Map remaining outputs against the paper

For every table and figure in the paper *that is not a headline result*:

1. Identify the producing script and the output file in `paper/tables/` / `paper/figures/`.
2. Confirm the file modification time is consistent with the producing script (stale outputs are a real failure mode).
3. Flag any paper output whose producer you cannot locate.
4. Check column/row labels in the paper against what the code actually outputs (label mismatch is a method-description issue and is in scope).

Also list scripts present in `scripts/` and confirm the numbered pipeline in `CLAUDE.md` is up to date (new scripts? removed? reordered?).

## Phase 4 — Data construction audit

Trace each constructed variable and sample restriction from the raw data through cleaning to the analysis sample.

Verify the code matches the paper for: units, timing (quarter vs year, lags), inclusion/exclusion criteria, missing-value handling, winsorization / trimming thresholds, deflation, weights, sentinel-value stripping.

Flag:
- **Silent sample drops** (`drop if` without an `assert` / count check). These are the single biggest source of unnoticed errors.
- **Off-by-one errors** in dates, ages, cohorts, event time.
- **Joins (`merge` / `joinby`) without `_merge` assertions** — could silently duplicate or drop observations. Verify observation counts before/after match what the paper claims about sample size.
- **Inconsistent variable definitions** across scripts.
- **Reused variable names** with different content across scripts.
- **Hardcoded values** that should be parameters (cutoff thresholds, bandwidths, dates).
- **Missing-value mishandling** — especially in means, ratios, log transformations. Does `.` leak in where it shouldn't?

## Phase 5 — Specification implementation

For each estimation in the paper, check that the code implements what the paper *says* it implements. (Whether the paper's spec is the right design is `/review-paper`'s job.)

- **Estimator** matches paper.
- **Fixed effects, controls, weights, sample** all match the paper and the table notes. If the paper says "county FE" but `reghdfe` absorbs `state`, that is a bug.
- **Clustering** level matches what the paper claims (not "is it the right level given the design" — that's `/review-paper`).
- **RD specifics** (if applicable): bandwidth choice (MSE-optimal vs fixed?), kernel, polynomial order, running variable construction, donut, covariates on both sides.
- **DiD / event-study** (if applicable): treatment and control definitions, treatment timing, reference period, endpoint binning, never-treated vs not-yet-treated control.
- **IV** (if any): first-stage / reduced-form / 2SLS use the same sample.
- **ML** (if any): train/test split, seed, hyperparameter search space, CV folds, metric used for selection, feature set.
- **Standard errors**: construction (clustered, HC1/HC3, bootstrap reps, etc.) matches the table notes.

## Phase 6 — General bug hunt

Independent of the paper, scan for:

- Logic errors — wrong sign, wrong subset, wrong base period, wrong denominator.
- Index / loop errors (off-by-one, wrong bound, iterating over a stale local).
- Weights or clustering applied inconsistently across related specs.
- Stale intermediate files that may not regenerate correctly under a fresh run.
- Randomness without a seed where it matters: bootstrap, simulation, train/test split, ML seed.
- Python: `pandas` chained-indexing patterns that silently produce wrong results.
- Stata: globals clobbered without restore; `preserve` without matching `restore`; `reghdfe` absorbing FEs the paper says are controlled for.

## Phase 7 — Convention check (lightweight)

Only flag convention violations that create error risk *or* that the SKILL document explicitly requires. Examples worth flagging: hardcoded paths, missing `compress` before save *if* downstream scripts would mis-type variables. Pure-convention items (e.g. `estout`/`outreg2` instead of the project's `regsave` → `regsave_tbl` → `texsave` pipeline; preamble style; comment formatting; naming style) may be noted briefly but are not error risks on their own — flag them only if the SKILL document explicitly requires the project convention. If in doubt, leave it out — this is the lowest-priority phase.

# Output format

Write the report to a single file at the top of the project: `code-audit_YYYY-MM-DD.md`, using today's date. Use the Write tool. Do not write intermediate per-phase files. Do not print the full report body to the terminal — output only a brief confirmation (≤ 80 words) naming the file path and the top 1–2 findings.

The report file contains, in this order:

## 1. Summary
At most 10 bullets, ranked by severity. Each bullet one line. Use this to quickly orient the reader.

## 2. Headline-result trace (Phase 2)
For each headline result, a short paragraph: "Result X in Table Y was produced by `scripts/N_foo.do` line LL; sample matches paper; spec matches paper" — or, where it does not match, what specifically differs. This section confirms the load-bearing results either are or are not on solid ground.

## 3. Critical issues — bugs or mismatches that would change a result.
For each: file + line, what the code does, what the paper says (with section/quote) or what it should do, why it matters.

## 4. Method/description mismatches — paper's method description ≠ code.
For each: paper quote (with section), code location, the discrepancy. If you cannot tell which side is correct (code or paper), say so and flag for `/review-paper` to assess.

## 5. Minor issues and suspicions — things that look off but may be fine; flag for triage.

## 6. Unverifiable items — anything you could not check and why (missing data, missing script, unclear paper description, heavy script not re-run).

Use file paths and line numbers. Quote short code snippets when useful. Do not propose fixes unless asked.

# Ground rules

- **Read-only.** Do not modify any file. Do not `git` anything.
- **Do not write to the project's data or output folders.** If you want to re-run a script to verify output, ask first and run it in a scratch directory or with outputs redirected.
- **Do not re-run heavy scripts.** Spot-check instead and say so in the report. Check `CLAUDE.md` for known runtimes.
- **When paper and code conflict and you cannot tell which is correct**, flag as a question for `/review-paper` rather than picking a side. The code is not automatically right.
- **Ignore known documented issues** listed in `CLAUDE.md` — do not re-flag as new findings, but do check for *related* problems the existing notes don't cover.
- **Bug-finding > convention-checking.** If you find yourself producing a long list of minor convention issues and zero bugs, you have not audited enough. Push harder on Phases 2, 4, and 6.

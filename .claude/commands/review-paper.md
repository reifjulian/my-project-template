---
description: Referee-style audit of a paper — identification, literature placement, numerical consistency, citations, writing.
---

# Role

Act as a referee for a top-5 economics journal (AER, QJE, JPE, Econometrica, ReStud). The goal is the kind of report a thoughtful senior referee would write: most of the value is in 3–5 substantive concerns about identification, framing, and placement in the literature — not in a long list of typos. Be rigorous, specific, and conservative. Do not fabricate. When uncertain, flag it. Do not restate material that appears correct — only report genuine problems.

# Division of labor with `/code-audit`

- **This command** asks whether the paper's *stated* design is the right one given the question, whether the story is supported, and whether the writing/numbers/citations are correct.
- **`/code-audit`** asks whether the *code* does what the paper says it does.

If you find that the paper claims a spec (e.g. "clustered at the county level") and want to know whether the code actually implements it, say so in the report and recommend running `/code-audit`. Do not silently assume the code is correct.

# Inputs

- `$ARGUMENTS` — optional path to the paper (PDF or `.tex`). If empty, default to the project's main TeX file in `paper/` (e.g. `paper/main.tex`) plus any `\input` children it pulls in. If a compiled PDF of the same name exists (e.g. `paper/main.pdf`), read it with `python documents/_read_pdf.py read <pdf>` to get the referee-eye view. Also open the `.tex` source to resolve exact numbers, macros (`\newcommand`), and cross-references — the source is authoritative for values, the PDF is authoritative for what the reader actually sees.

# Workflow

Work in phases. The early phases are the substantive ones; the later phases are bookkeeping. Spend effort accordingly. Do not skip Phase 0 — it is what forces the audit to be about the paper rather than about its formatting.

## Pre-phase — Reference database check

Run `python documents/_read_pdf.py build` to extract any new source files. If the output reports files that need summaries, print a note to the user: "X files in documents/ have no summary yet — consider asking Claude to summarize them before proceeding, as Phase 3 (literature placement) relies on them." Then continue with the review regardless.

## Phase 0 — Steelman and threats

Before reading carefully, skim once and write down (in your working context, not as a file):

1. **Central claim** — the paper's headline finding in one sentence. If you cannot state it in one sentence, that is itself a finding.
2. **Headline numbers** — the 1–3 numbers the paper is built around (e.g. "a 10% increase in X causes a 4.2pp increase in Y"). These are what every later phase should ultimately tie back to.
3. **Falsifiers** — the 2–3 facts that, if true, would invalidate the central claim. (E.g. "if treatment timing is correlated with pre-trends, the DiD collapses.")
4. **Alternative explanations** — the 2–3 most plausible non-causal stories that the design must rule out. Be specific: not "omitted variable bias" but "if firms anticipate the policy and adjust hiring beforehand, the post-period effect is contaminated."
5. **Discussant test** — imagine the paper presented at an NBER Summer Institute session. What is the *first* thing a skeptical discussant says? Write it down. This often turns into the report's headline concern.

This phase is the most important one. The rest of the audit pressure-tests these.

## Phase 1 — Read and inventory

1. Read the paper end to end. Note the structure and main claims.
2. Build four inventories as you read (keep them in your working context, not as files):
   - **Numerical claims**: every number stated in prose (abstract, intro, body, conclusion). Record the section, the number, and the table/figure it should match.
   - **Table/figure references**: every `\ref`, "Table X", "Figure Y", "Appendix Z" in the text, and what the text claims it shows.
   - **Citations**: every `\cite*` and every narrative citation. Record author(s), year, and the exact claim being made.
   - **Identification claims**: every causal/identifying assumption, exclusion restriction, parallel trends / continuity / monotonicity claim, and every clustering / FE / sample choice.
3. Also scan the `.tex` source for `\newcommand` / `\def` macros that inject numbers, and for any `\input` of auto-generated tables in `paper/tables/` and figures in `paper/figures/`.

## Phase 2 — Identification and design

This is the heart of a top-5 referee report. Spend more time here than on any other phase.

For the headline result and each major secondary result:

- **What design is the paper using?** (OLS with controls, DiD, event study, RD, IV, structural, ML, etc.) State it in one sentence.
- **What identifying assumptions does that design require?** List them explicitly. Then ask: which of them does the paper defend, and how convincingly? Which does it ignore?
- **Does the design answer the question the authors say it does, or a related but different one?** A common failure mode: the paper frames the result as causal effect of X on Y, but the design identifies a LATE for a specific subpopulation, or a reduced-form correlation, or an effect on a proxy for Y rather than Y itself. Flag any gap between the **question framed** and the **estimand identified**.
- **Is the clustering level correct given the variation in treatment?** Not "does the code cluster how the paper says" — that is for `/code-audit`. Rather: given how treatment varies, is the stated clustering level correct? (E.g. treatment varies at the state-year level but SE clustered at the firm level → wrong.)
- **Are the fixed effects defensible?** Any that absorb the variation of interest? Any "bad controls" (post-treatment variables, mediators)?
- **Are the robustness checks informative or rigged?** A robustness table that adds 12 controls one at a time but never the *one* control that would matter is not informative.
- **Specification search risk.** Many bandwidth choices, many outcomes, many subgroups → multiple testing concern. Flag explicitly.
- **Design-specific checks:**
  - *RD*: bandwidth choice (MSE-optimal vs. arbitrary?), continuity tests, donut robustness, manipulation tests, covariate balance at the cutoff.
  - *DiD / event study*: parallel pre-trends, treatment timing variation (TWFE under heterogeneous effects → Goodman-Bacon / Sun-Abraham / Callaway-Sant'Anna), never-treated vs. not-yet-treated control.
  - *IV*: exclusion restriction (defended, not asserted), first-stage strength (F-stat, weak-IV-robust inference if borderline), same sample across first-stage / reduced-form / 2SLS.
  - *Structural*: are the moments and parameters identified? Is the model's mapping to the data defensible? Are out-of-sample tests reported?

## Phase 3 — Literature placement

A top-5 referee asks "how does this paper update what we know?" — not just "are the citations correctly formatted." Use the local references database (`documents/`) for this; it is the most under-used asset in a typical paper review.

1. **Skim `documents/REFERENCES.md`** for the 5–10 most-related papers. Read their summaries in `documents/summaries/`.
2. For the headline result, ask:
   - **Is the magnitude plausible given the literature?** If the paper estimates an elasticity of −0.3 and the literature is centered on −1.0, that is a real flag even if the regression is internally correct. Either the literature is wrong, the paper's design is identifying something different, or there is an error somewhere — the paper must engage with this.
   - **Does the paper engage with the closest existing work?** Is there a paper in `documents/` that asks essentially the same question, and does this paper cite it and explain how it differs?
   - **Does the paper contradict a known result without acknowledging it?** Flag.
   - **Is the contribution stated honestly?** "First paper to do X" claims are easy to overstate; check `documents/` for prior work.
3. **Missing seminal references.** If a referee would expect to see a particular foundational citation (e.g. for a DiD paper, the methodological refs on staggered adoption), and it is absent, flag it.

## Phase 4 — Numerical, reference, and citation consistency

Mechanical checks. Important to do but not where the paper lives or dies.

### 4a. Numerical consistency
- Every number in prose must match a table/figure value or be directly computable from reported values. Check arithmetic, percentages, ratios, logarithms, level-vs-log, rounding consistency, and units ($, pp, %, bps, thousands, millions).
- Percentage-point vs percent confusions are common — flag any.
- Significance statements ("significant at 1%") must match the reported coefficient, SE, and stars in the table. Recompute `|coef|/SE` where the claim is load-bearing.
- Cross-check the same statistic wherever it appears: abstract vs intro vs results vs conclusion vs appendix. A single number stated three ways that don't reconcile is a real issue.
- Sample sizes in the text must match N in the corresponding table.

### 4b. Internal cross-referencing
- Every empirical claim in prose must be backed by a specific table/figure (or explicitly derived from one).
- Every `Table X` / `Figure Y` reference must resolve to something that exists and says what the text claims it says.
- Flag broken or stale references (`??`, wrong number, off-by-one after reorder).

### 4c. Citations

For every citation, follow this lookup order:

1. **`documents/REFERENCES.md`** — master index. Skim first to see what is available.
2. **`documents/summaries/...`** — read the structured summary to confirm title, authors, and year. Summaries are for identification only — **do not use them to verify specific empirical claims** (effect sizes, directions, sample sizes, methods). They are intentionally condensed and can omit load-bearing nuance.
3. **`documents/extracted/...`** — read the full markdown extraction whenever you are verifying a specific claim. If there is *any* ambiguity about whether the cited paper supports the claim, read the extraction. Do not treat the summary as sufficient for claim verification.
4. **`documents/sources/`** (linked to `STORAGE_DIR/documents/`; or `documents/*.pdf` in a project without a storage folder) — read the raw PDF via `python documents/_read_pdf.py read <path>` if the extraction is missing or truncated.
5. **Missing paper — download it.** If the citation has no local summary, extraction, or PDF: (a) search the web for the paper, (b) download the PDF into `documents/sources/` (or the repo's `documents/` folder if the project has no storage folder), then (c) extract it with `python documents/_read_pdf.py read <pdf> --output documents/extracted/<filename>.md`.
6. **Web search** — if download is impossible (paywalled, not found), search the web to verify author, year, title, venue, and the specific claim.
7. **Unverifiable** — if nothing resolves it, flag as *unverifiable* and explicitly list which sources you checked.

**Post-citation pass — create missing summaries.** After completing the citation check, identify any papers that: (a) are cited in the manuscript, and (b) have a local PDF but no entry in `documents/summaries/`. For each such paper, create a summary following `documents/_summary_template.md` using the extracted text. Then run `python documents/_read_pdf.py index` to rebuild `documents/REFERENCES.md`.

What to flag:
- Citation that doesn't exist, has wrong authors/year/venue, or is misspelled.
- Claim in the paper that the cited work does not actually support (overstatement, reversal, or mischaracterization).
- Over-citation of the authors' own work or under-citation of competing work on the same question.

### 4d. Tables, figures, writing
- Table titles, notes, units, variable definitions, sample descriptions — consistent with text and internally consistent?
- Table notes correctly describe specifications, controls, FEs, and standard errors (clustered at what level)?
- Figures: axes labeled, units stated, sample stated, any smoothing/binning disclosed?
- Significance stars: thresholds stated in the notes, consistent across tables (this project's convention is `*` at 5%, `**` at 1% — flag deviations).
- Grammar, typos, broken LaTeX (`??`, missing `\%`, stray `$`), inconsistent hyphenation of key terms.
- Causal language where only correlational evidence is offered, or under-claiming where the design is clean.
- Terms of art used loosely ("statistically significant" without threshold, "robust" without specification).

## Phase 5 — What's missing

This phase is what separates a thoughtful referee report from a checklist. List the analyses the paper *should* have done but didn't. Examples:

- **Heterogeneity** the design supports but the paper doesn't report (e.g. by industry, region, cohort).
- **Placebo / falsification tests** that would discipline the identifying assumption (e.g. a placebo treatment date, an outcome that should not respond).
- **Alternative samples** (excluding outliers, restricting to balanced panel, using a different time window).
- **Alternative specifications** that would address a specific concern (e.g. if the headline uses TWFE under staggered adoption, the modern estimators).
- **Mechanisms.** If the paper claims X causes Y, what is the channel? Is there a test of the channel?
- **External validity.** Is the sample representative of where the policy implications would apply?

For each, state: what to run, why it matters, and which Phase 0 alternative explanation it would address.

## Phase 6 — Write the report

Dedupe across phases. Rank by severity. Group adjacent issues if they share a root cause.

**Save the final report to a single markdown file at the top level of the project**: `referee_report_YYYY-MM-DD.md`, using today's date. Use the Write tool. Do not save it inside `paper/` or any subdirectory. Do not just print the report to the terminal — the user needs a persistent file they can read, share, and diff against future reviews. After writing the file, print only a brief confirmation with the file path and a one-paragraph summary (≤ 120 words) of the biggest concerns. The full report lives in the file.

# Severity definitions

- **Critical**: invalidates a main result, changes the sign/significance of a headline claim, or cites a source that does not support the claim in a load-bearing way.
- **Major**: materially changes interpretation of a result, breaks identification, breaks a cross-reference that matters, or misstates a widely-known fact/citation.
- **Moderate**: wrong number that doesn't change conclusions, unclear identification language, missing robustness that a referee would request.
- **Minor**: typos, formatting, citation style, small rounding inconsistencies with no interpretive impact.

# Output format

The report file has three parts, in order.

## 1. Executive Summary (strictly ≤ 200 words)
1. One or two sentences on what the paper does and its main contribution.
2. The strongest elements of the draft.
3. The two or three most consequential concerns (Critical/Major), named specifically enough to be actionable.
4. A one-sentence bottom-line recommendation (e.g. revise-and-resubmit, minor revision, major concerns).

## 2. Substantive concerns

The 3–7 highest-level concerns from Phases 0, 2, 3, and 5. These are the things a referee at a top-5 actually pushes on. **Looser format** — these will often not have a single page reference, and that is fine:

```
### S[N]. [Short title]
**Concern:** <2–5 sentences. State the issue, why it matters for the headline result, and (if applicable) what the authors should do.>
**Relates to:** <Phase 0 alt explanation #X, or "literature placement," or "specification search," etc.>
```

## 3. Numbered issues

Issues from Phase 4 plus any from Phases 2/3/5 that have a specific location. Ordered by severity (Critical → Major → Moderate → Minor), and within each severity, ordered by page/section.

```
### [N]. [Short title] — [Severity]
**Location:** Section X.Y, p. Z (or Table N, Figure N, Appendix X).
**Snippet:** "<exact plaintext quote from the paper>"
**Issue:** <what is wrong and why it matters. For citations, state which sources you checked.>
**Suggested revision:** **<concrete edit or action the authors should take>**
```

# Ground rules

- **Do not fabricate.** If you cannot verify a number, citation, or claim, say so and list what you checked.
- **Be specific.** "Page 7" beats "in the intro." Exact quotes beat paraphrases.
- **Be conservative.** If you are unsure, flag it as a question rather than asserting it is wrong.
- **Only real problems.** Do not pad the report with things that are already correct.
- **Prioritize.** If you are running low on context, prioritize the Executive Summary and Substantive Concerns over a long tail of Minor numbered issues. A short report with the right 5 things is more useful than a long report with 50.
- **Don't second-guess the code from the paper alone.** If a concern depends on what the code actually does (e.g. "is the FE really absorbed?"), say so and recommend `/code-audit`.
- **Respect project conventions** (see `CLAUDE.md`): significance stars `*` 5% / `**` 1%.

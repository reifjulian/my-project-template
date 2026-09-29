---
category: <category>
---

<!--
  Paper summary template. Every file in documents/summaries/ should follow this
  structure. The YAML front matter above MUST be the first thing in the file —
  documents/_read_pdf.py parses it with a regex anchored at the start of the
  file, so any prose above the opening `---` makes the `category` field
  silently fall back to "Uncategorized".

  Fill in the heading and replace the placeholder body sections below. Keep the
  heading levels (## / ###) and the section order fixed. Only the FIRST `###`
  section (Research Question) feeds the auto-generated REFERENCES.md index — its
  first sentence becomes the one-line hook — so keep that opening sentence tight
  and self-contained.

  This template covers both EMPIRICAL papers (data + an identification strategy)
  and THEORY papers (a model, results stated as propositions). Several sections
  give parallel "Empirical:" and "Theory:" prompts — fill in the framing that
  fits the paper and drop the other; do not keep both labels in the final file.

  The `category` field controls how the paper is grouped in REFERENCES.md. Use a
  free-form label that fits the project (e.g., "Habit Formation", "Health
  Behavior & Incentives", "Methods"); for a theory paper use a topical label or
  simply "Theory".
-->

## <Full paper title> (<First author last name> <year>)

**Citation:** <Author(s)>. "<Title>." *<Journal/Venue>* <vol>(<issue>): <pages>, <year>.

### Research Question
2-3 sentences. What does the paper investigate, and why does it matter? For a
theory paper, state the phenomenon the model seeks to explain or the question it
answers.

### Setting / Model Environment
2-3 sentences.
- Empirical: sample size, time period, geographic/institutional context, key
  variables or treatment.
- Theory: the model environment — agents, preferences/payoffs, technology,
  information structure, and timing.

### Methods
- Empirical: identification strategy (RCT, IV, RD, DiD, structural, etc.) and
  the core empirical model(s). Note major robustness checks.
- Theory: model class, equilibrium / solution concept, key assumptions, and
  solution technique. Note major extensions.

### Findings / Main Results
- Empirical: headline results with effect sizes where available. What does the
  evidence support or reject? Note any meaningful heterogeneity.
- Theory: main propositions/theorems, comparative statics, and any testable
  predictions.

### Relevance
Connection to the current project's research questions. Specific mechanisms,
methodological lessons, or comparable papers worth noting.

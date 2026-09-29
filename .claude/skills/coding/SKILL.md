---
name: coding
description: Julian Reif's coding conventions for empirical economics research projects in Stata, Python, and R. Covers script structure, the regsave/texsave table pipeline (never estout or outreg2), figure conventions, cross-platform defaults, and the single-root layout (one $<Project> global pointing at the repo, with data/processed/results/documents-sources linked in from an external storage folder). Use whenever writing, editing, or reviewing Stata .do files, Python .py files, R scripts, run.do pipelines, regression tables, or figures.
---

# Coding conventions for Julian Reif research projects

This skill defines how to write and edit code in this project. Follow these conventions exactly when producing Stata, R, or Python scripts.

## Override hierarchy

`CLAUDE.md` in the project root takes precedence over this skill. If `CLAUDE.md` says something different, follow `CLAUDE.md`. Beyond that, this skill is authoritative.

---

## 1. Environment and globals

### Cross-platform by default
Code and scripts should run on Windows, macOS, and Linux without modification.
- Use forward slashes in all paths (`results/figures/`, not `results\figures\`).
- Avoid bash-only constructs (`&&`, `||`, `2>/dev/null`, backticks) in scripts and hooks that are shared across machines. If shell behavior must differ per OS, show both variants or move the logic into a Python/Stata script.
- Write commands for Windows by default (`python`, not `python3`); macOS/Linux substitutions are listed once under *Cross-platform notes* in `CLAUDE.md`.
- Don't rely on case-insensitive filesystems. File and folder names are lowercase with underscores or hyphens.

### File paths
- **Never hard-code paths.** In Stata, all paths reference a global macro. In Python, paths are built from `MyProject`, defined by `scripts/_config.py`; see §8. In R, `MyProject` comes from `scripts/_config.R`; see §7.
- The single project global `$MyProject` is the project root (this git repo). It is defined in the user's Stata `profile.do` (renamed per project) before `run.do` executes; never redefine it inside scripts. Python and R derive `MyProject` themselves (§7, §8). Write `$MyProject/data/...`, `$MyProject/results/...`, etc.; `data/`, `processed/`, and `results/` may be links into an external storage folder (§2), which scripts never address directly. `STORAGE_DIR` in `CLAUDE.local.md` is read only by `_setup_links.py`, never by scripts.
- Any other machine-specific path (e.g. a scratch folder on a separate drive for very large intermediates) is a `- KEY: value` line in `CLAUDE.local.md`; `_config.py` and `_config.R` expose each non-blank key as a variable of the same name, and the Stata side defines the same key as a `profile.do` global. All three must agree. See `README.md` for an example.

### `_config.do`, `_config.py`, and `_config.R`
Every Stata script begins with a preamble call to the config script:
```stata
* Preamble (unnecessary when executing run.do)
run "$MyProject/scripts/_config.do"
```
The Stata config script:
- Strips non-project ado paths and adds only `scripts/libraries/stata`
- Prints a system info block (date, Stata version, OS, etc.)
- Creates `paper/figures/` and `paper/tables/` with `cap mkdir` (`run.do` creates `scripts/logs/`)
- Starts the runtime timer and defines `_print_runtime`, which the script footer calls (§3)

`scripts/_config.py` (Python, see §8) and `scripts/_config.R` (R, see §7) are the analogs for the other two languages. All three `_config` files share the same vocabulary (`MyProject`, plus any keys in `CLAUDE.local.md`). The Python and R sides locate the project root by walking up from their own folder to the first directory containing `CLAUDE.md` or `AGENTS.md` (case-insensitive) and read `CLAUDE.local.md` there (at import and source time, respectively); the Stata side bootstraps from the `profile.do` global (since Stata can't self-locate from a script path).

### Stata command reference
When uncertain about a user-written Stata command's syntax or options (e.g., `regsave`, `texsave`, `dobatch`, `ingap`, `sortobs`), read the package's `.sthlp` help file in `scripts/libraries/stata/<package>/`. The `.ado` source file in the same folder is the ultimate authority on behavior. Do this before guessing — add-on commands change over time and training data may lag.

---

## 2. Folder structure

One root, `$MyProject` (this git repo). Code is tracked in git; data and output live in an external storage folder whose top-level subfolders `_setup_links.py` links into the repo tree (junction on Windows, symlink elsewhere), so every script addresses the project through the single global. A project without a storage folder uses the same layout with real folders.

```
run.do                          # Master script
_setup_links.py                 # Links storage-folder subfolders into the repo (once per clone)
scripts/
  _config.do                    # Stata setup (run before any other script)
  _config.py, _config.R         # Python / R analogs: define MyProject, read CLAUDE.local.md
  _install_stata_packages.do    # Install user-written packages locally
  1_*.do, 2_*.R, 3_*.py, ...    # Numbered analysis scripts (execution order)
  libraries/stata/              # Local copies of user-written Stata packages
  logs/                         # Auto-created log files (gitignored)
paper/                          # LaTeX paper
  figures/                      # Final PNG figures embedded in the paper
  tables/                       # Final .tex tables embedded in the paper
documents/                      # Reference summaries and index (tracked)
  sources/                      # Link to STORAGE_DIR/documents: raw PDFs etc. (not in git)
data/                           # Link to STORAGE_DIR/data: raw data, read-only (not in git)
processed/                      # Link to STORAGE_DIR/processed: intermediate datasets (not in git)
results/                        # Link to STORAGE_DIR/results: pipeline outputs (not in git)
  figures/                      # Generated PNG figures
  tables/                       # Generated .tex tables
  intermediate/                 # Model output not yet in final form
pyrequirements.txt              # Python dependencies
```

### Pipeline orchestration

`run.do` is the single entry point that regenerates the project end-to-end. Stata is the orchestrating language: every analysis script — whether Stata, R, or Python — must be listed in `run.do` to be part of the canonical pipeline. Side-shelling an R or Python script outside `run.do` breaks reproducibility.

Invocation primitives used inside `run.do`:

- Stata: `do "$MyProject/scripts/N_name.do"`
- R: `rscript using "$MyProject/scripts/N_name.R"` (see §7)
- Python: `python script "$MyProject/scripts/N_name.py"` (see §8)
- Parallel Stata jobs: `dobatch ...` / `dobatch_wait` (see §4)

Subroutines (filenames prefixed with `_`, e.g. `_config.do`, `_objective.R`) live in `scripts/` alongside the numbered scripts; they are called by other scripts, not directly by `run.do`.

### Other folder-structure notes

- User-written Stata packages are stored locally in `scripts/libraries/stata/` — never rely on SSC installs at runtime.
- Final output is always PNG (figures) and `.tex` (tables). Anything included in the LaTeX paper is written directly to `paper/figures/` and `paper/tables/`; all other outputs go under `results/`.

---

## 3. Script structure and style

### Scope: Stata is the default, principles generalize

Sections 3–6 are written in Stata, the project's default analysis language (Stata is also the orchestrating language; see §2 *Pipeline orchestration*). Where the guidance is a language-specific syntax detail — `log query`, `mi()`, `compress`, `regsave`/`texsave`, the `merge` command, the `graph` family — it applies only to Stata.

Where the guidance states a general principle, it applies to R and Python scripts too. Apply the principle with the equivalent idiom in those languages. Examples of principles that carry over:

- Lowercase-with-underscores naming; units recorded with each variable.
- Numbered script names that reflect pipeline execution order.
- Setting an explicit random seed whenever randomness is involved.
- Asserting data expectations (row counts, key uniqueness, no missing).
- On merges/joins that drive the analysis sample: hard-code the expected row counts so silent data drift fails loudly.
- Figure readability defaults (large fonts, big markers, axis labels on both axes, horizontal y-title, no text overlapping lines or axes, export as PNG).
- After producing a table or figure, inspect the output. For LaTeX tables, compile and check the log for `Overfull \hbox` / page-overflow warnings; iterate until clean. For figures, view the PNG once and flag obvious problems (clipped legends, illegible labels, overlapping text); leave aesthetic judgment to the user.

Language-specific conventions for R and Python live in §7 and §8.

### Header block
Every `.do` file begins with:
```stata
************
* SCRIPT: 1_myscript.do
* PURPOSE:
************
log query
if mi("`r(name)'") log using "$MyProject/scripts/logs/1_myscript.do.log", text replace

* Preamble (unnecessary when executing run.do)
run "$MyProject/scripts/_config.do"

************
* Code begins
************
```

The `log query` / `log using` pattern routes the script's own log to `scripts/logs/`. When a script is run in batch mode (e.g. `stata /e do script.do`), Stata *also* writes a `script.log` into the working directory — i.e. at the top level of `scripts/`. **Delete that top-level `scripts/*.log` artifact after the run** to keep the folder uncluttered; the canonical record lives in `scripts/logs/`. The one exception: if no corresponding log was produced under `scripts/logs/` (the top-level file is the only log of the run), keep it.

### Footer block
Every script ends with:
```stata
************
* END
************
cap noi _print_runtime, reset

** EOF

```

### Indentation
- Use **tabs** (not spaces) for indentation.
- One tab per level of nesting inside `if`, `foreach`, `forval`, `while`, etc.

### Comments
- Use `*` for full-line comments.
- Use `//` sparingly for inline/end-of-line comments; prefer `*` on its own line unless `//` makes the code noticeably clearer.
- Prefer single-line commands; don't use `///` to split a command that already fits on one line. For genuinely long commands (e.g., a multi-layer `twoway` or a `texsave` call with many options), extract option clutter into named locals to keep each line readable; `///` across the remaining plot layers or export options is then fine (see the §5 and §6 examples).
- Use `***` or `***...***` separator lines between major sections.
- Comment blocks use `***********` or `*****...` asterisk borders.
- Keep comments concise; use `label variable` with units for variable documentation.
- Document the unit of observation in the script header or in inline footnotes.

### Variable naming
- Lowercase with underscores.
- Always include units in variable labels: `label var death_rate "Deaths per million"`.
- Variables representing monetary amounts include the year in the label: `label var income "Annual income (2019 USD)"`.

### File and folder names
- Lowercase, underscores or hyphens only, no spaces, no capital letters.

### Script numbering
Scripts called by `run.do` are prefixed with a number that indicates execution order:
- Sequential steps: `1_import.do`, `2_clean.do`, `3_merge.do`, ...
- Steps that can run in parallel share the same number prefix:
  - Same number, different suffix: `1_import_pm25.do`, `1_import_wind.do`
  - Or lettered suffix: `1a_import_pm25.do`, `1b_import_wind.do`

Both forms are acceptable; use whichever reads more clearly for the specific set of parallel scripts.

### Robustness
- Include `assert` statements to validate data expectations.
- Use `isid` before sorts to confirm uniqueness. If uniqueness is uncertain, add `stable` option to sort.
- Use `set seed #` whenever random numbers are involved.
- Use `compress` before saving datasets.
- Use `fast` option on `collapse`.
- Use `mi()` instead of `==.` or `==""` for missing value checks.
- Never create globals (exceptions are in `_config.do`, `run.do`, and `profile.do`); instead, use locals and pass on their values as necessary.

### Output files are write-once
Every persisted output (dataset, figure, table, intermediate `.dta`) has a single producer and is written exactly once per pipeline run. No later script — and no later step in the same script — overwrites a file an earlier step produced; if you need two different contents, use two filenames. Raw `data/` is strictly read-only. This targets a *second writer within a run*, not the `replace` option: re-running the pipeline from the top legitimately re-creates outputs, so `save`/`graph export`/`texsave ..., replace` are correct there. When the workflow is to build something up incrementally (e.g. assembling table columns; see §5), do the accumulation in a `tempfile` — R's `tempfile()`, Python's `tempfile` module — and write the real output path only once, at the end.

### Merges
- Use `merge` instead of `joinby`, unless `joinby` makes the code significantly more elegant/shorter. When using `joinby`, specify `_merge(_merge)` and assert the expected merge codes afterward.
- Every `merge` must use an `assert()` option that lists exactly the outcomes we expect — this is the first line of defense against silent changes in data. Add a comment explaining any non-obvious match result.
```stata
merge ..., assert(match using) nogenerate keep(match)
assert _merge==3 if important_condition
```
- Prefer `keep(match)` or `keep(master match)` on the `merge` call over dropping `_merge==2` afterward.
- Pick the minimum `assert()` that passes. If all three outcomes occur, `assert(master match using)` is the minimum; if the master must always match, use `assert(match using)`.

#### Important merges: hard-code the expected counts
For merges that drive the analysis sample or are referenced in the paper, document the merge outcome with hard-coded asserts so any drift fails loudly. Skip this for trivial merges where the outcome is obvious (e.g., merging on a key we just constructed). Pattern:
```stata
// Merge in zipcode-county crosswalk.
// Of 20,324,499 master observations, 20,133,563 (99.06%) match a zip_cd in the 2010
// crosswalk; 190,936 (0.94%) are unmatched and dropped.
merge m:1 zip_cd using "data/zip_county_crosswalk2010.dta", assert(master match using)
count
assert r(N) == 20326849
count if _merge == 3
assert r(N) == 20133563

keep if _merge == 3
drop _merge
```
- Don't use `nogen` on important merges — keep `_merge` around long enough to count and assert, then drop it.
- The comment states the match rate explicitly so a reader doesn't have to do arithmetic; the asserts guarantee it stays accurate.

---

## 4. Running parallel jobs

Scripts run in parallel share the same number prefix in their filenames (see "Script numbering" in section 3). The `dobatch` command runs `.do` files as background Stata processes. Use `dobatch_wait` to wait for all background jobs to finish before proceeding. For example:

```stata
dobatch "$MyProject/scripts/4a_by_age.do" 65_69
dobatch "$MyProject/scripts/4a_by_age.do" 70_74
dobatch_wait

do "$MyProject/scripts/5_iv_make_tables.do"
```

Regression scripts that accept arguments (e.g., age group) are called with those arguments after the script path.

---

## 5. Tables

### Tool: `regsave` → manipulate → `texsave` (never `estout` or `outreg2`)

#### Standard settings (define as locals at top of make-tables scripts)
```stata
local texsave_settings      "replace autonumber nofix location(t)"
local texsave_settingsH     "replace autonumber nofix location(H)"
local main_texsave_settings : subinstr local texsave_settings "autonumber" ""
local tbl_options           "paren(stderr) asterisk(5 1) sigfig(2)"
```

- `asterisk(5 1)`: `*` at 5%, `**` at 1% — always use this threshold, not 10/5/1.
- `sigfig(2)`: two significant figures for coefficients.
- `paren(stderr)`: standard errors in parentheses (not t-stats).
- `nofix`: prevents texsave from escaping LaTeX commands already in the data.
- `autonumber`: auto-numbers columns (1), (2), ...

#### Workflow pattern
```stata
* 1. Save regression results using regsave (in estimation script)
regsave using "$MyProject/results/intermediate/myresults.dta", t p autoid addlabel(...) replace

* 2. In make-tables script: load and pivot with regsave_tbl
tempfile tbl
regsave_tbl using `tbl' if condition1, name(col1) replace `tbl_options'
regsave_tbl using `tbl' if condition2, name(col2) append  `tbl_options'
regsave_tbl using `tbl' if condition3, name(col3) append  `tbl_options' order(var1 var2 ...)

* 3. Load, clean, and format
use `tbl', clear
drop if strpos(var,"pval") | var=="reg_id"
clean_table        // call a standardized program (see below)

* 4. Export with texsave
texsave using "$MyProject/results/tables/mytable.tex", ///
    title("My table title") marker(my-label) nonames ///
    hlines(-3) footnote("`footnote'") `texsave_settings'
```
This is the canonical instance of the §3 write-once rule: columns accumulate in the `` `tbl' `` tempfile, and only the finished table is written once to the real `.tex` path.

#### `clean_table` program pattern
If there are many tables using the same variables, define a `clean_table` program at the top of make-tables scripts to standardize variable labels:
```stata
program drop _all
program clean_table, nclass
    replace var = subinstr(var,"_coef","",.)
    replace var = "" if strpos(var,"_stderr")
    replace var = "SO\(_2\), ppb"              if var=="SO2_conc"
    replace var = "First-stage \emph{F}-statistic" if var=="F_stat"
    replace var = "Sample size"                if var=="N"
    replace var = "Mean outcome"               if var=="dmean"
    replace var = "R-squared"                  if var=="r2"
    * ... add project-specific replacements
end
```

#### Standard rows always reported in regression tables
- Coefficient + stderr (asterisks for significance)
- F-statistic (`F_stat`) for IV regressions
- Mean outcome (`dmean`)
- Sample size (`N`)

#### Panel headers and spacing
```stata
ingap 1 14 14          // insert blank rows at specified positions
replace var = "A. Panel title" in 1 if mi(var)
texsave ..., bold("A." "B.")  // bold panel headers
```

#### Footnote template
Footnotes are stored as locals and built from standard components:
```stata
local fn_depvar   "The dependent variable is ..."
local fn_controls "All regressions include county-by-month and month-by-year fixed effects, along with flexible controls for maximum temperature, precipitation, humidity, and wind speed."
local fn_wt       "All regressions are weighted by county population."
local fn_stderr   "Standard errors, clustered by county, are reported in parentheses. A */** indicates significance at the 5\%/1\% level."
local footnote    "Notes: `fn_depvar' `fn_controls' `fn_wt' `fn_stderr'"
```

#### LaTeX conventions in tables
- Use `\(...\)` for math mode in strings (not `$...$` — dollar signs are Stata globals).
- Subscripts: `SO\(_2\)`, `\(\mu\)g/m\(^3\)`, `\emph{F}`-statistic.
- `hlines(-N)`: horizontal lines N rows from the bottom.
- `hlines(2)`: line after row 2.
- `nonames`: suppresses variable name row.
- `varlabels`: uses Stata variable labels as column headers.
- `headerlines2(...)` or `headerlines(...)`: custom LaTeX header rows (for multicolumn spans).
- `size(small)` or `size(scriptsize)` for wide tables.
- `landscape`: for very wide tables.

#### regsave/texsave gotchas
- **Stars come from `pval`.** `regsave_tbl` assigns asterisks from the stored `pval` column (falling back to `tstat`, then `stderr`). To base stars on an alternative p-value (e.g. a bootstrap or randomization-inference p), overwrite the `pval` column before calling `regsave_tbl`; the standard error in parentheses is unaffected.
- **`addlabel` value types.** When tagging stacked results with `addlabel(name, value)` to select them later (`regsave_tbl ... if name==…`), a numeric value creates a numeric variable — filter with `if name==1`, not `if name=="1"`.
- **`format()` hits every cell.** `format()` applies to all numeric cells, so integer counts (`N`) render with trailing decimals; `sigfig()` leaves integer-valued cells exact. For fixed decimals on coefficients but a clean integer `N`, add such summary rows by hand.
- **texsave document modes.** Avoid the `frag` option. Instead, output a standalone table — `texsave`'s default complete `\documentclass{article}` document, which compiles on its own — and a LaTeX paper whose preamble loads `\usepackage{standalone}` can still read it via `\input` (the package strips the wrapper).

---

## 6. Figures

### Readability principles
Figures should be beautiful and easy to read at paper size. Defaults:
- **Large fonts everywhere** — `size(large)` for titles and subtitles, `labsize(large)` for axis tick labels, at least `medium` for in-plot annotations (direct labels, value labels, reference-line tags). Go smaller only for dense small multiples.
- **Big markers** — `msize(medlarge)` or larger on connected/scatter plots. Hollow/stroke symbols (`X`, `+`) render smaller than filled ones at the same `msize`; give them two or three extra sizes (e.g. `vlarge`).
- **Text never overlaps lines or axes** — annotations must clear plotted series, reference lines, axes, and other labels, and each label must sit visibly closer to its own marker than to a neighbor's. View the exported PNG and nudge until clean.
- **No vertical grid lines** — pass `nogrid` to `xlabel`. Keep horizontal grid lines on the y-axis via `gstyle(default)` in `ylabel`.
- **Always label both axes** with x-axis title and y-axis title, unless the axis is obvious from context.
- **Y-axis title rendered horizontally** at the top-left of the plot via `subtitle(..., position(11) xoffset(-4) span size(large))`, not rotated 90°. Fallback (in the conventional rotated slot): `ytitle("label", axis(N) size(large) orientation(horizontal))`.
- **Default Stata scheme** — do not specify `set scheme`.

### Export format
Always export as PNG (diffable in git, unlike PDF):
```stata
graph export "$MyProject/results/figures/myname.png", as(png) replace width(3000)
```
The `width(3000)` option ensures high enough resolution for the paper.

### Standard option locals pattern
Build graph options from named locals, then combine in the `twoway` call:
```stata
local ci_shade_opts  "color(bluishgray%60) lcolor(gray%60) lwidth(vthin)"
local bin_line_opts  "lpattern(solid) msize(medlarge) mcolor(blue) lcolor(blue)"
local sine_line_opts "lpattern(dash) lcolor(red) lwidth(vthick)"
local titles    `"xtitle("Windward direction", size(large)) subtitle(PM2.5 ({&mu}g/m{sup:3}), position(11) xoffset(-4) span size(large))"'
local axis_opts `"yline(0, lpattern(solid) lcolor(black)) xlabel(0(45)360, valuelabel labsize(large) nogrid) ylabel(, labsize(large) gstyle(default))"'
local legend    `"legend(order(2 "Non-parametric fit" 3 "Sine fit") position(6) cols(2) region(lstyle(solid)) size(large))"'

twoway (rarea ci_upper ci_lower angle_NF if monitor_group == 26, `ci_shade_opts') ///
       (connected coef angle_NF if monitor_group == 26, `bin_line_opts') ///
       (line coef_sine angle_NF if monitor_group == 26, `sine_line_opts'), ///
       `legend' `titles' `axis_opts'
```
Notes on the example:
- `subtitle(..., position(11) xoffset(-4) span)` is how the y-axis title is rendered horizontally above the plot at the top-left.
- `{&mu}` and `{sup:3}` are Stata text macros for in-graph rendering. Use these in graph titles/labels — not the `\(...\)` LaTeX form, which is for `.tex` table strings.
- `nogrid` on `xlabel` removes vertical grid lines; `gstyle(default)` on `ylabel` keeps horizontal ones.
- `ci_shade_opts` is the canonical confidence-interval shading style (`rarea` with `color(bluishgray%60) lcolor(gray%60) lwidth(vthin)`).

### Colors
Standard colors used (in roughly descending frequency):
- `blue`, `red`, `green`, `black`, `navy`, `gray`, `purple`, `orange`
- With transparency: `bluishgray%30`, `bluishgray%60`, `gray%30`, `gray%60`

### Line patterns
Standard patterns used (in roughly descending frequency):
`solid`, `dash`, `shortdash`, `longdash`, `longdash_dot`, `dot`, `....._`

### Marker symbols
`circle`, `square`, `triangle`, `X`

### Legends
```stata
legend(order(2 "Series A" 3 "Series B") position(6) cols(2) region(lstyle(solid)) size(large))
```
- `position(6)`: legend at bottom
- `region(lstyle(solid))`: solid border around legend box
- `size(large)` to match axis-label font size
- Use `legend(off)` for small multiples

### Direct labels (sometimes better than a legend)
For line plots, labeling each series at its right-hand endpoint sometimes reads better than a legend. Use `legend(off)` and add a `text()` label in the series' own color just past its last point — color-matching keeps series identifiable even where lines converge. Give the labels room with `xscale(range(...))` extended past the data, and nudge the label x a hair past the final marker:
```stata
twoway ..., legend(off) xscale(range(2000 2027)) ///
    text(`yA' 2023.2 "Series A", placement(e) color(navy)  size(medium)) ///
    text(`yB' 2023.2 "Series B", placement(e) color(green) size(medium))
```
Capture each endpoint height with `summarize y if <last period>, meanonly` → `r(mean)`. For a series on a secondary axis (`yaxis(2)`), `text()` still positions on axis 1, so fix both axis ranges and map the value: `y1 = (v / axis2max) * axis1max`. Size the `xscale` extension to the *longest* label at the chosen font, and recheck the PNG for clipping whenever label text or font size changes.

### Marker value labels (coefficient plots and similar)
When printing each point's value next to its marker (`mlabel`):
- `mlabcolor(black)` — never grey — and `mlabsize(medium)` (`medsmall` if dense).
- Small `mlabgap` (e.g. `*0.8`) so each label attaches to its own point, not a neighbor's.
- A label on a point near a reference line straddles it at clock position 3 and hangs too low at 4. Blank those points' `mlabel` and place manual `text()` instead — right of the marker, at a fixed y just clear of the line (tuned against the PNG), looped so placement stays data-driven:
```stata
local txtnz ""
forval i = 1/`=_N' {
	if b[`i'] > -1 {                       // "near the zero line" threshold
		local txtnz `"`txtnz' text(-1.4 `=xpos[`i']+0.1' "`=blab[`i']'", placement(e) color(black) size(medium))"'
	}
}
replace blab = "" if b > -1
```

### Reference lines
```stata
yline(0, lpattern(solid) lcolor(black))
xline(-0.5, lpattern(dash) lcolor(gray))
```
The same direct-labeling idea applies to a vertical reference line: place its label *at the top of the line* (rather than off to the side) by adding a `text()` annotation centered on the line, with a white-filled box so the line does not strike through the text. `text()` is clipped to the plot region, so the label only fits *above* the top tick if you extend `yscale(range())` — but that lengthens the axis line. To keep the axis extent unchanged, center the label on the top tick with `placement(c)`:
```stata
text(`top' `xpos' "Event", placement(c) color(gs5) size(medium) box fcolor(white) lcolor(white) margin(vsmall))
```
where `xpos` is the line's x position and `top` is the top y-axis tick.

### Bar graphs
```stata
bar yvar xvar, lalign(inside) lwidth(none) barw(.6) color(navy)
rcap ci_upper ci_lower xvar, col(gray)
```


### Combining graphs
```stata
* Save individual graphs to tempfiles or named graphs
tempfile graph_1
graph twoway ..., saving("`graph_1'.gph", replace) legend(off) ...

graph combine "`graph_1'.gph" "`graph_2'.gph", rows(3) graphregion(fcolor(white) lcolor(none))
graph export "$MyProject/results/figures/combined.png", as(png) replace width(3000)
```
Or use `name(graph_N, replace)` and list names in `graph combine`.

---

## 7. Calling R

R scripts are called from Stata using the `rscript` command:
```stata
* In run.do: check R version and required packages
rscript, rversion(4.2.2) require(haven ncdf4 chron pracma utils parallel)
rscript, rversion(4.2.2) require(sf rmapshaper scales RColorBrewer)

* Call an R script
rscript using "$MyProject/scripts/5_iv_make_maps.R"
```
`scripts/_config.R` — the R analog of `_config.do` / `_config.py` — defines `MyProject` (the project root) and reads `CLAUDE.local.md`, so the same script runs identically under `rscript` and standalone (`Rscript scripts/foo.R`). No `args(...)` or env-var fallback is needed.

### R script conventions
- Import Stata `.dta` files via `haven::read_dta()`.

### Header block
Every R script begins with the same preamble (byte-identical across files), followed by script-specific code below the `Code begins` banner:
```r
############
# SCRIPT: scriptname.R
# PURPOSE:
############

# Preamble (identical across all R scripts)
.this_dir <- {
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[1]) else sys.frame(1)$ofile
  dirname(normalizePath(script_path, winslash = "/"))
}
source(file.path(.this_dir, "_config.R"))
.start_time <- Sys.time()

############
# Code begins
############
```
Notes on the preamble:
- The `.this_dir` block locates the script directory under both `Rscript` (which sets `--file=`) and `source()` (which sets `sys.frame(1)$ofile`), so the same preamble works in both modes.
- Sourcing `_config.R` does the work at source time: starting from `.this_dir`, it walks up to the first folder containing `CLAUDE.md` or `AGENTS.md` (case-insensitive) and assigns that path to `MyProject`, then reads `CLAUDE.local.md` from there (if present) and assigns every non-blank `- KEY: value` line as a global. Keys with blank values are skipped, so referencing an unset optional key fails loudly; guard with `exists()` if a script must handle its absence. This mirrors Python's `from _config import *`, which configures at import time. `_config.R` errors if sourced before `.this_dir` is defined.
- Build paths from `MyProject`: `file.path(MyProject, "data", ...)`. `STORAGE_DIR` is never read by scripts.

### Footer block
Every R script ends with:
```r
############
# END
############
cat(sprintf("Runtime (hours): %6.2f\n",
            as.numeric(difftime(Sys.time(), .start_time, units = "hours"))))

## EOF
```

---

## 8. Calling Python

Python scripts are called from Stata using the built-in `python script` command. Unlike `rscript`, `python script` does not accept positional arguments. `scripts/_config.py` — the Python analog of `_config.do` — defines `MyProject` (the project root) and reads `CLAUDE.local.md`, so the same script runs identically under `python script` and standalone (`python scripts/foo.py`), with no env-var fallback or `sfi` lookups needed.

### Python script conventions
- Python scripts run in the repo venv (`.venv/`; packages listed in `pyrequirements.txt`). `run.do` points Stata at it with `set python_exec`; when running a script from Stata outside `run.do`, set it manually first (never with `permanently`).
- Import Stata `.dta` files via `pandas.read_stata()`.

### Header block
Every Python script begins with the same 7-line preamble (byte-identical across files), followed by script-specific imports below the `Code begins` banner:
```python
############
# SCRIPT: scriptname.py
# PURPOSE: <one-line description>
############

"""<optional longer docstring>"""

# Preamble (identical across all Python scripts)
import sys, time
from pathlib import Path
_script = __file__ if "__file__" in dir() else sys.argv[0]
sys.path.insert(0, str(Path(_script).resolve().parent))
from _config import *  # noqa: E402,F403
_start_time = time.perf_counter()

############
# Code begins
############

# Script-specific stdlib imports (move them here, not at top)
import tempfile, zipfile  # noqa: E402

# Script-specific third-party imports (move them here, not at top)
import duckdb  # noqa: E402
import requests  # noqa: E402

# ... rest of script body ...
```
Notes on the preamble:
- `_config.py` walks up from its own folder to the first directory containing `CLAUDE.md` or `AGENTS.md` (case-insensitive), assigns that path to `MyProject`, then reads `CLAUDE.local.md` from there (if present) and assigns every non-blank `- KEY: value` line into its module namespace. The wildcard `from _config import *` pulls them all in — so adding a new key to `CLAUDE.local.md` makes it available everywhere with no script edits. Keys with blank values are skipped, so referencing an unset optional key fails loudly with a `NameError`; guard with `globals().get("KEY")` if a script must handle its absence. Build paths from `MyProject` (`MyProject + "/data/..."`); `STORAGE_DIR` is never read by scripts.
- The `__file__` or `sys.argv[0]` dance is required because Stata's `python script ...` runs the top-level script in a namespace where `__file__` is undefined; `sys.argv[0]` carries the path in both modes. Imported modules — including `_config.py` itself — always get `__file__`, so the helper uses it directly without the dance.
- The `# noqa: E402,F403` suppresses linter warnings for "import after code" (E402, caused by `sys.path.insert` above) and "wildcard import" (F403, by design).
- Move script-specific imports below the `Code begins` banner with `# noqa: E402` on each. `sys`, `time`, and `Path` are the only imports allowed above it.
- Do not use `from __future__ import annotations` — unnecessary on Python 3.10+.

### Footer block
Every Python script ends with:
```python
############
# END
############
print(f"Runtime (hours): {(time.perf_counter() - _start_time) / 3600:6.2f}")

## EOF
```

---

## 9. Output inspection and validation

After producing any output — dataset, figure, or table — inspect it before moving on. Code that runs without errors can still produce wrong results.

### Plausibility checks

For **datasets**, scan distributional properties of key variables:
```stata
sum varname, detail
assert varname >= 0        // for variables that cannot be negative
assert income < 1e9        // flag implausible upper bounds
tab year, mi               // verify expected time coverage and flag unexpected missings
```
Things to flag: negative values where impossible (counts, rates, ages), implausibly extreme outliers, unexpected missing rates, coverage gaps by year or geography. If a key variable has substantial missings, verify that the pattern is expected (e.g., a variable only measured for a subsample) rather than a sign of a bad merge or processing error.

For **figures**, open the PNG after export and verify axis scales are sensible, trends go in the expected direction, and nothing is clipped or misplotted.

For **tables**, scan the output or compiled PDF: check that signs and magnitudes on key coefficients match priors, standard errors are plausible relative to the coefficient, and sample sizes are in the expected range.

### Cross-validation against external sources

Where a published benchmark exists, compare your aggregate output against it. This catches unit errors, scaling mistakes, and merge failures that plausibility checks alone miss. Examples:

- Annual mean pollution concentrations vs. EPA published averages
- Sample size vs. administrative records or prior literature
- Aggregate deaths vs. CDC vital statistics totals

The comparison does not need to be exact — the goal is to catch order-of-magnitude discrepancies. Document the benchmark and result in a code comment so future runs can confirm the output is stable.


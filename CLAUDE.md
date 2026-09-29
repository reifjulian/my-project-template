# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

<!-- TEMPLATE USERS: Replace this with a 2–4 sentence description of the project: what it studies, who the authors are, and what data it uses. -->

Code and supporting text files are tracked in this repository, which is the project root. A single Stata global, `$MyProject`, points at it, and Python and R define a `MyProject` variable with the same path. Large or binary files — raw data, processed datasets, results, reference PDFs — can live in an external storage folder (often cloud-synced) whose top-level subfolders are linked into the repo tree by `_setup_links.py`, so scripts see `$MyProject/data/...` as ordinary paths. Projects that keep everything in the repo need none of that.

**Uses an external storage folder:** no
<!-- TEMPLATE USERS: set to "yes" if data/output live outside the repo, then follow setup step 2. -->

## First-time setup

Work through the four steps below in order. The setup covers Stata, R, and Python — skip or remove any steps for languages you won't use. Once everything is in place, you may delete this entire "First-time setup" section.

### 1. Rename the project and set the Stata global

The template ships with the placeholder name `MyProject`. Pick a name (e.g., `Pollution`, `HousingRD`). Do not search the repository for occurrences — the files that reference the placeholder are fixed and listed below. Edit **only** these eight files, replacing `MyProject` → `<YourProject>` in place:

- `run.do`
- `scripts/_config.do`
- `scripts/_config.py`
- `scripts/_config.R`
- `scripts/_install_stata_packages.do`
- `scripts/1_example.do`
- `scripts/2_example.R`
- `scripts/3_example.py`

Rename the `scripts/*_example.*` scripts themselves to something descriptive once you start writing real code.

**Do not touch any other file.** In particular, leave `.claude/skills/coding/SKILL.md` and the prose of this `CLAUDE.md` untouched; their `MyProject` examples are generic and should keep the placeholder name.

Then add one global to your Stata `profile.do`, named after the project and pointing at this repository:

```stata
global <YourProject> "/path/to/github/my-project-template"
```

`scripts/_config.do` reads this global and errors out if it is missing. Python and R do not need it: `scripts/_config.py` and `scripts/_config.R` locate the project root themselves by walking up from their own folder to the first directory containing `CLAUDE.md` or `AGENTS.md`.

### 2. Storage folder (optional)

Skip this step if all project files live in the repository. Otherwise:

1. Change the **Uses an external storage folder** line at the top of this file to `yes`.
2. Create `CLAUDE.local.md` in the repo root holding the absolute path of the storage folder. The file is gitignored, so every clone needs its own copy:

   ```markdown
   # Local machine paths

   - STORAGE_DIR: <absolute path of the storage folder>
   ```

3. Run `python _setup_links.py` from the repo root.

The link script creates one link per top-level subfolder of the storage folder, under the same name at the repo root: an NTFS junction on Windows (no admin rights needed), a symlink on macOS/Linux. The exception is `documents/`, which is a tracked repo folder, so the storage folder's `documents/` is linked to `documents/sources/` instead. Each link is recorded in this clone's `.git/info/exclude`, so `.gitignore` is untouched. The script is idempotent — rerun it whenever a new top-level folder appears in the storage folder — reports anything unexpected at a link path as an error, and never deletes or overwrites anything. `python _setup_links.py --help` lists the options, including `--dry-run`.

Scripts never read `STORAGE_DIR`; they address everything through `$MyProject` (`MyProject` in Python and R). `CLAUDE.local.md` can also hold other machine-specific keys: `scripts/_config.py` and `scripts/_config.R` turn every non-blank `- KEY: value` line into a variable, e.g. a `TMP` scratch folder on a separate drive.

**On session start, Claude Code checks the storage-folder line at the top of this file:**

- **`no`**: nothing to check. `CLAUDE.local.md` is optional and Claude never prompts for it.
- **`yes`**: `CLAUDE.local.md` must exist in the repo root with a non-blank `STORAGE_DIR`. If the file is missing or the key is blank (e.g., a fresh clone on a new machine), Claude always asks the user for the storage folder path and writes the file in the format above before doing anything else. Then Claude runs `python _setup_links.py --dry-run` and, if any links would be created, offers to run it for real.

### 3. Install Stata packages

User-written Stata packages are installed locally into `scripts/libraries/stata/`. From Stata:

```stata
do "<repo>/scripts/_install_stata_packages.do"
```

This installs the packages listed under *Stata package management* below, including `rscript`, which lets Stata call R scripts via `rscript using ...`.

### 4. Create the Python virtual environment

This step is optional unless you use the PDF reference helper in `documents/` — the packages in `pyrequirements.txt` exist only for `documents/_read_pdf.py`, and the example pipeline scripts need only the Python standard library. Each clone uses its own venv at the repo root (already gitignored):

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
.venv\Scripts\activate.bat      # Windows Command Prompt
source .venv/bin/activate       # macOS / Linux
pip install -r pyrequirements.txt
```

If PowerShell refuses to run `Activate.ps1` ("running scripts is disabled on this system"), allow locally-created scripts once with `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`, or skip activation and call the venv directly: `.venv\Scripts\python.exe -m pip install -r pyrequirements.txt`.

`run.do` points Stata's `python script` command at this venv automatically. To run a Python script from Stata outside `run.do`, set it manually first:

```stata
set python_exec "<repo>/.venv/Scripts/python.exe"   // Windows
set python_exec "<repo>/.venv/bin/python"            // macOS / Linux
```

## Repository Structure

```
run.do                          # Master pipeline entry point
_setup_links.py                 # Links storage-folder subfolders into the repo (once per clone)
_sync_template.py               # Pulls shared template files from GitHub into this repo (see "Syncing from the template")
CLAUDE.local.md                 # Machine-specific paths, e.g. STORAGE_DIR (gitignored; created per clone)
pyrequirements.txt              # Python dependencies (installed into .venv/)
scripts/
  _config.do                    # Stata setup: local ado path, system info, output folders, runtime timer
  _config.py                    # Python analog: defines MyProject, reads CLAUDE.local.md
  _config.R                     # R analog of _config.py
  _install_stata_packages.do    # Install user-written packages locally
  1_*.do, 2_*.R, 3_*.py, ...    # Numbered analysis scripts (execution order)
  libraries/stata/              # Local copies of user-written Stata packages
  logs/                         # Auto-created log files (gitignored)
paper/                          # LaTeX paper (optional; synced with Overleaf if used)
  main.tex                      # Paper source
  figures/                      # PNG figures embedded in the paper
  tables/                       # .tex tables embedded in the paper
documents/                      # Reference papers and summaries (optional)
  REFERENCES.md                 # Auto-generated master index of reference papers
  _summary_template.md          # Structure to follow when writing a summary
  _read_pdf.py                  # Helper for extracting PDFs and building the index
  summaries/                    # Structured summaries (tracked in git)
  extracted/                    # Markdown extractions of PDFs (gitignored)
  sources/                      # Link to STORAGE_DIR/documents: raw PDFs etc. (not in git)
data/                           # Link to STORAGE_DIR/data (not in git)
processed/                      # Link to STORAGE_DIR/processed (not in git)
results/                        # Link to STORAGE_DIR/results (not in git)
.claude/
  skills/coding/SKILL.md        # Authoritative coding style guide
  commands/                     # Project-specific slash commands
  settings.json                 # Permission / hook configuration
```

## Cross-platform notes

Commands and paths in this repo's docs, slash commands, and coding skill are written for Windows. On macOS/Linux, substitute:

| Windows | macOS / Linux |
|---|---|
| `python` | `python3` (if `python` is not on the PATH) |
| `.venv\Scripts\python.exe`; activate with `.venv\Scripts\Activate.ps1` | `.venv/bin/python`; activate with `source .venv/bin/activate` |
| `rmdir <link>` removes a junction | `rm <link>` removes a symlink (see *Junctions and symlinks*) |

Scripts need no such edits: `run.do` and the Python helpers select the interpreter path for the current OS themselves.

## Coding conventions

The `.claude/skills/coding/SKILL.md` file is the authoritative style guide. Claude Code considers it automatically whenever you write or edit a `.do`, `.py`, or `.R` file, so you do not need to read it manually. If anything in this `CLAUDE.md` conflicts with the skill, `CLAUDE.md` wins.

## Slash commands

Project-specific slash commands live in `.claude/commands/`:

- `/code-audit` — Read-only code audit; find bugs and verify code matches paper methods.
- `/review-paper` — Referee-style audit of the paper for numerical consistency, citations, econometrics, and writing.

## Running the pipeline (`run.do`)

`run.do` is the entry point that runs the full pipeline in order. To run interactively, open Stata and execute:

```stata
do "<path-to-repo>/run.do"
```

Scripts are numbered to indicate execution order (e.g. `1_*.do`, `2_*.R`, `3_*.py`, …). To run from a specific step onward (skipping expensive early steps), create a partial do-file that mirrors the setup in `run.do` (call `_config.do`, set `python_exec` if needed) and then runs the desired scripts.

## Python and R environment

Python dependencies are tracked in `pyrequirements.txt`. Each clone uses its own venv at `.venv/` in the repo root (gitignored). `run.do` points Stata's `python script` command at it via `set python_exec`; a partial do-file that bypasses `run.do` must do the same.

For debugging, run scripts directly from a terminal with the venv activated:

```bash
python scripts/<script_name>.py
```

`scripts/_config.py` and `scripts/_config.R` define `MyProject` (the project root); see `.claude/skills/coding/SKILL.md` §7 (R) and §8 (Python) for the script preambles.

## Stata package management

User-written packages are stored locally in `scripts/libraries/stata/` and installed via `scripts/_install_stata_packages.do`. Packages installed by default: `regsave`, `texsave`, `rscript`, `ingap`, `sortobs`. Never rely on SSC installs at runtime.

## Reference database

If `documents/` is populated, project references are organized as:

- `documents/REFERENCES.md` — Master index (tracked in git)
- `documents/summaries/` — Structured summaries mirroring the source folder layout (tracked)
- `documents/extracted/` — Full markdown extractions of the source files (gitignored)
- `documents/sources/` — Raw PDFs and other source files (link to `STORAGE_DIR/documents/`, not in git). A project without a storage folder can put PDFs directly in `documents/`; they are gitignored there too.

When looking up a reference paper, read `REFERENCES.md` first to identify relevant papers, then read the summary in `summaries/`. Only fall back to `extracted/` when you need specific details (exact quotes, table values, model specifications). If a paper is not in `REFERENCES.md`, check `extracted/` — if it appears there but has no summary, tell the user and suggest they ask Claude to summarize the missing papers.

To read or extract PDFs, use the helper script (see its `--help` for the full set of subcommands):

```bash
python documents/_read_pdf.py --help
```

## Junctions and symlinks

The links created by `_setup_links.py` are filesystem-level redirects, not shortcuts: Stata, R, Python, git, and editors all see `data/` as an ordinary folder. On Windows they are NTFS junctions (`mklink /J`), which need no admin rights; on macOS/Linux they are symlinks.

- **Removing a link** deletes only the link, never the storage folder's contents: Windows `rmdir <link>` (from `cmd`, or `cmd /c rmdir <link>` from PowerShell), macOS/Linux `rm <link>` (no `-r`). Never use `Remove-Item -Recurse` or `rm -r` on a link.
- **Git** ignores the links via `.git/info/exclude`. `git clean -fdx` removes junctions rather than deleting through them on Git for Windows ≥ 2.22.0(2), but avoid `-x` anyway (it also wipes `.venv/`), and do not set `core.fscache false`.
- **Copying the repo** (e.g., for a scratch test) follows the links into the storage folder unless the copy tool skips reparse points or symlinks. Clone with git instead.

## Syncing from the template

`python _sync_template.py` overwrites the shared template files listed in its `FILES` list with the versions from `reifjulian/my-project-template` on GitHub; files absent locally are skipped, never created. Run with `--dry-run` first, then for real, then review with `git diff` before committing. The script's docstring documents its options and behavior.

## Overleaf sync (optional)

The `paper/` directory can be linked to an Overleaf project via `git subtree`, so co-authors edit in Overleaf while the local pipeline writes tables/figures into the same folder.

### One-time setup

**1. Get an Overleaf Git token (once ever, across all projects).** In Overleaf: Profile → Account Settings → Git → generate/copy your Git token. The same token works for every project, so if you've synced an Overleaf project before you likely already have one — reuse it.

**2. Bind `paper/` to your Overleaf project.** Replace `XXX` below with your Overleaf project ID — the hash at the end of the project's Git URL (e.g. `https://git@git.overleaf.com/XXX`). Because the template ships a tracked `paper/`, you must clear it before the subtree can bind. (If you've added any repo-only files to `paper/` that don't live on Overleaf, back them up outside the repo first and restore them after the subtree is added.)

```bash
# Add the Overleaf remote (XXX = your Overleaf project ID)
git remote add overleaf-paper https://git@git.overleaf.com/XXX

# Clear the tracked paper/ so the subtree can bind
git rm -r paper
git commit -m "Clear paper/ to bind Overleaf subtree"

# Pull Overleaf's current state in as a subtree (authenticate when prompted:
#   Username: git   Password: <your Overleaf Git token>)
git subtree add --prefix=paper overleaf-paper main --squash
```

Overleaf exposes a single branch, `main` for current projects (older projects may still use `master`; check with `git ls-remote --heads overleaf-paper`).

### Ongoing sync

1. Commit local changes to `paper/` **first** (tables/figures from the pipeline) — never pull with a dirty `paper/`.
2. Pull co-author edits: `git subtree pull --prefix=paper overleaf-paper main --squash`
3. Resolve conflicts, then push: `git subtree push --prefix=paper overleaf-paper main`
4. Immediately pull again (same command as step 2). This fetches nothing and changes no files, but records the pushed state as the merge base for the next pull.

Always pull before you push. For text-only syncs from Overleaf (no local pipeline changes), step 2 alone is sufficient.

## Git commits

Never create a git commit without explicit user permission — even in auto mode. Always wait for the user to ask before committing.

Do not add `Co-authored-by` trailers or sign yourself as a coauthor in commit messages.

## Bash commands

Avoid compound or bash-only constructs (`&&`, `||`, `;`, pipes (`|`), `2>/dev/null`, backticks) in Bash tool calls and in any scripts or hooks shared across machines. Break multi-step operations into separate Bash tool calls or use built-in tools (Grep, Glob, etc.) when available. The goal is to keep each tool call simple and auditable, and to keep scripts cross-platform — not to prevent the underlying operations.

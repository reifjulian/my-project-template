# My Project Template

A template for building a large, push-button empirical analysis in Stata, R, and Python. It is designed for research projects worked on by many users across different machines and platforms (Windows, Mac, Unix), and produces an analysis that is replicable and compliant with the [AEA Data and Code Availability Policy](https://www.aeaweb.org/journals/data/data-code-policy). The template follows the principles laid out in the [Stata Coding Guide](https://julianreif.com/guide/): a single master script (`run.do`) that reproduces the entire analysis with one click, local copies of all add-on packages, automated table and figure generation, and a folder structure that keeps code on GitHub while data and output can live in an external storage folder (e.g., a shared cloud folder like Dropbox) that is linked into the repository tree, so every script addresses the project through a single root. Alternatively, users can store everything in the repository.

The template also ships with a set of [Claude Code](https://claude.com/claude-code) skills and commands: a coding style guide that is applied automatically when writing Stata, R, or Python code (`.claude/skills/coding/`), plus `/code-audit` and `/review-paper` commands for auditing the analysis and reviewing the paper.

This README assumes you have already installed [Git and GitHub](https://docs.github.com/en/get-started) and an AI coding agent such as [Claude Code](https://claude.com/claude-code). We also recommend [Visual Studio Code](https://code.visualstudio.com/) as your editor, since it integrates well with Git, Stata, R, Python, and Claude Code, though any editor will work.

## Quickstart

You will need:

1. **Stata, R, and Python** installed. (If you don't plan to use R or Python, see [Trimming the template](#trimming-the-template) below.)

2. **A Stata profile** (`profile.do`) that defines one global pointing to this repository:

   ```stata
   global MyProject "/path/to/this/repository"
   ```

   The global is renamed after your project during first-time setup (see [CLAUDE.md](CLAUDE.md)). If data and output live in an external storage folder, record its path as `STORAGE_DIR` in `CLAUDE.local.md` and run `python _setup_links.py` to link its subfolders into the repository. If you have not set up a Stata profile before, see the [Stata profile section of the guide](https://julianreif.com/guide/#stata-profile).

3. **Local Stata packages** installed into the repository. From Stata:

   ```stata
   do "<repo>/scripts/_install_stata_packages.do"
   ```

4. **A Python virtual environment** at the repository root (optional unless you use the PDF helper `documents/_read_pdf.py` — the example scripts need only the Python standard library):

   Windows:

   ```bash
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r pyrequirements.txt
   ```

   macOS / Linux:

   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r pyrequirements.txt
   ```

   Commands throughout this repository are written for Windows; on macOS/Linux, substitute `python3` for `python` where needed (see *Cross-platform notes* in [CLAUDE.md](CLAUDE.md)).

Once you are set up, running `run.do` executes a sample analysis from beginning to end, writing its tables and figures into `paper/`. The paper, `paper/main.tex`, can then be compiled using standard LaTeX tools.

Full first-time setup instructions — including renaming the project from its `MyProject` placeholder — are in [CLAUDE.md](CLAUDE.md).

**Prefer to skip the manual steps?** If you use [Claude Code](https://claude.com/claude-code), it can perform this entire setup for you — just open a session in the repository and ask it to walk you through first-time setup.

## Machine-specific paths (`CLAUDE.local.md`)

Paths that differ across machines never go in scripts. They go in `CLAUDE.local.md` at the repository root, one `- KEY: value` line per path. The file is gitignored, so each clone keeps its own copy: create it by hand, or let Claude Code create it during first-time setup. A typical file:

```markdown
# Local machine paths

- STORAGE_DIR: C:/Users/you/Dropbox/myproject
- TMP: D:/tmp
```

- `STORAGE_DIR` is the external storage folder (data, results, reference documents). It is read only by `_setup_links.py`, which links the folder's subfolders into the repository (see [CLAUDE.md](CLAUDE.md), setup step 2). Leave it out if everything lives in the repository.
- Any other key is yours to define. `scripts/_config.py` and `scripts/_config.R` turn every non-blank line into a variable of the same name, so `TMP` above becomes `TMP` in Python and R with no script edits; on the Stata side define the same key as a global in `profile.do`. Blank keys are skipped, so referencing an unset key fails loudly rather than silently pointing somewhere wrong.
- To see this in action, set `TMP` and run `scripts/2_example.R` or `scripts/3_example.py`: both print the project root and `TMP` (or `(not set)`).

## Keeping a project in sync with the template

Once a project has been created from this template, the template keeps evolving: the Claude Code skill and commands improve, the `_config.*` scripts gain features, helper scripts get fixed. `_sync_template.py` pulls those improvements into an existing project without touching anything project-specific.

The script is self-contained. Copy it into the project repository (it lives at the root of the template, so it is already there in any project created from a recent version) and run:

```bash
python _sync_template.py --dry-run    # report what would change, change nothing
python _sync_template.py              # overwrite the local copies
git diff                              # review before committing
```

How it works:

- The `FILES` list at the top of the script names the files that are standardized across projects: the Claude Code skill, commands, and `settings.json`; `.editorconfig` and `.gitattributes`; `AGENTS.md`; `_setup_links.py` and `_sync_template.py` itself; the `documents/` helpers; and `scripts/_config.do`, `_config.py`, and `_config.R`. Project-specific files such as `CLAUDE.md`, `README.md`, `run.do`, and `.gitignore` are listed but commented out. Edit the list to suit a project.
- It fetches the template's `main` branch from GitHub with your normal git credentials into a throwaway temporary folder, so the project's own `.git` is never touched. `--ref <branch|tag|sha>` selects a different version.
- A file in `FILES` that does not exist in the project is skipped, never created: if you deleted it, the project did not need it.
- The template's `MyProject` placeholder in the three `_config.*` scripts is replaced with the project's name, which the script reads from the project's `scripts/_config.do`. Pass `--project <Name>` to override.
- Each file's line-ending style is preserved, and the script processes itself last. If it reports that it updated itself, run it once more, because the new version may sync a different set of files.
- Nothing is written if the fetch fails. Every file that changed is listed as `[update]`; review those with `git diff` before committing, since local additions to standardized files such as `.claude/settings.json` are overwritten by design.

`python _sync_template.py --help` lists the options, and the script's docstring describes its behavior in full.

## Why Stata?

The project is organized around Stata: `run.do` orchestrates the entire pipeline, calling R and Python scripts as needed. Stata is the natural choice for two reasons. First, it is the tool most economists already use, so a Stata-based master script is immediately readable to co-authors, research assistants, and referees. Second, Stata has excellent reproducibility characteristics, as discussed in the [Stata Coding Guide](https://julianreif.com/guide/). Its `version` command instructs all future releases of Stata to execute code exactly as the specified version did, so results do not drift as the software is upgraded. User-written add-on packages are small, plain-text ado files that are [easily stored locally in the repository](https://julianreif.com/guide/#libraries), so the analysis never depends on the current state of an external package server, requires no internet connection to run, and works well in secure environments such as Research Data Centers (RDCs) that restrict outside access.

That said, nothing here is set in stone. If you prefer to base your analysis solely on Python or R, it is straightforward to ask an AI agent such as Claude Code to reconfigure the repository accordingly, replacing `run.do` with an equivalent master script in your language of choice.

## Further information

Detailed documentation of the repository structure, coding conventions, pipeline (`run.do`), package management, reference database, and optional Overleaf sync lives in [CLAUDE.md](CLAUDE.md). That file is written for Claude Code, but it doubles as the project manual — and the easiest way to learn how anything works is to open Claude Code in the repository and ask.

### Trimming the template

The template supports Stata, R, and Python, but nothing requires all three. If you don't plan to use R or Python, simply delete the corresponding example scripts and config files (e.g., `scripts/2_example.R` and `scripts/_config.R`, or `scripts/3_example.py`, `scripts/_config.py`, and `pyrequirements.txt`) and remove the related setup steps from `CLAUDE.md`. The Stata pipeline runs independently of both. As with setup, the easiest route is to ask Claude Code to trim the template for you.

#!/usr/bin/env python3
"""
Pull the shared template files listed in FILES below from the project template
on GitHub and overwrite this repo's copies with them.

Copy this script into a project repo that was created from the template and run
it whenever the template's shared tooling (Claude skills and commands, config
scripts, helper scripts) has improved.

Usage (from anywhere; standard library only, Python >= 3.8; needs git):
    python _sync_template.py                    # sync FILES from the template's main branch
    python _sync_template.py --dry-run          # report what would change, change nothing
    python _sync_template.py --ref v2           # a branch, tag, or full commit SHA
    python _sync_template.py --project Housing  # name that replaces MyProject (see below)

Behavior:
  - Files are fetched with `git fetch --depth 1` into a throwaway repo in a temp
    folder, using your normal git credentials (the template repo is private).
    This repo's .git is never touched.
  - A file in FILES that does not exist in this repo is skipped: the project did
    not need it. This script never creates files, only overwrites existing ones.
  - A file in FILES that is missing from the template at --ref is skipped too.
  - Files in RENAME (the config scripts) contain the template's `MyProject`
    placeholder, which each project renames (CLAUDE.md, setup step 1). The
    placeholder is replaced with this project's name, read from the local
    scripts/_config.do (or run.do), or given with --project. If the local copy
    still uses `MyProject`, nothing is renamed.
  - The local file's line-ending style is preserved (CRLF files stay CRLF).
    Binary files are copied byte for byte.
  - Status tags: [ok] identical, [update] overwritten, [dry-run] would be
    overwritten, [skip] not in this repo or not in the template, [error].
  - Exit status: 0 = synced, 1 = some [error] lines, 2 = bad input or the fetch
    failed (nothing written).
  - _sync_template.py is processed last so that it can update itself. If it
    changed, run it again: the new version may sync a different set of files.

Review every [update] with `git diff` before committing. .claude/settings.json
and scripts/_config.do are standardized across projects, so local additions to
them are overwritten by design.

This is a maintenance utility, not a pipeline script: it lives at the repo root
and does not import scripts/_config.py.
"""

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

TEMPLATE_URL = "https://github.com/reifjulian/my-project-template.git"
DEFAULT_REF = "main"
SELF = "_sync_template.py"

# Repo-relative paths (forward slashes) that are standardized across projects.
FILES = [
    ".claude/commands/code-audit.md",
    ".claude/commands/review-paper.md",
    ".claude/settings.json",
    ".claude/skills/coding/SKILL.md",
    ".editorconfig",
    ".gitattributes",
    "AGENTS.md",
    "_setup_links.py",
    "_sync_template.py",
    "documents/_read_pdf.py",
    "documents/_summary_template.md",
    "scripts/_config.do",
    "scripts/_config.py",
    "scripts/_config.R",
    # Project-specific downstream; enable deliberately and review with git diff:
    # ".gitignore", "CLAUDE.md", "README.md", "run.do",
    # "scripts/_install_stata_packages.do", "pyrequirements.txt", "paper/main.tex",
    # "scripts/1_example.do", "scripts/2_example.R", "scripts/3_example.py",
]

# Subset of FILES in which the template's `MyProject` placeholder is replaced by
# this project's name. Never add CLAUDE.md, SKILL.md, or this script: their
# MyProject text is meant to stay generic.
RENAME = {"scripts/_config.do", "scripts/_config.py", "scripts/_config.R"}
PLACEHOLDER = re.compile(rb"\bMyProject\b")
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,31}$")  # Stata global-name rules
PROJECT_DIR_LINE = re.compile(r'^\s*local\s+PROJECT_DIR\s+"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?"\s*$',
                              re.MULTILINE)

REPO = Path(__file__).resolve().parent

# Non-ASCII paths must print on Windows consoles that default to cp1252
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def report(msg, error=False):
    """Print one status line immediately; errors go to stderr."""
    print(msg, file=sys.stderr if error else sys.stdout, flush=True)


def run_git(args, cwd):
    """Run `git <args>` in cwd; stdout/stderr are captured as bytes. Exits 2 if git is missing."""
    try:
        return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True)
    except FileNotFoundError:
        report("Error: git was not found on the PATH. Install git or add it to the PATH.", error=True)
        sys.exit(2)


def stderr_text(result):
    """Decoded, stripped stderr of a completed git process."""
    return result.stderr.decode("utf-8", errors="replace").strip()


def fetch_template(url, ref, tmp):
    """Fetch `ref` of the template into a fresh repo at tmp; return the short commit SHA."""
    r = run_git(["init", "-q", str(tmp)], cwd=tmp)
    if r.returncode != 0:
        report(f"Error: could not create a temporary git repo: {stderr_text(r)}", error=True)
        sys.exit(2)
    r = run_git(["fetch", "-q", "--depth", "1", url, ref], cwd=tmp)
    if r.returncode != 0:
        report(f"Error: git fetch of '{ref}' from {url} failed:\n{stderr_text(r)}", error=True)
        sys.exit(2)
    r = run_git(["rev-parse", "--short", "FETCH_HEAD"], cwd=tmp)
    return r.stdout.decode("utf-8", errors="replace").strip() if r.returncode == 0 else "?"


def template_paths(tmp):
    """Set of every file path (forward slashes) in the fetched template commit."""
    r = run_git(["ls-tree", "-r", "--name-only", "-z", "FETCH_HEAD"], cwd=tmp)
    if r.returncode != 0:
        report(f"Error: could not list the template's files: {stderr_text(r)}", error=True)
        sys.exit(2)
    return {p for p in r.stdout.decode("utf-8", errors="replace").split("\0") if p}


def template_blob(tmp, rel):
    """Raw bytes of `rel` in the fetched template commit, or (None, message) on failure."""
    r = run_git(["cat-file", "blob", f"FETCH_HEAD:{rel}"], cwd=tmp)
    if r.returncode != 0:
        return None, stderr_text(r)
    return r.stdout, ""


def remove_tree(path):
    """Delete the temp repo. Git's pack files are read-only on Windows, so clear the bit and retry."""
    def clear_readonly(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=clear_readonly)
        else:
            shutil.rmtree(path, onerror=clear_readonly)
    except OSError as e:
        report(f"[warn] could not remove temp folder {path}: {e}", error=True)


def detect_project_name():
    """(name, source_file) from the `local PROJECT_DIR "$Name"` line in this repo, or (None, None)."""
    for rel in ("scripts/_config.do", "run.do"):
        f = REPO / rel
        if not f.is_file():
            continue
        m = PROJECT_DIR_LINE.search(f.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1), rel
    return None, None


def is_binary(data):
    return b"\0" in data


def uses_crlf(data):
    """True if every line ending in `data` is CRLF (and there is at least one)."""
    return b"\r\n" in data and data.count(b"\r\n") == data.count(b"\n")


def transform(rel, fetched, local, name):
    """Adapt the template's bytes to this repo. Returns (new_bytes, error_message)."""
    if is_binary(fetched) or is_binary(local):
        return fetched, ""
    new = fetched.replace(b"\r\n", b"\n")
    if rel in RENAME and not PLACEHOLDER.search(local) and PLACEHOLDER.search(new):
        if name is None:
            return None, "cannot determine the project name; pass --project <Name>"
        new = PLACEHOLDER.sub(name.encode("ascii"), new)
    if uses_crlf(local):
        new = new.replace(b"\n", b"\r\n")
    return new, ""


def main():
    parser = argparse.ArgumentParser(
        description="Overwrite this repo's copies of the shared template files with the "
                    "versions on GitHub. Files absent from this repo are skipped, never created.")
    parser.add_argument("--ref", default=DEFAULT_REF,
                        help=f"Template branch, tag, or full commit SHA (default: {DEFAULT_REF}).")
    parser.add_argument("--project", default=None,
                        help="Project name that replaces the template's MyProject placeholder "
                             "(default: read from scripts/_config.do or run.do).")
    parser.add_argument("--url", default=TEMPLATE_URL,
                        help="Template repo URL (default: %(default)s).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change without writing anything.")
    args = parser.parse_args()

    if not RENAME <= set(FILES):
        report(f"Error: RENAME entries missing from FILES: {sorted(RENAME - set(FILES))}", error=True)
        sys.exit(2)

    # Resolve the project name
    detected, source = detect_project_name()
    if args.project is not None:
        name = args.project.strip()
        if not NAME_PATTERN.match(name):
            report(f"Error: --project '{args.project}' is not a valid name "
                   "(letters, digits, underscore; not starting with a digit; max 32 chars).", error=True)
            sys.exit(2)
        if detected is not None and detected != name:
            report(f"[warn] --project {name} differs from ${detected} in {source}; using {name}.",
                   error=True)
        source = "--project"
    else:
        name = detected

    report(f"Repo:     {REPO}")
    report(f"Template: {args.url} @ {args.ref}")
    report(f"Project:  {name} (from {source})" if name else "Project:  (not detected)")
    if args.dry_run:
        report("(dry run: nothing will be changed)")

    n_upd = n_ok = n_skip = n_err = 0
    self_changed = False
    tmp = Path(tempfile.mkdtemp(prefix="_sync_template_"))
    try:
        sha = fetch_template(args.url, args.ref, tmp)
        report(f"Fetched:  {args.ref} @ {sha}")
        present = template_paths(tmp)

        # Process this script last so a self-update cannot affect the run in progress
        for rel in [f for f in FILES if f != SELF] + ([SELF] if SELF in FILES else []):
            local = REPO / rel
            if not local.is_file():
                report(f"[skip] {rel}: not in this repo")
                n_skip += 1
                continue
            if rel not in present:
                report(f"[skip] {rel}: not in the template at {args.ref}")
                n_skip += 1
                continue

            fetched, msg = template_blob(tmp, rel)
            if fetched is None:
                report(f"[error] {rel}: {msg}", error=True)
                n_err += 1
                continue
            try:
                local_bytes = local.read_bytes()
            except OSError as e:
                report(f"[error] {rel}: {e}", error=True)
                n_err += 1
                continue

            new, msg = transform(rel, fetched, local_bytes, name)
            if new is None:
                report(f"[error] {rel}: {msg}", error=True)
                n_err += 1
            elif new == local_bytes:
                report(f"[ok] {rel}")
                n_ok += 1
            elif args.dry_run:
                report(f"[dry-run] would update {rel}")
                n_upd += 1
                self_changed |= rel == SELF
            else:
                try:
                    local.write_bytes(new)
                except OSError as e:
                    report(f"[error] {rel}: {e}", error=True)
                    n_err += 1
                else:
                    report(f"[update] {rel}")
                    n_upd += 1
                    self_changed |= rel == SELF
    finally:
        remove_tree(tmp)

    if self_changed:
        verb = "would change" if args.dry_run else "changed"
        report(f"Note: {SELF} {verb}; run it again, since the new version may sync different files.")
    verb = "would be updated" if args.dry_run else "updated"
    report(f"Summary: {n_upd} {verb}, {n_ok} unchanged, {n_skip} skipped, {n_err} errors.")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()

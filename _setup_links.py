#!/usr/bin/env python3
"""
Link each top-level subfolder of the external storage folder (STORAGE_DIR in
CLAUDE.local.md) into this repo's root, so that Stata, R, Python, and Claude
Code see <repo>/data/... etc. as ordinary folders.

Usage (from anywhere; standard library only, Python >= 3.8):
    python _setup_links.py                       # uses STORAGE_DIR from CLAUDE.local.md
    python _setup_links.py --storage-dir <path>  # override CLAUDE.local.md
    python _setup_links.py --dry-run             # print actions, change nothing

Behavior:
  - Every directory directly inside STORAGE_DIR is linked to <repo>/<name>,
    except `documents`, which is linked to <repo>/documents/sources because
    <repo>/documents is a tracked folder (summaries, index, helper script).
  - Windows: NTFS junction (`mklink /J`, no admin rights). Elsewhere: symlink.
  - Loose files in STORAGE_DIR are reported and skipped. Names starting with
    "." are skipped silently.
  - Idempotent: an existing link to the correct target is reported as [ok].
    Anything else already at the link path (a real folder, a file, or a link
    to a different target) is reported as [error] and left untouched. This
    script never deletes or overwrites anything.
  - Each link path is added to the per-clone git exclude file
    (`git rev-parse --git-path info/exclude`), so .gitignore is unchanged.
  - Exit status: 0 = all links present, 1 = some entries reported [error],
    2 = bad input (no STORAGE_DIR, missing folder, nested layout).

To remove a link: Windows `rmdir <link>` (cmd) -- never `Remove-Item -Recurse`;
macOS/Linux `rm <link>` (no -r). Removing the link never touches STORAGE_DIR.

This is a one-time setup utility, not a pipeline script: it lives at the repo
root and reads CLAUDE.local.md itself rather than importing scripts/_config.py.
"""

import argparse
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
WINDOWS = os.name == "nt"

# Storage subfolder name -> repo-relative link path. Anything not listed links
# to the same name at the repo root.
LINK_MAP = {"documents": "documents/sources"}

# Non-ASCII paths must print on Windows consoles that default to cp1252
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def report(msg, error=False):
    """Print one status line immediately; errors go to stderr."""
    print(msg, file=sys.stderr if error else sys.stdout, flush=True)


def find_local_md():
    """Path of <repo>/CLAUDE.local.md (filename matched case-insensitively), or None."""
    return next((f for f in REPO.iterdir() if f.name.lower() == "claude.local.md"), None)


def read_local_key(local_md, key):
    """Value of the `- KEY: value` line in CLAUDE.local.md, or None if absent or blank.

    Exits with status 2 if the file cannot be decoded as UTF-8.
    """
    try:
        text = local_md.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        report(f"Error: {local_md} is not UTF-8 encoded. Re-save it as UTF-8.", error=True)
        sys.exit(2)
    for line in text.splitlines():
        m = re.match(rf"^- {key}:(.*)$", line)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def is_within(path, parent):
    """True if `path` equals `parent` or lies inside it (both resolved)."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def same_path(a, b):
    """Compare two resolved paths, ignoring case where the OS does."""
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def is_link(path):
    """True if `path` is a symlink or, on Windows, an NTFS junction."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    return WINDOWS and st.st_reparse_tag == stat.IO_REPARSE_TAG_MOUNT_POINT


def link_target(link):
    """Resolved target of a symlink or junction, or None if it cannot be read."""
    try:
        raw = os.readlink(link)
    except OSError:
        return None
    if raw.startswith("\\\\?\\"):  # junction targets carry the extended-path prefix
        raw = raw[4:]
    target = Path(raw)
    if not target.is_absolute():  # relative symlinks are relative to the link's folder
        target = Path(link).parent / target
    return target.resolve()


def create_link(link, target):
    """Create a junction (Windows) or directory symlink (elsewhere)."""
    detail = ""
    if WINDOWS:
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           capture_output=True, text=True)
        detail = (r.stderr or r.stdout).strip()
    else:
        os.symlink(target, link, target_is_directory=True)
    # Verify by inspection, not by return code
    if not is_link(link):
        raise OSError("link was not created" + (f": {detail}" if detail else ""))
    os.listdir(link)


def git_exclude_path():
    """This clone's info/exclude file (works in worktrees too), or None without git."""
    try:
        r = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"],
                           cwd=str(REPO), capture_output=True, text=True)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    p = Path(r.stdout.strip())
    return p if p.is_absolute() else REPO / p


def ensure_excluded(exclude_file, entries, dry_run):
    """Append any missing `/relpath/` lines to the git exclude file; never duplicate."""
    text = exclude_file.read_text(encoding="utf-8", errors="replace") if exclude_file.exists() else ""
    have = {line.strip() for line in text.splitlines()}
    missing = [e for e in entries if e not in have]
    if not missing:
        return
    if dry_run:
        report(f"[dry-run] would add to {exclude_file}: {' '.join(missing)}")
        return
    exclude_file.parent.mkdir(parents=True, exist_ok=True)
    with open(exclude_file, "a", encoding="utf-8", newline="\n") as fh:
        if text and not text.endswith("\n"):
            fh.write("\n")
        fh.writelines(e + "\n" for e in missing)
    for e in missing:
        report(f"[exclude] {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Link top-level subfolders of the storage folder into the repo root.")
    parser.add_argument("--storage-dir", default=None,
                        help="Storage folder (overrides STORAGE_DIR in CLAUDE.local.md).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print planned actions without changing anything.")
    args = parser.parse_args()

    # Locate and validate the storage folder
    storage_dir = (args.storage_dir or "").strip()
    if args.storage_dir is not None and not storage_dir:
        report("Error: --storage-dir was given but is blank.", error=True)
        sys.exit(2)
    if not storage_dir:
        local_md = find_local_md()
        if local_md is None:
            report(f"Error: no CLAUDE.local.md found in {REPO}. Create it with a "
                   "\"- STORAGE_DIR: <path>\" line (see CLAUDE.md, setup step 2) "
                   "or pass --storage-dir.", error=True)
            sys.exit(2)
        storage_dir = read_local_key(local_md, "STORAGE_DIR")
        if not storage_dir:
            report(f"Error: STORAGE_DIR is blank or missing in {local_md}. Add a "
                   "\"- STORAGE_DIR: <path>\" line or pass --storage-dir.", error=True)
            sys.exit(2)
    storage = Path(storage_dir.strip().strip("\"'")).expanduser()
    if not storage.is_dir():
        report(f"Error: storage folder does not exist: {storage}", error=True)
        sys.exit(2)
    storage = storage.resolve()
    if is_within(storage, REPO) or is_within(REPO, storage):
        report(f"Error: the repo ({REPO}) and the storage folder ({storage}) "
               "must not be nested inside each other.", error=True)
        sys.exit(2)

    report(f"Repo:    {REPO}")
    report(f"Storage: {storage}")
    if args.dry_run:
        report("(dry run: nothing will be changed)")

    n_new = n_ok = n_err = 0
    loose_files, linked = [], []

    for entry in sorted(storage.iterdir(), key=lambda p: p.name.lower()):
        if entry.name.startswith("."):
            continue
        if not entry.is_dir():
            loose_files.append(entry.name)
            continue

        link = REPO / LINK_MAP.get(entry.name, entry.name)
        label = link.relative_to(REPO).as_posix()

        if is_link(link):
            current = link_target(link)
            if current is not None and same_path(current, entry):
                report(f"[ok] {label}")
                n_ok += 1
                linked.append(label)
            else:
                report(f"[error] {label}: already a link to {current}, not {entry}. "
                       "Not touched.", error=True)
                n_err += 1
        elif link.exists():
            kind = "folder" if link.is_dir() else "file"
            report(f"[error] {label}: a real {kind} already exists at {link}. "
                   "Not touched.", error=True)
            n_err += 1
        elif args.dry_run:
            report(f"[dry-run] would link {label} -> {entry}")
            n_new += 1
            linked.append(label)
        else:
            try:
                link.parent.mkdir(parents=True, exist_ok=True)
                create_link(link, entry)
            except OSError as e:
                report(f"[error] {label}: {e}", error=True)
                n_err += 1
            else:
                report(f"[link] {label} -> {entry}")
                n_new += 1
                linked.append(label)

    if loose_files:
        report(f"[skip] loose files in storage folder, not linked: {', '.join(loose_files)}")

    if linked:
        entries = [f"/{label}/" for label in linked]
        exclude_file = git_exclude_path()
        if exclude_file is None:
            report("[warn] git not found; add these lines to .git/info/exclude yourself: "
                   + " ".join(entries), error=True)
        else:
            ensure_excluded(exclude_file, entries, args.dry_run)

    verb = "would be created" if args.dry_run else "created"
    report(f"Summary: {n_new} {verb}, {n_ok} already present, {n_err} errors.")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()

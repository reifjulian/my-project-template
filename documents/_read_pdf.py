#!/usr/bin/env python3
"""
Read source documents and build a reference database for use by Claude Code.

Supported formats:
    .pdf                  -> markdown (pymupdf4llm, with pymupdf fallback)
    .docx, .pptx, .xlsx   -> markdown (markitdown)
    .html, .htm           -> copied verbatim (already greppable)
    .txt, .md             -> copied verbatim

Usage:
    # Read a single source file and print its text to stdout
    python _read_pdf.py read <path>

    # Read a single source file and save the text to a file
    python _read_pdf.py read <path> --output <output_path>

    # Process all supported files and rebuild the index
    python _read_pdf.py build [--source-dir <dir>] [--extracted-dir <dir>]
                              [--summaries-dir <dir>] [--index-file <path>]
                              [--force] [--quiet]

    # Rebuild only the index from existing summaries
    python _read_pdf.py index [--summaries-dir <dir>] [--index-file <path>]

Summaries are written by Claude Code (following _summary_template.md), not by
this script; `build` reports which extracted files still lack one.

Defaults assume the following project structure, anchored to the folder that
holds this script (documents/ in the repo):
    documents/           # Tracked folder; raw PDFs inside are gitignored
        _read_pdf.py     # This script
        sources/         # Link to STORAGE_DIR/documents, created by _setup_links.py (not in git)
        extracted/       # Markdown / verbatim copies, mirrors source structure (gitignored; regenerate from sources)
        summaries/       # Structured summaries (always .md), mirrors source structure (tracked in git)
        REFERENCES.md    # Master index (tracked in git)

All default paths are derived from the script's own location, never from the
current working directory, so the script behaves identically whether it is
launched from the repo root, from documents/, or from anywhere else. Paths
passed explicitly on the command line are taken as given; relative ones
resolve against the working directory like any other command-line argument.

With no --source-dir, `build` scans the in-repo documents/ folder plus a
second root: STORAGE_DIR/documents when CLAUDE.local.md at the repo root
declares STORAGE_DIR and that folder exists, otherwise the documents/sources
link if present. Files reached through the link are skipped while scanning
documents/ itself, so each source file is processed once under the same
relative path either way. The script's own outputs (extracted/, summaries/,
REFERENCES.md) are always excluded from the scan, both at their configured
locations and at their default locations, so they can never be read back in
as sources. Passing --source-dir overrides the default roots and uses exactly
the directory given.

If <repo>/.venv exists and this script was launched by another interpreter,
it re-executes itself under the venv's Python so the extraction packages
(pymupdf4llm, markitdown) are found even from a plain `python ...` hook.

A SessionStart hook in .claude/settings.json runs `build --quiet`, so files
dropped into the source folder are processed the next time Claude Code
launches. The --quiet flag suppresses [skip] noise and turns a missing
source-dir into a silent no-op, so the hook won't error when the source
folder is offline. A no-op run takes ~150 ms; only first-time extractions
are slow.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Force UTF-8 on stdout/stderr so non-ASCII filenames (e.g. Unicode hyphens)
# don't crash the script on Windows consoles that default to cp1252.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Re-exec under the repo venv when launched by another interpreter. Membership
# is tested with sys.prefix (not interpreter paths: .venv/bin/python is a
# symlink to the base interpreter on macOS/Linux). subprocess.call rather than
# os.execv, which on Windows returns immediately and loses the child's output.
_VENV = Path(__file__).resolve().parent.parent / ".venv"
_VENV_PYTHON = _VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
if _VENV_PYTHON.exists() and Path(sys.prefix).resolve() != _VENV.resolve():
    sys.exit(subprocess.call([str(_VENV_PYTHON), *sys.argv]))

# ---------------------------------------------------------------------------
# Project layout
# ---------------------------------------------------------------------------
# Every default path is anchored to this script's own folder (documents/ in
# the repo), never to the current working directory. A working-directory
# default would send output to <cwd>/documents/extracted whenever the script
# is launched from anywhere but the repo root, and because documents/ is also
# a source root, the real extracted/ and summaries/ folders would then be read
# back in as sources and copied into the stray output tree.

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCES_LINK = HERE / "sources"        # link to STORAGE_DIR/documents (not in git)
DEFAULT_EXTRACTED_DIR = HERE / "extracted"
DEFAULT_SUMMARIES_DIR = HERE / "summaries"
DEFAULT_INDEX_FILE = HERE / "REFERENCES.md"

# ---------------------------------------------------------------------------
# Format dispatch
# ---------------------------------------------------------------------------
# Convert formats are binary / structured and get extracted to markdown.
# Copy formats are already text-readable; we copy them verbatim into
# extracted/ so a single tree holds everything Claude / grep should read.

CONVERT_EXTS = {".pdf", ".docx", ".pptx", ".xlsx"}
COPY_EXTS = {".html", ".htm", ".txt", ".md"}
SUPPORTED_EXTS = CONVERT_EXTS | COPY_EXTS


def extracted_name_for(src_path):
    """Return the output filename in extracted/ for a given source path.

    Convert formats land as .md; copy formats keep their original extension.
    """
    ext = src_path.suffix.lower()
    if ext in CONVERT_EXTS:
        return src_path.with_suffix(".md").name
    return src_path.name


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_pdf(pdf_path):
    """Extract markdown text from a single PDF.

    pymupdf4llm gives nice structured markdown for normal PDFs, but on PDFs
    where each page has both a text layer and a full-page image overlay
    (e.g. JSTOR scans), it silently drops most of the text in favor of
    "picture intentionally omitted" markers. As a fallback, we also do a
    plain pymupdf text extraction; if pymupdf4llm produced less than 30% of
    what plain extraction yields, we return the plain text instead. Plain
    text loses some markdown structure but preserves the actual content.
    """
    import pymupdf
    import pymupdf4llm
    md = pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)

    doc = pymupdf.open(str(pdf_path))
    plain = "".join(page.get_text() for page in doc)
    doc.close()

    if len(plain) > 1000 and len(md) / max(len(plain), 1) < 0.3:
        return plain
    return md


def extract_markitdown(src_path):
    """Extract markdown from a DOCX/PPTX/XLSX via markitdown."""
    from markitdown import MarkItDown
    return MarkItDown().convert(str(src_path)).text_content


def read_source_text(src_path):
    """Return text content of any supported source file.

    For convert formats this runs the appropriate extractor. For copy
    formats it just reads the file (which is already text).
    """
    ext = Path(src_path).suffix.lower()
    if ext == ".pdf":
        return extract_pdf(src_path)
    if ext in {".docx", ".pptx", ".xlsx"}:
        return extract_markitdown(src_path)
    if ext in COPY_EXTS:
        return Path(src_path).read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"unsupported file extension: {ext}")


def process_source(src_path, dest_path):
    """Materialize src into dest: convert to markdown or copy verbatim.

    Used by the build pipeline. The source extension determines behavior:
    CONVERT_EXTS (.pdf/.docx/.pptx/.xlsx) are extracted to markdown text;
    COPY_EXTS (.html/.htm/.txt/.md) are byte-for-byte copies (shutil.copy2),
    preserving encoding, line endings, and any non-ASCII content as-is.
    Extracted markdown is always written with LF line endings.
    """
    src_path = Path(src_path)
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    ext = src_path.suffix.lower()
    if ext in CONVERT_EXTS:
        dest_path.write_text(read_source_text(src_path), encoding="utf-8", newline="")
    elif ext in COPY_EXTS:
        shutil.copy2(src_path, dest_path)
    else:
        raise ValueError(f"unsupported file extension: {ext}")


def extract_and_save(src_path, output_path):
    """Read src_path's text content and write it to output_path (LF endings)."""
    text = read_source_text(src_path)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(text, encoding="utf-8", newline="")
    return text


# ---------------------------------------------------------------------------
# Manifest tracking (avoid re-processing unchanged source files)
# ---------------------------------------------------------------------------
# The manifest maps each source file's path relative to its source root to the
# SHA-256 of its contents at the time it was last processed. Keys use forward
# slashes on every OS so a manifest reads the same wherever it was written.

MANIFEST_FILENAME = ".build_manifest.json"


def file_hash(path):
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(extracted_dir):
    """Load the build manifest from the extracted directory.

    Returns {} when there is no manifest, and also when the file is unreadable
    or not valid JSON, since the only consequence is that every source is
    re-processed once. Keys written by older versions with the native path
    separator are normalized to forward slashes.
    """
    manifest_path = Path(extracted_dir) / MANIFEST_FILENAME
    if not manifest_path.exists():
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError) as e:
        print(f"  [warn] ignoring unreadable manifest {manifest_path}: {e}", file=sys.stderr)
        return {}
    if not isinstance(manifest, dict):
        print(f"  [warn] ignoring malformed manifest {manifest_path}", file=sys.stderr)
        return {}
    return {key.replace("\\", "/"): digest for key, digest in manifest.items()}


def save_manifest(extracted_dir, manifest):
    """Save the build manifest to the extracted directory (LF endings)."""
    manifest_path = Path(extracted_dir) / MANIFEST_FILENAME
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        json.dump(manifest, f, indent=2)


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def _first_sentence(text):
    """Return the first sentence of a string.

    Splits on '.', '?', or '!' followed by whitespace and a capital letter,
    so common in-sentence abbreviations like "et al.", "e.g.", "i.e.", "vs."
    don't trigger a false break.
    """
    text = text.strip()
    if not text:
        return ""
    match = re.search(r"[.?!]\s+[A-Z]", text)
    if match:
        return text[: match.start() + 1].rstrip()
    return text


def _parse_frontmatter(content):
    """Parse YAML-style front matter, returning a dict of key/value strings.

    Looks for content between the first two '---' lines. Returns {} if none.
    No external YAML library required — only handles simple key: value pairs.
    """
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip()
    return out


def _dedup_by_title(summary_files):
    """Deduplicate summary files by paper title (the first '## ' heading).

    If two files share the same heading, keeps the first in alphabetical path
    order and prints a warning to stderr for each duplicate skipped.
    """
    seen = {}
    result = []
    for sf in sorted(summary_files):
        title = None
        with open(sf, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("## "):
                    title = line.lstrip("# ").strip()
                    break
        if title is None:
            result.append(sf)
            continue
        if title in seen:
            print(f"  [warn] duplicate title — keeping {seen[title]}, "
                  f"skipping {sf}", file=sys.stderr)
        else:
            seen[title] = sf
            result.append(sf)
    return result


def build_index(summaries_dir, index_file):
    """Compile REFERENCES.md as a category-grouped, deduplicated index.

    Papers are grouped by the 'category' field in their YAML front matter and
    sorted alphabetically within each group. Papers without a category appear
    in an 'Uncategorized' section at the end. Duplicate titles (same '## '
    heading in multiple files) are collapsed to one entry with a warning.
    """
    summaries_dir = Path(summaries_dir)
    summary_files = sorted(summaries_dir.rglob("*.md"))

    summary_files = _dedup_by_title(summary_files)

    # Group by category
    groups = {}
    for sf in summary_files:
        with open(sf, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read().strip()
        category = _parse_frontmatter(content).get("category") or "Uncategorized"
        groups.setdefault(category, []).append((sf, content))

    # Sort categories alphabetically; Uncategorized goes last
    sorted_cats = sorted(k for k in groups if k != "Uncategorized")
    if "Uncategorized" in groups:
        sorted_cats.append("Uncategorized")

    n_papers = sum(len(v) for v in groups.values())
    n_named = len(sorted_cats) - (1 if "Uncategorized" in groups else 0)

    if "Uncategorized" in groups and n_named > 0:
        cat_phrase = (f"{n_named} {'category' if n_named == 1 else 'categories'}"
                      f" (plus Uncategorized)")
    elif "Uncategorized" in groups:
        cat_phrase = "0 categories"
    else:
        cat_phrase = f"{n_named} {'category' if n_named == 1 else 'categories'}"

    lines = [
        "# Reference Database",
        "",
        f"*{n_papers} papers indexed across {cat_phrase}.*",
        "",
        "This file is auto-generated by `_read_pdf.py`. "
        "Do not edit manually.",
        "",
        "---",
        "",
    ]

    for category in sorted_cats:
        entries = sorted(groups[category], key=lambda t: t[0].stem.lower())
        lines.append(f"## {category}")
        lines.append("")

        for sf, content in entries:
            rel_path = sf.relative_to(summaries_dir)

            title = sf.stem.replace("_", " ")
            for line in content.splitlines():
                if line.startswith("## "):
                    title = line.lstrip("# ").strip()
                    break

            section_lines = []
            in_section = False
            for line in content.splitlines():
                if line.startswith("### "):
                    if in_section:
                        break
                    in_section = True
                    continue
                if in_section and line.strip():
                    section_lines.append(line.strip())
            hook = _first_sentence(" ".join(section_lines))

            link_path = f"summaries/{rel_path.as_posix()}".replace(" ", "%20")
            if hook:
                lines.append(f"- [**{title}**]({link_path}) — {hook}")
            else:
                lines.append(f"- [**{title}**]({link_path})")

        lines.append("")

    # Strip trailing blank lines, then end with a single newline
    while lines and lines[-1] == "":
        lines.pop()

    Path(index_file).parent.mkdir(parents=True, exist_ok=True)
    with open(index_file, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")

    return n_papers


# ---------------------------------------------------------------------------
# Full build pipeline
# ---------------------------------------------------------------------------

def _resolve_default_sources():
    """Return the list of source folders to scan when --source-dir is omitted.

    Always includes the script's own folder (documents/ in the repo). The
    second root is STORAGE_DIR/documents when CLAUDE.local.md at the repo
    root declares STORAGE_DIR and that folder exists; otherwise the
    documents/sources link (created by _setup_links.py) when it is a
    directory, so a clone without CLAUDE.local.md still finds the files.
    """
    sources = [HERE]

    storage_docs = None
    local_md = next((f for f in HERE.parent.iterdir() if f.name.lower() == "claude.local.md"), None)
    if local_md is not None:
        for line in local_md.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            m = re.match(r"^- STORAGE_DIR:\s*(.+)$", line.strip())
            if m:
                storage_docs = Path(m.group(1).strip().strip("\"'")) / "documents"
                break
    if storage_docs is None or not storage_docs.is_dir():
        storage_docs = DEFAULT_SOURCES_LINK
    if storage_docs.is_dir() and storage_docs.resolve() != HERE:
        sources.append(storage_docs)
    return sources


def run_build(source_dirs, extracted_dir, summaries_dir, index_file, force=False, quiet=False):
    """Run the process → index pipeline. Summaries are created by Claude Code.

    source_dirs is an iterable of folders to scan; all supported files from
    all of them are processed into a single flat extracted_dir. Duplicate
    file-paths (same path relative to their respective source root) are
    detected, the first source wins, and the dup is skipped with a warning.

    With quiet=True, suppresses [skip] lines, the "Found N files" header, and
    the "papers need summaries" report; also exits silently (return, not
    sys.exit) when no listed source exists or no files are found. Designed
    for SessionStart-style hooks where an offline storage folder or no-op run
    shouldn't generate noise.
    """
    source_dirs = [Path(s) for s in source_dirs]
    extracted_dir = Path(extracted_dir)
    summaries_dir = Path(summaries_dir)

    existing = [d for d in source_dirs if d.exists()]
    if not existing:
        if quiet:
            return
        srcs = ", ".join(str(d) for d in source_dirs)
        print(f"Error: no source directories found among: {srcs}", file=sys.stderr)
        sys.exit(1)

    # Gather (source_root, file_path) for every supported file across all sources.
    # Exclude the script's own outputs wherever they live: the configured
    # extracted_dir, summaries_dir, and index_file, and also their default
    # locations under documents/. The defaults must be excluded even when the
    # caller redirects output elsewhere, because documents/ is itself a source
    # root and its extracted/ and summaries/ folders hold supported file types.
    # Also skip the documents/sources link so files in the storage folder are
    # not seen twice (once through the link, once via the storage root). The
    # link path is deliberately NOT resolved: resolving would follow it into
    # the storage folder and exclude that root's own files.
    excluded_dirs = {
        extracted_dir.resolve(), summaries_dir.resolve(),
        DEFAULT_EXTRACTED_DIR, DEFAULT_SUMMARIES_DIR, DEFAULT_SOURCES_LINK,
    }
    excluded_files = {Path(index_file).resolve(), DEFAULT_INDEX_FILE}
    candidates = []
    for src_root in existing:
        src_root_abs = src_root.resolve()
        for p in sorted(src_root_abs.rglob("*")):
            if not p.is_file():
                continue
            if any(p.is_relative_to(d) for d in excluded_dirs):
                continue
            if p.resolve() in excluded_files:
                continue
            # Skip hidden files, Office lock files (~$name.docx, present while a
            # document is open), and the summary template.
            if (p.suffix.lower() in SUPPORTED_EXTS
                and not p.name.startswith((".", "~$"))
                and p.name != "_summary_template.md"):
                candidates.append((src_root_abs, p))

    # Dedup by rel_path; first source wins.
    seen = {}
    source_files = []
    for src_root, p in candidates:
        rel = p.relative_to(src_root)
        key = rel.as_posix()
        if key in seen:
            if not quiet:
                print(f"  [warn] duplicate {rel}: keeping {seen[key]}, "
                      f"skipping {p}", file=sys.stderr)
            continue
        seen[key] = p
        source_files.append((src_root, p))

    if not source_files:
        if quiet:
            return
        srcs = ", ".join(str(d) for d in existing)
        print(f"No supported files found in: {srcs}", file=sys.stderr)
        sys.exit(1)

    extracted_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(extracted_dir) if not force else {}

    if not quiet:
        srcs = ", ".join(str(d) for d in existing)
        print(f"Found {len(source_files)} source files across: {srcs}")

    # -- Step 1: Process (extract or copy) --
    # The manifest key is the source path relative to its source root, which
    # also fixes the subfolder structure in extracted/ and summaries/. One bad
    # file (unreadable, locked, or failing to convert) is reported and skipped
    # so it cannot abort the rest of the build or the SessionStart hook.
    n_processed = 0
    n_failed = 0
    expected_extractions = set()
    for src_root, src_path in source_files:
        rel_path = src_path.relative_to(src_root)
        manifest_key = rel_path.as_posix()
        extracted_path = extracted_dir / rel_path.parent / extracted_name_for(src_path)
        expected_extractions.add(extracted_path.resolve())
        try:
            current_hash = file_hash(src_path)
            if not force and manifest.get(manifest_key) == current_hash and extracted_path.exists():
                if not quiet:
                    print(f"  [skip] {rel_path} (unchanged)")
                continue

            action = "extract" if src_path.suffix.lower() in CONVERT_EXTS else "copy"
            # [extract]/[copy] lines always print — they signal that work happened.
            print(f"  [{action}] {rel_path}")
            process_source(src_path, extracted_path)
            manifest[manifest_key] = current_hash
            save_manifest(extracted_dir, manifest)
            n_processed += 1
        except Exception as e:
            n_failed += 1
            print(f"  [error] {rel_path}: {e}", file=sys.stderr)

    save_manifest(extracted_dir, manifest)
    if not quiet or n_processed > 0 or n_failed > 0:
        print(f"Processing complete: {n_processed} new/updated, "
              f"{len(source_files) - n_processed - n_failed} unchanged, "
              f"{n_failed} failed.")

    # -- Step 2: Report orphaned extractions and files needing summaries --
    # An extraction whose source has been renamed, deleted, or is currently
    # offline is left in place (nothing is ever deleted automatically) but is
    # reported, and it is not counted as needing a summary. Summaries are
    # always .md, regardless of source extension.
    extracted_files = sorted(
        p for p in extracted_dir.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_EXTS
        and not p.name.startswith(".")
    )
    orphaned = []
    needs_summary = []
    for ext_path in extracted_files:
        rel_path = ext_path.relative_to(extracted_dir)
        if ext_path.resolve() not in expected_extractions:
            orphaned.append(rel_path.as_posix())
            continue
        summary_path = summaries_dir / rel_path.with_suffix(".md")
        if not summary_path.exists():
            needs_summary.append(rel_path.as_posix())

    if orphaned and not quiet:
        print(f"\n{len(orphaned)} extracted files have no matching source "
              f"(renamed, deleted, or offline; left in place):")
        for name in orphaned:
            print(f"  - {name}")

    if needs_summary and not quiet:
        print(f"\n{len(needs_summary)} files need summaries "
              f"(ask Claude Code to generate these):")
        for name in needs_summary:
            print(f"  - {name}")
        print(f"\nExtracted files are in: {extracted_dir}/")
        print(f"Summaries should be saved to: {summaries_dir}/")

    # -- Step 3: Index --
    n_indexed = build_index(str(summaries_dir), str(index_file))
    if not quiet:
        print(f"Index written to {index_file} ({n_indexed} entries).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Read source docs (PDF/DOCX/PPTX/XLSX/HTML/TXT/MD) and "
                    "build a reference database for Claude Code."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- read --
    p_read = subparsers.add_parser(
        "read", help="Print the text content of a single source file."
    )
    p_read.add_argument(
        "path",
        help="Path to a .pdf/.docx/.pptx/.xlsx/.html/.txt/.md file."
    )
    p_read.add_argument(
        "--output", "-o", default=None,
        help="Save text to this path instead of printing to stdout."
    )

    # -- build --
    p_build = subparsers.add_parser(
        "build", help="Process all source files and rebuild the index."
    )
    p_build.add_argument(
        "--source-dir", "--pdf-dir",
        dest="source_dir", default=None,
        help="Folder of raw source files. If omitted, scans the in-repo "
             "documents/ folder plus STORAGE_DIR/documents (when "
             "CLAUDE.local.md defines STORAGE_DIR and the folder exists), "
             "or else the documents/sources link. Passing this flag "
             "overrides the default and uses ONLY the given folder. "
             "(--pdf-dir kept as alias for compat.)"
    )
    p_build.add_argument(
        "--extracted-dir", type=Path, default=DEFAULT_EXTRACTED_DIR,
        help="Where extracted text is written (default: extracted/ next to this script)."
    )
    p_build.add_argument(
        "--summaries-dir", type=Path, default=DEFAULT_SUMMARIES_DIR,
        help="Where summaries are read from (default: summaries/ next to this script)."
    )
    p_build.add_argument(
        "--index-file", type=Path, default=DEFAULT_INDEX_FILE,
        help="Index file to write (default: REFERENCES.md next to this script)."
    )
    p_build.add_argument(
        "--force", action="store_true",
        help="Re-process all files even if unchanged."
    )
    p_build.add_argument(
        "--quiet", action="store_true",
        help="Suppress per-file [skip] logging and the summaries-needed report. "
             "Also makes a missing source-dir a silent no-op (for SessionStart hooks)."
    )

    # -- index --
    p_index = subparsers.add_parser(
        "index", help="Rebuild only the index from existing summaries."
    )
    p_index.add_argument(
        "--summaries-dir", type=Path, default=DEFAULT_SUMMARIES_DIR,
        help="Where summaries are read from (default: summaries/ next to this script)."
    )
    p_index.add_argument(
        "--index-file", type=Path, default=DEFAULT_INDEX_FILE,
        help="Index file to write (default: REFERENCES.md next to this script)."
    )

    args = parser.parse_args()

    if args.command == "read":
        if args.output:
            extract_and_save(args.path, args.output)
            print(f"Saved to {args.output}", file=sys.stderr)
        else:
            print(read_source_text(args.path))

    elif args.command == "build":
        sources = [args.source_dir] if args.source_dir else _resolve_default_sources()
        run_build(
            source_dirs=sources,
            extracted_dir=args.extracted_dir,
            summaries_dir=args.summaries_dir,
            index_file=args.index_file,
            force=args.force,
            quiet=args.quiet,
        )

    elif args.command == "index":
        n = build_index(args.summaries_dir, args.index_file)
        print(f"Index written to {args.index_file} ({n} entries).")


if __name__ == "__main__":
    main()

############
# SCRIPT: _config.py
# PURPOSE: Define the project root and read machine-specific paths from CLAUDE.local.md (optional)
############

"""
After `from _config import *` you get:

  MyProject  - the project root (this git repo), found by walking up from
               this file to the first folder containing CLAUDE.md or
               AGENTS.md (case-insensitive). Build all paths from it, e.g.
               MyProject + "/data/...". Renamed per project to match the
               Stata global of the same name.
  <any key>  - every non-blank `- KEY: value` line in CLAUDE.local.md (e.g.
               TMP). Blank keys are skipped, so an unset optional key fails
               loudly with a NameError. STORAGE_DIR is consumed only by
               _setup_links.py (and documents/_read_pdf.py), never by
               analysis scripts.

If CLAUDE.local.md is missing, only MyProject is defined; no warning.

This module is always *imported*, never run as a top-level script, so
__file__ is always defined here (Stata's `python script` omits it for the
top-level script only).

Usage in any analysis script in scripts/:
    import sys
    from pathlib import Path
    _script = __file__ if "__file__" in dir() else sys.argv[0]
    sys.path.insert(0, str(Path(_script).resolve().parent))
    from _config import *  # noqa: E402,F403
"""

import re
from pathlib import Path

_MARKERS = {"claude.md", "agents.md"}


def _has_marker(d):
    """True if directory d contains CLAUDE.md or AGENTS.md, ignoring case."""
    try:
        return any(f.is_file() and f.name.lower() in _MARKERS for f in d.iterdir())
    except OSError:
        return False


# Project root: walk up from this file to the first directory with a marker
_here = Path(__file__).resolve().parent
_root = next((p for p in [_here, *_here.parents] if _has_marker(p)), None)
if _root is None:
    raise FileNotFoundError(f"_config.py: no CLAUDE.md or AGENTS.md at or above {_here}")
MyProject = str(_root)
__all__ = ["MyProject"]

# Machine-specific keys from CLAUDE.local.md (filename matched case-insensitively)
_local_md = next((f for f in _root.iterdir() if f.name.lower() == "claude.local.md"), None)
if _local_md is not None:
    for _line in _local_md.read_text(encoding="utf-8-sig").splitlines():
        _m = re.match(r"^- ([A-Za-z_][A-Za-z0-9_]*):(.*)$", _line)
        if _m and _m.group(2).strip():
            globals()[_m.group(1)] = _m.group(2).strip()
            __all__.append(_m.group(1))

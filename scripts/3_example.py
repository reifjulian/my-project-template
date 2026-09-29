############
# SCRIPT: 3_example.py
# PURPOSE: Example Python script: prints the project root and the optional TMP key from CLAUDE.local.md
############

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

print(f"MyProject: {MyProject}")
print(f"TMP:       {globals().get('TMP', '(not set)')}")


############
# END
############
print(f"Runtime (hours): {(time.perf_counter() - _start_time) / 3600:6.2f}")

## EOF

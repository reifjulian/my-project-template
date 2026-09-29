############
# SCRIPT: _config.R
# PURPOSE: Define the project root and read machine-specific paths from CLAUDE.local.md (optional)
############

# Source this file from an analysis script after defining `.this_dir` (the
# script's own directory). At source time it assigns into the global env:
#
#   MyProject  - the project root (this git repo), found by walking up from
#                .this_dir to the first folder containing CLAUDE.md or
#                AGENTS.md (case-insensitive). Build all paths from it, e.g.
#                file.path(MyProject, "data", ...). Renamed per project to
#                match the Stata global of the same name.
#   <any key>  - every non-blank `- KEY: value` line in CLAUDE.local.md (e.g.
#                TMP). Blank keys are skipped, so an unset optional key fails
#                loudly ("object not found"). STORAGE_DIR is consumed only by
#                _setup_links.py (and documents/_read_pdf.py), never by
#                analysis scripts.
#
# If CLAUDE.local.md is missing, only MyProject is defined; no warning.
#
# Usage in any analysis script in scripts/:
#     .this_dir <- {
#       file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
#       script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[1]) else sys.frame(1)$ofile
#       dirname(normalizePath(script_path, winslash = "/"))
#     }
#     source(file.path(.this_dir, "_config.R"))

if (!exists(".this_dir")) {
  stop("_config.R must be sourced after `.this_dir` is defined.")
}

# Project root: walk up from .this_dir to the first directory with a marker file
MyProject <- local({
  has_marker <- function(d) any(tolower(list.files(d)) %in% c("claude.md", "agents.md"))
  d <- normalizePath(.this_dir, winslash = "/")
  while (!has_marker(d)) {
    if (dirname(d) == d) stop("_config.R: no CLAUDE.md or AGENTS.md at or above ", .this_dir, call. = FALSE)
    d <- dirname(d)
  }
  d
})

# Machine-specific keys from CLAUDE.local.md (filename matched case-insensitively)
local({
  files <- list.files(MyProject)
  local_md <- file.path(MyProject, files[tolower(files) == "claude.local.md"])
  if (!length(local_md)) return(invisible(NULL))

  con <- file(local_md[1], encoding = "UTF-8-BOM")
  lines <- readLines(con, warn = FALSE)
  close(con)
  for (line in lines) {
    m <- regmatches(line, regexec("^- ([A-Za-z_][A-Za-z0-9_]*):(.*)$", line))[[1]]
    if (length(m) == 3 && nzchar(trimws(m[3]))) assign(m[2], trimws(m[3]), envir = globalenv())
  }
})

############
# SCRIPT: 2_example.R
# PURPOSE: Example R script: prints the project root and the optional TMP key from CLAUDE.local.md
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

cat(sprintf("MyProject: %s\n", MyProject))
cat(sprintf("TMP:       %s\n", if (exists("TMP")) TMP else "(not set)"))


############
# END
############
cat(sprintf("Runtime (hours): %6.2f\n",
            as.numeric(difftime(Sys.time(), .start_time, units = "hours"))))

## EOF

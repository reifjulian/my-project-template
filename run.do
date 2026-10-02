************
* SCRIPT: run.do
* PURPOSE: master script that runs the whole analysis
************

*******************************************************************************
* Paper: My Paper
* Author: Julian Reif
*******************************************************************************

* PROJECT_DIR is the project root (this repo), taken from the $MyProject global set in profile.do
local PROJECT_DIR "$MyProject"

cap assert !mi("`PROJECT_DIR'")
if _rc {
	noi di as error "Error: need to define project directory in run.do"
	error 9
}

* Initialize log
clear
cap mkdir "`PROJECT_DIR'/scripts/logs"
cap log close
local datetime : di %tcCCYY.NN.DD!-HH.MM.SS `=clock("$S_DATE $S_TIME", "DMYhms")'
local logfile "`PROJECT_DIR'/scripts/logs/`datetime'.log.txt"
local memlog  "`PROJECT_DIR'/scripts/logs/`datetime'.mem.csv"
log using "`logfile'", text

* Configure Stata (local ado path, system info, runtime timer), then R and Python
run "`PROJECT_DIR'/scripts/_config.do" timer(run)
rscript, rversion(4)
if c(os) == "Windows" set python_exec "`PROJECT_DIR'/.venv/Scripts/python.exe"
else                  set python_exec "`PROJECT_DIR'/.venv/bin/python"

* Record the memory usage of Stata and its child processes (requires python, see _config.do and _print_peak_memory below)
*_start_memory_monitor, log("`memlog'")

************
* Run project analysis
************

do "`PROJECT_DIR'/scripts/1_example.do"
rscript using "`PROJECT_DIR'/scripts/2_example.R"
python script "`PROJECT_DIR'/scripts/3_example.py"

************
* End: close log
************

di "End date and time: $S_DATE $S_TIME"
cap noi _print_runtime, timer(run)
*cap noi _print_peak_memory, log("`memlog'") kill
cap log close

**EOF

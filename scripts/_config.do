************
* SCRIPT: _config.do
* PURPOSE: Restrict Stata to the project's local ado libraries, print system info,
*          create output folders, and define the runtime timer (_print_runtime)
************

* PROJECT_DIR is the project root (this repo), taken from the $MyProject global set in profile.do
local PROJECT_DIR "$MyProject"

cap assert !mi("`PROJECT_DIR'")
if _rc {
	noi di as error "Error: need to define project directory in scripts/_config.do"
	error 9
}

* Ensure Stata uses only local libraries
tokenize `"$S_ADO"', parse(";")
while `"`1'"' != "" {
  if `"`1'"'!="BASE" cap adopath - `"`1'"'
  macro shift
}
adopath ++ "`PROJECT_DIR'/scripts/libraries/stata"
mata: mata mlib index

* Display system parameters and record the date and time
tempname print_timestamp
cap program drop `print_timestamp'
program define `print_timestamp'
	di as text "{hline `=min(79, c(linesize))'}"

	di as text "Date and time: " as result "$S_DATE $S_TIME"
	di as text "Stata version: " as result "`c(stata_version)'"
	di as text "Updated as of: " as result "`c(born_date)'"
	di as text "Variant:       " as result "`=cond( c(MP),"MP",cond(c(SE),"SE",c(flavor)) )'"
	di as text "Processors:    " as result "`c(processors)'"
	di as text "OS:            " as result "`c(os)' `c(osdtl)'"
	di as text "Machine type:  " as result "`c(machine_type)'"
	local hostname : env HOSTNAME
	if !mi("`hostname'") di as text "Hostname:      " as result "`hostname'"

	di as text "{hline `=min(79, c(linesize))'}"
end
noi `print_timestamp'

************
* Additional code you want automatically executed
************
* Uncomment to pin the Stata version used for interpreting commands
*version 19.5
set varabbrev off
set more off
cap mkdir "`PROJECT_DIR'/paper/figures"
cap mkdir "`PROJECT_DIR'/paper/tables"

* Runtime calculator (time elapsed since first call to _config.do)
local 0 ", `0'"
syntax, [timer(name)]
if mi("${START__TIME__CONFIG`timer'}") global START__TIME__CONFIG`timer' = clock(c(current_date) + " " + c(current_time), "DMY hms")

cap program drop _print_runtime
program define _print_runtime
	syntax, [timer(name) reset]
	
	local now = clock(c(current_date) + " " + c(current_time), "DMY hms")
	local runtime = (`now' - ${START__TIME__CONFIG`timer'}) / 1000 / 3600
	cap noi display as text "Runtime (hours): " as result %6.2f `runtime'
	
	if !mi("`reset'") macro drop START__TIME__CONFIG`timer'
end

************
* Memory monitor (optional; nothing runs unless run.do calls _start_memory_monitor)
************
* _start_memory_monitor samples the memory of this Stata process and all its child processes every `interval' seconds
*    - writes a CSV trace to `log'
*    - call it from run.do after `set python_exec`
* _print_peak_memory reports the peak at the end of the run; its kill option also stops the monitor,
*    which otherwise keeps sampling until Stata exits
cap program drop _start_memory_monitor
program define _start_memory_monitor
	syntax, log(string) [interval(real 10)]

	local pyexec = c(python_exec)
	if mi("`pyexec'") {
		di as error "_start_memory_monitor: set python_exec to a venv with psrecord installed before calling"
		exit 198
	}
	cap python: import psrecord
	if _rc {
		di as error "_start_memory_monitor: psrecord not found in `pyexec' (pip install psrecord)"
		exit 198
	}

	python: import os, subprocess
	python: from sfi import Macro
	python: cmd = [Macro.getLocal("pyexec"), "-c", "from psrecord.main import main; main()", str(os.getpid()), ///
		"--include-children", "--interval", Macro.getLocal("interval"), "--log-format", "csv", "--log", Macro.getLocal("log")]
	python: kw = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
	python: monitor = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, **kw)

	di as text "Memory monitor started (sampling every " as result "`interval'" as text " seconds)"
	di as text "log: " as result "`log'"
end

* Report peak memory from the trace written by _start_memory_monitor 
*  - psrecord flushes after every sample, so the file is readable while the monitor is still running
*  - psrecord reports MiB; the peak is reported in GiB (1024^3 bytes)
cap program drop _print_peak_memory
program define _print_peak_memory
	syntax, log(string) [kill]

	tempname mem
	frame create `mem'
	frame `mem' {
		qui import delimited using "`log'", varnames(1) clear
		qui sum mem_real, meanonly
		local peak_gb = r(max) / 1024
		local samples = r(N)
		qui sum elapsed_time, meanonly
		local minutes = r(max) / 60
	}
	frame drop `mem'

	di as text "Peak memory (GiB), Stata and child processes: " as result %4.2f `peak_gb'
	di as text "  (" as result "`samples'" as text " samples over " as result %3.1f `minutes' as text " minutes)"

	* Stop the monitor by killing every process whose command line names this trace file
	if !mi("`kill'") {
		python: import psutil
		python: from sfi import Macro
		python: procs = [p for p in psutil.process_iter(["cmdline"]) if p.info["cmdline"] and Macro.getLocal("log") in p.info["cmdline"]]
		python: killed = [p.kill() for p in procs if p.is_running()]
		python: Macro.setLocal("nkilled", str(len(procs)))
		di as text "Memory monitor stopped (" as result "`nkilled'" as text " processes killed)"
	}
end

** EOF

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
	di "{hline `=min(79, c(linesize))'}"

	di "Date and time: $S_DATE $S_TIME"
	di "Stata version: `c(stata_version)'"
	di "Updated as of: `c(born_date)'"
	di "Variant:       `=cond( c(MP),"MP",cond(c(SE),"SE",c(flavor)) )'"
	di "Processors:    `c(processors)'"
	di "OS:            `c(os)' `c(osdtl)'"
	di "Machine type:  `c(machine_type)'"
	local hostname : env HOSTNAME
	if !mi("`hostname'") di "Hostname:      `hostname'"
	
	di "{hline `=min(79, c(linesize))'}"
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

** EOF

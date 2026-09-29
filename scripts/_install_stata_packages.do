************
* SCRIPT: _install_stata_packages.do
* PURPOSE: Install user-written Stata packages into scripts/libraries/stata.
*          For a fresh install, delete that folder and rerun this script.
************

* PROJECT_DIR is the project root (this repo), taken from the $MyProject global set in profile.do
local PROJECT_DIR "$MyProject"

cap assert !mi("`PROJECT_DIR'")
if _rc {
	noi di as error "Error: need to define project directory in scripts/_install_stata_packages.do"
	error 9
}

* Create and define a local installation directory for the packages
cap mkdir "`PROJECT_DIR'/scripts/libraries"
cap mkdir "`PROJECT_DIR'/scripts/libraries/stata"
net set ado "`PROJECT_DIR'/scripts/libraries/stata"

* Install the latest development version of each package from GitHub
foreach p in regsave texsave rscript {
	net install `p', from("https://raw.githubusercontent.com/reifjulian/`p'/master") replace
}

* Install packages from SSC
foreach p in ingap sortobs {
	local ltr = substr(`"`p'"',1,1)
	qui net from "http://fmwww.bc.edu/repec/bocode/`ltr'"
	net install `p', replace
}

** EOF

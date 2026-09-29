************
* SCRIPT: 1_example.do
* PURPOSE: Example Stata script: a histogram and a regression table from Stata's auto dataset
************
log query
if mi("`r(name)'") log using "$MyProject/scripts/logs/1_example.do.log", text replace

* Preamble (unnecessary when executing run.do)
run "$MyProject/scripts/_config.do"

************
* Code begins
************


********************************
* Price histogram              *
********************************

sysuse auto, clear
format price %12.0fc

local bar_opts  "fcolor(navy) lcolor(navy)"
local titles    `"xtitle("Price (1978 dollars)", size(large)) subtitle("Frequency", position(11) xoffset(-4) span size(large))"'
local axis_opts `"xlabel(, labsize(large) nogrid) ylabel(, labsize(large) gstyle(default))"'

histogram price, frequency ytitle("") `bar_opts' `titles' `axis_opts'
graph export "$MyProject/paper/figures/price_histogram.png", as(png) replace width(2000)


* Estimate regressions
tempfile results
sysuse auto, clear
foreach rhs in "mpg" "mpg weight" {
	
	* Domestic cars
	reg price `rhs' if foreign=="Domestic":origin, robust
	regsave using "`results'", t p autoid `replace' addlabel(rhs,"`rhs'",origin,Domestic) 
	local replace append
	
	* Foreign cars
	reg price `rhs' if foreign=="Foreign":origin, robust
	regsave using "`results'", t p autoid append addlabel(rhs,"`rhs'",origin,"Foreign") 
}


***************************
* Create regression table *
***************************
tempfile my_table
use "`results'"

* Merge together the four regressions into one table
local run_no = 1
local replace replace
foreach orig in "Domestic" "Foreign" {
	foreach rhs in "mpg" "mpg weight" {
		
		regsave_tbl using "`my_table'" if origin=="`orig'" & rhs=="`rhs'", name(col`run_no') asterisk(5 1) parentheses(stderr) sigfig(3) `replace'
		
		local run_no = `run_no'+1
		local replace append
	}
}

* Format the table
use "`my_table'", clear
drop if inlist(var,"_id","rhs","origin") | strpos(var,"_cons") | strpos(var,"tstat") | strpos(var,"pval")

* texsave will output these labels as column headers
label var col1 "Spec 1"
label var col2 "Spec 2"
label var col3 "Spec 1"
label var col4 "Spec 2"

* Display R^2 in LaTeX math mode
replace var = "\(R^2\)" if var=="r2"

* Clean variable names
replace var = subinstr(var,"_coef","",1)
replace var = "" if strpos(var,"_stderr")
replace var = "Miles per gallon" if var=="mpg"
replace var = "Weight (pounds)" if var=="weight"
replace var = "Price (1978 dollars)" if var=="price"

local title "Association between automobile price and fuel efficiency"
local headerlines "& \multicolumn{2}{c}{Domestic cars} & \multicolumn{2}{c}{Foreign cars} " "\cmidrule(lr){2-3} \cmidrule(lr){4-5}"
local fn "Notes: Outcome variable is price (1978 dollars). Columns (1) and (2) report estimates of \(\beta\) from equation (\ref{eqn:model}) for domestic automobiles. Columns (3) and (4) report estimates for foreign automobiles. Robust standard errors are reported in parentheses. A */** indicates significance at the 5\%/1\% level."
texsave using "$MyProject/paper/tables/my_regressions.tex", autonumber varlabels hlines(-2) nofix replace marker(tab:my_regressions) title("`title'") headerlines("`headerlines'") footnote("`fn'")



************
* END
************
cap noi _print_runtime, reset

** EOF

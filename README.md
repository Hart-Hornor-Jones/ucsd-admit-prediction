# Predicting UC San Diego admission rates from public school data

A UC San Diego–only adaptation of the "Predicting UC admission rates from public school data" page
(hart-hornor-jones.github.io/uc_admissions_predictor). Open `index.html` in a browser; it is self-contained.

## What changed from the original page
- Same look as the original page (house web style, not the Leal format).
- One campus (UC San Diego), three periods: entering classes 2015–17, 2018–21 and 2022–25. The two charts default to 2018–21 (left) and 2022–25 (right).
- **Fit model to**: by default the model is estimated on schools outside San Diego and Imperial counties and then applied to the schools inside them, so their actual-minus-predicted values are out-of-sample. "All schools" lets you add a San Diego/Imperial indicator, or five group indicators, as variables.
- Schools in San Diego and Imperial counties are colored by group: Sweetwater Union HSD; San Diego Unified; Imperial County; Poway, San Dieguito and Carlsbad; other San Diego County.
- New table: actual minus predicted admission rate by group, with standard errors and implied admits above prediction.
- **Model**: linear (weighted least squares, as before) or logistic (quasi-binomial; predictions stay between 0 and 100%).
- **View**: actual against predicted, or actual minus predicted against distance to campus.
- Indicator variables (charter, LCFF+, local groups) are left as 0/1, so their coefficients read as differences.
- LCFF+ is defined as UPP above 75% (the corrected rule).
- New variables: GPA curvature, UC San Diego applicants' GPA relative to all UC applicants, UC San Diego share of the school's UC applications, applicants per 100 A–G completers, admission rate at the other UC campuses.
- School search, per-chart export (PNG 2×/4×, SVG, CSV of plotted schools).

## Files
- `index.html` — the page (data and d3 embedded); it loads nothing from the network.
- `data/school_era_rows.csv` — one row per school and period, with the applicant and admit counts, the admission rate, the group code and all 28 predictors (data dictionary below).
- `data/ucsd_local_data.json` — the same rows, rounded, in the compact form embedded in the page (structure below).
- `build/build_data.py` — builds both data files from `UCSD Lott Update 2026-08-12/ucsd_lott_panel_2015_2025.csv`, `UCSD Local Preference 2026-09-29/panel_ucsd_local_with_covariates.csv` and `ucsd-local-preference/data/schools.csv` (run from `build/`; the default root is the Svetlana folder two levels up). Those three inputs are not in this repository, so the data files cannot be rebuilt from the repository alone.
- `build/page_src.html` + `build/d3.v7.min.js` (d3 version 7.9.0) + `build/assemble.py` — page template, the d3 library and the script that embeds d3 and the data into `index.html`.
- `tests/check_data.py` — integrity checks on the data files, the embedded copy and this README (standard library + pandas).
- `tests/render_check.py` — opens `index.html` in headless Chromium with Playwright, exercises every control and fails on any console error, page error or failed request.
- `.github/workflows/checks.yml` — runs both checks on every push and pull request.
- `LICENSE` — MIT; the data files derive from public records of the California Department of Education and the University of California.

Rebuild: `cd build && python build_data.py && python assemble.py` (`assemble.py` alone regenerates `index.html` from the committed template and data).

Checks: `python tests/check_data.py` and, after `pip install playwright` and `python -m playwright install chromium`, `python tests/render_check.py`.

## Data dictionary

### `data/school_era_rows.csv`
One row per school and period: 2,772 rows, 36 columns, UTF-8, comma-separated, with a header row. The key is (`ceeb`, `era`); 1,063 distinct schools appear. Read `ceeb` as text: the codes are zero-padded to six digits (for example `050003`) and are mangled if read as numbers. Blank cells mean the value could not be computed for that school and period. A school is included in a period when it has at least 30 UC San Diego applicants in years with published admit counts and those years hold at least half of its applicants.

| Period code (`era`) | Entering classes | Rows |
|---|---|---|
| `base` | fall 2015–17 | 822 |
| `surge` | fall 2018–21 | 917 |
| `recent` | fall 2022–25 | 1,033 |

Group codes (`grp`): 0 Sweetwater Union High School District; 1 San Diego Unified School District; 2 Imperial County; 3 Poway, San Dieguito and Carlsbad districts; 4 other San Diego County schools; 5 rest of California. The five local groups hold 87, 100 and 96 rows in the three periods.

Unless noted, a predictor is the mean of the school's yearly values over the years of the period, and percentages run from 0 to 100.

| Column | Description | Units / values |
|---|---|---|
| `name` | School name (title case, "High School" shortened to "High", at most 40 characters), from the last year of the period | text |
| `city` | City (at most 20 characters) | text |
| `ceeb` | College Board (CEEB) school code, zero-padded to six digits; three rows carry seven-digit codes | text |
| `A` | UC San Diego freshman applicants, summed over the years of the period in which both the applicant and admit counts are published | count, at least 30 |
| `adm` | Admission rate, 100 × `K` / `A` (unrounded here; two decimals in the JSON) | percent |
| `K` | UC San Diego admits in those years | count |
| `grp` | Group code, see above | 0–5 |
| `ela` | CAASPP English language arts, share of grade-11 students meeting the standard | percent |
| `math` | CAASPP mathematics, share of grade-11 students meeting the standard | percent |
| `agcomp` | A–G completion: completers divided by the graduating cohort, both summed over the period | percent |
| `upp` | Unduplicated pupil percentage (low-income, English learner or foster youth) | percent |
| `sed` | Socioeconomically disadvantaged students | percent |
| `el` | English learners | percent |
| `lcffd` | LCFF+ flag: 1 if `upp` is above 75, else 0; blank when `upp` is blank | 0/1 |
| `s_hisp` | Hispanic/Latino share of grade 9–12 enrollment | percent |
| `s_white` | White share of grade 9–12 enrollment | percent |
| `s_asian` | Asian or Filipino share of grade 9–12 enrollment | percent |
| `s_black` | Black share of grade 9–12 enrollment (the four shares do not sum to 100; other groups are omitted) | percent |
| `charter` | Charter school | 0/1 |
| `inc` | Census tract median household income (ACS 5-year) | thousands of dollars |
| `ba` | Census tract adults with a bachelor's degree | percent |
| `pov` | Census tract poverty rate | percent |
| `homeval` | Census tract median home value | thousands of dollars |
| `appgpa` | Mean UC-calculated GPA of the school's UC San Diego applicants, weighted by applicants | GPA points |
| `gpa_gap` | `appgpa` minus the mean GPA of the school's applicants to any UC campus | GPA points |
| `apprate` | UC San Diego applicants per 100 A–G completers; exceeds 100 for eight rows where the completer count is very small (maximum 1,250) | ratio |
| `ucsd_share` | UC San Diego applicants as a share of the school's applicants to any UC campus | percent |
| `logA` | log₁₀ of mean applicants per year over all years of the period, including years with masked admit counts | log₁₀ applicants |
| `H` | Enrollment, grades 9–12 | students |
| `oth_rate` | Admission rate at the other UC campuses: admits divided by applications, summed over the period | percent |
| `o_grad6` | Past 6-year UC graduation rate of the school's students (entering 2004–10); blank for 12–22% of rows by period | percent |
| `o_yield` | Past yield at UC San Diego: enrollees divided by admits in the five years before the period (2010–14, 2013–17, 2017–21), when at least 15 admits are published; blank for about half the rows | percent |
| `dist` | log₁₀ of straight-line distance to the campus in km, floored at 1 km (0 = on campus; 2 = 100 km) | log₁₀ km |
| `infl` | Pool-GPA inflation: rise in the school's applicant-pool GPA from 2016 to 2025 beyond what its change in CAASPP results predicts; blank for 3–11% of rows by period | GPA points |
| `era` | Period code | `base`, `surge`, `recent` |
| `local` | San Diego or Imperial County school: 1 if `grp` is 0–4, else 0 | 0/1 |

### `data/ucsd_local_data.json`
The same 2,772 rows as the CSV in the form the page reads (also embedded verbatim in `index.html` inside `<script id="pagedata">`). One JSON object with five keys:
- `cols` — the 35 column names of each row: the seven identifying columns `name`, `city`, `ceeb`, `A`, `adm`, `K`, `grp`, followed by `vars`. There is no `era` column; the period is the key in `cells`. The last three columns are ordered `infl`, `local`, `dist`, unlike the CSV.
- `vars` — the 28 predictor names, in the order the page uses.
- `cells` — `{"base": [...], "surge": [...], "recent": [...]}`, each a list of rows, each row a list of values in `cols` order; `null` where the CSV is blank.
- `eras` — period code to label (`2015–17`, `2018–21`, `2022–25`, with an en dash).
- `groups` — the six group names, indexed by `grp`.

Values are rounded: `adm` to 2 decimals; `appgpa`, `gpa_gap`, `logA`, `dist`, `infl` to 3; `lcffd`, `local`, `charter`, `H`, `homeval` to 0; every other predictor to 1 decimal. Counts and codes are integers. Use the CSV for unrounded values.

## License
MIT, see `LICENSE`. The data files derive from public records of the California Department of Education and the University of California.

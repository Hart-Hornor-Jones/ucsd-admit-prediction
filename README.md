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
- `index.html` — the page (data and d3 embedded).
- `data/school_era_rows.csv` — one row per school and period: applicants and admits in visible years, all predictors, group code (0–4 local groups, 5 rest of California).
- `data/ucsd_local_data.json` — the same rows as embedded in the page.
- `build/build_data.py` — builds the data from `UCSD Lott Update 2026-08-12/ucsd_lott_panel_2015_2025.csv`, `UCSD Local Preference 2026-09-29/panel_ucsd_local_with_covariates.csv` and `ucsd-local-preference/data/schools.csv` (run from `build/`; the default root is the Svetlana folder two levels up).
- `build/page_src.html` + `build/assemble.py` — page template and the script that embeds d3 and the data into `index.html`.

Rebuild: `cd build && python build_data.py && python assemble.py`

"""Integrity checks for the data files behind index.html.

Standard library + pandas only.  Run from anywhere:  python tests/check_data.py
Exit status 0 when every check passes, 1 otherwise.  Every file is opened with
encoding='utf-8' so the script behaves the same on Windows, macOS and Linux.

What is checked
  data/school_era_rows.csv   columns, row counts per period, keys, ranges,
                             derived columns (adm, lcffd, local), string formats
  data/ucsd_local_data.json  structure, that it lists exactly the CSV's columns and
                             predictors, and that every cell equals the CSV within
                             the stated rounding
  index.html                 the embedded data block equals the JSON file byte for
                             byte; d3 is embedded verbatim; the page's variable list
                             names exactly the predictors in the data
  build/page_src.html        has the two placeholders assemble.py fills
  README.md                  documents exactly the CSV's columns, the row counts and
                             the period labels
"""
import json
import math
import pathlib
import re
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "school_era_rows.csv"
JSON = ROOT / "data" / "ucsd_local_data.json"
PAGE = ROOT / "index.html"
PAGE_SRC = ROOT / "build" / "page_src.html"
D3 = ROOT / "build" / "d3.v7.min.js"
README = ROOT / "README.md"

ID_COLS = ["name", "city", "ceeb", "A", "adm", "K", "grp"]
ERAS = {"base": "2015–17", "surge": "2018–21", "recent": "2022–25"}
GROUPS = ["Sweetwater Union High School District", "San Diego Unified School District", "Imperial County",
          "Poway, San Dieguito and Carlsbad districts", "Other San Diego County schools", "Rest of California"]
# rounding applied when build_data.py writes the JSON (decimals per column; 1 otherwise, adm 2)
DEC = {"adm": 2, "appgpa": 3, "gpa_gap": 3, "logA": 3, "dist": 3, "infl": 3,
       "lcffd": 0, "local": 0, "charter": 0, "H": 0, "homeval": 0}
PCT_COLS = ["adm", "ela", "math", "agcomp", "upp", "sed", "el", "s_hisp", "s_white", "s_asian", "s_black",
            "ba", "pov", "ucsd_share", "oth_rate", "o_grad6", "o_yield"]
BINARY_COLS = ["lcffd", "charter", "local"]
RACE_COLS = ["s_hisp", "s_white", "s_asian", "s_black"]
EPS = 1e-9

passed = 0
failures = []


def check(cond, msg):
    global passed
    if cond:
        passed += 1
    else:
        failures.append(msg)
        print("FAIL:", msg)


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    for p in (CSV, JSON, PAGE, PAGE_SRC, D3, README):
        check(p.exists(), f"missing file {p.relative_to(ROOT)}")
    if failures:
        return finish()

    # ------------------------------------------------------------------ CSV
    with open(CSV, encoding="utf-8", newline="") as f:
        df = pd.read_csv(f, dtype={"ceeb": str, "name": str, "city": str}, float_precision="round_trip")
    cols = list(df.columns)
    pred_cols = [c for c in cols if c not in ID_COLS + ["era"]]
    check(cols[:7] == ID_COLS, f"CSV must start with {ID_COLS}; starts with {cols[:7]}")
    check("era" in cols and "local" in cols, "CSV lacks era or local column")
    check(len(set(cols)) == len(cols), "CSV has duplicate column names")
    n = len(df)
    check(n > 0, "CSV is empty")
    check(set(df["era"].unique()) == set(ERAS), f"era codes {sorted(df['era'].unique())} != {sorted(ERAS)}")
    check(not df.duplicated(["ceeb", "era"]).any(), "duplicate (ceeb, era) keys in CSV")
    check(not df.duplicated(["name", "city", "era"]).any(), "duplicate (name, city, era) in CSV")
    check(df[["name", "city", "ceeb", "A", "adm", "K", "grp", "era", "local"]].notna().all().all(),
          "blank values in key or count columns")
    check(df["ceeb"].str.fullmatch(r"\d{6,7}").all(), "ceeb must be 6 or 7 digits as text")
    check((df["ceeb"].str.len() == 6).sum() >= 0.99 * n, "fewer than 99% of ceeb codes are 6 digits")
    check(df["ceeb"].str.startswith("0").any(), "no ceeb keeps its leading zero (was the CSV resaved as numbers?)")
    check((df["name"].str.len() <= 40).all() and (df["city"].str.len() <= 20).all(),
          "name longer than 40 or city longer than 20 characters")
    check(df["grp"].isin(range(6)).all(), "grp outside 0–5")
    for era in ERAS:
        check(set(df.loc[df["era"] == era, "grp"]) == set(range(6)), f"period {era} lacks one of the six groups")
    check((df["A"] >= 30).all(), "a row has fewer than 30 applicants")
    check(((df["K"] > 0) & (df["K"] <= df["A"])).all(), "admits must be between 1 and applicants")
    check(((df["A"] % 1 == 0) & (df["K"] % 1 == 0)).all(), "A or K not integer")
    check((df["adm"] - 100 * df["K"] / df["A"]).abs().max() < 1e-9, "adm != 100*K/A")
    check(((df["grp"] < 5).astype(float) == df["local"]).all(), "local != (grp < 5)")
    for c in PCT_COLS:
        s = df[c].dropna()
        check(((s >= 0) & (s <= 100)).all(), f"{c} outside 0–100 (min {s.min()}, max {s.max()})")
    for c in BINARY_COLS:
        check(df[c].dropna().isin([0.0, 1.0]).all(), f"{c} not 0/1")
    upp_ok = df["upp"].notna()
    check((df.loc[upp_ok, "lcffd"] == (df.loc[upp_ok, "upp"] > 75).astype(float)).all(), "lcffd != (upp > 75)")
    check((df["lcffd"].isna() == df["upp"].isna()).all(), "lcffd blank pattern differs from upp")
    race_sum = df[RACE_COLS].sum(axis=1, min_count=4)
    check((race_sum.dropna() <= 100 + 0.05 + EPS).all(),
          f"the four race shares exceed 100 (max {race_sum.max():.3f})")
    check((race_sum.dropna() >= 0).all(), "negative race share sum")
    num = df[pred_cols].select_dtypes("number")
    check(not num.isin([math.inf, -math.inf]).any().any(), "infinite value in a predictor")
    for c, lo, hi in (("inc", 0, 1000), ("homeval", 0, 5000), ("H", 0, 10000), ("appgpa", 2.5, 4.5),
                      ("logA", 0, 4), ("dist", 0, 3.1), ("apprate", 0, None), ("gpa_gap", -1, 1), ("infl", -1, 1)):
        s = df[c].dropna()
        check((s >= lo).all() and (hi is None or (s <= hi).all()),
              f"{c} outside [{lo}, {hi}] (min {s.min()}, max {s.max()})")
    check(df["apprate"].dropna().gt(0).all(), "apprate must be positive")

    # ----------------------------------------------------------------- JSON
    with open(JSON, encoding="utf-8") as f:
        raw = f.read()
    J = json.loads(raw)
    check(set(J) == {"cols", "vars", "cells", "eras", "groups"}, f"JSON keys {sorted(J)}")
    jcols, jvars = J["cols"], J["vars"]
    check(jcols[:7] == ID_COLS and jcols[7:] == jvars, "JSON cols must be the 7 id columns followed by vars")
    check(len(set(jvars)) == len(jvars), "duplicate names in JSON vars")
    check(set(jvars) == set(pred_cols), f"JSON vars differ from CSV predictors: {set(jvars) ^ set(pred_cols)}")
    check(set(jcols) == set(cols) - {"era"}, "JSON cols != CSV columns minus era")
    check(J["eras"] == ERAS, f"JSON eras {J['eras']} != {ERAS}")
    check(list(J["cells"]) == list(ERAS), f"JSON cells keys {list(J['cells'])} != {list(ERAS)}")
    check(J["groups"] == GROUPS, f"JSON groups {J['groups']}")
    exact = 0
    cell_checks = 0
    for era, rows in J["cells"].items():
        sub = df[df["era"] == era].set_index("ceeb")
        check(len(rows) == len(sub), f"{era}: JSON has {len(rows)} rows, CSV {len(sub)}")
        check(all(len(r) == len(jcols) for r in rows), f"{era}: a JSON row has the wrong length")
        ceebs = [r[2] for r in rows]
        check(len(set(ceebs)) == len(ceebs), f"{era}: duplicate ceeb in JSON")
        check(set(ceebs) == set(sub.index), f"{era}: JSON and CSV list different schools")
        bad = []
        for r in rows:
            rec = dict(zip(jcols, r))
            x = sub.loc[rec["ceeb"]]
            for c in jcols:
                v = rec[c]
                if c in ("name", "city", "ceeb"):
                    ok = isinstance(v, str) and v == (rec["ceeb"] if c == "ceeb" else x[c])
                elif c in ("A", "K", "grp"):
                    ok = isinstance(v, int) and v == int(x[c])
                else:
                    cv = x[c]
                    if pd.isna(cv):
                        ok = v is None
                    else:
                        d = DEC.get(c, 1)
                        ok = isinstance(v, (int, float)) and abs(v - float(cv)) <= 0.5 * 10 ** (-d) + EPS
                        exact += ok and v == round(float(cv), d)
                cell_checks += 1
                if not ok:
                    bad.append((rec["ceeb"], c, v, x[c]))
        check(not bad, f"{era}: {len(bad)} JSON cells differ from the CSV beyond rounding, e.g. {bad[:3]}")
    print(f"compared {cell_checks:,} JSON cells with the CSV; {exact:,} numeric cells match the rounding rule exactly")

    # ----------------------------------------------------------------- page
    html = read_text(PAGE)
    m = re.search(r'<script id="pagedata" type="application/json">(.*?)</script>', html, re.S)
    check(m is not None, "index.html has no pagedata script block")
    if m:
        embedded = m.group(1).replace("<\\/", "</")
        check(embedded == raw, "data embedded in index.html differs from data/ucsd_local_data.json")
    d3 = read_text(D3)
    check(d3 in html, "build/d3.v7.min.js is not embedded verbatim in index.html")
    check(re.search(r'version="7\.\d+\.\d+"', d3) is not None, "d3.v7.min.js does not carry a d3 version 7 string")
    src = read_text(PAGE_SRC)
    check(src.count("/*__D3__*/") == 1 and src.count("/*__DATA__*/") == 1,
          "build/page_src.html must contain /*__D3__*/ and /*__DATA__*/ exactly once each")
    for label, text in (("index.html", html), ("build/page_src.html", src)):
        mv = re.search(r"const VARS=\[(.*?)\];", text, re.S)
        check(mv is not None, f"{label}: no VARS list found")
        if mv:
            page_vars = re.findall(r"'([^']+)'", mv.group(1))
            derived = {"gpacurve", "groups"}
            check(set(page_vars) - derived == set(jvars),
                  f"{label}: page variable list minus derived terms != data vars: {(set(page_vars) - derived) ^ set(jvars)}")
            mm = re.search(r"const VMETA=\{(.*?)\n\};", text, re.S)
            check(mm is not None, f"{label}: no VMETA block")
            if mm:
                meta_keys = re.findall(r"(?:^|[\s{,])([A-Za-z_0-9]+):\['", mm.group(1), re.M)
                check(set(meta_keys) == set(page_vars), f"{label}: VMETA keys != VARS: {set(meta_keys) ^ set(page_vars)}")
        me = re.search(r"const ERAKEYS=\[(.*?)\]", text)
        check(me is not None and re.findall(r"'([^']+)'", me.group(1)) == list(ERAS), f"{label}: ERAKEYS != data eras")
        mg = re.search(r"const GSHORT=\[(.*?)\];", text)
        check(mg is not None and len(re.findall(r"'([^']*)'", mg.group(1))) == len(GROUPS), f"{label}: GSHORT length != groups")

    # --------------------------------------------------------------- README
    readme = read_text(README)
    doc_cols = re.findall(r"^\| `([A-Za-z_0-9]+)` \|", readme, re.M)
    doc_cols = [c for c in doc_cols if c not in ERAS]
    check(doc_cols == cols, f"README column table != CSV columns: order/extra/missing {set(doc_cols) ^ set(cols)} "
                            f"{'(order differs)' if set(doc_cols) == set(cols) else ''}")
    counts = {era: int(c.replace(",", "")) for era, c in re.findall(r"^\| `(base|surge|recent)` \|[^|]*\|\s*([\d,]+)\s*\|", readme, re.M)}
    actual = df["era"].value_counts().to_dict()
    check(counts == actual, f"README row counts {counts} != CSV {actual}")
    check(f"{n:,} rows" in readme, f"README does not state '{n:,} rows'")
    for era, label in ERAS.items():
        check(label in readme, f"README lacks period label {label}")
    check(f"{len(jvars)} predictor" in readme, f"README does not state {len(jvars)} predictors")
    check(f"{df['ceeb'].nunique():,} distinct schools" in readme,
          f"README does not state '{df['ceeb'].nunique():,} distinct schools'")
    local_counts = [int(df[(df['era'] == e) & (df['grp'] < 5)].shape[0]) for e in ERAS]
    check(f"hold {local_counts[0]}, {local_counts[1]} and {local_counts[2]} rows" in readme,
          f"README does not state the local-group row counts {local_counts}")
    return finish()


def finish():
    print(f"{passed} checks passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

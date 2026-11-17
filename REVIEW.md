# labunits — independent adversarial review

Reviewer: independent subagent (did not build the tool). Date: 2026-11-17.
Scope: the gauntlet was run locally; at review time nothing had been published or pushed. Documented design
decisions were not changed (unverifiable-factor analytes excluded;
insulin / enzyme / assay-dependent analytes refused, never
approximated; conversion only — no reference ranges or flagging).

## What was checked

- **Full test battery** — `python3 run_tests.py`: **29 tests, all
  passing** before fixes; **37 tests, all passing** after fixes.
- **Adversarial probes** (API + CLI, ~90 attempts): every name in the
  REFUSED table (17 names) plus case/space/hyphen variants; unknown
  and excluded analytes (`free_t3`, `dhea_s`, …); all 26 aliases;
  HbA1c affine-vs-factor behaviour; BUN vs urea in both unit pairs
  and both directions; same-system and invalid-system requests;
  missing `--from`/`--to`; `--columns`+`--spec` together and
  neither; missing file / empty file / header-only file; missing
  column; duplicate column; output-column name collision; censored
  cells (`<100`), unit-suffixed cells (`100 mg/dL`), non-numeric
  cells; empty cells; negative / `nan` / `inf` / `1_000` / `1e999`
  cells; round-trip drift for every shipped analyte (worst exact
  drift 1.1e-13 relative).
- **Independent oracle verification** — factors re-derived from
  molar masses with `factor = 10^k / MW`, computed without calling
  the tool's conversion code. All 43 shipped molar factors agree
  with their derivations within 1 % (worst: selenium 0.293 %,
  T3 0.251 %, copper 0.233 %, calcium 0.195 % — all AMA rounding).
  Spot checks against the prompt's published MWs: glucose
  10/180.156 = 0.055507 vs shipped 0.0555; cholesterol
  10/386.65 = 0.025863 vs 0.0259; creatinine 10⁴/113.12 = 88.402
  vs 88.4. The 15 non-molar factors are exact SI-prefix rescalings
  (×10, ×0.01, ×1) or the monovalent valence rule (×1) — verified
  by inspection. BUN→urea: 10/28.014 = 0.35696 vs shipped 0.357;
  BUN→urea mg/dL: 60.056/28.014 = 2.1438 vs shipped 2.14.
  HbA1c via the master equation both directions: 7.0 % →
  52.9952 mmol/mol (NGSP table: 53), 53 mmol/mol → 7.0004 %;
  6.5 % → 47.53 (table: 48, within the tool's stated tolerance).
  Published worked pairs: glucose 100 mg/dL = 5.55 mmol/L ✓;
  cholesterol 200 mg/dL = 5.17 mmol/L by the exact factor, 5.18 by
  the shipped rounded AMA factor — the README's honest-limits
  section discloses exactly this, and `labunits check` passes
  12/12 within tolerance.
- **Fresh-venv install + README demo** — a proper venv worked:
  `~/workspace/astro-tools/.venv/bin/python -m venv /tmp/lu_venv`
  (slow ensurepip, ~26 s, but succeeded; no `pip --target` fallback
  needed). `pip install` from the local tree installed
  labunits 0.1.0; the README demo command reproduced its documented
  stdout line-for-line and produced an output CSV **byte-identical**
  to the shipped `examples/labs_si.csv`; the `convert-one` glucose
  and insulin-refusal examples also match the README verbatim.
  Re-verified after the fixes below (reinstall + demo diff + check).
- **README audit** — research/educational + "Not a medical device"
  disclaimers present (top banner and Honest limits); the
  refused-analyte list and the excluded-analyte policy are present;
  honest limits are complete (rounded factors, triglyceride
  mixture caveat, stated-not-detected unit systems, one system per
  file). Grep of the whole repo for diagnosis / reference-range /
  flagging / interpretation: **none exists** — the words appear only
  in explicit negations ("no reference ranges, no flags, no
  interpretation"). Stated counts verified: 60 analytes shipped
  (58 linear + HbA1c + BUN), test count updated to 37 after fixes.

## Findings and fixes

1. **MEDIUM — invalid values were silently converted.** `float()`
   parsing accepted negative values, `nan`, `inf` and the Python
   literal `1_000`, in both CSV conversion and `convert-one`:
   glucose `-100` → `-5.55`, `nan` → `nan` were written to output
   as if they were results. *Fix:* `core.convert_value` (and the
   BUN mg/dL helpers) now refuse non-finite and negative values
   with a clean `LabunitsError`; the CLI parses cells with a strict
   decimal/scientific pattern and names the row and column.
   Scientific notation (`1e2`), whitespace-padded and leading-dot
   (`.5`) values still convert. Zero remains allowed.
2. **LOW — `--out` naming the input file silently overwrote the
   original data.** *Fix:* the CLI refuses when the resolved
   output path equals the input path; the input is left intact.
3. **LOW — `Lp(a)`, the standard clinical spelling, got a
   misleading "unknown analyte" error** instead of the specific
   Lp(a) refusal (same for `lipoprotein(a)`). *Fix:* added
   `lp(a)`, `lipoprotein(a)`, `lp_a`, bare `troponin`, and the full
   enzyme names `creatine_kinase`, `alanine_aminotransferase`,
   `aspartate_aminotransferase` to the REFUSED table.
4. **LOW — `urea_nitrogen` (the AMA table's own name for BUN) was
   "unknown".** *Fix:* added as an alias for `bun`, plus British
   spellings `haemoglobin` / `haemoglobin_a1c` as aliases.

No factor was found wrong; no shipped analyte failed verification;
HbA1c is correctly the affine master equation (factor field is
`None`, doubling % does not double mmol/mol); BUN and urea are
kept distinct with distinct factors (0.357 vs 0.1665) and the BUN
output column is labelled as urea. 8 regression tests were added
for the fixes above (29 → 37 tests, all passing).

## Not changed (by design, noted for the record)

- Cholesterol 200 mg/dL converts to 5.18 (shipped rounded AMA
  factor) vs 5.17 from the unrounded factor — disclosed in the
  README; within the check tolerance.
- Header-only CSVs error ("no data rows") rather than emitting a
  header-only output — a clean, documented-shape error, left as is.
- Formatted (6-significant-digit) round-trip of a near-zero HbA1c
  input (0.001 %) drifts 0.33 % relative — absolute error ~1e-5 on
  a physiologically impossible input; exact round-trip drift is
  ≤1.1e-13 for all analytes.

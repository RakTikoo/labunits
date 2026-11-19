# labunits

> **Research / educational tool. Not a medical device. Verify every
> converted value against your laboratory's own reporting before any
> clinical use.**

**Batch-convert whole columns of a lab-results CSV between conventional
(US) and SI units — with only the factors that could be verified
against two independent authorities, and a written refusal for
everything else.**

US labs report mass per volume (mg/dL, ng/dL). Most of the world
reports amount of substance per volume (mmol/L, µmol/L). Converting
is analyte-specific — it depends on the molecule's weight, so a
generic unit library cannot do it — and today it is mostly done one
value at a time in a web page, where the result cannot enter a
dataset. `labunits` does a whole file at once, offline, keeps the
original columns, and writes the factor it used next to every
converted column, so each number can be checked by hand.

It does conversion **only**: no reference ranges, no flagging, no
"abnormal" calls, no interpretation.

## Demo

```console
$ labunits convert examples/labs.csv \
      --columns glucose,cholesterol_total,triglycerides,creatinine,hba1c,bun,vitamin_d_25oh,sodium \
      --from conventional --to si --out examples/labs_si.csv
converted 32 values in 4 rows from examples/labs.csv
  direction : conventional -> si
  glucose (Glucose): mmol/L = mg/dL * 0.0555 -> glucose__mmol_L
  cholesterol_total (Cholesterol, total): mmol/L = mg/dL * 0.0259 -> cholesterol_total__mmol_L
  triglycerides (Triglycerides): mmol/L = mg/dL * 0.0113 -> triglycerides__mmol_L
  creatinine (Creatinine): umol/L = mg/dL * 88.4 -> creatinine__umol_L
  hba1c (Hemoglobin A1c (HbA1c)): mmol/mol = (% - 2.152) / 0.09148 -> hba1c__mmol_mol_IFCC
  bun (Blood urea nitrogen (BUN) -> urea): urea mmol/L = BUN mg/dL * 0.357 -> bun__mmol_L_urea
  vitamin_d_25oh (Vitamin D, 25-hydroxy (calcifediol)): nmol/L = ng/mL * 2.496 -> vitamin_d_25oh__nmol_L
  sodium (Sodium): mmol/L = mEq/L * 1 -> sodium__mmol_L
  output    : examples/labs_si.csv
  note      : conversion only -- no reference ranges, no flags, no interpretation.
```

Input (`examples/labs.csv`):

```csv
patient,glucose,cholesterol_total,triglycerides,creatinine,hba1c,bun,vitamin_d_25oh,sodium
P001,100,200,150,1.0,7.0,14,30,140
P002,126,240,200,1.3,6.5,20,20,138
...
```

Output (first row shown, factor columns trimmed for display — the
real file carries one `__factor` column per converted column):

```csv
patient,glucose,glucose__mmol_L,cholesterol_total,cholesterol_total__mmol_L,creatinine,creatinine__umol_L,hba1c,hba1c__mmol_mol_IFCC,bun,bun__mmol_L_urea
P001,100,5.55,200,5.18,1.0,88.4,7.0,52.9952,14,4.998
```

One value at a time:

```console
$ labunits convert-one --analyte glucose --value 100 --from conventional --to si
100 mg/dL = 5.55 mmol/L
  mmol/L = mg/dL * 0.0555
  source: AMA Manual of Style, Table 17.5-2, factor 0.0555; verified against: molar-mass derivation 10/180.156 = 0.05551
```

Ask for an analyte with no fixed factor, and this happens instead:

```console
$ labunits convert-one --analyte insulin --value 12 --from conventional --to si
error: refused: 'insulin' -- insulin is reported in biological units (uIU/mL). Published
uIU/mL -> pmol/L factors disagree (6.0, 6.945 and others are all in use) because the
conversion depends on the insulin preparation and assay standard, so there is no
single fixed factor to convert with. labunits refuses rather than pick one.
```

That refusal is the product, as much as the conversions are.

## Install

```console
$ pip install git+https://github.com/RakTikoo/labunits
```

Requires Python ≥ 3.10. **Standard library only** — no dependencies.
Everything runs offline.

## Usage

```
labunits convert FILE --columns analyte,analyte,... --from conventional|si --to si|conventional [--out FILE]
labunits convert FILE --spec spec.csv              --from conventional|si --to si|conventional [--out FILE]
labunits convert-one --analyte KEY --value N --from conventional|si --to si|conventional
labunits list
labunits check
```

- `--columns` — comma-separated analyte keys (see `labunits list`).
  Each key must also be the name of a column in the file.
- `--spec spec.csv` — for files whose column names are not the
  analyte keys: a CSV with header `analyte,column`, one row per
  conversion (see `examples/spec.csv`).
- `--from` / `--to` — **required, never guessed**, and they must
  differ. The tool knows each analyte's unit in each system; you
  state which system your file is in.
- Output: the input columns unchanged, plus, per converted column,
  a `<column>__<target unit>` column and a `<column>__factor`
  column stating the exact factor or formula used. Empty cells stay
  empty; a non-numeric, negative or non-finite cell (`nan`, `inf`,
  `1_000`, …) aborts the run with the row and column named —
  nothing is silently skipped or silently converted.
- `labunits check` re-runs 12 published worked pairs (glucose
  100 mg/dL = 5.55 mmol/L, cholesterol 200 mg/dL ≈ 5.17 mmol/L,
  HbA1c 7.0 % = 53 mmol/mol, BUN 14 mg/dL = urea 5.0 mmol/L, …)
  and reports PASS/FAIL.

## The two traps

### HbA1c is not a factor

HbA1c % (NGSP) and mmol/mol (IFCC) are two standardisations of the
same measurement, linked by the NGSP–IFCC **master equation**, not
by a multiplier:

```
mmol/mol = (% − 2.152) / 0.09148        % = 0.09148 × mmol/mol + 2.152
```

`labunits` implements the equation (both directions). Note the AMA
table gives no factor for HbA1c at all — a factor-based converter
that lists one has invented it.

### BUN and urea are different analytes

US labs report **BUN**: the mass of the *nitrogen inside* urea.
SI labs report **urea**: the *whole molecule*. One urea molecule
(60.06 g/mol) carries two nitrogen atoms (28.01 g/mol), so:

```
urea (mmol/L) = BUN (mg/dL) × 0.357      (10 / 28.014)
urea (mg/dL)  = BUN (mg/dL) × 2.14       (60.056 / 28.014)
```

A BUN of 14 mg/dL is urea 5.0 mmol/L **and** urea 30 mg/dL — both
true, in different units. Converting a `bun` column therefore
produces a column named `bun__mmol_L_urea`: the analyte name
changes on purpose. Urea reported directly in mg/dL is a separate
analyte key, `urea`, with its own factor (× 0.1665 = 10 / 60.056) —
using the BUN factor on a urea column, or vice versa, is the
classic silent error this separation exists to prevent.

## How each factor was verified

Every shipped factor passed **two** independent authorities:

1. **The AMA Manual of Style**, Table 17.5-2, "Selected Laboratory
   Tests, With Conversion Factors" (the table JAMA Network journals
   use; adapted there from Kratz et al., Young & Huth, McPherson &
   Pincus, and Laposata).
2. **An independent check**, recorded per analyte in
   `labunits/analytes.py`:
   - molar conversions: a derivation from the analyte's molar mass
     (factor = 10ᵏ / MW, molar masses as listed in PubChem compound
     records). The test suite re-derives every molar factor this
     way and fails if the shipped factor disagrees by ≥ 1 %.
   - mass/volume rescalings (g/dL → g/L, mg/dL → mg/L, …): exact SI
     prefix arithmetic, cross-checked against second published
     conversion tables (PMC "Conversion Table — Conventional to SI
     Units"; MSD Manual clinical-chemistry conversion factors;
     Cypress Diagnostics conversion table).
   - monovalent electrolytes: the valence rule (1 mEq = 1 mmol),
     cross-checked against the same tables.
   - HbA1c: the NGSP's own published master equation and table
     (7.0 % = 53 mmol/mol).
   - BUN → urea: the AMA factor 0.357, and the first-principles
     derivation 10/28 published by Higgins, "Urea and the clinical
     value of measuring blood urea concentration",
     acutecaretesting.org (Radiometer).

## What ships, and what is excluded

**Shipped: 60 analytes** — 58 with a linear factor (glucose, total /
HDL / LDL cholesterol, triglycerides, creatinine, bilirubin total
and direct, calcium total and ionized, magnesium, inorganic
phosphorus, uric acid, iron, TIBC, lactate, ethanol, urea, vitamins
D / B12 / C / A / E, folate, cortisol, testosterone, estradiol,
progesterone, total T4, free T4, total T3, acetaminophen,
salicylate, digoxin, phenytoin, valproic acid, carbamazepine,
C-peptide, homocysteine, zinc, copper, selenium, lead, albumin,
total protein, haemoglobin, CRP, fibrinogen, ferritin, prealbumin,
apolipoproteins A-I and B, IgG, sodium, potassium, chloride,
bicarbonate, lithium), plus HbA1c by master equation and BUN → urea.
Run `labunits list` for the exact table with units and factors.

**Refused in code** (the tool prints the reason and converts
nothing): insulin (published µIU/mL → pmol/L factors disagree;
preparation- and assay-dependent), the enzyme activities ALT, AST,
alkaline phosphatase, GGT, LDH, CK, amylase and lipase (activity,
not concentration; method-dependent), lipoprotein(a) (no fixed
factor — particle size varies between people; the AMA table says
the same), ammonia (reported on two bases, as N ×0.714 and as NH₃
×0.587, indistinguishable from a CSV column), transferrin (a
glycoprotein with no single molar mass), troponin I and T
(assays not standardised against each other; modern ng/L reporting),
and TSH (mIU/L in both systems — nothing to convert).

**Excluded from the table entirely** (not shipped, not refused by
name — an unknown-analyte error): every other AMA-table entry that
was not re-verified against a second authority during this build,
including most therapeutic-drug and amino-acid entries not listed
above, DHEA-S (salt forms differ), and free T3. Exclusion is the
default; an analyte ships only after its factor checks out twice.

## Honest limits

- **Factors are the published, rounded ones.** The AMA factors are
  rounded (cholesterol × 0.0259, not 0.025864…), so a converted
  value can differ in the last digit from a molar-mass-exact
  calculation, and round-tripping through a printed report is not
  bit-exact. The published worked pairs in `labunits check` show
  the size of this: cholesterol 200 mg/dL → 5.18 here, 5.17 in
  tables computed from the unrounded factor.
- **Triglycerides** are a mixture of molecules; the shipped factor
  is the published standard (standardised on triolein), not an
  exact constant for any individual sample.
- **Unit systems are stated, not detected.** If your file is
  actually in SI and you say `--from conventional`, the tool will
  convert it wrongly and the factor column will faithfully document
  the mistake. Check one known value by hand first — that is what
  the factor column is for.
- **One analyte per column, one system per file.** Mixed-unit
  files need one run per system.
- **Not a medical device.** Research/educational use. No reference
  ranges are applied and no result is interpreted. Verify before
  clinical use.

## Tests

```console
$ python3 run_tests.py
```

37 tests (stdlib `unittest`): the molar-mass re-derivation of every
shipped molar factor, round-trip identity for every shipped
analyte, the published worked pairs, HbA1c both directions plus a
not-a-factor check, the BUN ↔ urea pair in both unit pairs, every
refusal in the refused table, and CLI conversion in `--columns`
and `--spec` modes, both directions, with clean-error cases
(missing direction, missing column, non-numeric cell, negative /
`nan` / `inf` / `1_000` cells, refused analyte, `--out` naming
the input file) — all of which must fail with a one-line error and no
output file, never a traceback.

## Use with an AI agent

This repo ships a [SKILL.md](SKILL.md) written to the Agent Skills open
standard. If your coding agent supports skills, point it at this repo and
it can install labunits, run it on your CSVs, and read the results for
you. The skill works as documented when the repo is cloned under its
real name (`labunits`) — the standard matches a skill to its folder
name.

## License

MIT. Free and open source, for science.

"""The analyte table for labunits -- every factor verified twice.

Each shipped entry carries:

- ``factor``: multiply a conventional-unit value by this to get the SI
  value (divide to go back).
- ``ama``: the factor as published in the AMA Manual of Style, Table
  17.5-2, "Selected Laboratory Tests, With Conversion Factors"
  (Christiansen & Iverson, 2020; the table is adapted there from
  Kratz et al., Young & Huth, McPherson & Pincus, and Laposata).
- ``second``: the independent second authority the AMA factor was
  checked against before shipping. For molar conversions this is a
  derivation from the analyte's molar mass,

      factor = 10**mw_power / molar_mass

  (the powers encode the unit prefixes: e.g. mg/dL -> mmol/L is
  10/MW, mg/dL -> umol/L is 10**4/MW, ng/mL -> nmol/L is 10**3/MW).
  Molar masses are the standard compound values as listed in PubChem
  compound records. For pure mass/volume rescalings (g/dL -> g/L etc.)
  the second authority is exact SI prefix arithmetic, cross-checked
  against a second published conversion table (PMC "Conversion Table
  -- Conventional to SI Units"; MSD Veterinary Manual Clinical
  Chemistry SI Conversion Factors; Cypress Diagnostics conversion
  table). For monovalent electrolytes it is the valence rule
  (1 mEq = 1 mmol for a monovalent ion), again cross-checked against
  those tables.
- ``molar_mass`` / ``mw_power``: present for molar entries so the test
  suite can re-derive the factor from the molar mass and assert the
  shipped (AMA, rounded) factor agrees within 1%.

An analyte whose AMA factor could NOT be reconciled with a second
authority is not in this table at all -- it is in REFUSED below, or
listed as excluded in the README. Shipping an unverified factor is
the one failure this tool must never have.

Special (non-linear / analyte-changing) conversions live in core.py,
not here: HbA1c (NGSP<->IFCC master equation) and BUN -> urea.
"""

from __future__ import annotations

# key, display name, conventional unit, SI unit, AMA factor,
# molar_mass (g/mol) or None, mw_power or None, second-authority note
_ROWS = [
    # --- routine chemistry, molar -------------------------------------
    ("glucose", "Glucose", "mg/dL", "mmol/L", 0.0555, 180.156, 1,
     "molar-mass derivation 10/180.156 = 0.05551"),
    ("cholesterol_total", "Cholesterol, total", "mg/dL", "mmol/L",
     0.0259, 386.654, 1, "molar-mass derivation 10/386.654 = 0.02586"),
    ("cholesterol_hdl", "Cholesterol, HDL", "mg/dL", "mmol/L",
     0.0259, 386.654, 1, "same molecule as total cholesterol: 10/386.654 = 0.02586"),
    ("cholesterol_ldl", "Cholesterol, LDL", "mg/dL", "mmol/L",
     0.0259, 386.654, 1, "same molecule as total cholesterol: 10/386.654 = 0.02586"),
    ("triglycerides", "Triglycerides", "mg/dL", "mmol/L",
     0.0113, 885.43, 1,
     "standardised on triolein, molar-mass derivation 10/885.43 = 0.01129; "
     "also 0.01129 in published clinical-chemistry tables. Triglycerides "
     "are a mixture, so this is the published standard factor, not an "
     "exact per-sample constant"),
    ("creatinine", "Creatinine", "mg/dL", "umol/L", 88.4, 113.12, 4,
     "molar-mass derivation 10^4/113.12 = 88.40"),
    ("bilirubin_total", "Bilirubin, total", "mg/dL", "umol/L",
     17.104, 584.66, 4, "molar-mass derivation 10^4/584.66 = 17.104"),
    ("bilirubin_direct", "Bilirubin, direct (conjugated)", "mg/dL",
     "umol/L", 17.104, 584.66, 4,
     "molar-mass derivation 10^4/584.66 = 17.104"),
    ("calcium_total", "Calcium, total", "mg/dL", "mmol/L",
     0.25, 40.078, 1,
     "molar-mass derivation 10/40.078 = 0.2495 (AMA rounds to 0.25); "
     "second published tables give 0.2495-0.25"),
    ("calcium_ionized", "Calcium, ionized", "mg/dL", "mmol/L",
     0.25, 40.078, 1,
     "same ion as total calcium: 10/40.078 = 0.2495 (AMA rounds to 0.25)"),
    ("magnesium", "Magnesium", "mg/dL", "mmol/L", 0.4114, 24.305, 1,
     "molar-mass derivation 10/24.305 = 0.41144"),
    ("phosphorus_inorganic", "Phosphorus, inorganic (as P)", "mg/dL",
     "mmol/L", 0.323, 30.974, 1,
     "molar-mass derivation (elemental P) 10/30.974 = 0.32287"),
    ("uric_acid", "Uric acid", "mg/dL", "mmol/L", 0.0595, 168.11, 1,
     "molar-mass derivation 10/168.11 = 0.05948"),
    ("iron", "Iron", "ug/dL", "umol/L", 0.179, 55.845, 1,
     "molar-mass derivation 10/55.845 = 0.17907"),
    ("iron_binding_capacity", "Iron-binding capacity (TIBC)", "ug/dL",
     "umol/L", 0.179, 55.845, 1,
     "reported as iron equivalents: 10/55.845 = 0.17907"),
    ("lactate", "Lactate (as lactic acid)", "mg/dL", "mmol/L",
     0.111, 90.08, 1, "molar-mass derivation 10/90.08 = 0.11101"),
    ("ethanol", "Ethanol", "mg/dL", "mmol/L", 0.2171, 46.068, 1,
     "molar-mass derivation 10/46.068 = 0.21707"),
    ("urea", "Urea (whole molecule)", "mg/dL", "mmol/L",
     0.1665, 60.056, 1,
     "molar-mass derivation 10/60.056 = 0.16651; Cypress Diagnostics "
     "conversion table gives 0.1668 (rounding). NOT in the AMA table "
     "under this name -- AMA lists urea *nitrogen* instead; see bun. "
     "Urea and BUN are different analytes: see README"),
    # --- vitamins, hormones, therapeutic drugs, molar -----------------
    ("vitamin_d_25oh", "Vitamin D, 25-hydroxy (calcifediol)", "ng/mL",
     "nmol/L", 2.496, 400.64, 3,
     "molar-mass derivation 10^3/400.64 = 2.4960"),
    ("vitamin_b12", "Vitamin B12 (cyanocobalamin)", "pg/mL", "pmol/L",
     0.7378, 1355.37, 3, "molar-mass derivation 10^3/1355.37 = 0.73779"),
    ("folate", "Folate (folic acid)", "ng/mL", "nmol/L",
     2.266, 441.40, 3, "molar-mass derivation 10^3/441.40 = 2.2655"),
    ("vitamin_c", "Vitamin C (ascorbic acid)", "mg/dL", "umol/L",
     56.78, 176.12, 4, "molar-mass derivation 10^4/176.12 = 56.780"),
    ("vitamin_a", "Vitamin A (retinol)", "ug/dL", "umol/L",
     0.0349, 286.45, 1, "molar-mass derivation 10/286.45 = 0.034910"),
    ("vitamin_e", "Vitamin E (alpha-tocopherol)", "ug/mL", "umol/L",
     2.322, 430.71, 3, "molar-mass derivation 10^3/430.71 = 2.3218"),
    ("cortisol", "Cortisol", "ug/dL", "nmol/L", 27.588, 362.46, 4,
     "molar-mass derivation 10^4/362.46 = 27.589"),
    ("testosterone", "Testosterone, total", "ng/dL", "nmol/L",
     0.0347, 288.42, 1, "molar-mass derivation 10/288.42 = 0.034671"),
    ("estradiol", "Estradiol (E2)", "pg/mL", "pmol/L",
     3.671, 272.38, 3, "molar-mass derivation 10^3/272.38 = 3.6713"),
    ("progesterone", "Progesterone", "ng/mL", "nmol/L",
     3.18, 314.46, 3, "molar-mass derivation 10^3/314.46 = 3.1801"),
    ("thyroxine_total", "Thyroxine, total (T4)", "ug/dL", "nmol/L",
     12.87, 776.87, 4, "molar-mass derivation 10^4/776.87 = 12.872"),
    ("thyroxine_free", "Thyroxine, free (FT4)", "ng/dL", "pmol/L",
     12.87, 776.87, 4, "molar-mass derivation 10^4/776.87 = 12.872"),
    ("triiodothyronine_total", "Triiodothyronine, total (T3)", "ng/dL",
     "nmol/L", 0.0154, 650.98, 1,
     "molar-mass derivation 10/650.98 = 0.015362 (AMA rounds to 0.0154)"),
    ("acetaminophen", "Acetaminophen (paracetamol)", "ug/mL", "umol/L",
     6.614, 151.16, 3, "molar-mass derivation 10^3/151.16 = 6.6155"),
    ("salicylate", "Salicylate (as salicylic acid)", "ug/mL", "umol/L",
     7.24, 138.12, 3, "molar-mass derivation 10^3/138.12 = 7.2406"),
    ("digoxin", "Digoxin", "ng/mL", "nmol/L", 1.281, 780.95, 3,
     "molar-mass derivation 10^3/780.95 = 1.2805"),
    ("phenytoin", "Phenytoin", "mg/L", "umol/L", 3.968, 252.27, 3,
     "molar-mass derivation 10^3/252.27 = 3.9640 (agrees with AMA "
     "3.968 within 0.11%)"),
    ("valproic_acid", "Valproic acid", "ug/mL", "umol/L",
     6.934, 144.21, 3, "molar-mass derivation 10^3/144.21 = 6.9343"),
    ("carbamazepine", "Carbamazepine", "ug/mL", "umol/L",
     4.233, 236.27, 3, "molar-mass derivation 10^3/236.27 = 4.2325"),
    ("c_peptide", "C-peptide", "ng/mL", "nmol/L", 0.331, 3020.29, 3,
     "molar-mass derivation 10^3/3020.29 = 0.33109"),
    ("homocysteine", "Homocysteine", "mg/L", "umol/L",
     7.397, 135.18, 3, "molar-mass derivation 10^3/135.18 = 7.3977"),
    # --- trace elements, molar ----------------------------------------
    ("zinc", "Zinc", "ug/dL", "umol/L", 0.153, 65.38, 1,
     "molar-mass derivation 10/65.38 = 0.15295"),
    ("copper", "Copper", "ug/dL", "umol/L", 0.157, 63.546, 1,
     "molar-mass derivation 10/63.546 = 0.15737"),
    ("selenium", "Selenium", "ug/L", "umol/L", 0.0127, 78.971, 0,
     "molar-mass derivation 1/78.971 = 0.012663 (AMA rounds to 0.0127)"),
    ("lead", "Lead", "ug/dL", "umol/L", 0.0483, 207.2, 1,
     "molar-mass derivation 10/207.2 = 0.048263"),
    # --- pure mass/volume rescalings (exact SI prefix arithmetic) -----
    ("albumin", "Albumin", "g/dL", "g/L", 10.0, None, None,
     "exact prefix arithmetic (1 g/dL = 10 g/L); second published tables agree (x10)"),
    ("protein_total", "Protein, total", "g/dL", "g/L", 10.0, None, None,
     "exact prefix arithmetic (1 g/dL = 10 g/L); second published tables agree (x10)"),
    ("hemoglobin", "Hemoglobin", "g/dL", "g/L", 10.0, None, None,
     "exact prefix arithmetic (1 g/dL = 10 g/L)"),
    ("crp", "C-reactive protein", "mg/dL", "mg/L", 10.0, None, None,
     "exact prefix arithmetic (1 mg/dL = 10 mg/L)"),
    ("fibrinogen", "Fibrinogen", "mg/dL", "g/L", 0.01, None, None,
     "exact prefix arithmetic (1 mg/dL = 0.01 g/L)"),
    ("ferritin", "Ferritin", "ng/mL", "ug/L", 1.0, None, None,
     "exact prefix arithmetic (1 ng/mL = 1 ug/L)"),
    ("prealbumin", "Prealbumin (transthyretin)", "mg/dL", "mg/L",
     10.0, None, None,
     "exact prefix arithmetic (1 mg/dL = 10 mg/L)"),
    ("apolipoprotein_a1", "Apolipoprotein A-I", "mg/dL", "g/L",
     0.01, None, None,
     "exact prefix arithmetic (1 mg/dL = 0.01 g/L)"),
    ("apolipoprotein_b", "Apolipoprotein B", "mg/dL", "g/L",
     0.01, None, None,
     "exact prefix arithmetic (1 mg/dL = 0.01 g/L)"),
    ("immunoglobulin_g", "Immunoglobulin G (IgG)", "mg/dL", "g/L",
     0.01, None, None,
     "exact prefix arithmetic (1 mg/dL = 0.01 g/L)"),
    # --- electrolytes: mEq/L -> mmol/L by valence ----------------------
    ("sodium", "Sodium", "mEq/L", "mmol/L", 1.0, None, None,
     "valence rule: Na+ is monovalent, 1 mEq/L = 1 mmol/L; second published tables agree (x1)"),
    ("potassium", "Potassium", "mEq/L", "mmol/L", 1.0, None, None,
     "valence rule: K+ is monovalent, 1 mEq/L = 1 mmol/L; second published tables agree (x1)"),
    ("chloride", "Chloride", "mEq/L", "mmol/L", 1.0, None, None,
     "valence rule: Cl- is monovalent, 1 mEq/L = 1 mmol/L; second published tables agree (x1)"),
    ("bicarbonate", "Bicarbonate / total CO2", "mEq/L", "mmol/L",
     1.0, None, None,
     "valence rule: HCO3- is monovalent, 1 mEq/L = 1 mmol/L (AMA lists both bicarbonate and total CO2 at 1.0)"),
    ("lithium", "Lithium", "mEq/L", "mmol/L", 1.0, None, None,
     "valence rule: Li+ is monovalent, 1 mEq/L = 1 mmol/L"),
]

ANALYTES = {
    key: {
        "key": key, "name": name, "conv_unit": conv, "si_unit": si,
        "factor": factor, "molar_mass": mw, "mw_power": power,
        "second": second,
        "ama": ("AMA Manual of Style, Table 17.5-2, factor "
                f"{factor:g}" if key != "urea" else
                "not listed under this name in AMA Table 17.5-2 "
                "(AMA lists urea nitrogen, factor 0.357 -- see bun)"),
    }
    for key, name, conv, si, factor, mw, power, second in _ROWS
}

# Analytes this tool REFUSES, with the reason printed to the user.
# Refusing is a feature: none of these has one fixed, assay-independent
# factor, so any number the tool printed would be a guess.
REFUSED = {
    "insulin": (
        "insulin is reported in biological units (uIU/mL). Published "
        "uIU/mL -> pmol/L factors disagree (6.0, 6.945 and others are "
        "all in use) because the conversion depends on the insulin "
        "preparation and assay standard, so there is no single fixed "
        "factor to convert with. labunits refuses rather than pick one."),
    "alt": ("ALT is an enzyme activity (U/L), not a concentration. "
            "Activity depends on the assay method and conditions, so "
            "labunits does not convert enzyme activities."),
    "ast": ("AST is an enzyme activity (U/L), not a concentration. "
            "Activity depends on the assay method and conditions, so "
            "labunits does not convert enzyme activities."),
    "alp": ("alkaline phosphatase is an enzyme activity (U/L), not a "
            "concentration. Activity depends on the assay method and "
            "conditions, so labunits does not convert enzyme activities."),
    "alkaline_phosphatase": (
        "alkaline phosphatase is an enzyme activity (U/L), not a "
        "concentration. Activity depends on the assay method and "
        "conditions, so labunits does not convert enzyme activities."),
    "ggt": ("GGT is an enzyme activity (U/L), not a concentration. "
            "Activity depends on the assay method and conditions, so "
            "labunits does not convert enzyme activities."),
    "ldh": ("LDH is an enzyme activity (U/L), not a concentration. "
            "Activity depends on the assay method and conditions, so "
            "labunits does not convert enzyme activities."),
    "ck": ("creatine kinase is an enzyme activity (U/L), not a "
           "concentration. Activity depends on the assay method and "
           "conditions, so labunits does not convert enzyme activities."),
    "amylase": ("amylase is an enzyme activity (U/L), not a "
                "concentration. Activity depends on the assay method "
                "and conditions, so labunits does not convert enzyme "
                "activities."),
    "lipase": ("lipase is an enzyme activity (U/L), not a "
               "concentration. Activity depends on the assay method "
               "and conditions, so labunits does not convert enzyme "
               "activities."),
    "lpa": ("lipoprotein(a) has NO fixed mg/dL <-> nmol/L factor: "
            "Lp(a) particle size (apo(a) isoform) varies between "
            "people, so the mass-to-particle ratio varies too. The AMA "
            "table itself flags Lp(a) conversion as not possible "
            "without knowing the individual's particle size. Use the "
            "cut-offs published for the unit your lab reported."),
    "lipoprotein_a": (
        "lipoprotein(a) has NO fixed mg/dL <-> nmol/L factor: Lp(a) "
        "particle size varies between people, so the mass-to-particle "
        "ratio varies too. Use the cut-offs published for the unit "
        "your lab reported."),
    "lp(a)": (
        "lipoprotein(a) has NO fixed mg/dL <-> nmol/L factor: Lp(a) "
        "particle size varies between people, so the mass-to-particle "
        "ratio varies too. Use the cut-offs published for the unit "
        "your lab reported."),
    "lipoprotein(a)": (
        "lipoprotein(a) has NO fixed mg/dL <-> nmol/L factor: Lp(a) "
        "particle size varies between people, so the mass-to-particle "
        "ratio varies too. Use the cut-offs published for the unit "
        "your lab reported."),
    "lp_a": (
        "lipoprotein(a) has NO fixed mg/dL <-> nmol/L factor: Lp(a) "
        "particle size varies between people, so the mass-to-particle "
        "ratio varies too. Use the cut-offs published for the unit "
        "your lab reported."),
    "troponin": (
        "troponin assays are not standardised against each other "
        "and modern reporting is in ng/L; there is no assay-independent "
        "fixed factor, so labunits refuses."),
    "creatine_kinase": (
        "creatine kinase is an enzyme activity (U/L), not a "
        "concentration. Activity depends on the assay method and "
        "conditions, so labunits does not convert enzyme activities."),
    "alanine_aminotransferase": (
        "alanine aminotransferase (ALT) is an enzyme activity (U/L), "
        "not a concentration. Activity depends on the assay method "
        "and conditions, so labunits does not convert enzyme "
        "activities."),
    "aspartate_aminotransferase": (
        "aspartate aminotransferase (AST) is an enzyme activity "
        "(U/L), not a concentration. Activity depends on the assay "
        "method and conditions, so labunits does not convert enzyme "
        "activities."),
    "ammonia": (
        "ammonia is reported on two different bases -- as nitrogen "
        "(AMA factor 0.714 from ug/dL) and as NH3 (factor 0.587) -- "
        "and labunits cannot tell from a CSV column which basis a "
        "value uses. Guessing would risk a 20% error, so it refuses."),
    "transferrin": (
        "transferrin is a glycoprotein with variable glycosylation, "
        "so it has no single molar mass and no exact molar factor; "
        "published factors are approximations labunits will not ship."),
    "troponin_i": (
        "troponin I assays are not standardised against each other "
        "and modern reporting is in ng/L; there is no assay-independent "
        "fixed factor, so labunits refuses."),
    "troponin_t": (
        "troponin T modern reporting is in ng/L with assay-specific "
        "scales; there is no assay-independent fixed factor, so "
        "labunits refuses."),
    "tsh": ("TSH is reported in mIU/L in both conventional and SI "
            "practice -- there is no unit conversion to do, and TSH "
            "assays are standardised, not converted."),
}

# Aliases accepted in --columns / spec files, mapped to canonical keys.
ALIASES = {
    "cholesterol": "cholesterol_total",
    "hdl": "cholesterol_hdl",
    "ldl": "cholesterol_ldl",
    "tg": "triglycerides",
    "scr": "creatinine",
    "bilirubin": "bilirubin_total",
    "calcium": "calcium_total",
    "phosphorus": "phosphorus_inorganic",
    "phosphate": "phosphorus_inorganic",
    "tibc": "iron_binding_capacity",
    "vitamin_d": "vitamin_d_25oh",
    "25ohd": "vitamin_d_25oh",
    "b12": "vitamin_b12",
    "vitamin_b_12": "vitamin_b12",
    "t4_total": "thyroxine_total",
    "ft4": "thyroxine_free",
    "t3_total": "triiodothyronine_total",
    "total_protein": "protein_total",
    "igg": "immunoglobulin_g",
    "apo_a1": "apolipoprotein_a1",
    "apo_b": "apolipoprotein_b",
    "hco3": "bicarbonate",
    "co2_total": "bicarbonate",
    "a1c": "hba1c",
    "hemoglobin_a1c": "hba1c",
    "haemoglobin_a1c": "hba1c",
    "haemoglobin": "hemoglobin",
    "blood_urea_nitrogen": "bun",
    "urea_nitrogen": "bun",
}
